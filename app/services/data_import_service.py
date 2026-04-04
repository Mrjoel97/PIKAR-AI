# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""DataImportService — CSV import pipeline with AI column mapping and validation.

Provides: parse CSV bytes into polars DataFrame, AI-suggested column mappings
via Gemini Flash, per-row validation against target table schemas, preview of
mapped data, and batched commit with progress callback for SSE streaming.
"""

from __future__ import annotations

import io
import json
import logging
import re
from collections.abc import Callable
from typing import Any

import polars as pl

from app.services.supabase import get_service_client
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB
COMMIT_BATCH_SIZE = 100

# ---------------------------------------------------------------------------
# Table schemas — required columns, types, enum values, FK references
# ---------------------------------------------------------------------------

IMPORTABLE_TABLES: dict[str, dict[str, Any]] = {
    "contacts": {
        "label": "Contacts",
        "required": ["name"],
        "columns": {
            "name": {"type": "text"},
            "email": {"type": "text"},
            "phone": {"type": "text"},
            "company": {"type": "text"},
            "lifecycle_stage": {
                "type": "enum",
                "values": [
                    "lead",
                    "qualified",
                    "opportunity",
                    "customer",
                    "churned",
                    "inactive",
                ],
            },
            "source": {
                "type": "enum",
                "values": [
                    "form_submission",
                    "stripe_payment",
                    "manual",
                    "import",
                    "referral",
                    "social",
                    "other",
                ],
            },
            "estimated_value": {"type": "numeric"},
            "notes": {"type": "text"},
        },
    },
    "financial_records": {
        "label": "Financial Records",
        "required": ["amount"],
        "columns": {
            "transaction_type": {"type": "text"},
            "amount": {"type": "numeric", "min": 0},
            "currency": {"type": "text"},
            "category": {"type": "text"},
            "description": {"type": "text"},
            "date": {"type": "date"},
        },
    },
    "department_tasks": {
        "label": "Tasks",
        "required": ["title"],
        "columns": {
            "title": {"type": "text"},
            "description": {"type": "text"},
            "status": {"type": "text"},
            "priority": {"type": "text"},
            "due_date": {"type": "date"},
        },
    },
    "initiatives": {
        "label": "Initiatives",
        "required": ["title"],
        "columns": {
            "title": {"type": "text"},
            "description": {"type": "text"},
            "priority": {"type": "text"},
            "status": {"type": "text"},
            "progress": {"type": "integer", "min": 0, "max": 100},
        },
    },
    "content_bundles": {
        "label": "Content Bundles",
        "required": ["title"],
        "columns": {
            "source": {"type": "text"},
            "title": {"type": "text"},
            "prompt": {"type": "text"},
            "bundle_type": {
                "type": "enum",
                "values": [
                    "social",
                    "blog",
                    "email",
                    "ad",
                    "video",
                    "general",
                ],
            },
            "status": {
                "type": "enum",
                "values": ["draft", "scheduled", "published", "archived"],
            },
        },
    },
    "support_tickets": {
        "label": "Support Tickets",
        "required": ["subject"],
        "columns": {
            "subject": {"type": "text"},
            "description": {"type": "text"},
            "customer_email": {"type": "text"},
            "priority": {"type": "text"},
            "status": {"type": "text"},
        },
    },
    "recruitment_candidates": {
        "label": "Candidates",
        "required": ["name"],
        "columns": {
            "name": {"type": "text"},
            "email": {"type": "text"},
            "status": {"type": "text"},
            "position": {"type": "text"},
            "notes": {"type": "text"},
        },
    },
    "compliance_risks": {
        "label": "Compliance Risks",
        "required": ["title"],
        "columns": {
            "title": {"type": "text"},
            "description": {"type": "text"},
            "severity": {"type": "text"},
            "status": {"type": "text"},
        },
    },
    "compliance_audits": {
        "label": "Compliance Audits",
        "required": ["title"],
        "columns": {
            "title": {"type": "text"},
            "scope": {"type": "text"},
            "auditor": {"type": "text"},
            "scheduled_date": {"type": "date"},
            "status": {"type": "text"},
        },
    },
}


class DataImportService:
    """CSV import pipeline: parse, map, validate, preview, commit.

    Args:
        user_id: Authenticated user's UUID for RLS-scoped operations.
    """

    def __init__(self, user_id: str) -> None:
        self._user_id = user_id
        self._admin_client = get_service_client()

    # ------------------------------------------------------------------
    # Parse
    # ------------------------------------------------------------------

    def parse_csv(self, csv_bytes: bytes) -> pl.DataFrame:
        """Parse raw CSV bytes into a polars DataFrame.

        Args:
            csv_bytes: Raw bytes of the uploaded CSV file.

        Returns:
            Parsed DataFrame with detected column headers.

        Raises:
            ValueError: If file exceeds 50 MB limit.
        """
        if len(csv_bytes) > MAX_FILE_SIZE_BYTES:
            msg = f"File size exceeds 50 MB limit ({len(csv_bytes)} bytes)"
            raise ValueError(msg)

        return pl.read_csv(
            io.BytesIO(csv_bytes),
            has_header=True,
            try_parse_dates=True,
            truncate_ragged_lines=True,
            encoding="utf8-lossy",
        )

    # ------------------------------------------------------------------
    # AI Column Mapping
    # ------------------------------------------------------------------

    async def suggest_mappings(
        self,
        df: pl.DataFrame,
        target_table: str,
    ) -> dict[str, str]:
        """Suggest column mappings from CSV headers to target table columns.

        First checks for a saved mapping for this user + table. If none found,
        calls Gemini Flash for AI-suggested mappings.

        Args:
            df: Parsed CSV DataFrame.
            target_table: Target table name (e.g. ``contacts``).

        Returns:
            Dict mapping CSV column names to target table column names.
        """
        # Try saved mapping first
        saved = await self.load_column_mapping(target_table)
        if saved:
            # Only return saved mapping if all CSV columns are covered
            csv_cols = set(df.columns)
            saved_cols = set(saved.keys())
            if csv_cols.issubset(saved_cols):
                return saved

        schema = IMPORTABLE_TABLES.get(target_table, {})
        target_columns = list(schema.get("columns", {}).keys())

        return await self._call_gemini_for_mapping(
            csv_headers=df.columns,
            target_columns=target_columns,
            target_table=target_table,
        )

    async def _call_gemini_for_mapping(
        self,
        csv_headers: list[str],
        target_columns: list[str],
        target_table: str,
    ) -> dict[str, str]:
        """Call Gemini Flash to suggest column mappings.

        Returns:
            Dict mapping CSV column names to target column names.
        """
        try:
            from google import genai
            from google.genai.types import GenerateContentConfig

            client = genai.Client()
            prompt = (
                f"Map these CSV column headers to the target database columns.\n"
                f"CSV headers: {csv_headers}\n"
                f"Target table '{target_table}' columns: {target_columns}\n\n"
                f"Return ONLY a JSON object mapping each CSV header to the best "
                f"matching target column. If a CSV header has no good match, map "
                f"it to null. Example: {{\"CSV Header\": \"target_column\"}}\n"
                f"Return ONLY valid JSON, no markdown formatting."
            )

            response = await client.aio.models.generate_content(
                model="gemini-2.0-flash-001",
                contents=prompt,
                config=GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=1024,
                ),
            )

            text = response.text.strip()
            # Strip markdown code fences if present
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
            mapping = json.loads(text)

            # Filter out null mappings
            return {k: v for k, v in mapping.items() if v is not None}

        except Exception:
            logger.exception("AI column mapping failed, falling back to exact matches")
            # Fallback: exact name matches
            return {
                h: h for h in csv_headers if h in target_columns
            }

    # ------------------------------------------------------------------
    # Column Mapping Persistence
    # ------------------------------------------------------------------

    async def save_column_mapping(
        self, table_name: str, mapping: dict[str, str]
    ) -> None:
        """Save a successful column mapping for repeat imports.

        Args:
            table_name: Target table name.
            mapping: Column mapping dict.
        """
        await execute_async(
            self._admin_client.table("csv_column_mappings").upsert(
                {
                    "user_id": self._user_id,
                    "table_name": table_name,
                    "mapping": mapping,
                },
                on_conflict="user_id,table_name",
            ),
            op_name="data_import.save_mapping",
        )

    async def load_column_mapping(
        self, table_name: str
    ) -> dict[str, str] | None:
        """Load a previously saved column mapping.

        Args:
            table_name: Target table name.

        Returns:
            Saved mapping dict or ``None`` if not found.
        """
        result = await execute_async(
            self._admin_client.table("csv_column_mappings")
            .select("mapping")
            .eq("user_id", self._user_id)
            .eq("table_name", table_name)
            .limit(1),
            op_name="data_import.load_mapping",
        )
        if result.data:
            return result.data[0]["mapping"]
        return None

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(
        self,
        df: pl.DataFrame,
        column_mapping: dict[str, str],
        target_table: str,
    ) -> list[dict[str, Any]]:
        """Validate DataFrame rows against the target table schema.

        Args:
            df: Parsed CSV DataFrame.
            column_mapping: Dict mapping CSV columns to target columns.
            target_table: Target table name.

        Returns:
            List of error dicts: ``{row, column, value, reason}``.
        """
        schema = IMPORTABLE_TABLES.get(target_table)
        if not schema:
            return [{"row": 0, "column": "", "value": "", "reason": f"Unknown table: {target_table}"}]

        errors: list[dict[str, Any]] = []
        required_cols = set(schema.get("required", []))
        col_defs = schema.get("columns", {})

        # Reverse mapping: target_col -> csv_col
        reverse_map = {v: k for k, v in column_mapping.items()}

        for row_idx in range(len(df)):
            # Check required fields
            for req_col in required_cols:
                csv_col = reverse_map.get(req_col)
                if csv_col is None:
                    # Required column not mapped
                    errors.append({
                        "row": row_idx + 1,
                        "column": req_col,
                        "value": None,
                        "reason": f"Required column '{req_col}' is not mapped from CSV",
                    })
                    continue

                val = df[csv_col][row_idx]
                if val is None or (isinstance(val, str) and not val.strip()):
                    errors.append({
                        "row": row_idx + 1,
                        "column": req_col,
                        "value": val,
                        "reason": f"Required field '{req_col}' is empty",
                    })

            # Check types and enums for mapped columns
            for csv_col, target_col in column_mapping.items():
                if target_col not in col_defs:
                    continue

                col_def = col_defs[target_col]
                val = df[csv_col][row_idx]

                if val is None or (isinstance(val, str) and not val.strip()):
                    continue  # Skip None/empty for non-required columns

                # Enum check
                if col_def["type"] == "enum":
                    valid_values = col_def["values"]
                    str_val = str(val).strip().lower()
                    if str_val not in valid_values:
                        errors.append({
                            "row": row_idx + 1,
                            "column": target_col,
                            "value": str(val),
                            "reason": (
                                f"Invalid value '{val}' for '{target_col}'. "
                                f"Valid options: {', '.join(valid_values)}"
                            ),
                        })

                # Numeric check
                elif col_def["type"] == "numeric":
                    try:
                        num_val = float(val)
                        if "min" in col_def and num_val < col_def["min"]:
                            errors.append({
                                "row": row_idx + 1,
                                "column": target_col,
                                "value": str(val),
                                "reason": f"Value {num_val} below minimum {col_def['min']}",
                            })
                    except (ValueError, TypeError):
                        errors.append({
                            "row": row_idx + 1,
                            "column": target_col,
                            "value": str(val),
                            "reason": f"Expected numeric value for '{target_col}', got '{val}'",
                        })

                # Integer check
                elif col_def["type"] == "integer":
                    try:
                        int_val = int(val)
                        if "min" in col_def and int_val < col_def["min"]:
                            errors.append({
                                "row": row_idx + 1,
                                "column": target_col,
                                "value": str(val),
                                "reason": f"Value {int_val} below minimum {col_def['min']}",
                            })
                        if "max" in col_def and int_val > col_def["max"]:
                            errors.append({
                                "row": row_idx + 1,
                                "column": target_col,
                                "value": str(val),
                                "reason": f"Value {int_val} above maximum {col_def['max']}",
                            })
                    except (ValueError, TypeError):
                        errors.append({
                            "row": row_idx + 1,
                            "column": target_col,
                            "value": str(val),
                            "reason": f"Expected integer value for '{target_col}', got '{val}'",
                        })

        return errors

    # ------------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------------

    def preview(
        self,
        df: pl.DataFrame,
        column_mapping: dict[str, str],
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Return the first N rows mapped to target column names.

        Args:
            df: Parsed DataFrame.
            column_mapping: CSV -> target column mapping.
            limit: Max rows to return (default 10).

        Returns:
            List of dicts with target column names as keys.
        """
        preview_df = df.head(limit)
        rows: list[dict[str, Any]] = []

        for row_idx in range(len(preview_df)):
            row_dict: dict[str, Any] = {}
            for csv_col, target_col in column_mapping.items():
                if csv_col in preview_df.columns:
                    row_dict[target_col] = preview_df[csv_col][row_idx]
            rows.append(row_dict)

        return rows

    # ------------------------------------------------------------------
    # Commit
    # ------------------------------------------------------------------

    async def commit(
        self,
        df: pl.DataFrame,
        column_mapping: dict[str, str],
        target_table: str,
        on_duplicate: str = "skip",
        progress_callback: Callable[[float], None] | None = None,
    ) -> dict[str, Any]:
        """Insert mapped rows into the target table in batches.

        Args:
            df: Parsed DataFrame.
            column_mapping: CSV -> target column mapping.
            target_table: Target Supabase table name.
            on_duplicate: ``skip`` or ``update`` behaviour on unique constraint violations.
            progress_callback: Called with percentage (0-100) after each batch.

        Returns:
            Dict: ``{imported_count, skipped_count, errors}``.
        """
        total_rows = len(df)
        imported = 0
        skipped = 0
        errors: list[dict[str, Any]] = []

        # Build row dicts
        all_rows: list[dict[str, Any]] = []
        for row_idx in range(total_rows):
            row_dict: dict[str, Any] = {"user_id": self._user_id}
            for csv_col, target_col in column_mapping.items():
                if csv_col in df.columns:
                    val = df[csv_col][row_idx]
                    # Convert polars types to Python native
                    if hasattr(val, "item"):
                        val = val.item()
                    row_dict[target_col] = val
            all_rows.append(row_dict)

        # Batch insert
        for batch_start in range(0, total_rows, COMMIT_BATCH_SIZE):
            batch_end = min(batch_start + COMMIT_BATCH_SIZE, total_rows)
            batch = all_rows[batch_start:batch_end]

            try:
                if on_duplicate == "update" and target_table == "contacts":
                    await execute_async(
                        self._admin_client.table(target_table).upsert(
                            batch, on_conflict="user_id,email"
                        ),
                        op_name=f"data_import.commit.{target_table}",
                    )
                else:
                    await execute_async(
                        self._admin_client.table(target_table).insert(batch),
                        op_name=f"data_import.commit.{target_table}",
                    )
                imported += len(batch)
            except Exception as exc:
                logger.warning(
                    "Batch insert error at rows %d-%d: %s",
                    batch_start,
                    batch_end,
                    exc,
                )
                if on_duplicate == "skip":
                    # Try inserting one-by-one to skip just the duplicates
                    for _i, row in enumerate(batch):
                        try:
                            await execute_async(
                                self._admin_client.table(target_table).insert(row),
                                op_name=f"data_import.commit_single.{target_table}",
                            )
                            imported += 1
                        except Exception:
                            skipped += 1
                else:
                    skipped += len(batch)
                    errors.append({
                        "row": batch_start + 1,
                        "column": "",
                        "value": "",
                        "reason": f"Batch insert failed: {exc!s}",
                    })

            if progress_callback:
                pct = min(100.0, (batch_end / total_rows) * 100)
                progress_callback(pct)

        return {
            "imported_count": imported,
            "skipped_count": skipped,
            "errors": errors,
        }

    # ------------------------------------------------------------------
    # Table Schema Info
    # ------------------------------------------------------------------

    @staticmethod
    def get_importable_tables() -> dict[str, dict[str, Any]]:
        """Return the table schemas available for import."""
        return IMPORTABLE_TABLES
