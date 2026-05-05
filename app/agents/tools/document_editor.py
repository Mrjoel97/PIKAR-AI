# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Document editor agent tools.

Seven tools (in this module): ``read_document_content``, the five
``edit_*`` tools (one per doc class), and ``list_document_versions``.
Each edit tool mutates the canonical source, re-renders the binary,
writes a version row, and returns a ``_workspace_command`` marker so
the SSE pipeline can notify the viewer.
"""

from __future__ import annotations

import copy
import logging
from typing import Any

import httpx

from app.agents.tools.base import agent_tool
from app.services.document_extraction_service import DocumentExtractionService
from app.services.document_source_service import DocumentSourceService
from app.services.document_version_service import DocumentVersionService

logger = logging.getLogger(__name__)

# Token cap for read_document_content output (~10K tokens, ~7500 words)
TEXT_TOKEN_CAP_WORDS = 7500


# --- Service factories (patchable in tests) ---


async def _get_source_service() -> DocumentSourceService:
    """Return a DocumentSourceService for cross-user reads (service role).

    Ownership is enforced in code via :func:`_load_owned_record`, not RLS.
    The default ``user_token=None`` constructor yields a service-role client
    via the shared async client; the agent runtime acts on the user's behalf
    so this is the intended access pattern for tools in this module.
    """
    return DocumentSourceService()


async def _get_version_service() -> DocumentVersionService:
    """Return a DocumentVersionService for cross-user reads (service role).

    Same rationale as :func:`_get_source_service` -- ownership is verified in
    code, not via RLS.
    """
    return DocumentVersionService()


def _get_extraction_service() -> DocumentExtractionService:
    """Return a DocumentExtractionService instance (stateless)."""
    return DocumentExtractionService()


def _get_google_docs_service(tool_context: Any):
    """Patchable factory for the Google Docs service.

    Delegates to :func:`app.agents.tools.docs._get_docs_service`. Tests can
    monkeypatch this attribute to inject a fake service without depending on
    Google credentials in ``tool_context.state``.
    """
    from app.agents.tools.docs import _get_docs_service

    return _get_docs_service(tool_context)


async def _fetch_binary(url: str) -> bytes:
    """Fetch binary bytes from a URL via httpx.

    Uses an async context manager so the underlying connection pool is
    released even when the HTTP call raises.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.content


def _truncate_text(
    text: str, cap_words: int = TEXT_TOKEN_CAP_WORDS
) -> tuple[str, bool]:
    """Truncate ``text`` to ``cap_words`` whitespace-split words.

    Returns:
        ``(text, was_truncated)``. When truncated, the returned text has a
        ``\\n\\n[...truncated...]`` marker appended so the model can tell
        the content was cut off.
    """
    words = text.split()
    if len(words) <= cap_words:
        return text, False
    return " ".join(words[:cap_words]) + "\n\n[...truncated...]", True


