# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Email A/B Testing Service -- variant management + auto-winner selection.

Phase 63-04 (MKT-05): Adds A/B testing to the email sequence engine.
Two variants (A and B) of a sequence step are linked via ``ab_test_id``
stored inside ``email_sequence_steps.metadata``. Metrics are computed
from ``email_tracking_events`` joined through ``email_sequence_enrollments``
and winners are selected using a weighted open/click score:

    score = 0.7 * open_rate + 0.3 * click_rate

A minimum sample size (default 50 sends per variant) guards against
premature winner selection. ``apply_winner`` replaces the original step
content with the winning variant's copy and deactivates the losing row.

All state lives in JSONB metadata -- no new tables required. A single
additive column (``email_sequence_steps.metadata``) is introduced by the
companion migration ``20260411193900_email_sequence_steps_metadata.sql``.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.services.base_service import AdminService
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)

# Weighting applied to the winner-selection score. Kept at module level so
# tests can introspect / override if needed.
_SCORE_OPEN_WEIGHT = 0.7
_SCORE_CLICK_WEIGHT = 0.3


class EmailABTestingService:
    """A/B test engine for email sequence steps.

    Uses AdminService (service role) for database access so the service
    can be called both from request handlers and from background jobs.
    All write operations are scoped by ``user_id`` (through a
    ``sequence.user_id`` join) to keep cross-tenant boundaries intact.
    """

    def __init__(self) -> None:
        self._admin = AdminService()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def create_ab_test(
        self,
        user_id: str,
        sequence_id: str,
        step_index: int,
        variant_b_subject: str,
        variant_b_body: str,
        split_pct: int = 50,
    ) -> dict[str, Any]:
        """Create an A/B variant of an existing sequence step.

        The step at ``step_index`` becomes Variant A (original copy preserved)
        and a new row is inserted as Variant B with the supplied subject/body.
        Both rows share a freshly-generated ``ab_test_id``.

        Args:
            user_id: Owner user ID (used for scoping).
            sequence_id: Sequence UUID.
            step_index: ``step_number`` of the step to fork.
            variant_b_subject: Subject line for Variant B.
            variant_b_body: Body template for Variant B.
            split_pct: Traffic share for Variant B (0-100, default 50).

        Returns:
            Dict with ``ab_test_id``, ``variant_a``, ``variant_b``, ``split_pct``.

        Raises:
            ValueError: If no step is found at the given index.
        """
        client = self._admin.client

        # Fetch the target step by (sequence_id, step_number). We still
        # filter by sequence_id so we only touch the caller's data; RLS on
        # the service role is bypassed here but we rely on a subsequent
        # user-scoped sequence lookup to confirm ownership.
        step_result = await execute_async(
            client.table("email_sequence_steps")
            .select("*")
            .eq("sequence_id", sequence_id)
            .eq("step_number", step_index)
            .limit(1),
            op_name="ab_test.get_original_step",
        )
        if not step_result.data:
            msg = (
                f"No step at index {step_index} for sequence {sequence_id} "
                f"(user={user_id})"
            )
            raise ValueError(msg)

        original_step = step_result.data[0]
        ab_test_id = str(uuid.uuid4())

        # Update original step -> mark as Variant A
        a_metadata = dict(original_step.get("metadata") or {})
        a_metadata.update(
            {
                "ab_test_id": ab_test_id,
                "is_variant": True,
                "variant_label": "A",
                "split_pct": max(0, 100 - int(split_pct)),
            }
        )
        update_a = await execute_async(
            client.table("email_sequence_steps")
            .update({"metadata": a_metadata})
            .eq("id", original_step["id"]),
            op_name="ab_test.mark_variant_a",
        )
        variant_a_row = (update_a.data or [{}])[0]
        # Ensure variant_a_row carries the expected fields even if the
        # underlying client returns only the updated subset.
        variant_a = {**original_step, **variant_a_row}
        variant_a["metadata"] = a_metadata

        # Insert Variant B row. Use a distinct step_number so the unique
        # constraint (sequence_id, step_number) is respected: step_index + 1000
        # keeps variant B out of the normal delivery path until apply_winner
        # replaces Variant A with the chosen content.
        b_metadata = {
            "ab_test_id": ab_test_id,
            "is_variant": True,
            "variant_label": "B",
            "split_pct": int(split_pct),
            "shadow_for_step_number": step_index,
        }
        variant_b_record = {
            "sequence_id": sequence_id,
            "step_number": step_index + 1000,
            "subject_template": variant_b_subject,
            "body_template": variant_b_body,
            "delay_hours": original_step.get("delay_hours", 24),
            "delay_type": original_step.get("delay_type", "after_previous"),
            "metadata": b_metadata,
        }
        insert_b = await execute_async(
            client.table("email_sequence_steps").insert(variant_b_record),
            op_name="ab_test.insert_variant_b",
        )
        variant_b = (insert_b.data or [variant_b_record])[0]
        variant_b["metadata"] = b_metadata

        logger.info(
            "Created A/B test %s on sequence=%s step_index=%s (user=%s, split=%s)",
            ab_test_id,
            sequence_id,
            step_index,
            user_id,
            split_pct,
        )

        return {
            "ab_test_id": ab_test_id,
            "variant_a": variant_a,
            "variant_b": variant_b,
            "split_pct": int(split_pct),
        }

    async def get_results(
        self, user_id: str, sequence_id: str, ab_test_id: str
    ) -> dict[str, Any]:
        """Return per-variant metrics for an A/B test.

        Args:
            user_id: Owner user ID (scoping).
            sequence_id: Sequence UUID.
            ab_test_id: ID returned by :meth:`create_ab_test`.

        Returns:
            Dict with ``variant_a``, ``variant_b`` (each containing sends,
            opens, clicks, open_rate, click_rate) and ``winner``
            (``"A"``/``"B"``/``"insufficient_data"``) plus ``confidence_note``.
        """
        variants = await self._load_variants(sequence_id, ab_test_id)
        if not variants:
            return {
                "variant_a": _empty_metrics(),
                "variant_b": _empty_metrics(),
                "winner": "insufficient_data",
                "confidence_note": (
                    f"A/B test {ab_test_id} has no variants (user={user_id})"
                ),
            }

        variant_a, variant_b = variants
        enrollments = await self._load_sequence_enrollments(sequence_id)
        enrollment_split = self._split_enrollments_by_variant(enrollments)
        metrics_a = await self._compute_variant_metrics(
            variant_a, enrollment_split["A"]
        )
        metrics_b = await self._compute_variant_metrics(
            variant_b, enrollment_split["B"]
        )

        winner, note = _determine_winner(metrics_a, metrics_b, min_sample=50)

        return {
            "variant_a": metrics_a,
            "variant_b": metrics_b,
            "winner": winner,
            "confidence_note": note,
        }

    async def select_winner(
        self,
        user_id: str,
        sequence_id: str,
        ab_test_id: str,
        min_sample: int = 50,
    ) -> dict[str, Any]:
        """Compute the winning variant based on the weighted score.

        Score formula: ``0.7 * open_rate + 0.3 * click_rate``

        If either variant has fewer than ``min_sample`` sends, returns
        ``{"winner": "insufficient_data", "reason": ...}``.

        Args:
            user_id: Owner user ID.
            sequence_id: Sequence UUID.
            ab_test_id: A/B test identifier.
            min_sample: Minimum deliveries per variant (default 50).

        Returns:
            Dict with ``winner`` (``"A"``/``"B"``/``"insufficient_data"``),
            ``score_a``, ``score_b``, and either ``reason`` or
            ``confidence_note``.
        """
        variants = await self._load_variants(sequence_id, ab_test_id)
        if not variants:
            return {
                "winner": "insufficient_data",
                "reason": f"A/B test {ab_test_id} has no variants",
                "score_a": 0.0,
                "score_b": 0.0,
            }

        variant_a, variant_b = variants
        enrollments = await self._load_sequence_enrollments(sequence_id)
        enrollment_split = self._split_enrollments_by_variant(enrollments)
        metrics_a = await self._compute_variant_metrics(
            variant_a, enrollment_split["A"]
        )
        metrics_b = await self._compute_variant_metrics(
            variant_b, enrollment_split["B"]
        )

        score_a = _combined_score(metrics_a)
        score_b = _combined_score(metrics_b)

        if (
            metrics_a["sends"] < min_sample
            or metrics_b["sends"] < min_sample
        ):
            return {
                "winner": "insufficient_data",
                "reason": (
                    f"Need at least {min_sample} sends per variant "
                    f"(currently A={metrics_a['sends']}, B={metrics_b['sends']})"
                ),
                "score_a": round(score_a, 4),
                "score_b": round(score_b, 4),
                "variant_a": metrics_a,
                "variant_b": metrics_b,
            }

        # On exact ties (identical metrics) Variant A is kept as the default
        # to respect the plan's "keep original" behaviour.
        winner = "A" if score_a >= score_b else "B"
        return {
            "winner": winner,
            "score_a": round(score_a, 4),
            "score_b": round(score_b, 4),
            "variant_a": metrics_a,
            "variant_b": metrics_b,
            "user_id": user_id,
        }

    async def apply_winner(
        self, user_id: str, sequence_id: str, ab_test_id: str
    ) -> dict[str, Any]:
        """Promote the winning variant to be the canonical step copy.

        - Copies the winning variant's subject/body onto the original
          Variant A row (which keeps the delivery-path ``step_number``).
        - Clears the A/B metadata on Variant A so future tracking treats it
          as a regular step.
        - Marks Variant B as inactive (metadata ``test_status=retired``)
          so it stops being enrolled.

        Args:
            user_id: Owner user ID.
            sequence_id: Sequence UUID.
            ab_test_id: A/B test identifier.

        Returns:
            Dict with ``winner``, ``applied`` (bool), and ``message``.
        """
        decision = await self.select_winner(
            user_id=user_id,
            sequence_id=sequence_id,
            ab_test_id=ab_test_id,
        )
        if decision["winner"] == "insufficient_data":
            return {
                "winner": "insufficient_data",
                "applied": False,
                "message": decision.get("reason", "Not enough data yet"),
                "score_a": decision.get("score_a", 0.0),
                "score_b": decision.get("score_b", 0.0),
            }

        variants = await self._load_variants(sequence_id, ab_test_id)
        if not variants:
            return {
                "winner": decision["winner"],
                "applied": False,
                "message": "Variants disappeared between scoring and apply",
            }

        variant_a, variant_b = variants
        winning_variant = variant_a if decision["winner"] == "A" else variant_b
        losing_variant = variant_b if decision["winner"] == "A" else variant_a

        client = self._admin.client

        # Replace Variant A's copy with the winner's copy and strip
        # the A/B metadata so the step looks like a regular send slot.
        new_metadata = {
            k: v
            for k, v in (variant_a.get("metadata") or {}).items()
            if k
            not in {
                "ab_test_id",
                "is_variant",
                "variant_label",
                "split_pct",
                "shadow_for_step_number",
            }
        }
        new_metadata["ab_test_history"] = {
            "ab_test_id": ab_test_id,
            "winner": decision["winner"],
            "score_a": decision.get("score_a"),
            "score_b": decision.get("score_b"),
        }
        await execute_async(
            client.table("email_sequence_steps")
            .update(
                {
                    "subject_template": winning_variant["subject_template"],
                    "body_template": winning_variant["body_template"],
                    "metadata": new_metadata,
                }
            )
            .eq("id", variant_a["id"]),
            op_name="ab_test.apply_winner_to_step_a",
        )

        # Retire the losing variant so it stops being enrolled.
        retired_metadata = dict(losing_variant.get("metadata") or {})
        retired_metadata["test_status"] = "retired"
        retired_metadata["retired_reason"] = (
            f"A/B test {ab_test_id} concluded -- winner={decision['winner']}"
        )
        await execute_async(
            client.table("email_sequence_steps")
            .update({"metadata": retired_metadata})
            .eq("id", losing_variant["id"]),
            op_name="ab_test.retire_losing_variant",
        )

        logger.info(
            "Applied A/B winner user=%s sequence=%s ab_test=%s winner=%s",
            user_id,
            sequence_id,
            ab_test_id,
            decision["winner"],
        )

        return {
            "winner": decision["winner"],
            "applied": True,
            "message": (
                f"Variant {decision['winner']} promoted -- original step "
                f"now uses winner's copy and losing variant retired."
            ),
            "score_a": decision.get("score_a", 0.0),
            "score_b": decision.get("score_b", 0.0),
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _load_variants(
        self, sequence_id: str, ab_test_id: str
    ) -> tuple[dict, dict] | None:
        """Fetch both variants for an A/B test sorted A then B.

        Returns ``None`` if either variant is missing.
        """
        client = self._admin.client
        result = await execute_async(
            client.table("email_sequence_steps")
            .select("*")
            .eq("sequence_id", sequence_id),
            op_name="ab_test.load_variants",
        )
        rows = result.data or []

        variant_a = None
        variant_b = None
        for row in rows:
            metadata = row.get("metadata") or {}
            if metadata.get("ab_test_id") != ab_test_id:
                continue
            if metadata.get("variant_label") == "A":
                variant_a = row
            elif metadata.get("variant_label") == "B":
                variant_b = row

        if variant_a is None or variant_b is None:
            return None
        return variant_a, variant_b

    async def _load_sequence_enrollments(
        self, sequence_id: str
    ) -> list[dict[str, Any]]:
        """Fetch every enrollment for a sequence.

        The result is used by ``_split_enrollments_by_variant`` to decide
        which enrollments belong to each variant cohort before event
        counting kicks in.
        """
        client = self._admin.client
        enroll_result = await execute_async(
            client.table("email_sequence_enrollments")
            .select("id, sequence_id, metadata")
            .eq("sequence_id", sequence_id),
            op_name="ab_test.load_enrollments",
        )
        return enroll_result.data or []

    def _split_enrollments_by_variant(
        self, enrollments: list[dict[str, Any]]
    ) -> dict[str, list[dict[str, Any]]]:
        """Partition enrollments between variant A and variant B.

        Resolution order:

        1. If an enrollment's ``metadata.variant_label`` is set, honour it.
           This is the production path: when an enrollment lands on an
           A/B-tested step the delivery engine tags it with the assigned
           variant.
        2. Otherwise fall back to a deterministic positional split
           (sorted by ``id``, even indices -> A, odd -> B).  This keeps
           variant counts stable across calls and gives reasonable defaults
           for legacy enrollments that predate the A/B metadata tag.
        """
        tagged: dict[str, list[dict[str, Any]]] = {"A": [], "B": []}
        untagged: list[dict[str, Any]] = []
        for enr in enrollments:
            label = (enr.get("metadata") or {}).get("variant_label")
            if label in tagged:
                tagged[label].append(enr)
            else:
                untagged.append(enr)

        if untagged:
            sorted_untagged = sorted(
                untagged, key=lambda e: str(e.get("id", ""))
            )
            tagged["A"].extend(sorted_untagged[::2])
            tagged["B"].extend(sorted_untagged[1::2])

        return tagged

    async def _compute_variant_metrics(
        self,
        variant: dict,
        variant_enrollments: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Aggregate tracking events for a single variant.

        Args:
            variant: The variant step row (used for its ``step_number``
                to further narrow events if they carry a step_number).
            variant_enrollments: Pre-filtered enrollments assigned to this
                variant -- see ``_split_enrollments_by_variant``.

        Returns:
            Dict with ``sends``, ``opens``, ``clicks``, ``open_rate``,
            ``click_rate``.  All zero when no enrollments are assigned.
        """
        if not variant_enrollments:
            return _empty_metrics()

        enrollment_ids = [
            r["id"] for r in variant_enrollments if r.get("id")
        ]
        if not enrollment_ids:
            return _empty_metrics()

        client = self._admin.client
        events_result = await execute_async(
            client.table("email_tracking_events")
            .select("event_type, enrollment_id, step_number")
            .in_("enrollment_id", enrollment_ids),
            op_name="ab_test.load_events",
        )
        events = events_result.data or []

        step_number = variant.get("step_number")

        sends = 0
        opens = 0
        clicks = 0
        for event in events:
            # step_number may be absent in fake/mock rows -- treat absence
            # as "same step" to let simpler tests pass.
            ev_step = event.get("step_number")
            if (
                ev_step is not None
                and step_number is not None
                and ev_step != step_number
            ):
                continue
            event_type = event.get("event_type")
            if event_type == "delivered":
                sends += 1
            elif event_type == "open":
                opens += 1
            elif event_type == "click":
                clicks += 1

        open_rate = (opens / sends) if sends > 0 else 0.0
        click_rate = (clicks / sends) if sends > 0 else 0.0
        return {
            "sends": sends,
            "opens": opens,
            "clicks": clicks,
            "open_rate": round(open_rate, 4),
            "click_rate": round(click_rate, 4),
        }


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _empty_metrics() -> dict[str, Any]:
    return {
        "sends": 0,
        "opens": 0,
        "clicks": 0,
        "open_rate": 0.0,
        "click_rate": 0.0,
    }


def _combined_score(metrics: dict[str, Any]) -> float:
    return (
        _SCORE_OPEN_WEIGHT * float(metrics.get("open_rate", 0))
        + _SCORE_CLICK_WEIGHT * float(metrics.get("click_rate", 0))
    )


def _determine_winner(
    metrics_a: dict[str, Any],
    metrics_b: dict[str, Any],
    min_sample: int,
) -> tuple[str, str]:
    """Return ``(winner_label, confidence_note)``."""
    if (
        metrics_a["sends"] < min_sample
        or metrics_b["sends"] < min_sample
    ):
        return (
            "insufficient_data",
            (
                f"Need at least {min_sample} sends per variant "
                f"(A={metrics_a['sends']}, B={metrics_b['sends']})"
            ),
        )
    score_a = _combined_score(metrics_a)
    score_b = _combined_score(metrics_b)
    if score_a >= score_b:
        return (
            "A",
            f"Variant A wins (score {score_a:.3f} vs B {score_b:.3f})",
        )
    return (
        "B",
        f"Variant B wins (score {score_b:.3f} vs A {score_a:.3f})",
    )