async def _load_owned_record(
    tool_context: Any,
    document_id: str,
    source_service: DocumentSourceService,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Fetch a ``document_sources`` row and verify ownership.

    Returns ``(record, None)`` on success or ``(None, error_response)`` if
    the row is missing or not owned by the caller. Every tool in this
    module MUST use this helper instead of ``source_service.get`` directly:
    agents run under a service-role client so RLS doesn't gate access, and
    we enforce ownership in code by matching ``tool_context.state.user_id``
    against ``document_sources.user_id``.
    """
    record = await source_service.get(document_id)
    if record is None:
        return None, {
            "status": "error",
            "message": f"Document {document_id} not found",
        }
    user_id = (
        tool_context.state.get("user_id") if hasattr(tool_context, "state") else None
    )
    if not user_id or record.get("user_id") != user_id:
        return None, {
            "status": "error",
            "message": "Document not accessible",
        }
    return record, None


async def _ensure_source_exists(
    record: dict[str, Any],
    source_service: DocumentSourceService,
) -> dict[str, Any]:
    """Lazy-fork a user upload to editable source on first edit.

    If ``record["source"]`` is already set, returns it unchanged. Otherwise
    fetches the binary from ``record["binary_url"]``, runs
    :class:`DocumentExtractionService` to generate a canonical source dict,
    marks the row as ``forked_from_upload``, and returns the freshly forked
    source.

    Raises:
        ValueError: If ``source`` is ``None`` AND ``binary_url`` is also
            missing (no path to recover content from).
    """
    # TODO: Capturing the original imported source as v0 in
    # ``document_versions`` BEFORE the user's first edit applies would
    # require an extra ``version_service.append`` call here with the
    # imported source as snapshot. Plan 1's scope as written doesn't
    # include capturing v0; tracked as a follow-up. The original binary
    # is preserved via ``binary_url`` + ``forked_from_upload=true``, so
    # users can still see the pre-edit document.
    if record.get("source") is not None:
        return record["source"]

    extraction_service = _get_extraction_service()
    binary_url = record.get("binary_url")
    if not binary_url:
        raise ValueError(
            f"Document {record['document_id']} has no source and no binary URL "
            "to fork from"
        )

    binary = await _fetch_binary(binary_url)
    forked = await extraction_service.fork_to_source(
        binary=binary, doc_class=record["doc_class"]
    )
    await source_service.mark_forked_from_upload(record["document_id"])
    return forked


async def _upload_render(
    *,
    record: dict[str, Any],
    file_bytes: bytes,
    content_type: str,
    file_type: str,
) -> str:
    """Upload re-rendered binary; upsert media_assets keyed on document_id.

    Returns the signed URL of the uploaded file. Re-uses the document_id
    as the media_assets doc_id so each edit upserts in place rather than
    accumulating asset rows. The version chain in document_versions is
    the canonical record of edit history; media_assets just needs the
    latest binary discoverable.
    """
    from app.services.document_service import DocumentService

    service = DocumentService()
    document_id = record["document_id"]
    title = (record.get("source") or {}).get("title") or "Document"
    filename = f"{document_id}.{file_type}"

    widget = await service._upload_document(
        file_bytes=file_bytes,
        user_id=record["user_id"],
        doc_id=document_id,
        filename=filename,
        content_type=content_type,
        title=title,
        template_name="edited",
        session_id=None,
        file_type=file_type,
    )
    # _upload_document returns a widget envelope: {"type": "document",
    # "title": ..., "data": {"documentUrl": signed_url, ...}, ...}
    data = widget.get("data") or {}
    url = (
        data.get("documentUrl")
        or data.get("file_url")
        or data.get("signed_url")
        or data.get("url")
        or widget.get("file_url")
        or widget.get("signed_url")
        or widget.get("url")
    )
    if not url:
        raise ValueError(
            f"_upload_document did not return a URL in its widget envelope: "
            f"keys={list(widget.keys())!r}, data_keys="
            f"{list(data.keys()) if isinstance(data, dict) else 'n/a'}"
        )
    return url


async def _persist_edit(
    *,
    record: dict[str, Any],
    new_source: dict[str, Any],
    new_binary: bytes,
    content_type: str,
    file_type: str,
    diff_summary: str,
) -> dict[str, Any]:
    """Common path for binary-rendered edits.

    Uploads the re-rendered binary (upserting ``media_assets`` keyed on
    ``document_id``), updates ``document_sources``, appends a row to
    ``document_versions``, and returns a ``_workspace_command`` envelope so
    the SSE post-processor can refresh the viewer.
    """
    new_url = await _upload_render(
        record=record,
        file_bytes=new_binary,
        content_type=content_type,
        file_type=file_type,
    )

    source_service = await _get_source_service()
    await source_service.update_source(
        document_id=record["document_id"],
        new_source=new_source,
        new_binary_url=new_url,
    )

    version_service = await _get_version_service()
    version = await version_service.append(
        document_id=record["document_id"],
        user_id=record["user_id"],
        source_snapshot=new_source,
        binary_url=new_url,
        diff_summary=diff_summary,
        created_by="agent",
    )

    return {
        "_workspace_command": True,
        "commands": [
            {
                "action": "replace_active",
                "payload": {
                    "widget": {
                        "type": "document_viewer",
                        "data": {
                            "document_id": record["document_id"],
                            "binary_url": new_url,
                            "doc_class": record["doc_class"],
                        },
                    },
                },
            },
        ],
        "status": "success",
        "new_version_id": version["id"],
        "new_render_url": new_url,
        "diff_summary": diff_summary,
    }


# --- Tool: read_document_content ---


@agent_tool
async def read_document_content(
    tool_context: Any,
    document_id: str,
    page_range: list[int] | None = None,
) -> dict[str, Any]:
    """Read text + structure from a document into the agent's context.

    Use when the user asks about a doc's contents, references something
    inside it, or before calling any ``edit_*`` tool that needs the current
    state to make a sensible change. Triggers lazy text extraction on the
    first call for a user upload.

    Args:
        tool_context: ADK tool context carrying ``state.user_id``.
        document_id: UUID of the document.
        page_range: 1-indexed pages to read (``None`` = whole doc, capped).
            Currently unused beyond pass-through; future versions will slice
            ``extracted_text`` by page.

    Returns:
        Dict with keys:
            * ``status`` -- ``"success"`` or ``"error"``.
            * ``text`` -- extracted text (capped at ~10K tokens; truncation
              marker appended when cut).
            * ``structure`` -- ``{type, section_count?, sheet_names?,
              slide_count?}``.
            * ``truncated`` -- ``True`` when content exceeded the token cap.
    """
    try:
        source_service = await _get_source_service()
        record, err = await _load_owned_record(
            tool_context,
            document_id,
            source_service,
        )
        if err is not None:
            return err
        assert record is not None  # _load_owned_record contract: err None => record set

        text = record.get("extracted_text")
        if not text:
            # Lazy extract from binary
            binary_url = record.get("binary_url")
            if not binary_url:
                return {
                    "status": "error",
                    "message": "Document has no binary URL to extract from",
                }
            binary = await _fetch_binary(binary_url)
            extraction_service = _get_extraction_service()
            text = await extraction_service.extract_text(
                binary=binary,
                doc_class=record["doc_class"],
            )
            await source_service.set_extracted_text(document_id, text)

        truncated_text, truncated = _truncate_text(text)

        structure: dict[str, Any] = {"type": record["doc_class"]}
        source = record.get("source")
        if source:
            if "sections" in source:
                structure["section_count"] = len(source["sections"])
            if "sheets" in source:
                structure["sheet_names"] = [s["name"] for s in source["sheets"]]
            if "slides" in source:
                structure["slide_count"] = len(source["slides"])

        return {
            "status": "success",
            "text": truncated_text,
            "structure": structure,
            "truncated": truncated,
        }
    except Exception as exc:
        logger.exception("read_document_content failed")
        return {"status": "error", "message": str(exc)}


# --- Tool: edit_report_doc (PDF reports) ---


@agent_tool
async def edit_report_doc(
    tool_context: Any,
    document_id: str,
    operation: str,
    target: str,
    new_content: str | None = None,
    new_heading: str | None = None,
) -> dict[str, Any]:
    """Edit a PDF report by mutating its sectioned source and re-rendering.

    Supported operations:
        * ``replace_section`` -- replace ``content`` of the section whose
          heading equals ``target``. Requires ``new_content``.
        * ``append_section`` -- append a new section at the end. ``target``
          is the new heading; ``new_content`` is the body.
        * ``delete_section`` -- remove the section whose heading equals
          ``target``.
        * ``rename_section`` -- rename the heading of the section whose
          current heading equals ``target`` to ``new_heading``.

    Args:
        tool_context: ADK tool context carrying ``state.user_id``.
        document_id: UUID of the report document.
        operation: One of the supported operations above.
        target: Anchor (existing heading) for the operation. For
            ``append_section``, this is the NEW heading.
        new_content: Replacement / appended body text. Required for
            ``replace_section`` and ``append_section``.
        new_heading: Replacement heading. Required for ``rename_section``.

    Returns:
        ``_workspace_command`` envelope on success, or
        ``{"status": "error", "message": ...}`` on failure.
    """
    try:
        source_service = await _get_source_service()
        record, err = await _load_owned_record(
            tool_context,
            document_id,
            source_service,
        )
        if err is not None:
            return err
        assert record is not None
        if record["doc_class"] != "report":
            return {
                "status": "error",
                "message": f"Wrong tool for {record['doc_class']}",
            }

        loaded_source = await _ensure_source_exists(record, source_service)
        source = copy.deepcopy(loaded_source or {"sections": []})
        sections = source.setdefault("sections", [])

        if operation == "replace_section":
            if new_content is None:
                return {
                    "status": "error",
                    "message": "replace_section requires new_content",
                }
            for section in sections:
                if section.get("heading") == target:
                    section["content"] = new_content
                    diff_summary = f"Replaced section '{target}'"
                    break
            else:
                return {
                    "status": "error",
                    "message": f"Section '{target}' not found",
                }
        elif operation == "append_section":
            if new_content is None:
                return {
                    "status": "error",
                    "message": "append_section requires new_content",
                }
            sections.append({"heading": target, "content": new_content})
            diff_summary = f"Appended section '{target}'"
        elif operation == "delete_section":
            new_sections = [s for s in sections if s.get("heading") != target]
            if len(new_sections) == len(sections):
                return {
                    "status": "error",
                    "message": f"Section '{target}' not found",
                }
            source["sections"] = new_sections
            diff_summary = f"Deleted section '{target}'"
        elif operation == "rename_section":
            if new_heading is None:
                return {
                    "status": "error",
                    "message": "rename_section requires new_heading",
                }
            for section in sections:
                if section.get("heading") == target:
                    section["heading"] = new_heading
                    diff_summary = f"Renamed section '{target}' to '{new_heading}'"
                    break
            else:
                return {
                    "status": "error",
                    "message": f"Section '{target}' not found",
                }
        else:
            return {
                "status": "error",
                "message": f"Unsupported operation '{operation}'",
            }

        from app.services.document_service import render_pdf_from_source

        new_binary = await render_pdf_from_source(source)

        return await _persist_edit(
            record=record,
            new_source=source,
            new_binary=new_binary,
            content_type="application/pdf",
            file_type="pdf",
            diff_summary=diff_summary,
        )
    except Exception as exc:
        logger.exception("edit_report_doc failed")
        return {"status": "error", "message": str(exc)}


# --- Tool: edit_spreadsheet (XLSX) ---


def _cell_to_indices(cell: str) -> tuple[int, int]:
    """Convert an A1-style cell reference (e.g. ``"B2"``) to ``(row, col)``.

    Both indices are 0-based. Multi-letter columns (``AA``, ``AB``, ...)
    are supported. Raises :class:`ValueError` on malformed input.
    """
    cell = cell.strip().upper()
    col_chars = ""
    row_chars = ""
    for ch in cell:
        if ch.isalpha():
            if row_chars:
                raise ValueError(f"Malformed cell reference: {cell!r}")
            col_chars += ch
        elif ch.isdigit():
            row_chars += ch
        else:
            raise ValueError(f"Malformed cell reference: {cell!r}")
    if not col_chars or not row_chars:
        raise ValueError(f"Malformed cell reference: {cell!r}")
    col_idx = 0
    for ch in col_chars:
        col_idx = col_idx * 26 + (ord(ch) - ord("A") + 1)
    return int(row_chars) - 1, col_idx - 1


@agent_tool
async def edit_spreadsheet(
    tool_context: Any,
    document_id: str,
    operation: str,
    sheet_name: str,
    cell: str | None = None,
    value: Any = None,
    row_index: int | None = None,
    formula: str | None = None,
    new_name: str | None = None,
) -> dict[str, Any]:
    """Edit a spreadsheet by mutating its sheet source and re-rendering XLSX.

    Supported operations:
        * ``set_cell`` -- set ``cell`` (e.g. ``"B2"``) to ``value``.
        * ``insert_row`` -- insert ``value`` (a list) at ``row_index``.
        * ``delete_row`` -- delete row at ``row_index``.
        * ``set_formula`` -- set ``cell`` to a formula string ``formula``.
        * ``rename_sheet`` -- rename sheet ``sheet_name`` to ``new_name``.

    Google Sheets editing is not yet implemented; the tool returns an
    informational error envelope when ``doc_class == "google_sheet"``.

    Args:
        tool_context: ADK tool context carrying ``state.user_id``.
        document_id: UUID of the spreadsheet document.
        operation: One of the supported operations above.
        sheet_name: Name of the sheet to operate on.
        cell: A1-style cell reference (``set_cell``, ``set_formula``).
        value: New cell value (``set_cell``) or row contents (``insert_row``).
        row_index: 0-based row index (``insert_row``, ``delete_row``).
        formula: Formula string starting with ``"="`` (``set_formula``).
        new_name: New sheet name (``rename_sheet``).

    Returns:
        ``_workspace_command`` envelope on success, or
        ``{"status": "error", "message": ...}`` on failure.
    """
    try:
        source_service = await _get_source_service()
        record, err = await _load_owned_record(
            tool_context,
            document_id,
            source_service,
        )
        if err is not None:
            return err
        assert record is not None
        if record["doc_class"] == "google_sheet":
            return {
                "status": "error",
                "message": "Google Sheets editing not yet implemented",
            }
        if record["doc_class"] != "spreadsheet":
            return {
                "status": "error",
                "message": f"Wrong tool for {record['doc_class']}",
            }

        loaded_source = await _ensure_source_exists(record, source_service)
        source = copy.deepcopy(loaded_source or {"sheets": []})
        sheets = source.setdefault("sheets", [])
        sheet = next((s for s in sheets if s.get("name") == sheet_name), None)
        if sheet is None and operation != "rename_sheet":
            return {
                "status": "error",
                "message": f"Sheet '{sheet_name}' not found",
            }

        if operation == "set_cell":
            if cell is None:
                return {"status": "error", "message": "set_cell requires cell"}
            row, col = _cell_to_indices(cell)
            assert sheet is not None
            rows = sheet.setdefault("rows", [])
            while len(rows) <= row:
                rows.append([])
            while len(rows[row]) <= col:
                rows[row].append(None)
            rows[row][col] = value
            diff_summary = f"Set {sheet_name}!{cell} = {value!r}"
        elif operation == "insert_row":
            if row_index is None:
                return {
                    "status": "error",
                    "message": "insert_row requires row_index",
                }
            assert sheet is not None
            rows = sheet.setdefault("rows", [])
            row_value = value if isinstance(value, list) else []
            rows.insert(row_index, row_value)
            diff_summary = f"Inserted row at {sheet_name} index {row_index}"
        elif operation == "delete_row":
            if row_index is None:
                return {
                    "status": "error",
                    "message": "delete_row requires row_index",
                }
            assert sheet is not None
            rows = sheet.get("rows") or []
            if row_index < 0 or row_index >= len(rows):
                return {
                    "status": "error",
                    "message": f"row_index {row_index} out of range",
                }
            rows.pop(row_index)
            diff_summary = f"Deleted row at {sheet_name} index {row_index}"
        elif operation == "set_formula":
            if cell is None or formula is None:
                return {
                    "status": "error",
                    "message": "set_formula requires cell and formula",
                }
            row, col = _cell_to_indices(cell)
            assert sheet is not None
            rows = sheet.setdefault("rows", [])
            while len(rows) <= row:
                rows.append([])
            while len(rows[row]) <= col:
                rows[row].append(None)
            rows[row][col] = formula
            diff_summary = f"Set {sheet_name}!{cell} = {formula}"
        elif operation == "rename_sheet":
            if new_name is None:
                return {
                    "status": "error",
                    "message": "rename_sheet requires new_name",
                }
            if sheet is None:
                return {
                    "status": "error",
                    "message": f"Sheet '{sheet_name}' not found",
                }
            sheet["name"] = new_name
            diff_summary = f"Renamed sheet '{sheet_name}' to '{new_name}'"
        else:
            return {
                "status": "error",
                "message": f"Unsupported operation '{operation}'",
            }

        from app.services.document_service import render_xlsx_from_source

        new_binary = await render_xlsx_from_source(source)

        return await _persist_edit(
            record=record,
            new_source=source,
            new_binary=new_binary,
            content_type=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
            file_type="xlsx",
            diff_summary=diff_summary,
        )
    except Exception as exc:
        logger.exception("edit_spreadsheet failed")
        return {"status": "error", "message": str(exc)}


# --- Tool: edit_presentation (PPTX) ---


@agent_tool
async def edit_presentation(
    tool_context: Any,
    document_id: str,
    operation: str,
    slide_index: int | None = None,
    field: str | None = None,
    new_value: str | None = None,
    layout: str | None = None,
    title: str | None = None,
    body: str | None = None,
    new_index: int | None = None,
    image_url: str | None = None,
) -> dict[str, Any]:
    """Edit a presentation by mutating its slide source and re-rendering PPTX.

    Supported operations:
        * ``edit_text`` -- set slide ``slide_index``'s ``field`` (one of
          ``title``, ``body``, ``speaker_notes``) to ``new_value``.
        * ``insert_slide`` -- insert a new slide at ``slide_index`` with
          ``layout``, ``title``, ``body``.
        * ``delete_slide`` -- delete slide at ``slide_index``.
        * ``reorder`` -- move slide from ``slide_index`` to ``new_index``.
        * ``set_speaker_notes`` -- set slide ``slide_index``'s
          ``speaker_notes`` to ``new_value``.
        * ``replace_image`` -- set slide ``slide_index``'s ``image_url`` field.

    Args:
        tool_context: ADK tool context carrying ``state.user_id``.
        document_id: UUID of the presentation document.
        operation: One of the supported operations above.
        slide_index: 0-based index of the slide to operate on.
        field: For ``edit_text`` -- ``title``, ``body``, or ``speaker_notes``.
        new_value: Replacement text for ``edit_text`` / ``set_speaker_notes``.
        layout: New slide layout for ``insert_slide``.
        title: New slide title for ``insert_slide``.
        body: New slide body for ``insert_slide``.
        new_index: Destination index for ``reorder``.
        image_url: Replacement image URL for ``replace_image``.

    Returns:
        ``_workspace_command`` envelope on success, or
        ``{"status": "error", "message": ...}`` on failure.
    """
    try:
        source_service = await _get_source_service()
        record, err = await _load_owned_record(
            tool_context,
            document_id,
            source_service,
        )
        if err is not None:
            return err
        assert record is not None
        if record["doc_class"] != "presentation":
            return {
                "status": "error",
                "message": f"Wrong tool for {record['doc_class']}",
            }

        loaded_source = await _ensure_source_exists(record, source_service)
        source = copy.deepcopy(loaded_source or {"slides": []})
        slides = source.setdefault("slides", [])

        def _bounds_check(idx: int | None, label: str) -> dict[str, Any] | None:
            if idx is None:
                return {"status": "error", "message": f"{label} requires slide_index"}
            if idx < 0 or idx >= len(slides):
                return {
                    "status": "error",
                    "message": f"slide_index {idx} out of range",
                }
            return None

        if operation == "edit_text":
            err2 = _bounds_check(slide_index, "edit_text")
            if err2 is not None:
                return err2
            if field not in {"title", "body", "speaker_notes"}:
                return {
                    "status": "error",
                    "message": "edit_text requires field in {title, body, speaker_notes}",
                }
            if new_value is None:
                return {
                    "status": "error",
                    "message": "edit_text requires new_value",
                }
            slides[slide_index][field] = new_value  # type: ignore[index]
            diff_summary = f"Set slide {slide_index} {field}"
        elif operation == "insert_slide":
            if slide_index is None:
                return {
                    "status": "error",
                    "message": "insert_slide requires slide_index",
                }
            if slide_index < 0 or slide_index > len(slides):
                return {
                    "status": "error",
                    "message": f"slide_index {slide_index} out of range",
                }
            new_slide = {
                "layout": layout or "title_and_body",
                "title": title or "",
                "body": body or "",
                "speaker_notes": None,
            }
            slides.insert(slide_index, new_slide)
            diff_summary = f"Inserted slide at index {slide_index}"
        elif operation == "delete_slide":
            err2 = _bounds_check(slide_index, "delete_slide")
            if err2 is not None:
                return err2
            slides.pop(slide_index)  # type: ignore[arg-type]
            diff_summary = f"Deleted slide at index {slide_index}"
        elif operation == "reorder":
            err2 = _bounds_check(slide_index, "reorder")
            if err2 is not None:
                return err2
            if new_index is None or new_index < 0 or new_index >= len(slides):
                return {
                    "status": "error",
                    "message": "reorder requires valid new_index",
                }
            slide = slides.pop(slide_index)  # type: ignore[arg-type]
            slides.insert(new_index, slide)
            diff_summary = f"Moved slide {slide_index} -> {new_index}"
        elif operation == "set_speaker_notes":
            err2 = _bounds_check(slide_index, "set_speaker_notes")
            if err2 is not None:
                return err2
            if new_value is None:
                return {
                    "status": "error",
                    "message": "set_speaker_notes requires new_value",
                }
            slides[slide_index]["speaker_notes"] = new_value  # type: ignore[index]
            diff_summary = f"Set speaker notes on slide {slide_index}"
        elif operation == "replace_image":
            err2 = _bounds_check(slide_index, "replace_image")
            if err2 is not None:
                return err2
            if image_url is None:
                return {
                    "status": "error",
                    "message": "replace_image requires image_url",
                }
            slides[slide_index]["image_url"] = image_url  # type: ignore[index]
            diff_summary = f"Replaced image on slide {slide_index}"
        else:
            return {
                "status": "error",
                "message": f"Unsupported operation '{operation}'",
            }

        from app.services.document_service import render_pptx_from_source

        new_binary = await render_pptx_from_source(source)

        return await _persist_edit(
            record=record,
            new_source=source,
            new_binary=new_binary,
            content_type=(
                "application/vnd.openxmlformats-officedocument."
                "presentationml.presentation"
            ),
            file_type="pptx",
            diff_summary=diff_summary,
        )
    except Exception as exc:
        logger.exception("edit_presentation failed")
        return {"status": "error", "message": str(exc)}


# --- Tool: edit_word_doc (DOCX) ---


@agent_tool
async def edit_word_doc(
    tool_context: Any,
    document_id: str,
    operation: str,
    target: str | None = None,
    new_content: str | None = None,
    new_heading: str | None = None,
) -> dict[str, Any]:
    """Edit a Word document by mutating its sectioned source and re-rendering DOCX.

    Supported operations:
        * ``replace_paragraph`` -- replace ``content`` of the section whose
          heading equals ``target``. Requires ``new_content``.
        * ``append`` -- append a new section at the end. ``target`` is the
          new heading; ``new_content`` is the body.
        * ``set_heading`` -- rename the heading of the section whose current
          heading equals ``target`` to ``new_heading``.
        * ``insert_table`` -- not yet implemented; returns informational error.

    Args:
        tool_context: ADK tool context carrying ``state.user_id``.
        document_id: UUID of the Word document.
        operation: One of the supported operations above.
        target: Anchor (existing heading) for the operation. For ``append``,
            this is the NEW heading.
        new_content: Replacement / appended body text.
        new_heading: Replacement heading for ``set_heading``.

    Returns:
        ``_workspace_command`` envelope on success, or
        ``{"status": "error", "message": ...}`` on failure.
    """
    try:
        source_service = await _get_source_service()
        record, err = await _load_owned_record(
            tool_context,
            document_id,
            source_service,
        )
        if err is not None:
            return err
        assert record is not None
        if record["doc_class"] != "word":
            return {
                "status": "error",
                "message": f"Wrong tool for {record['doc_class']}",
            }

        if operation == "insert_table":
            return {
                "status": "error",
                "message": "insert_table not yet implemented",
            }

        loaded_source = await _ensure_source_exists(record, source_service)
        source = copy.deepcopy(loaded_source or {"sections": []})
        sections = source.setdefault("sections", [])

        if operation == "replace_paragraph":
            if target is None or new_content is None:
                return {
                    "status": "error",
                    "message": "replace_paragraph requires target and new_content",
                }
            for section in sections:
                if section.get("heading") == target:
                    section["content"] = new_content
                    diff_summary = f"Replaced section '{target}'"
                    break
            else:
                return {
                    "status": "error",
                    "message": f"Section '{target}' not found",
                }
        elif operation == "append":
            if target is None or new_content is None:
                return {
                    "status": "error",
                    "message": "append requires target and new_content",
                }
            sections.append({"heading": target, "content": new_content})
            diff_summary = f"Appended section '{target}'"
        elif operation == "set_heading":
            if target is None or new_heading is None:
                return {
                    "status": "error",
                    "message": "set_heading requires target and new_heading",
                }
            for section in sections:
                if section.get("heading") == target:
                    section["heading"] = new_heading
                    diff_summary = f"Renamed section '{target}' to '{new_heading}'"
                    break
            else:
                return {
                    "status": "error",
                    "message": f"Section '{target}' not found",
                }
        else:
            return {
                "status": "error",
                "message": f"Unsupported operation '{operation}'",
            }

        from app.services.document_service import render_docx_from_source

        new_binary = await render_docx_from_source(source)

        return await _persist_edit(
            record=record,
            new_source=source,
            new_binary=new_binary,
            content_type=(
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document"
            ),
            file_type="docx",
            diff_summary=diff_summary,
        )
    except Exception as exc:
        logger.exception("edit_word_doc failed")
        return {"status": "error", "message": str(exc)}


# --- Tool: edit_google_doc ---


@agent_tool
async def edit_google_doc(
    tool_context: Any,
    document_id: str,
    operation: str,
    anchor: str,
    new_content: str,
) -> dict[str, Any]:
    """Edit a Google Doc via the Docs API and snapshot the BEFORE text.

    Unlike the binary doc classes, Google Docs are not re-rendered locally:
    we call ``GoogleDocsService.replace_section`` directly and append a row
    to ``document_versions`` whose ``source_snapshot`` is the BEFORE-text
    (used for soft undo).

    The Pikar ``document_id`` (UUID) is distinct from the Google Doc ID --
    the latter must be stored in ``record["source"]["google_doc_id"]``.

    Supported operations:
        * ``replace_section`` -- replace the section under heading
          ``anchor`` with ``new_content``.

    Args:
        tool_context: ADK tool context carrying user state and Google
            credentials (``google_provider_token``,
            ``google_refresh_token``).
        document_id: Pikar UUID of the document.
        operation: Currently only ``replace_section`` is supported.
        anchor: Exact heading text to anchor on.
        new_content: Replacement text.

    Returns:
        ``_workspace_command`` envelope on success, or
        ``{"status": "error", "message": ...}`` on failure.
    """
    try:
        source_service = await _get_source_service()
        record, err = await _load_owned_record(
            tool_context,
            document_id,
            source_service,
        )
        if err is not None:
            return err
        assert record is not None
        if record["doc_class"] != "google_doc":
            return {
                "status": "error",
                "message": f"Wrong tool for {record['doc_class']}",
            }

        source = record.get("source") or {}
        google_doc_id = source.get("google_doc_id")
        if not google_doc_id:
            return {
                "status": "error",
                "message": "Document source is missing google_doc_id",
            }

        if operation != "replace_section":
            return {
                "status": "error",
                "message": f"Unsupported operation '{operation}'",
            }

        google_service = _get_google_docs_service(tool_context)

        # Capture BEFORE-text for soft undo (best-effort — failures are
        # logged but don't block the edit; the snapshot is convenience for
        # soft undo, not a correctness requirement).
        try:
            before_text = google_service.read_doc_content(google_doc_id)
        except Exception as exc:
            logger.warning("Failed to read before-text from Google Doc: %s", exc)
            before_text = ""

        google_service.replace_section(google_doc_id, anchor, new_content)

        version_service = await _get_version_service()
        version = await version_service.append(
            document_id=record["document_id"],
            user_id=record["user_id"],
            source_snapshot={
                "google_doc_id": google_doc_id,
                "before_text": before_text,
                "anchor": anchor,
            },
            binary_url=record.get("binary_url") or "",
            diff_summary=f"Replaced section '{anchor}' in Google Doc",
            created_by="agent",
        )

        return {
            "_workspace_command": True,
            "commands": [
                {
                    "action": "replace_active",
                    "payload": {
                        "widget": {
                            "type": "document_viewer",
                            "data": {
                                "document_id": record["document_id"],
                                "doc_class": "google_doc",
                                "google_doc_id": google_doc_id,
                            },
                        },
                    },
                },
            ],
            "status": "success",
            "new_version_id": version["id"],
            "diff_summary": f"Replaced section '{anchor}' in Google Doc",
        }
    except Exception as exc:
        logger.exception("edit_google_doc failed")
        return {"status": "error", "message": str(exc)}


# --- Tool: list_document_versions ---


@agent_tool
async def list_document_versions(
    tool_context: Any,
    document_id: str,
    limit: int = 10,
) -> dict[str, Any]:
    """List versions for a document, newest first.

    Performs an ownership pre-check via :func:`_load_owned_record` before
    returning rows -- the version table is queried via a service-role
    client, so this gate is the only thing preventing cross-user reads.
    This is a tightening over the original plan, which omitted the check.

    Args:
        tool_context: ADK tool context carrying ``state.user_id``.
        document_id: UUID of the document.
        limit: Max number of versions to return (default 10).

    Returns:
        ``{"status": "success", "versions": [...]}`` on success, or
        ``{"status": "error", "message": ...}`` on failure.
    """
    try:
        source_service = await _get_source_service()
        record, err = await _load_owned_record(
            tool_context,
            document_id,
            source_service,
        )
        if err is not None:
            return err
        assert record is not None

        version_service = await _get_version_service()
        versions = await version_service.list(document_id, limit=limit)
        return {"status": "success", "versions": versions}
    except Exception as exc:
        logger.exception("list_document_versions failed")
        return {"status": "error", "message": str(exc)}


DOCUMENT_EDITOR_TOOLS: list = [
    read_document_content,
    edit_report_doc,
    edit_spreadsheet,
    edit_presentation,
    edit_word_doc,
    edit_google_doc,
    list_document_versions,
]


__all__ = [
    "DOCUMENT_EDITOR_TOOLS",
    "edit_google_doc",
    "edit_presentation",
    "edit_report_doc",
    "edit_spreadsheet",
    "edit_word_doc",
    "list_document_versions",
    "read_document_content",
]
