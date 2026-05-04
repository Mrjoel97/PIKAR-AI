# Document Viewer — Plan 1: Backend Foundation (B1 + B2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Spec:** `docs/superpowers/specs/2026-05-05-document-viewer-widget-design.md` (Sections 4 + 5 + sub-phases B1, B2).
> **Predecessor:** none — this plan is independent of Track A. Can begin immediately.
> **Successor:** `2026-05-05-document-viewer-frontend.md` (Plan 2, B3+B4) — depends on the API surfaces this plan creates.
>
> **Known deferral:** Google Sheets editing branch in `edit_spreadsheet` is stubbed with `"not yet implemented"` in this plan. The architecture supports it (per spec Section 4b), but the Google Sheets API integration (`app/integrations/google/sheets.py` currently only supports create) needs `read_sheet`, `update_cell`, `insert_row` methods added. Track as Plan 1.5 follow-up — does not block Plans 2 or 3.

**Goal:** Build the persistence + tool surfaces that let the agent read and edit documents (PDF/XLSX/PPTX/DOCX/Google Docs/Google Sheets) through a canonical-source model with version history.

**Architecture:** Two new tables (`document_sources`, `document_versions`) hold the canonical source JSON and the version chain. Five edit tools mutate source → re-render binary → write a version row. Lazy extraction forks user uploads to editable on first edit. ContentCreationAgent gets the new tools first.

**Tech Stack:** Python 3.10+, FastAPI, Google ADK, Pydantic, Supabase (PostgreSQL + JSONB + RLS), `python-pptx`, `openpyxl`, `pdfplumber`, `python-docx`, `mammoth` (DOCX→HTML for extraction), LibreOffice headless + `pdf2image` (PPTX→PNG slide rendering), pytest with pytest-asyncio, ruff, ty, uv.

---

## File Plan

### Create
- `supabase/migrations/20260505120000_document_editor.sql` — `document_sources` + `document_versions` tables + RLS
- `app/services/document_source_service.py` — read/write source JSONB; binary URL tracking
- `app/services/document_version_service.py` — version row insert; revert; redo
- `app/services/document_extraction_service.py` — per-format binary → source extraction (lazy)
- `app/services/slide_image_service.py` — PPTX → per-slide PNG via LibreOffice + pdf2image
- `app/agents/tools/document_editor.py` — `read_document_content` + 5 edit tools + `list_document_versions`
- `app/routers/document_viewer.py` — `GET /documents/{id}/source`, `GET /documents/{id}/versions`, `POST /documents/{id}/revert`
- `app/tests/unit/test_document_source_service.py`
- `app/tests/unit/test_document_version_service.py`
- `app/tests/unit/test_document_extraction_service.py`
- `app/tests/unit/test_slide_image_service.py`
- `app/tests/unit/test_document_editor_tools.py`
- `app/tests/integration/test_document_viewer_router.py`
- `app/tests/integration/test_lazy_fork_to_editable.py`

### Modify
- `app/services/document_service.py` — extract `render_pdf_from_source(source) -> bytes`, `render_xlsx_from_source(source) -> bytes`, `render_pptx_from_source(source) -> bytes`, `render_docx_from_source(source) -> bytes` as pure functions on top of existing `generate_*` methods
- `app/integrations/google/docs.py` — add `read_doc_content(doc_id) -> str` and `replace_section(doc_id, anchor, content)`
- `app/agents/tools/__init__.py` — register `DOCUMENT_EDITOR_TOOLS`
- `app/agents/shared_instructions.py` — add `DOCUMENT_EDITOR_INSTRUCTION` block
- `app/agents/content/agent.py` — import + register tools, append instruction to prompt
- `app/fast_api_app.py` — register `document_viewer` router
- `pyproject.toml` — add `pdfplumber`, `mammoth`, `pdf2image` to dependencies

---

## Task 1: Migration — document_sources + document_versions

**Files:**
- Create: `supabase/migrations/20260505120000_document_editor.sql`

- [ ] **Step 1: Write the migration**

```sql
-- supabase/migrations/20260505120000_document_editor.sql

-- moddatetime is required for the updated_at trigger below; idempotent.
CREATE EXTENSION IF NOT EXISTS moddatetime SCHEMA extensions;

CREATE TABLE document_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    document_id UUID NOT NULL UNIQUE,
    doc_class TEXT NOT NULL CHECK (doc_class IN
        ('report','spreadsheet','presentation','word','google_doc','google_sheet')),
    source JSONB,
    extracted_text TEXT,
    extracted_at TIMESTAMPTZ,
    forked_from_upload BOOLEAN DEFAULT false,
    binary_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_document_sources_user ON document_sources(user_id);
CREATE INDEX idx_document_sources_doc ON document_sources(document_id);

CREATE TABLE document_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    source_snapshot JSONB,
    binary_url TEXT NOT NULL,
    diff_summary TEXT,
    created_by TEXT NOT NULL CHECK (created_by IN ('agent','user','system')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_document_versions_doc ON document_versions(document_id, created_at DESC);

ALTER TABLE document_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_versions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users see their own document sources"
    ON document_sources FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users insert their own document sources"
    ON document_sources FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users update their own document sources"
    ON document_sources FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Service role full access on document_sources"
    ON document_sources FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Users see their own document versions"
    ON document_versions FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users insert their own document versions"
    ON document_versions FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Service role full access on document_versions"
    ON document_versions FOR ALL USING (auth.role() = 'service_role');

CREATE TRIGGER document_sources_updated_at
    BEFORE UPDATE ON document_sources
    FOR EACH ROW EXECUTE FUNCTION moddatetime(updated_at);
```

- [ ] **Step 2: Apply locally**

Run: `supabase db reset --local`

Expected: migration applies without errors.

- [ ] **Step 3: Verify schema**

Run:
```bash
supabase db psql --local -c "\d document_sources" -c "\d document_versions"
```

Expected: both tables exist, RLS enabled, indexes present, CHECK constraints visible on `doc_class` and `created_by`.

- [ ] **Step 4: Commit**

```bash
git add supabase/migrations/20260505120000_document_editor.sql
git commit -m "feat(doc-viewer): add document_sources + document_versions tables"
```

---

## Task 2: Add backend dependencies

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add deps**

In `pyproject.toml` `[project.dependencies]`, add (alphabetically):

```toml
"mammoth>=1.6,<2",
"pdfplumber>=0.10,<1",
"pdf2image>=1.17,<2",
```

Note: `python-pptx`, `openpyxl`, `python-docx` are already in deps (verify with `grep -E "python-pptx|openpyxl|python-docx" pyproject.toml`); skip if present.

- [ ] **Step 2: Sync**

Run: `uv sync`

Expected: lockfile updates, all packages install.

- [ ] **Step 3: Verify imports**

Run: `uv run python -c "import pdfplumber, mammoth, pdf2image; print('ok')"`

Expected: prints `ok`.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore(deps): add pdfplumber, mammoth, pdf2image for doc extraction"
```

---

## Task 3: DocumentSourceService — write tests

**Files:**
- Create: `app/tests/unit/test_document_source_service.py`

- [ ] **Step 1: Write the failing tests**

```python
# app/tests/unit/test_document_source_service.py
"""Tests for DocumentSourceService."""

from uuid import uuid4

import pytest

from app.services.document_source_service import DocumentSourceService


@pytest.fixture
async def service(supabase_client):
    return DocumentSourceService(supabase_client)


async def test_create_source_inserts_row(service):
    user_id = str(uuid4())
    document_id = str(uuid4())
    source = {"sections": [{"heading": "Intro", "content": "Hello"}]}

    row = await service.create(
        user_id=user_id,
        document_id=document_id,
        doc_class="report",
        source=source,
        binary_url="https://example.com/file.pdf",
    )

    assert row["document_id"] == document_id
    assert row["doc_class"] == "report"
    assert row["source"] == source
    assert row["binary_url"] == "https://example.com/file.pdf"
    assert row["forked_from_upload"] is False


async def test_get_source_returns_row(service):
    user_id = str(uuid4())
    document_id = str(uuid4())
    await service.create(
        user_id=user_id,
        document_id=document_id,
        doc_class="spreadsheet",
        source={"sheets": []},
        binary_url="https://example.com/x.xlsx",
    )

    row = await service.get(document_id)
    assert row is not None
    assert row["document_id"] == document_id


async def test_get_source_returns_none_for_unknown_id(service):
    row = await service.get(str(uuid4()))
    assert row is None


async def test_update_source_mutates_row_and_bumps_updated_at(service):
    user_id = str(uuid4())
    document_id = str(uuid4())
    await service.create(
        user_id=user_id,
        document_id=document_id,
        doc_class="report",
        source={"sections": []},
        binary_url="https://example.com/v1.pdf",
    )

    new_source = {"sections": [{"heading": "Updated", "content": "..."}]}
    row = await service.update_source(
        document_id=document_id,
        new_source=new_source,
        new_binary_url="https://example.com/v2.pdf",
    )

    assert row["source"] == new_source
    assert row["binary_url"] == "https://example.com/v2.pdf"


async def test_set_extracted_text_caches_text_and_timestamps(service):
    user_id = str(uuid4())
    document_id = str(uuid4())
    await service.create(
        user_id=user_id,
        document_id=document_id,
        doc_class="report",
        source=None,
        binary_url="https://example.com/upload.pdf",
    )

    row = await service.set_extracted_text(document_id, "Lorem ipsum")
    assert row["extracted_text"] == "Lorem ipsum"
    assert row["extracted_at"] is not None


async def test_mark_forked_sets_flag(service):
    user_id = str(uuid4())
    document_id = str(uuid4())
    await service.create(
        user_id=user_id,
        document_id=document_id,
        doc_class="report",
        source=None,
        binary_url="https://example.com/upload.pdf",
    )

    row = await service.mark_forked_from_upload(document_id)
    assert row["forked_from_upload"] is True
```

- [ ] **Step 2: Run, confirm fail**

Run: `uv run pytest app/tests/unit/test_document_source_service.py -v`

Expected: ImportError on `DocumentSourceService` (module not yet implemented).

---

## Task 4: DocumentSourceService — implement

**Files:**
- Create: `app/services/document_source_service.py`

- [ ] **Step 1: Implement**

```python
# app/services/document_source_service.py
"""Read/write the document_sources table."""

from datetime import UTC, datetime
from typing import Any

from supabase import AsyncClient


class DocumentSourceService:
    """CRUD for canonical document sources."""

    def __init__(self, client: AsyncClient):
        self._client = client

    async def create(
        self,
        *,
        user_id: str,
        document_id: str,
        doc_class: str,
        source: dict[str, Any] | None,
        binary_url: str | None,
        forked_from_upload: bool = False,
    ) -> dict[str, Any]:
        result = await self._client.table("document_sources").insert(
            {
                "user_id": user_id,
                "document_id": document_id,
                "doc_class": doc_class,
                "source": source,
                "binary_url": binary_url,
                "forked_from_upload": forked_from_upload,
            }
        ).execute()
        return result.data[0]

    async def get(self, document_id: str) -> dict[str, Any] | None:
        result = (
            await self._client.table("document_sources")
            .select("*")
            .eq("document_id", document_id)
            .maybe_single()
            .execute()
        )
        return result.data

    async def update_source(
        self,
        *,
        document_id: str,
        new_source: dict[str, Any],
        new_binary_url: str | None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"source": new_source}
        if new_binary_url is not None:
            payload["binary_url"] = new_binary_url
        result = (
            await self._client.table("document_sources")
            .update(payload)
            .eq("document_id", document_id)
            .execute()
        )
        return result.data[0]

    async def set_extracted_text(
        self, document_id: str, text: str
    ) -> dict[str, Any]:
        result = (
            await self._client.table("document_sources")
            .update(
                {
                    "extracted_text": text,
                    "extracted_at": datetime.now(UTC).isoformat(),
                }
            )
            .eq("document_id", document_id)
            .execute()
        )
        return result.data[0]

    async def mark_forked_from_upload(
        self, document_id: str
    ) -> dict[str, Any]:
        result = (
            await self._client.table("document_sources")
            .update({"forked_from_upload": True})
            .eq("document_id", document_id)
            .execute()
        )
        return result.data[0]
```

- [ ] **Step 2: Run tests, confirm green**

Run: `uv run pytest app/tests/unit/test_document_source_service.py -v`

Expected: 6 passed.

- [ ] **Step 3: Lint + types**

Run: `uv run ruff check app/services/document_source_service.py && uv run ty check app/services/document_source_service.py`

Expected: clean.

- [ ] **Step 4: Commit**

```bash
git add app/services/document_source_service.py app/tests/unit/test_document_source_service.py
git commit -m "feat(doc-viewer): add DocumentSourceService"
```

---

## Task 5: DocumentVersionService — write tests

**Files:**
- Create: `app/tests/unit/test_document_version_service.py`

- [ ] **Step 1: Write tests**

```python
# app/tests/unit/test_document_version_service.py
"""Tests for DocumentVersionService."""

from uuid import uuid4

import pytest

from app.services.document_version_service import DocumentVersionService


@pytest.fixture
async def service(supabase_client):
    return DocumentVersionService(supabase_client)


async def test_append_version_inserts_row(service):
    document_id = str(uuid4())
    user_id = str(uuid4())

    row = await service.append(
        document_id=document_id,
        user_id=user_id,
        source_snapshot={"sections": [{"heading": "v1"}]},
        binary_url="https://example.com/v1.pdf",
        diff_summary="Initial version",
        created_by="agent",
    )

    assert row["document_id"] == document_id
    assert row["created_by"] == "agent"
    assert row["diff_summary"] == "Initial version"


async def test_list_versions_returns_newest_first(service):
    document_id = str(uuid4())
    user_id = str(uuid4())

    for i in range(3):
        await service.append(
            document_id=document_id,
            user_id=user_id,
            source_snapshot={"v": i},
            binary_url=f"https://example.com/v{i}.pdf",
            diff_summary=f"version {i}",
            created_by="agent",
        )

    versions = await service.list(document_id, limit=10)
    assert len(versions) == 3
    assert versions[0]["diff_summary"] == "version 2"
    assert versions[2]["diff_summary"] == "version 0"


async def test_get_version_by_id(service):
    document_id = str(uuid4())
    user_id = str(uuid4())
    appended = await service.append(
        document_id=document_id,
        user_id=user_id,
        source_snapshot={"v": 1},
        binary_url="https://example.com/v1.pdf",
        diff_summary="x",
        created_by="agent",
    )

    fetched = await service.get(appended["id"])
    assert fetched["id"] == appended["id"]
```

- [ ] **Step 2: Run, confirm fail**

Run: `uv run pytest app/tests/unit/test_document_version_service.py -v`

Expected: ImportError.

---

## Task 6: DocumentVersionService — implement

**Files:**
- Create: `app/services/document_version_service.py`

- [ ] **Step 1: Implement**

```python
# app/services/document_version_service.py
"""Read/write the document_versions table."""

from typing import Any

from supabase import AsyncClient


class DocumentVersionService:
    """Insert and query document version rows."""

    def __init__(self, client: AsyncClient):
        self._client = client

    async def append(
        self,
        *,
        document_id: str,
        user_id: str,
        source_snapshot: dict[str, Any] | None,
        binary_url: str,
        diff_summary: str | None,
        created_by: str,
    ) -> dict[str, Any]:
        if created_by not in {"agent", "user", "system"}:
            raise ValueError(f"Invalid created_by: {created_by}")
        result = (
            await self._client.table("document_versions")
            .insert(
                {
                    "document_id": document_id,
                    "user_id": user_id,
                    "source_snapshot": source_snapshot,
                    "binary_url": binary_url,
                    "diff_summary": diff_summary,
                    "created_by": created_by,
                }
            )
            .execute()
        )
        return result.data[0]

    async def list(
        self, document_id: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        result = (
            await self._client.table("document_versions")
            .select("*")
            .eq("document_id", document_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data

    async def get(self, version_id: str) -> dict[str, Any] | None:
        result = (
            await self._client.table("document_versions")
            .select("*")
            .eq("id", version_id)
            .maybe_single()
            .execute()
        )
        return result.data
```

- [ ] **Step 2: Run, confirm green**

Run: `uv run pytest app/tests/unit/test_document_version_service.py -v`

Expected: 3 passed.

- [ ] **Step 3: Commit**

```bash
git add app/services/document_version_service.py app/tests/unit/test_document_version_service.py
git commit -m "feat(doc-viewer): add DocumentVersionService"
```

---

## Task 7: Refactor DocumentService — render-from-source

**Files:**
- Modify: `app/services/document_service.py`

This task adds four pure functions — `render_pdf_from_source`, `render_xlsx_from_source`, `render_pptx_from_source`, `render_docx_from_source` — that take source JSON and return bytes. Existing `generate_pdf` etc. methods stay; the new ones are thin wrappers over the existing builder helpers (`_build_pptx`, `_build_xlsx`, etc.).

- [ ] **Step 1: Open `app/services/document_service.py` and read the current method shapes** (lines 84-505 per `grep -n "def " app/services/document_service.py`).

- [ ] **Step 2: Add module-level functions after the `DocumentService` class**

Append at the end of the file:

```python
# ---------------------------------------------------------------------------
# Source-based render functions (pure, async — used by document_editor tools)
# ---------------------------------------------------------------------------


async def render_pdf_from_source(source: dict) -> bytes:
    """Render a markdown-source report to PDF bytes.

    `source` shape: {"title": str, "sections": [{"heading": str, "content": str}]}.
    """
    if "sections" not in source:
        raise ValueError("Report source must have 'sections' key")
    service = DocumentService()
    title = source.get("title", "Untitled")
    sections = source["sections"]
    return await service.generate_pdf(
        title=title,
        sections=sections,
        brand_result=source.get("brand_result"),
    )


async def render_xlsx_from_source(source: dict) -> bytes:
    """Render a sheet-schema source to XLSX bytes.

    `source` shape: {"sheets": [{"name": str, "rows": list[list[Any]]}]}.
    """
    if "sheets" not in source:
        raise ValueError("Spreadsheet source must have 'sheets' key")
    service = DocumentService()
    return await service.generate_xlsx(sheets=source["sheets"])


async def render_pptx_from_source(source: dict) -> bytes:
    """Render a slide-JSON source to PPTX bytes.

    `source` shape: {"title": str, "slides": [{"layout": str, "title": str,
                     "body": str, "speaker_notes": str | None}]}.
    """
    if "slides" not in source:
        raise ValueError("Presentation source must have 'slides' key")
    service = DocumentService()
    return await service.generate_pptx(
        title=source.get("title", "Untitled"),
        slides=source["slides"],
        brand_result=source.get("brand_result"),
    )


async def render_docx_from_source(source: dict) -> bytes:
    """Render a markdown-source word doc to DOCX bytes.

    `source` shape: {"title": str, "sections": [{"heading": str, "content": str}]}.
    """
    if "sections" not in source:
        raise ValueError("Word doc source must have 'sections' key")
    from docx import Document  # python-docx

    doc = Document()
    doc.add_heading(source.get("title", "Untitled"), level=1)
    for section in source["sections"]:
        doc.add_heading(section["heading"], level=2)
        for paragraph in section["content"].split("\n\n"):
            if paragraph.strip():
                doc.add_paragraph(paragraph)

    import io
    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()
```

- [ ] **Step 3: Add round-trip test**

Create `app/tests/unit/test_document_service_render_from_source.py`:

```python
# app/tests/unit/test_document_service_render_from_source.py
"""Round-trip tests for render-from-source functions."""

import pytest

from app.services.document_service import (
    render_docx_from_source,
    render_pdf_from_source,
    render_pptx_from_source,
    render_xlsx_from_source,
)


@pytest.mark.asyncio
async def test_render_pdf_from_source_returns_bytes():
    source = {
        "title": "Test Report",
        "sections": [
            {"heading": "Intro", "content": "Hello world."},
            {"heading": "Body", "content": "More content."},
        ],
    }
    result = await render_pdf_from_source(source)
    assert isinstance(result, bytes)
    assert result.startswith(b"%PDF")


@pytest.mark.asyncio
async def test_render_xlsx_from_source_returns_bytes():
    source = {
        "sheets": [
            {"name": "Sheet1", "rows": [["A", "B"], [1, 2]]},
        ]
    }
    result = await render_xlsx_from_source(source)
    assert isinstance(result, bytes)
    # XLSX is a ZIP container
    assert result.startswith(b"PK")


@pytest.mark.asyncio
async def test_render_pptx_from_source_returns_bytes():
    source = {
        "title": "Test",
        "slides": [
            {"layout": "title", "title": "Hello", "body": "", "speaker_notes": None},
        ],
    }
    result = await render_pptx_from_source(source)
    assert isinstance(result, bytes)
    assert result.startswith(b"PK")


@pytest.mark.asyncio
async def test_render_docx_from_source_returns_bytes():
    source = {
        "title": "Doc",
        "sections": [{"heading": "S1", "content": "Para 1.\n\nPara 2."}],
    }
    result = await render_docx_from_source(source)
    assert isinstance(result, bytes)
    assert result.startswith(b"PK")


@pytest.mark.asyncio
async def test_render_pdf_rejects_missing_sections():
    with pytest.raises(ValueError, match="sections"):
        await render_pdf_from_source({"title": "x"})
```

- [ ] **Step 4: Run tests, confirm green**

Run: `uv run pytest app/tests/unit/test_document_service_render_from_source.py -v`

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add app/services/document_service.py app/tests/unit/test_document_service_render_from_source.py
git commit -m "feat(doc-viewer): add render-from-source pure functions"
```

---

## Task 8: SlideImageService — write tests

**Files:**
- Create: `app/tests/unit/test_slide_image_service.py`

- [ ] **Step 1: Write tests**

```python
# app/tests/unit/test_slide_image_service.py
"""Tests for SlideImageService — PPTX → PNG strip."""

import pytest

from app.services.document_service import render_pptx_from_source
from app.services.slide_image_service import SlideImageService


@pytest.mark.asyncio
async def test_render_slides_to_pngs_returns_one_png_per_slide(tmp_path):
    source = {
        "title": "Test",
        "slides": [
            {"layout": "title", "title": f"Slide {i}", "body": "", "speaker_notes": None}
            for i in range(3)
        ],
    }
    pptx_bytes = await render_pptx_from_source(source)
    service = SlideImageService()

    pngs = await service.render_to_pngs(pptx_bytes)

    assert len(pngs) == 3
    for png in pngs:
        assert isinstance(png, bytes)
        assert png.startswith(b"\x89PNG")


@pytest.mark.asyncio
async def test_render_single_slide_returns_one_png():
    source = {
        "title": "X",
        "slides": [{"layout": "title", "title": "One", "body": "", "speaker_notes": None}],
    }
    pptx_bytes = await render_pptx_from_source(source)
    service = SlideImageService()

    png = await service.render_single_slide(pptx_bytes, slide_index=0)

    assert isinstance(png, bytes)
    assert png.startswith(b"\x89PNG")
```

- [ ] **Step 2: Run, confirm fail**

Run: `uv run pytest app/tests/unit/test_slide_image_service.py -v`

Expected: ImportError.

---

## Task 9: SlideImageService — implement

**Files:**
- Create: `app/services/slide_image_service.py`

- [ ] **Step 1: Implement**

```python
# app/services/slide_image_service.py
"""Render PPTX to per-slide PNG via LibreOffice headless + pdf2image."""

import asyncio
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

from pdf2image import convert_from_path

logger = logging.getLogger(__name__)

LIBREOFFICE_BIN = shutil.which("libreoffice") or shutil.which("soffice")


class LibreOfficeNotInstalledError(RuntimeError):
    """LibreOffice headless is required but not on PATH."""


class SlideImageService:
    """PPTX → PNG using LibreOffice → PDF → pdf2image → PNG."""

    def __init__(self, dpi: int = 150):
        self._dpi = dpi

    async def render_to_pngs(self, pptx_bytes: bytes) -> list[bytes]:
        if not LIBREOFFICE_BIN:
            raise LibreOfficeNotInstalledError(
                "LibreOffice (libreoffice/soffice) not found on PATH. "
                "Install it: apt-get install libreoffice on Linux, "
                "brew install --cask libreoffice on macOS."
            )

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            pptx_path = tmp_path / "input.pptx"
            pptx_path.write_bytes(pptx_bytes)

            await asyncio.to_thread(
                self._run_libreoffice,
                pptx_path=pptx_path,
                output_dir=tmp_path,
            )

            pdf_path = tmp_path / "input.pdf"
            if not pdf_path.exists():
                raise RuntimeError(
                    f"LibreOffice did not produce {pdf_path}. "
                    f"Check {tmp_path} for stderr."
                )

            images = await asyncio.to_thread(
                convert_from_path, str(pdf_path), dpi=self._dpi
            )

            png_bytes_list: list[bytes] = []
            for i, img in enumerate(images):
                png_path = tmp_path / f"slide_{i}.png"
                img.save(str(png_path), format="PNG")
                png_bytes_list.append(png_path.read_bytes())

            return png_bytes_list

    async def render_single_slide(
        self, pptx_bytes: bytes, slide_index: int
    ) -> bytes:
        # For now, render all and pick the requested. Optimization: build a
        # single-slide PPTX before conversion (saves 70% of LibreOffice time on
        # large decks); deferred to a follow-up.
        pngs = await self.render_to_pngs(pptx_bytes)
        if slide_index < 0 or slide_index >= len(pngs):
            raise IndexError(
                f"slide_index {slide_index} out of range (deck has {len(pngs)} slides)"
            )
        return pngs[slide_index]

    @staticmethod
    def _run_libreoffice(*, pptx_path: Path, output_dir: Path) -> None:
        result = subprocess.run(
            [
                LIBREOFFICE_BIN,
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                str(output_dir),
                str(pptx_path),
            ],
            capture_output=True,
            timeout=120,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"LibreOffice failed (rc={result.returncode}): {result.stderr.decode()}"
            )
```

- [ ] **Step 2: Run tests, confirm green (requires LibreOffice on PATH)**

Run: `uv run pytest app/tests/unit/test_slide_image_service.py -v`

Expected: 2 passed. If LibreOffice not installed, the test errors with a clear message — install it before continuing.

- [ ] **Step 3: Commit**

```bash
git add app/services/slide_image_service.py app/tests/unit/test_slide_image_service.py
git commit -m "feat(doc-viewer): add SlideImageService for PPTX→PNG"
```

---

## Task 10: DocumentExtractionService — write tests

**Files:**
- Create: `app/tests/unit/test_document_extraction_service.py`

- [ ] **Step 1: Write tests**

```python
# app/tests/unit/test_document_extraction_service.py
"""Tests for DocumentExtractionService — binary → source extraction."""

import pytest

from app.services.document_extraction_service import (
    DocumentExtractionService,
    UnsupportedFormatError,
)
from app.services.document_service import (
    render_docx_from_source,
    render_pdf_from_source,
    render_pptx_from_source,
    render_xlsx_from_source,
)


@pytest.fixture
def service():
    return DocumentExtractionService()


@pytest.mark.asyncio
async def test_extract_text_from_pdf(service):
    pdf = await render_pdf_from_source({
        "title": "Sample",
        "sections": [{"heading": "Intro", "content": "Hello world from extraction test."}],
    })

    text = await service.extract_text(binary=pdf, doc_class="report")

    assert "Hello world from extraction test." in text


@pytest.mark.asyncio
async def test_extract_text_from_xlsx(service):
    xlsx = await render_xlsx_from_source({
        "sheets": [{"name": "Data", "rows": [["Name", "Age"], ["Alice", 30]]}]
    })

    text = await service.extract_text(binary=xlsx, doc_class="spreadsheet")

    assert "Alice" in text
    assert "30" in text


@pytest.mark.asyncio
async def test_extract_text_from_pptx(service):
    pptx = await render_pptx_from_source({
        "title": "Deck",
        "slides": [
            {"layout": "title", "title": "Findings", "body": "Conclusion: ship it.",
             "speaker_notes": None},
        ],
    })

    text = await service.extract_text(binary=pptx, doc_class="presentation")

    assert "Findings" in text
    assert "ship it" in text


@pytest.mark.asyncio
async def test_extract_text_from_docx(service):
    docx = await render_docx_from_source({
        "title": "Doc",
        "sections": [{"heading": "S", "content": "Some unique paragraph text."}],
    })

    text = await service.extract_text(binary=docx, doc_class="word")

    assert "Some unique paragraph text." in text


@pytest.mark.asyncio
async def test_extract_text_raises_on_unsupported_class(service):
    with pytest.raises(UnsupportedFormatError):
        await service.extract_text(binary=b"...", doc_class="image")


@pytest.mark.asyncio
async def test_fork_to_source_pdf_produces_report_source(service):
    pdf = await render_pdf_from_source({
        "title": "Report",
        "sections": [{"heading": "S1", "content": "Para A.\n\nPara B."}],
    })

    source = await service.fork_to_source(binary=pdf, doc_class="report")

    assert "sections" in source
    assert isinstance(source["sections"], list)
    assert len(source["sections"]) >= 1


@pytest.mark.asyncio
async def test_fork_to_source_xlsx_produces_sheet_source(service):
    xlsx = await render_xlsx_from_source({
        "sheets": [{"name": "S", "rows": [["a", "b"], [1, 2]]}]
    })

    source = await service.fork_to_source(binary=xlsx, doc_class="spreadsheet")

    assert "sheets" in source
    assert source["sheets"][0]["rows"][0] == ["a", "b"]
```

- [ ] **Step 2: Run, confirm fail**

Run: `uv run pytest app/tests/unit/test_document_extraction_service.py -v`

Expected: ImportError.

---

## Task 11: DocumentExtractionService — implement

**Files:**
- Create: `app/services/document_extraction_service.py`

- [ ] **Step 1: Implement**

```python
# app/services/document_extraction_service.py
"""Lazy extraction: binary → text and binary → canonical source.

`extract_text` is called on agent's first read; cheap, returns plain text.
`fork_to_source` is called on agent's first edit; structured, generates the
canonical source JSON for future renders.
"""

import io
from typing import Any

import mammoth
import pdfplumber
from openpyxl import load_workbook
from pptx import Presentation


class UnsupportedFormatError(ValueError):
    """Raised when a doc class is not handled by extraction."""


class DocumentExtractionService:
    """Convert binary documents to text + structured source."""

    SUPPORTED_CLASSES = {"report", "spreadsheet", "presentation", "word"}

    async def extract_text(
        self, *, binary: bytes, doc_class: str
    ) -> str:
        if doc_class not in self.SUPPORTED_CLASSES:
            raise UnsupportedFormatError(
                f"Cannot extract text from doc_class={doc_class}"
            )
        if doc_class == "report":
            return self._pdf_to_text(binary)
        if doc_class == "spreadsheet":
            return self._xlsx_to_text(binary)
        if doc_class == "presentation":
            return self._pptx_to_text(binary)
        if doc_class == "word":
            return self._docx_to_text(binary)
        raise UnsupportedFormatError(doc_class)  # unreachable

    async def fork_to_source(
        self, *, binary: bytes, doc_class: str
    ) -> dict[str, Any]:
        if doc_class not in self.SUPPORTED_CLASSES:
            raise UnsupportedFormatError(
                f"Cannot fork doc_class={doc_class} to source"
            )
        if doc_class == "report":
            return self._pdf_to_source(binary)
        if doc_class == "spreadsheet":
            return self._xlsx_to_source(binary)
        if doc_class == "presentation":
            return self._pptx_to_source(binary)
        if doc_class == "word":
            return self._docx_to_source(binary)
        raise UnsupportedFormatError(doc_class)

    @staticmethod
    def _pdf_to_text(binary: bytes) -> str:
        chunks = []
        with pdfplumber.open(io.BytesIO(binary)) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                chunks.append(text)
        return "\n\n".join(chunks)

    @staticmethod
    def _xlsx_to_text(binary: bytes) -> str:
        wb = load_workbook(io.BytesIO(binary), read_only=True, data_only=True)
        chunks = []
        for sheet in wb.worksheets:
            chunks.append(f"# {sheet.title}")
            for row in sheet.iter_rows(values_only=True):
                chunks.append("\t".join(str(c) if c is not None else "" for c in row))
        return "\n".join(chunks)

    @staticmethod
    def _pptx_to_text(binary: bytes) -> str:
        prs = Presentation(io.BytesIO(binary))
        chunks = []
        for i, slide in enumerate(prs.slides):
            chunks.append(f"--- Slide {i + 1} ---")
            for shape in slide.shapes:
                if shape.has_text_frame:
                    for paragraph in shape.text_frame.paragraphs:
                        text = "".join(run.text for run in paragraph.runs)
                        if text.strip():
                            chunks.append(text)
        return "\n".join(chunks)

    @staticmethod
    def _docx_to_text(binary: bytes) -> str:
        result = mammoth.extract_raw_text(io.BytesIO(binary))
        return result.value

    def _pdf_to_source(self, binary: bytes) -> dict[str, Any]:
        # Naive: each page becomes a section with the whole page as content.
        # Better: detect headings via font size — deferred to follow-up.
        sections = []
        with pdfplumber.open(io.BytesIO(binary)) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                sections.append({
                    "heading": f"Page {i + 1}",
                    "content": text,
                })
        return {"title": "Imported PDF", "sections": sections}

    def _xlsx_to_source(self, binary: bytes) -> dict[str, Any]:
        wb = load_workbook(io.BytesIO(binary), data_only=True)
        sheets = []
        for sheet in wb.worksheets:
            rows = [list(row) for row in sheet.iter_rows(values_only=True)]
            sheets.append({"name": sheet.title, "rows": rows})
        return {"sheets": sheets}

    def _pptx_to_source(self, binary: bytes) -> dict[str, Any]:
        prs = Presentation(io.BytesIO(binary))
        slides = []
        for slide in prs.slides:
            title_text = ""
            body_text_parts = []
            for shape in slide.shapes:
                if shape.has_text_frame:
                    text = shape.text_frame.text
                    if shape.placeholder_format and shape.placeholder_format.idx == 0:
                        title_text = text
                    else:
                        body_text_parts.append(text)
            slides.append({
                "layout": "title_and_content",
                "title": title_text,
                "body": "\n".join(body_text_parts),
                "speaker_notes": (
                    slide.notes_slide.notes_text_frame.text
                    if slide.has_notes_slide
                    else None
                ),
            })
        return {"title": "Imported Deck", "slides": slides}

    def _docx_to_source(self, binary: bytes) -> dict[str, Any]:
        from docx import Document

        doc = Document(io.BytesIO(binary))
        sections = []
        current_heading = "Document"
        current_content: list[str] = []

        for para in doc.paragraphs:
            if para.style.name.startswith("Heading"):
                if current_content:
                    sections.append({
                        "heading": current_heading,
                        "content": "\n\n".join(current_content),
                    })
                    current_content = []
                current_heading = para.text
            elif para.text.strip():
                current_content.append(para.text)

        if current_content:
            sections.append({
                "heading": current_heading,
                "content": "\n\n".join(current_content),
            })

        return {"title": "Imported Document", "sections": sections}
```

- [ ] **Step 2: Run tests, confirm green**

Run: `uv run pytest app/tests/unit/test_document_extraction_service.py -v`

Expected: 7 passed.

- [ ] **Step 3: Commit**

```bash
git add app/services/document_extraction_service.py app/tests/unit/test_document_extraction_service.py
git commit -m "feat(doc-viewer): add DocumentExtractionService"
```

---

## Task 12: Extend Google Docs integration with read + replace

**Files:**
- Modify: `app/integrations/google/docs.py`

- [ ] **Step 1: Add `read_doc_content` and `replace_section` to `GoogleDocsService`**

After the existing `append_text` method in `app/integrations/google/docs.py`, add:

```python
    def read_doc_content(self, document_id: str) -> str:
        """Return the document body as plain text."""
        doc = self.docs.documents().get(documentId=document_id).execute()
        body = doc.get("body", {})
        chunks: list[str] = []
        for element in body.get("content", []):
            paragraph = element.get("paragraph")
            if not paragraph:
                continue
            for run in paragraph.get("elements", []):
                text_run = run.get("textRun")
                if text_run:
                    chunks.append(text_run.get("content", ""))
        return "".join(chunks)

    def replace_section(
        self,
        document_id: str,
        anchor: str,
        new_content: str,
    ) -> dict:
        """Find the heading `anchor` in the doc, replace its body until the
        next heading with `new_content`. Returns the API response.

        Anchor matching is exact (case-sensitive).
        """
        doc = self.docs.documents().get(documentId=document_id).execute()
        body = doc.get("body", {}).get("content", [])

        # Locate anchor heading + next heading boundaries
        anchor_start: int | None = None
        section_end: int | None = None
        in_anchor = False
        for element in body:
            paragraph = element.get("paragraph")
            if not paragraph:
                continue
            style = paragraph.get("paragraphStyle", {}).get("namedStyleType", "")
            text = "".join(
                r.get("textRun", {}).get("content", "")
                for r in paragraph.get("elements", [])
            ).strip()

            if style.startswith("HEADING") and text == anchor:
                anchor_start = element["endIndex"]
                in_anchor = True
                continue
            if in_anchor and style.startswith("HEADING"):
                section_end = element["startIndex"]
                break

        if anchor_start is None:
            raise ValueError(f"Anchor heading '{anchor}' not found")
        if section_end is None:
            section_end = body[-1]["endIndex"] - 1  # to end of doc

        requests = [
            {"deleteContentRange": {"range": {
                "startIndex": anchor_start, "endIndex": section_end
            }}},
            {"insertText": {"location": {"index": anchor_start}, "text": new_content}},
        ]
        return self.docs.documents().batchUpdate(
            documentId=document_id, body={"requests": requests}
        ).execute()
```

- [ ] **Step 2: Add unit test**

Create `app/tests/unit/test_google_docs_extensions.py`:

```python
# app/tests/unit/test_google_docs_extensions.py
"""Tests for Google Docs read_doc_content + replace_section.

Uses mock Google API responses (full integration covered in integration suite).
"""

from unittest.mock import MagicMock

import pytest

from app.integrations.google.docs import GoogleDocsService


def _mock_doc_response(*, content: list[dict]) -> dict:
    return {"body": {"content": content}}


def test_read_doc_content_concatenates_text_runs():
    service = GoogleDocsService(credentials=MagicMock())
    service._docs_service = MagicMock()
    service._docs_service.documents.return_value.get.return_value.execute.return_value = (
        _mock_doc_response(content=[
            {"paragraph": {"elements": [
                {"textRun": {"content": "Hello "}},
                {"textRun": {"content": "world."}},
            ]}}
        ])
    )

    result = service.read_doc_content("doc-1")

    assert result == "Hello world."


def test_replace_section_raises_when_anchor_missing():
    service = GoogleDocsService(credentials=MagicMock())
    service._docs_service = MagicMock()
    service._docs_service.documents.return_value.get.return_value.execute.return_value = (
        _mock_doc_response(content=[
            {"paragraph": {
                "paragraphStyle": {"namedStyleType": "NORMAL_TEXT"},
                "elements": [{"textRun": {"content": "no headings here"}}],
            }, "endIndex": 20}
        ])
    )

    with pytest.raises(ValueError, match="Anchor heading"):
        service.replace_section("doc-1", "Missing", "x")
```

- [ ] **Step 3: Run tests, confirm green**

Run: `uv run pytest app/tests/unit/test_google_docs_extensions.py -v`

Expected: 2 passed.

- [ ] **Step 4: Commit**

```bash
git add app/integrations/google/docs.py app/tests/unit/test_google_docs_extensions.py
git commit -m "feat(doc-viewer): extend Google Docs with read + replace_section"
```

---

## Task 13: document_editor tools — write tests for read_document_content

**Files:**
- Create: `app/tests/unit/test_document_editor_tools.py`

- [ ] **Step 1: Write the test for `read_document_content`**

```python
# app/tests/unit/test_document_editor_tools.py
"""Tests for document_editor agent tools.

Each tool returns a dict with status="success"|"error" and optionally
a `_workspace_command` envelope (for re-render notifications).
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest


@pytest.fixture
def tool_context():
    """Mock ADK tool context with state dict."""
    ctx = MagicMock()
    ctx.state = {"user_id": str(uuid4()), "agent_id": "test-agent"}
    return ctx


@pytest.fixture
def mock_services(monkeypatch):
    """Patch the service factories used inside document_editor."""
    source_service = AsyncMock()
    version_service = AsyncMock()
    extraction_service = AsyncMock()

    from app.agents.tools import document_editor

    monkeypatch.setattr(
        document_editor,
        "_get_source_service",
        AsyncMock(return_value=source_service),
    )
    monkeypatch.setattr(
        document_editor,
        "_get_version_service",
        AsyncMock(return_value=version_service),
    )
    monkeypatch.setattr(
        document_editor,
        "_get_extraction_service",
        lambda: extraction_service,
    )
    return source_service, version_service, extraction_service


@pytest.mark.asyncio
async def test_read_document_content_returns_cached_text(tool_context, mock_services):
    source_service, _, _ = mock_services
    document_id = str(uuid4())
    source_service.get.return_value = {
        "document_id": document_id,
        "doc_class": "report",
        "extracted_text": "Cached text from prior read.",
        "source": None,
    }

    from app.agents.tools.document_editor import read_document_content

    result = await read_document_content(tool_context, document_id=document_id)

    assert result["status"] == "success"
    assert "Cached text from prior read." in result["text"]
    assert result["truncated"] is False


@pytest.mark.asyncio
async def test_read_document_content_triggers_lazy_extraction(
    tool_context, mock_services, monkeypatch
):
    source_service, _, extraction_service = mock_services
    document_id = str(uuid4())
    source_service.get.return_value = {
        "document_id": document_id,
        "doc_class": "report",
        "extracted_text": None,  # not yet extracted
        "source": None,
        "binary_url": "https://example.com/upload.pdf",
    }
    extraction_service.extract_text = AsyncMock(return_value="Freshly extracted.")
    source_service.set_extracted_text = AsyncMock(
        return_value={"extracted_text": "Freshly extracted."}
    )

    fake_binary = b"%PDF-1.4 ..."

    async def fake_fetch(url):
        return fake_binary

    monkeypatch.setattr(
        "app.agents.tools.document_editor._fetch_binary", fake_fetch
    )

    from app.agents.tools.document_editor import read_document_content

    result = await read_document_content(tool_context, document_id=document_id)

    assert result["status"] == "success"
    assert "Freshly extracted." in result["text"]
    extraction_service.extract_text.assert_awaited_once_with(
        binary=fake_binary, doc_class="report"
    )
    source_service.set_extracted_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_read_document_content_truncates_long_text(tool_context, mock_services):
    source_service, _, _ = mock_services
    long_text = "word " * 50_000  # ~50K tokens
    source_service.get.return_value = {
        "document_id": "x",
        "doc_class": "report",
        "extracted_text": long_text,
        "source": None,
    }

    from app.agents.tools.document_editor import read_document_content

    result = await read_document_content(tool_context, document_id="x")

    assert result["status"] == "success"
    assert result["truncated"] is True
    # ~10K tokens cap
    assert len(result["text"].split()) <= 11_000
```

- [ ] **Step 2: Run, confirm fail**

Run: `uv run pytest app/tests/unit/test_document_editor_tools.py -v`

Expected: ImportError on `app.agents.tools.document_editor`.

---

## Task 14: document_editor — implement read_document_content

**Files:**
- Create: `app/agents/tools/document_editor.py`

- [ ] **Step 1: Implement the module skeleton + `read_document_content`**

```python
# app/agents/tools/document_editor.py
"""Document editor agent tools.

Six tools: read_document_content + 5 edit tools (one per doc class) +
list_document_versions. Each edit tool mutates the canonical source,
re-renders the binary, writes a version row, and returns a
_workspace_command marker so the SSE pipeline can notify the viewer.
"""

import logging
from typing import Any, Literal

import httpx

from app.agents.tools.base import agent_tool
from app.services.document_extraction_service import DocumentExtractionService
from app.services.document_source_service import DocumentSourceService
from app.services.document_version_service import DocumentVersionService

logger = logging.getLogger(__name__)

# Token cap for read_document_content (~10K tokens, ~7500 words)
TEXT_TOKEN_CAP_WORDS = 7500


# ---------------------------------------------------------------------------
# Service factories — wrap so they're patchable in tests
# ---------------------------------------------------------------------------


async def _get_source_service() -> DocumentSourceService:
    from app.services.supabase_client import get_async_client
    return DocumentSourceService(await get_async_client())


async def _get_version_service() -> DocumentVersionService:
    from app.services.supabase_client import get_async_client
    return DocumentVersionService(await get_async_client())


def _get_extraction_service() -> DocumentExtractionService:
    return DocumentExtractionService()


async def _fetch_binary(url: str) -> bytes:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.content


def _truncate_text(text: str, cap_words: int = TEXT_TOKEN_CAP_WORDS) -> tuple[str, bool]:
    words = text.split()
    if len(words) <= cap_words:
        return text, False
    return " ".join(words[:cap_words]) + "\n\n[...truncated...]", True


async def _load_owned_record(
    tool_context: Any,
    document_id: str,
    source_service: DocumentSourceService,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Fetch a document_sources row and verify it belongs to the calling user.

    Returns (record, None) on success or (None, error_response) if missing /
    not owned. Every tool in this module MUST use this instead of calling
    source_service.get() directly — the agent runs under a service client
    so RLS doesn't gate access. We enforce ownership in code.
    """
    record = await source_service.get(document_id)
    if record is None:
        return None, {"status": "error", "message": f"Document {document_id} not found"}
    user_id = tool_context.state.get("user_id")
    if not user_id or record["user_id"] != user_id:
        return None, {"status": "error", "message": "Document not accessible"}
    return record, None


# ---------------------------------------------------------------------------
# Tool: read_document_content
# ---------------------------------------------------------------------------


@agent_tool
async def read_document_content(
    tool_context: Any,
    document_id: str,
    page_range: list[int] | None = None,
) -> dict[str, Any]:
    """Read text + structure from a document into the agent's context.

    Use when the user asks about a doc's contents, references something
    inside it, or before calling any edit_* tool that needs the current
    state to make a sensible change. Triggers lazy text extraction on
    first call for user uploads.

    Args:
        tool_context: ADK tool context.
        document_id: UUID of the document.
        page_range: 1-indexed pages to read (None = whole doc, capped).

    Returns:
        status: "success" | "error"
        text: extracted text (capped at ~10K tokens)
        structure: {type, page_count?, sheet_names?, slide_count?}
        truncated: bool — true when content exceeded the token cap
    """
    try:
        source_service = await _get_source_service()
        record, err = await _load_owned_record(tool_context, document_id, source_service)
        if err is not None:
            return err
        assert record is not None

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
                binary=binary, doc_class=record["doc_class"]
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
    except Exception as e:
        logger.exception("read_document_content failed")
        return {"status": "error", "message": str(e)}


# Edit tools follow in subsequent tasks.

DOCUMENT_EDITOR_TOOLS: list = [read_document_content]
```

- [ ] **Step 2: Run tests, confirm 3 pass**

Run: `uv run pytest app/tests/unit/test_document_editor_tools.py -v`

Expected: 3 passed (the three `read_document_content` tests).

- [ ] **Step 3: Commit**

```bash
git add app/agents/tools/document_editor.py app/tests/unit/test_document_editor_tools.py
git commit -m "feat(doc-viewer): add read_document_content tool"
```

---

## Task 15: edit_report_doc — write test + implement

**Files:**
- Modify: `app/tests/unit/test_document_editor_tools.py` (add test)
- Modify: `app/agents/tools/document_editor.py` (add tool)

> **Ownership check (applies to Tasks 15-19):** Every edit tool in this plan MUST replace the pattern
> ```python
> record = await source_service.get(document_id)
> if record is None:
>     return {"status": "error", "message": "Document not found"}
> ```
> with
> ```python
> record, err = await _load_owned_record(tool_context, document_id, source_service)
> if err is not None:
>     return err
> assert record is not None
> ```
> This enforces that the calling user owns the document. The helper is defined in Task 14. Tests in Tasks 15-19 already pass `tool_context.state["user_id"]` matching `record["user_id"]`, so they exercise the success path; add one negative test in Task 15 below to exercise the failure path.

- [ ] **Step 1: Append test**

Append to `app/tests/unit/test_document_editor_tools.py`:

```python
@pytest.mark.asyncio
async def test_edit_report_doc_replace_section(tool_context, mock_services, monkeypatch):
    source_service, version_service, _ = mock_services
    document_id = str(uuid4())
    source_service.get.return_value = {
        "document_id": document_id,
        "doc_class": "report",
        "user_id": tool_context.state["user_id"],
        "source": {
            "title": "Report",
            "sections": [
                {"heading": "Summary", "content": "Old summary."},
                {"heading": "Body", "content": "Body."},
            ],
        },
        "binary_url": "https://example.com/v1.pdf",
    }
    source_service.update_source.return_value = {"binary_url": "https://example.com/v2.pdf"}
    version_service.append.return_value = {"id": "version-uuid"}

    async def fake_render(source):
        return b"%PDF-fake"

    monkeypatch.setattr(
        "app.services.document_service.render_pdf_from_source", fake_render
    )

    async def fake_upload(*, user_id, content, mime_type, filename):
        return "https://example.com/v2.pdf"

    monkeypatch.setattr(
        "app.agents.tools.document_editor._upload_render", fake_upload
    )

    from app.agents.tools.document_editor import edit_report_doc

    result = await edit_report_doc(
        tool_context,
        document_id=document_id,
        op="replace_section",
        target="Summary",
        content="Updated summary.",
    )

    assert result["status"] == "success"
    assert result["new_render_url"] == "https://example.com/v2.pdf"
    assert "Replaced" in result["diff_summary"]
    source_service.update_source.assert_awaited_once()
    version_service.append.assert_awaited_once()


@pytest.mark.asyncio
async def test_edit_report_doc_target_not_found(tool_context, mock_services):
    source_service, _, _ = mock_services
    source_service.get.return_value = {
        "document_id": "x",
        "doc_class": "report",
        "user_id": tool_context.state["user_id"],
        "source": {"title": "R", "sections": [{"heading": "Intro", "content": ""}]},
        "binary_url": "https://example.com/v1.pdf",
    }

    from app.agents.tools.document_editor import edit_report_doc

    result = await edit_report_doc(
        tool_context, document_id="x", op="replace_section",
        target="Missing", content="x",
    )

    assert result["status"] == "error"
    assert "Missing" in result["message"]


@pytest.mark.asyncio
async def test_edit_report_doc_rejects_other_users_doc(tool_context, mock_services):
    """Ownership check: document_id owned by a different user_id is rejected."""
    source_service, _, _ = mock_services
    source_service.get.return_value = {
        "document_id": "x",
        "doc_class": "report",
        "user_id": "different-user-id",
        "source": {"title": "R", "sections": []},
        "binary_url": "https://example.com/v1.pdf",
    }

    from app.agents.tools.document_editor import edit_report_doc

    result = await edit_report_doc(
        tool_context, document_id="x", op="rewrite", content="x",
    )

    assert result["status"] == "error"
    assert "not accessible" in result["message"].lower()
```

- [ ] **Step 2: Run, confirm fail**

Run: `uv run pytest app/tests/unit/test_document_editor_tools.py::test_edit_report_doc_replace_section -v`

Expected: ImportError on `edit_report_doc`.

- [ ] **Step 3: Implement**

Append to `app/agents/tools/document_editor.py` (before the `DOCUMENT_EDITOR_TOOLS` list — and update the list to include the new tool):

```python
# ---------------------------------------------------------------------------
# Helpers shared across edit tools
# ---------------------------------------------------------------------------

async def _upload_render(
    *, user_id: str, content: bytes, mime_type: str, filename: str
) -> str:
    """Upload re-rendered binary to storage and return a signed URL."""
    from app.services.document_service import DocumentService

    service = DocumentService()
    return await service._upload_document(
        user_id=user_id,
        content=content,
        mime_type=mime_type,
        filename=filename,
    )


async def _persist_edit(
    *,
    record: dict,
    new_source: dict,
    new_binary: bytes,
    mime_type: str,
    filename: str,
    diff_summary: str,
) -> dict[str, Any]:
    """Common path: upload, update source row, append version."""
    new_url = await _upload_render(
        user_id=record["user_id"],
        content=new_binary,
        mime_type=mime_type,
        filename=filename,
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


# ---------------------------------------------------------------------------
# Tool: edit_report_doc
# ---------------------------------------------------------------------------


@agent_tool
async def edit_report_doc(
    tool_context: Any,
    document_id: str,
    op: Literal["replace_section", "append_section", "rewrite"],
    target: str | None = None,
    content: str = "",
) -> dict[str, Any]:
    """Edit a markdown-source report.

    Mutates the canonical source, re-renders PDF, returns the new render
    URL. Creates a new version row. Use after read_document_content so
    you know the current structure.

    Args:
        document_id: UUID.
        op: replace_section | append_section | rewrite.
        target: heading anchor for replace_section (ignored otherwise).
        content: markdown content to insert / rewrite to.
    """
    try:
        source_service = await _get_source_service()
        record, err = await _load_owned_record(tool_context, document_id, source_service)
        if err is not None:
            return err
        assert record is not None
        if record["doc_class"] != "report":
            return {"status": "error",
                    "message": f"Wrong tool for doc_class={record['doc_class']}"}

        source = dict(record["source"] or {"title": "Untitled", "sections": []})
        sections = list(source.get("sections", []))

        if op == "replace_section":
            if target is None:
                return {"status": "error", "message": "replace_section needs target"}
            for i, sec in enumerate(sections):
                if sec["heading"] == target:
                    sections[i] = {"heading": target, "content": content}
                    diff_summary = f"Replaced section '{target}'"
                    break
            else:
                return {"status": "error",
                        "message": f"Section '{target}' not found"}
        elif op == "append_section":
            heading = target or f"Section {len(sections) + 1}"
            sections.append({"heading": heading, "content": content})
            diff_summary = f"Appended section '{heading}'"
        elif op == "rewrite":
            sections = [{"heading": "Document", "content": content}]
            diff_summary = "Rewrote entire report"
        else:
            return {"status": "error", "message": f"Unknown op: {op}"}

        new_source = {**source, "sections": sections}

        from app.services.document_service import render_pdf_from_source
        new_binary = await render_pdf_from_source(new_source)

        return await _persist_edit(
            record=record,
            new_source=new_source,
            new_binary=new_binary,
            mime_type="application/pdf",
            filename=f"{source.get('title', 'report')}.pdf",
            diff_summary=diff_summary,
        )
    except Exception as e:
        logger.exception("edit_report_doc failed")
        return {"status": "error", "message": str(e)}


DOCUMENT_EDITOR_TOOLS = [read_document_content, edit_report_doc]
```

- [ ] **Step 4: Run tests, confirm green**

Run: `uv run pytest app/tests/unit/test_document_editor_tools.py -v`

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add app/agents/tools/document_editor.py app/tests/unit/test_document_editor_tools.py
git commit -m "feat(doc-viewer): add edit_report_doc tool"
```

---

## Task 16: edit_spreadsheet — write test + implement

**Files:**
- Modify: `app/tests/unit/test_document_editor_tools.py` (append test)
- Modify: `app/agents/tools/document_editor.py` (append tool)

- [ ] **Step 1: Append test**

```python
@pytest.mark.asyncio
async def test_edit_spreadsheet_set_cell(tool_context, mock_services, monkeypatch):
    source_service, version_service, _ = mock_services
    document_id = str(uuid4())
    source_service.get.return_value = {
        "document_id": document_id,
        "doc_class": "spreadsheet",
        "user_id": tool_context.state["user_id"],
        "source": {
            "sheets": [{"name": "Sheet1", "rows": [["A", "B"], [1, 2]]}],
        },
        "binary_url": "https://example.com/v1.xlsx",
    }
    version_service.append.return_value = {"id": "version-uuid"}

    async def fake_render(source):
        return b"PK-fake-xlsx"

    monkeypatch.setattr(
        "app.services.document_service.render_xlsx_from_source", fake_render
    )

    async def fake_upload(**kwargs):
        return "https://example.com/v2.xlsx"

    monkeypatch.setattr(
        "app.agents.tools.document_editor._upload_render", fake_upload
    )

    from app.agents.tools.document_editor import edit_spreadsheet

    result = await edit_spreadsheet(
        tool_context,
        document_id=document_id,
        op="set_cell",
        sheet="Sheet1",
        cell="B2",
        values=[42],
    )

    assert result["status"] == "success"
    assert result["new_render_url"] == "https://example.com/v2.xlsx"
    update_call = source_service.update_source.await_args
    new_source = update_call.kwargs["new_source"]
    assert new_source["sheets"][0]["rows"][1][1] == 42
```

- [ ] **Step 2: Implement `edit_spreadsheet`**

Append to `app/agents/tools/document_editor.py`:

```python
def _cell_to_indices(cell: str) -> tuple[int, int]:
    """A1 → (row, col), zero-indexed."""
    import re
    m = re.match(r"^([A-Z]+)(\d+)$", cell.upper())
    if not m:
        raise ValueError(f"Invalid cell reference: {cell}")
    col_letters, row_str = m.groups()
    col = 0
    for ch in col_letters:
        col = col * 26 + (ord(ch) - ord("A") + 1)
    return int(row_str) - 1, col - 1


@agent_tool
async def edit_spreadsheet(
    tool_context: Any,
    document_id: str,
    op: Literal["set_cell", "insert_row", "delete_row", "set_formula", "rename_sheet"],
    sheet: str,
    cell: str | None = None,
    row: int | None = None,
    values: list[Any] | None = None,
    formula: str | None = None,
) -> dict[str, Any]:
    """Edit an XLSX/CSV spreadsheet OR a Google Sheet.

    Dispatches by document class: local XLSX/CSV mutates the source via
    openpyxl and re-renders; Google Sheets uses the Sheets API directly.
    Caller doesn't need to distinguish — the tool reads doc_class from
    document_sources and routes appropriately.

    Args:
        document_id: UUID.
        op: set_cell | insert_row | delete_row | set_formula | rename_sheet.
        sheet: sheet name.
        cell: A1-style for set_cell / set_formula.
        row: 1-indexed for insert/delete.
        values: cell value(s).
        formula: for set_formula.
    """
    try:
        source_service = await _get_source_service()
        record, err = await _load_owned_record(tool_context, document_id, source_service)
        if err is not None:
            return err
        assert record is not None
        if record["doc_class"] not in {"spreadsheet", "google_sheet"}:
            return {"status": "error",
                    "message": f"Wrong tool for {record['doc_class']}"}

        if record["doc_class"] == "google_sheet":
            return {"status": "error",
                    "message": "Google Sheets editing not yet implemented"}

        source = dict(record["source"] or {"sheets": []})
        sheets = list(source.get("sheets", []))

        target_idx = next(
            (i for i, s in enumerate(sheets) if s["name"] == sheet), None
        )
        if target_idx is None:
            return {"status": "error", "message": f"Sheet '{sheet}' not found"}

        target = dict(sheets[target_idx])
        rows = [list(r) for r in target.get("rows", [])]

        if op == "set_cell":
            if cell is None or values is None or not values:
                return {"status": "error",
                        "message": "set_cell needs cell + values"}
            r, c = _cell_to_indices(cell)
            while len(rows) <= r:
                rows.append([])
            while len(rows[r]) <= c:
                rows[r].append(None)
            rows[r][c] = values[0]
            diff_summary = f"Set {sheet}!{cell} = {values[0]}"
        elif op == "insert_row":
            if row is None or values is None:
                return {"status": "error",
                        "message": "insert_row needs row + values"}
            rows.insert(row - 1, list(values))
            diff_summary = f"Inserted row at {sheet}!{row}"
        elif op == "delete_row":
            if row is None:
                return {"status": "error", "message": "delete_row needs row"}
            if not (1 <= row <= len(rows)):
                return {"status": "error",
                        "message": f"row {row} out of range"}
            del rows[row - 1]
            diff_summary = f"Deleted row {sheet}!{row}"
        elif op == "set_formula":
            if cell is None or formula is None:
                return {"status": "error",
                        "message": "set_formula needs cell + formula"}
            r, c = _cell_to_indices(cell)
            while len(rows) <= r:
                rows.append([])
            while len(rows[r]) <= c:
                rows[r].append(None)
            rows[r][c] = formula
            diff_summary = f"Set formula at {sheet}!{cell}"
        elif op == "rename_sheet":
            if values is None or not values:
                return {"status": "error",
                        "message": "rename_sheet needs values=[new_name]"}
            target["name"] = values[0]
            diff_summary = f"Renamed sheet '{sheet}' to '{values[0]}'"
        else:
            return {"status": "error", "message": f"Unknown op: {op}"}

        target["rows"] = rows
        sheets[target_idx] = target
        new_source = {**source, "sheets": sheets}

        from app.services.document_service import render_xlsx_from_source
        new_binary = await render_xlsx_from_source(new_source)

        return await _persist_edit(
            record=record,
            new_source=new_source,
            new_binary=new_binary,
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename="spreadsheet.xlsx",
            diff_summary=diff_summary,
        )
    except Exception as e:
        logger.exception("edit_spreadsheet failed")
        return {"status": "error", "message": str(e)}


DOCUMENT_EDITOR_TOOLS = [
    read_document_content, edit_report_doc, edit_spreadsheet,
]
```

- [ ] **Step 3: Run tests, confirm green**

Run: `uv run pytest app/tests/unit/test_document_editor_tools.py -v`

Expected: 7 passed.

- [ ] **Step 4: Commit**

```bash
git add app/agents/tools/document_editor.py app/tests/unit/test_document_editor_tools.py
git commit -m "feat(doc-viewer): add edit_spreadsheet tool"
```

---

## Task 17: edit_presentation — write test + implement

**Files:**
- Modify: `app/tests/unit/test_document_editor_tools.py` (append test)
- Modify: `app/agents/tools/document_editor.py` (append tool)

- [ ] **Step 1: Append test**

```python
@pytest.mark.asyncio
async def test_edit_presentation_edit_text(tool_context, mock_services, monkeypatch):
    source_service, version_service, _ = mock_services
    document_id = str(uuid4())
    source_service.get.return_value = {
        "document_id": document_id,
        "doc_class": "presentation",
        "user_id": tool_context.state["user_id"],
        "source": {
            "title": "Deck",
            "slides": [
                {"layout": "title", "title": "Old", "body": "", "speaker_notes": None},
                {"layout": "title", "title": "Slide 2", "body": "Content",
                 "speaker_notes": None},
            ],
        },
        "binary_url": "https://example.com/v1.pptx",
    }
    version_service.append.return_value = {"id": "version-uuid"}

    async def fake_render(source):
        return b"PK-fake-pptx"

    monkeypatch.setattr(
        "app.services.document_service.render_pptx_from_source", fake_render
    )

    async def fake_upload(**kwargs):
        return "https://example.com/v2.pptx"

    monkeypatch.setattr(
        "app.agents.tools.document_editor._upload_render", fake_upload
    )

    from app.agents.tools.document_editor import edit_presentation

    result = await edit_presentation(
        tool_context,
        document_id=document_id,
        op="edit_text",
        slide_index=0,
        content="Updated Title",
    )

    assert result["status"] == "success"
    update_call = source_service.update_source.await_args
    new_source = update_call.kwargs["new_source"]
    assert new_source["slides"][0]["title"] == "Updated Title"


@pytest.mark.asyncio
async def test_edit_presentation_insert_slide(tool_context, mock_services, monkeypatch):
    source_service, version_service, _ = mock_services
    document_id = str(uuid4())
    source_service.get.return_value = {
        "document_id": document_id,
        "doc_class": "presentation",
        "user_id": tool_context.state["user_id"],
        "source": {
            "title": "Deck",
            "slides": [
                {"layout": "title", "title": "S1", "body": "", "speaker_notes": None},
            ],
        },
        "binary_url": "https://example.com/v1.pptx",
    }
    version_service.append.return_value = {"id": "version-uuid"}

    monkeypatch.setattr(
        "app.services.document_service.render_pptx_from_source",
        AsyncMock(return_value=b"PK-fake-pptx"),
    )
    monkeypatch.setattr(
        "app.agents.tools.document_editor._upload_render",
        AsyncMock(return_value="https://example.com/v2.pptx"),
    )

    from app.agents.tools.document_editor import edit_presentation

    result = await edit_presentation(
        tool_context,
        document_id=document_id,
        op="insert_slide",
        slide_index=1,
        content="New slide title",
    )

    assert result["status"] == "success"
    update_call = source_service.update_source.await_args
    new_source = update_call.kwargs["new_source"]
    assert len(new_source["slides"]) == 2
    assert new_source["slides"][1]["title"] == "New slide title"
```

- [ ] **Step 2: Implement**

```python
@agent_tool
async def edit_presentation(
    tool_context: Any,
    document_id: str,
    op: Literal[
        "edit_text", "replace_image", "insert_slide", "delete_slide",
        "reorder", "set_speaker_notes",
    ],
    slide_index: int | None = None,
    text_anchor: str | None = None,
    content: str = "",
    new_order: list[int] | None = None,
    image_url: str | None = None,
) -> dict[str, Any]:
    """Edit a PPTX presentation.

    Args:
        document_id: UUID.
        op: edit_text | replace_image | insert_slide | delete_slide |
            reorder | set_speaker_notes.
        slide_index: 0-indexed slide.
        text_anchor: shape/placeholder ID; None defaults to slide title.
        content: text content.
        new_order: list of original indices in new order (for reorder).
        image_url: for replace_image.
    """
    try:
        source_service = await _get_source_service()
        record, err = await _load_owned_record(tool_context, document_id, source_service)
        if err is not None:
            return err
        assert record is not None
        if record["doc_class"] != "presentation":
            return {"status": "error",
                    "message": f"Wrong tool for {record['doc_class']}"}

        source = dict(record["source"] or {"title": "Untitled", "slides": []})
        slides = [dict(s) for s in source.get("slides", [])]

        if op == "edit_text":
            if slide_index is None:
                return {"status": "error", "message": "edit_text needs slide_index"}
            if not (0 <= slide_index < len(slides)):
                return {"status": "error", "message": "slide_index out of range"}
            target_field = text_anchor or "title"
            slides[slide_index][target_field] = content
            diff_summary = f"Edited {target_field} on slide {slide_index + 1}"
        elif op == "insert_slide":
            insert_at = slide_index if slide_index is not None else len(slides)
            slides.insert(insert_at, {
                "layout": "title_and_content",
                "title": content,
                "body": "",
                "speaker_notes": None,
            })
            diff_summary = f"Inserted slide at position {insert_at + 1}"
        elif op == "delete_slide":
            if slide_index is None or not (0 <= slide_index < len(slides)):
                return {"status": "error", "message": "delete_slide needs valid slide_index"}
            del slides[slide_index]
            diff_summary = f"Deleted slide {slide_index + 1}"
        elif op == "reorder":
            if not new_order or sorted(new_order) != list(range(len(slides))):
                return {"status": "error",
                        "message": "reorder needs new_order with all original indices"}
            slides = [slides[i] for i in new_order]
            diff_summary = "Reordered slides"
        elif op == "set_speaker_notes":
            if slide_index is None:
                return {"status": "error", "message": "set_speaker_notes needs slide_index"}
            if not (0 <= slide_index < len(slides)):
                return {"status": "error", "message": "slide_index out of range"}
            slides[slide_index]["speaker_notes"] = content
            diff_summary = f"Updated speaker notes on slide {slide_index + 1}"
        elif op == "replace_image":
            if slide_index is None or image_url is None:
                return {"status": "error",
                        "message": "replace_image needs slide_index + image_url"}
            slides[slide_index]["image_url"] = image_url
            diff_summary = f"Replaced image on slide {slide_index + 1}"
        else:
            return {"status": "error", "message": f"Unknown op: {op}"}

        new_source = {**source, "slides": slides}

        from app.services.document_service import render_pptx_from_source
        new_binary = await render_pptx_from_source(new_source)

        return await _persist_edit(
            record=record,
            new_source=new_source,
            new_binary=new_binary,
            mime_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            filename=f"{source.get('title', 'presentation')}.pptx",
            diff_summary=diff_summary,
        )
    except Exception as e:
        logger.exception("edit_presentation failed")
        return {"status": "error", "message": str(e)}


DOCUMENT_EDITOR_TOOLS = [
    read_document_content, edit_report_doc, edit_spreadsheet, edit_presentation,
]
```

- [ ] **Step 3: Run tests, confirm green**

Run: `uv run pytest app/tests/unit/test_document_editor_tools.py -v`

Expected: 9 passed.

- [ ] **Step 4: Commit**

```bash
git add app/agents/tools/document_editor.py app/tests/unit/test_document_editor_tools.py
git commit -m "feat(doc-viewer): add edit_presentation tool"
```

---

## Task 18: edit_word_doc — write test + implement

**Files:**
- Modify: `app/tests/unit/test_document_editor_tools.py`
- Modify: `app/agents/tools/document_editor.py`

- [ ] **Step 1: Append test**

```python
@pytest.mark.asyncio
async def test_edit_word_doc_replace_paragraph(tool_context, mock_services, monkeypatch):
    source_service, version_service, _ = mock_services
    document_id = str(uuid4())
    source_service.get.return_value = {
        "document_id": document_id,
        "doc_class": "word",
        "user_id": tool_context.state["user_id"],
        "source": {
            "title": "Doc",
            "sections": [
                {"heading": "Intro", "content": "Old para 1.\n\nOld para 2."},
            ],
        },
        "binary_url": "https://example.com/v1.docx",
    }
    version_service.append.return_value = {"id": "version-uuid"}

    monkeypatch.setattr(
        "app.services.document_service.render_docx_from_source",
        AsyncMock(return_value=b"PK-fake-docx"),
    )
    monkeypatch.setattr(
        "app.agents.tools.document_editor._upload_render",
        AsyncMock(return_value="https://example.com/v2.docx"),
    )

    from app.agents.tools.document_editor import edit_word_doc

    result = await edit_word_doc(
        tool_context,
        document_id=document_id,
        op="replace_paragraph",
        anchor="Intro",
        content="Brand new paragraph.",
    )

    assert result["status"] == "success"
    update_call = source_service.update_source.await_args
    new_source = update_call.kwargs["new_source"]
    assert new_source["sections"][0]["content"] == "Brand new paragraph."
```

- [ ] **Step 2: Implement**

```python
@agent_tool
async def edit_word_doc(
    tool_context: Any,
    document_id: str,
    op: Literal["replace_paragraph", "append", "set_heading", "insert_table"],
    anchor: str | None = None,
    content: str = "",
) -> dict[str, Any]:
    """Edit a DOCX word document.

    Args:
        document_id: UUID.
        op: replace_paragraph | append | set_heading | insert_table.
        anchor: heading text identifying the section to modify.
        content: new content.
    """
    try:
        source_service = await _get_source_service()
        record, err = await _load_owned_record(tool_context, document_id, source_service)
        if err is not None:
            return err
        assert record is not None
        if record["doc_class"] != "word":
            return {"status": "error",
                    "message": f"Wrong tool for {record['doc_class']}"}

        source = dict(record["source"] or {"title": "Untitled", "sections": []})
        sections = [dict(s) for s in source.get("sections", [])]

        if op == "replace_paragraph":
            if anchor is None:
                return {"status": "error", "message": "replace_paragraph needs anchor"}
            target_idx = next(
                (i for i, s in enumerate(sections) if s["heading"] == anchor), None
            )
            if target_idx is None:
                return {"status": "error", "message": f"Anchor '{anchor}' not found"}
            sections[target_idx]["content"] = content
            diff_summary = f"Replaced paragraph under '{anchor}'"
        elif op == "append":
            heading = anchor or f"Section {len(sections) + 1}"
            sections.append({"heading": heading, "content": content})
            diff_summary = f"Appended section '{heading}'"
        elif op == "set_heading":
            if anchor is None:
                return {"status": "error", "message": "set_heading needs anchor"}
            target_idx = next(
                (i for i, s in enumerate(sections) if s["heading"] == anchor), None
            )
            if target_idx is None:
                return {"status": "error", "message": f"Anchor '{anchor}' not found"}
            sections[target_idx]["heading"] = content
            diff_summary = f"Renamed heading '{anchor}' to '{content}'"
        elif op == "insert_table":
            return {"status": "error",
                    "message": "insert_table not yet implemented"}
        else:
            return {"status": "error", "message": f"Unknown op: {op}"}

        new_source = {**source, "sections": sections}

        from app.services.document_service import render_docx_from_source
        new_binary = await render_docx_from_source(new_source)

        return await _persist_edit(
            record=record,
            new_source=new_source,
            new_binary=new_binary,
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=f"{source.get('title', 'document')}.docx",
            diff_summary=diff_summary,
        )
    except Exception as e:
        logger.exception("edit_word_doc failed")
        return {"status": "error", "message": str(e)}


DOCUMENT_EDITOR_TOOLS = [
    read_document_content, edit_report_doc, edit_spreadsheet,
    edit_presentation, edit_word_doc,
]
```

- [ ] **Step 3: Run tests, confirm green**

Run: `uv run pytest app/tests/unit/test_document_editor_tools.py -v`

Expected: 10 passed.

- [ ] **Step 4: Commit**

```bash
git add app/agents/tools/document_editor.py app/tests/unit/test_document_editor_tools.py
git commit -m "feat(doc-viewer): add edit_word_doc tool"
```

---

## Task 19: edit_google_doc + list_document_versions

**Files:**
- Modify: `app/tests/unit/test_document_editor_tools.py`
- Modify: `app/agents/tools/document_editor.py`

- [ ] **Step 1: Append tests**

```python
@pytest.mark.asyncio
async def test_edit_google_doc_replace_section(tool_context, mock_services, monkeypatch):
    source_service, version_service, _ = mock_services
    document_id = str(uuid4())
    source_service.get.return_value = {
        "document_id": document_id,
        "doc_class": "google_doc",
        "user_id": tool_context.state["user_id"],
        "source": {"google_doc_id": "g-doc-id-123"},
        "binary_url": None,
    }
    version_service.append.return_value = {"id": "version-uuid"}

    tool_context.state["google_provider_token"] = "fake-token"

    fake_google_service = MagicMock()
    fake_google_service.read_doc_content.return_value = "Before edit text"
    fake_google_service.replace_section.return_value = {"replies": []}

    monkeypatch.setattr(
        "app.agents.tools.document_editor._get_google_docs_service",
        lambda ctx: fake_google_service,
    )

    from app.agents.tools.document_editor import edit_google_doc

    result = await edit_google_doc(
        tool_context,
        document_id=document_id,
        op="replace_section",
        anchor="Summary",
        content="New summary text.",
    )

    assert result["status"] == "success"
    fake_google_service.replace_section.assert_called_once_with(
        "g-doc-id-123", "Summary", "New summary text."
    )


@pytest.mark.asyncio
async def test_list_document_versions(tool_context, mock_services):
    _, version_service, _ = mock_services
    version_service.list.return_value = [
        {"id": "v3", "diff_summary": "edit 3", "created_at": "2026-05-05T12:00:00Z",
         "created_by": "agent"},
        {"id": "v2", "diff_summary": "edit 2", "created_at": "2026-05-05T11:00:00Z",
         "created_by": "agent"},
    ]

    from app.agents.tools.document_editor import list_document_versions

    result = await list_document_versions(tool_context, document_id="x", limit=5)

    assert result["status"] == "success"
    assert len(result["versions"]) == 2
    assert result["versions"][0]["id"] == "v3"
```

- [ ] **Step 2: Implement**

```python
def _get_google_docs_service(tool_context: Any):
    """Patchable factory for the Google Docs service."""
    from app.agents.tools.docs import _get_docs_service
    return _get_docs_service(tool_context)


@agent_tool
async def edit_google_doc(
    tool_context: Any,
    document_id: str,
    op: Literal["replace_section", "append", "set_heading", "delete_section"],
    anchor: str | None = None,
    content: str = "",
) -> dict[str, Any]:
    """Edit a Google Doc.

    Calls the Docs API directly. No binary re-render — the iframe reflects
    the new state automatically. Still creates a version row in
    document_versions for undo support (snapshot of pre-edit text).
    """
    try:
        source_service = await _get_source_service()
        record, err = await _load_owned_record(tool_context, document_id, source_service)
        if err is not None:
            return err
        assert record is not None
        if record["doc_class"] != "google_doc":
            return {"status": "error",
                    "message": f"Wrong tool for {record['doc_class']}"}

        google_doc_id = record["source"]["google_doc_id"]
        google_service = _get_google_docs_service(tool_context)

        # Capture pre-edit content for undo
        before_text = google_service.read_doc_content(google_doc_id)

        if op == "replace_section":
            if anchor is None:
                return {"status": "error", "message": "replace_section needs anchor"}
            google_service.replace_section(google_doc_id, anchor, content)
            diff_summary = f"Replaced section '{anchor}' in Google Doc"
        elif op == "append":
            google_service.append_text(google_doc_id, "\n\n" + content)
            diff_summary = "Appended to Google Doc"
        elif op in {"set_heading", "delete_section"}:
            return {"status": "error",
                    "message": f"{op} not yet implemented for Google Docs"}
        else:
            return {"status": "error", "message": f"Unknown op: {op}"}

        # Append version with the BEFORE snapshot in source_snapshot so undo
        # can restore. (Imperfect — Google's own change history is the real
        # source of truth, but this gives us a recovery hook.)
        version_service = await _get_version_service()
        version = await version_service.append(
            document_id=document_id,
            user_id=record["user_id"],
            source_snapshot={"before_text": before_text},
            binary_url=f"https://docs.google.com/document/d/{google_doc_id}/preview",
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
                                "document_id": document_id,
                                "binary_url": (
                                    f"https://docs.google.com/document/d/"
                                    f"{google_doc_id}/preview"
                                ),
                                "doc_class": "google_doc",
                            },
                        },
                    },
                },
            ],
            "status": "success",
            "new_version_id": version["id"],
            "new_render_url": (
                f"https://docs.google.com/document/d/{google_doc_id}/preview"
            ),
            "diff_summary": diff_summary,
        }
    except Exception as e:
        logger.exception("edit_google_doc failed")
        return {"status": "error", "message": str(e)}


@agent_tool
async def list_document_versions(
    tool_context: Any,
    document_id: str,
    limit: int = 10,
) -> dict[str, Any]:
    """List recent versions of a document.

    Use when the user asks 'what did you change' or to find a version to
    revert to.
    """
    try:
        version_service = await _get_version_service()
        versions = await version_service.list(document_id, limit=limit)
        return {
            "status": "success",
            "versions": [
                {
                    "id": v["id"],
                    "diff_summary": v.get("diff_summary"),
                    "created_at": v["created_at"],
                    "created_by": v["created_by"],
                }
                for v in versions
            ],
        }
    except Exception as e:
        logger.exception("list_document_versions failed")
        return {"status": "error", "message": str(e)}


DOCUMENT_EDITOR_TOOLS = [
    read_document_content,
    edit_report_doc,
    edit_spreadsheet,
    edit_presentation,
    edit_word_doc,
    edit_google_doc,
    list_document_versions,
]
```

- [ ] **Step 3: Run tests, confirm green**

Run: `uv run pytest app/tests/unit/test_document_editor_tools.py -v`

Expected: 12 passed.

- [ ] **Step 4: Commit**

```bash
git add app/agents/tools/document_editor.py app/tests/unit/test_document_editor_tools.py
git commit -m "feat(doc-viewer): add edit_google_doc + list_document_versions tools"
```

---

## Task 20: HTTP router for source / versions / revert

**Files:**
- Create: `app/routers/document_viewer.py`
- Create: `app/tests/integration/test_document_viewer_router.py`
- Modify: `app/fast_api_app.py`

- [ ] **Step 1: Write the integration test**

```python
# app/tests/integration/test_document_viewer_router.py
"""Integration tests for /documents/{id} HTTP endpoints."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.fast_api_app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_get_source_returns_404_when_unknown(client, auth_headers):
    response = client.get(f"/documents/{uuid4()}/source", headers=auth_headers)
    assert response.status_code == 404


def test_get_versions_empty_list_for_unknown_doc(client, auth_headers):
    response = client.get(f"/documents/{uuid4()}/versions", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {"versions": []}


def test_revert_404_when_target_version_missing(client, auth_headers):
    document_id = str(uuid4())
    bad_version = str(uuid4())
    response = client.post(
        f"/documents/{document_id}/revert",
        json={"target_version_id": bad_version},
        headers=auth_headers,
    )
    assert response.status_code == 404
```

> The `auth_headers` fixture already exists in `app/tests/conftest.py` (used by other integration tests like `test_workspace_event_service.py`); use it as-is.

- [ ] **Step 2: Implement the router**

Create `app/routers/document_viewer.py`:

```python
# app/routers/document_viewer.py
"""HTTP endpoints for the document viewer widget.

GET  /documents/{id}/source    — fetch current source + binary_url
GET  /documents/{id}/versions  — list versions (newest first)
POST /documents/{id}/revert    — revert to target version, returns new binary_url
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import verify_token
from app.services.document_source_service import DocumentSourceService
from app.services.document_version_service import DocumentVersionService
from app.services.supabase_client import get_async_client

router = APIRouter(prefix="/documents", tags=["document-viewer"])


class SourceResponse(BaseModel):
    document_id: str
    doc_class: str
    binary_url: str | None
    source: dict[str, Any] | None
    forked_from_upload: bool


class VersionItem(BaseModel):
    id: str
    diff_summary: str | None
    binary_url: str
    created_at: str
    created_by: str


class VersionsResponse(BaseModel):
    versions: list[VersionItem]


class RevertRequest(BaseModel):
    target_version_id: str


class RevertResponse(BaseModel):
    new_version_id: str
    new_binary_url: str
    diff_summary: str


async def _source_service() -> DocumentSourceService:
    return DocumentSourceService(await get_async_client())


async def _version_service() -> DocumentVersionService:
    return DocumentVersionService(await get_async_client())


@router.get("/{document_id}/source", response_model=SourceResponse)
async def get_source(
    document_id: str,
    user_id: str = Depends(verify_token),
    service: DocumentSourceService = Depends(_source_service),
) -> SourceResponse:
    record = await service.get(document_id)
    if record is None or record["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="Document not found")
    return SourceResponse(**{
        k: record[k] for k in
        ("document_id", "doc_class", "binary_url", "source", "forked_from_upload")
    })


@router.get("/{document_id}/versions", response_model=VersionsResponse)
async def get_versions(
    document_id: str,
    limit: int = 10,
    user_id: str = Depends(verify_token),
    service: DocumentVersionService = Depends(_version_service),
) -> VersionsResponse:
    rows = await service.list(document_id, limit=limit)
    rows = [r for r in rows if r["user_id"] == user_id]
    return VersionsResponse(versions=[VersionItem(**r) for r in rows])


@router.post("/{document_id}/revert", response_model=RevertResponse)
async def revert(
    document_id: str,
    body: RevertRequest,
    user_id: str = Depends(verify_token),
    source_svc: DocumentSourceService = Depends(_source_service),
    version_svc: DocumentVersionService = Depends(_version_service),
) -> RevertResponse:
    target = await version_svc.get(body.target_version_id)
    if target is None or target["document_id"] != document_id:
        raise HTTPException(status_code=404, detail="Target version not found")
    if target["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    await source_svc.update_source(
        document_id=document_id,
        new_source=target["source_snapshot"] or {},
        new_binary_url=target["binary_url"],
    )

    new_version = await version_svc.append(
        document_id=document_id,
        user_id=user_id,
        source_snapshot=target["source_snapshot"],
        binary_url=target["binary_url"],
        diff_summary=f"Reverted to {body.target_version_id[:8]}",
        created_by="user",
    )

    return RevertResponse(
        new_version_id=new_version["id"],
        new_binary_url=target["binary_url"],
        diff_summary=new_version["diff_summary"],
    )
```

- [ ] **Step 3: Register the router**

In `app/fast_api_app.py`, near the other router registrations (search for `app.include_router(`), add:

```python
from app.routers.document_viewer import router as document_viewer_router
app.include_router(document_viewer_router)
```

- [ ] **Step 4: Run integration tests, confirm green**

Run: `uv run pytest app/tests/integration/test_document_viewer_router.py -v`

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add app/routers/document_viewer.py app/tests/integration/test_document_viewer_router.py app/fast_api_app.py
git commit -m "feat(doc-viewer): add HTTP router for source/versions/revert"
```

---

## Task 21: Lazy fork integration test

**Files:**
- Create: `app/tests/integration/test_lazy_fork_to_editable.py`

- [ ] **Step 1: Write the integration test**

```python
# app/tests/integration/test_lazy_fork_to_editable.py
"""Integration: user uploads PDF → first agent edit forks to editable source."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.agents.tools.document_editor import edit_report_doc, read_document_content
from app.services.document_service import render_pdf_from_source


@pytest.fixture
async def uploaded_pdf_record(supabase_client):
    """Insert a document_sources row representing a user upload (binary
    only, no source)."""
    user_id = str(uuid4())
    document_id = str(uuid4())
    pdf = await render_pdf_from_source({
        "title": "Original",
        "sections": [{"heading": "S", "content": "Imported content."}],
    })

    # In a real upload, the binary lives in storage. For the test, we'll
    # serve it from a test fixture URL via httpx's mock transport.
    await supabase_client.table("document_sources").insert({
        "user_id": user_id,
        "document_id": document_id,
        "doc_class": "report",
        "source": None,
        "binary_url": "https://test.example.com/upload.pdf",
        "forked_from_upload": False,
    }).execute()

    return {
        "user_id": user_id,
        "document_id": document_id,
        "binary": pdf,
    }


@pytest.mark.asyncio
async def test_first_read_extracts_text_lazily(
    uploaded_pdf_record, supabase_client, monkeypatch
):
    record = uploaded_pdf_record
    tool_context = MagicMock()
    tool_context.state = {"user_id": record["user_id"]}

    async def fake_fetch(url):
        return record["binary"]

    monkeypatch.setattr(
        "app.agents.tools.document_editor._fetch_binary", fake_fetch
    )

    result = await read_document_content(
        tool_context, document_id=record["document_id"]
    )

    assert result["status"] == "success"
    assert "Imported content." in result["text"]

    row = (
        await supabase_client.table("document_sources")
        .select("*")
        .eq("document_id", record["document_id"])
        .single()
        .execute()
    )
    assert row.data["extracted_text"] is not None


@pytest.mark.asyncio
async def test_first_edit_forks_to_editable(
    uploaded_pdf_record, supabase_client, monkeypatch
):
    record = uploaded_pdf_record
    tool_context = MagicMock()
    tool_context.state = {"user_id": record["user_id"]}

    async def fake_fetch(url):
        return record["binary"]

    monkeypatch.setattr(
        "app.agents.tools.document_editor._fetch_binary", fake_fetch
    )
    monkeypatch.setattr(
        "app.agents.tools.document_editor._upload_render",
        AsyncMock(return_value="https://test.example.com/v1.pdf"),
    )

    # First edit: source is None → must trigger fork_to_source
    result = await edit_report_doc(
        tool_context,
        document_id=record["document_id"],
        op="rewrite",
        content="Brand new content.",
    )

    assert result["status"] == "success"

    row = (
        await supabase_client.table("document_sources")
        .select("*")
        .eq("document_id", record["document_id"])
        .single()
        .execute()
    )
    assert row.data["source"] is not None
    assert row.data["forked_from_upload"] is True

    versions = (
        await supabase_client.table("document_versions")
        .select("*")
        .eq("document_id", record["document_id"])
        .execute()
    )
    assert len(versions.data) >= 1
```

- [ ] **Step 2: Update `edit_report_doc` to handle source=None (lazy fork)**

The current `edit_report_doc` from Task 15 reads `record["source"]` but doesn't fork on first edit. Modify the early section of `edit_report_doc` (where it reads the source) to:

```python
        source = record["source"]
        if source is None:
            # First edit on a user upload — fork to editable
            extraction_service = _get_extraction_service()
            binary_url = record["binary_url"]
            if not binary_url:
                return {"status": "error", "message": "No source and no binary URL"}
            binary = await _fetch_binary(binary_url)
            source = await extraction_service.fork_to_source(
                binary=binary, doc_class="report"
            )
            await source_service.mark_forked_from_upload(record["document_id"])

        source = dict(source)
        sections = list(source.get("sections", []))
        # ...rest unchanged
```

Apply the same pattern to `edit_spreadsheet`, `edit_presentation`, `edit_word_doc` (extract a helper `_ensure_source_exists`).

- [ ] **Step 3: Add the helper**

In `app/agents/tools/document_editor.py`, add:

```python
async def _ensure_source_exists(
    record: dict, source_service: DocumentSourceService
) -> dict:
    """Lazy-fork a user upload to editable source on first edit."""
    if record["source"] is not None:
        return record["source"]

    extraction_service = _get_extraction_service()
    binary_url = record["binary_url"]
    if not binary_url:
        raise ValueError("No source and no binary URL to fork from")

    binary = await _fetch_binary(binary_url)
    forked = await extraction_service.fork_to_source(
        binary=binary, doc_class=record["doc_class"]
    )
    await source_service.mark_forked_from_upload(record["document_id"])
    return forked
```

Replace direct `record["source"]` reads in all four `edit_*` tools with `await _ensure_source_exists(record, source_service)`.

- [ ] **Step 4: Run integration tests**

Run: `uv run pytest app/tests/integration/test_lazy_fork_to_editable.py -v`

Expected: 2 passed.

- [ ] **Step 5: Run full test file (regression check)**

Run: `uv run pytest app/tests/unit/test_document_editor_tools.py -v`

Expected: 12 still passing.

- [ ] **Step 6: Commit**

```bash
git add app/agents/tools/document_editor.py app/tests/integration/test_lazy_fork_to_editable.py
git commit -m "feat(doc-viewer): add lazy fork-to-editable on first edit"
```

---

## Task 22: Wire tools into ContentCreationAgent

**Files:**
- Modify: `app/agents/tools/__init__.py`
- Modify: `app/agents/shared_instructions.py`
- Modify: `app/agents/content/agent.py`
- Create: `app/tests/integration/test_content_agent_doc_tools.py`

- [ ] **Step 1: Export the tools**

In `app/agents/tools/__init__.py`, add:

```python
from app.agents.tools.document_editor import DOCUMENT_EDITOR_TOOLS
```

Make sure `DOCUMENT_EDITOR_TOOLS` appears in any aggregating list (e.g., `ALL_TOOLS` if one exists).

- [ ] **Step 2: Add the instruction block**

In `app/agents/shared_instructions.py`, add at module level:

```python
DOCUMENT_EDITOR_INSTRUCTION = """
## Editing Documents

When the user asks you to modify a document (PDF / spreadsheet / slides /
Word doc / Google Doc) or asks about its contents:

1. **Always call `read_document_content(document_id)` first** to load the
   current text and structure into your context. The user may reference
   sections/pages/slides/cells you don't yet know about.
2. **Pick the right edit tool by class:**
   - `edit_report_doc` → markdown-source PDFs (reports, briefs)
   - `edit_spreadsheet` → XLSX, CSV, AND Google Sheets (single tool, internal dispatch)
   - `edit_presentation` → PPTX
   - `edit_word_doc` → DOCX
   - `edit_google_doc` → Google Docs (not Sheets)
3. **State the change concisely in chat** before calling — one line.
   Example: "Replacing slide 3 with a friendlier opening."
4. **After the tool returns**, the viewer auto-refreshes to the new
   render. The user does NOT need to refresh manually. Confirm in chat:
   "Done. Slide 3 now reads...".
5. **Never call edit_* without document_id** — if you don't have one, ask
   the user "which document?" first.
6. If you need to know what changed previously, call
   `list_document_versions(document_id)`.

The user controls Undo via the version strip. Don't try to revert via
re-edit — say "click Undo to revert" instead.
""".strip()
```

- [ ] **Step 3: Wire into ContentCreationAgent**

In `app/agents/content/agent.py`:
- Add `from app.agents.tools.document_editor import DOCUMENT_EDITOR_TOOLS` at top
- Append `DOCUMENT_EDITOR_TOOLS` to the agent's `tools=[...]` list
- Append `DOCUMENT_EDITOR_INSTRUCTION` to the agent's instruction string (use `\n\n`.join logic if there's a list/concat pattern already; otherwise append directly)

Concretely, locate where the agent is constructed (search for `create_content_agent` or similar) and modify the `tools` and `instruction` parameters.

- [ ] **Step 4: Add integration test**

Create `app/tests/integration/test_content_agent_doc_tools.py`:

```python
# app/tests/integration/test_content_agent_doc_tools.py
"""ContentCreationAgent has the document editor tools registered."""

from app.agents.content.agent import create_content_agent
from app.agents.tools.document_editor import (
    edit_google_doc,
    edit_presentation,
    edit_report_doc,
    edit_spreadsheet,
    edit_word_doc,
    list_document_versions,
    read_document_content,
)


def test_content_agent_has_all_doc_tools():
    agent = create_content_agent()
    tool_names = {t.__name__ for t in agent.tools}
    assert "read_document_content" in tool_names
    assert "edit_report_doc" in tool_names
    assert "edit_spreadsheet" in tool_names
    assert "edit_presentation" in tool_names
    assert "edit_word_doc" in tool_names
    assert "edit_google_doc" in tool_names
    assert "list_document_versions" in tool_names


def test_content_agent_instruction_mentions_doc_workflow():
    agent = create_content_agent()
    assert "read_document_content" in agent.instruction
    assert "edit_report_doc" in agent.instruction
```

> The exact factory function name (`create_content_agent`) should match what's in `app/agents/content/agent.py`. Adjust the import if the file uses a different name (e.g., `build_content_agent`).

- [ ] **Step 5: Run integration tests**

Run: `uv run pytest app/tests/integration/test_content_agent_doc_tools.py -v`

Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add app/agents/tools/__init__.py app/agents/shared_instructions.py app/agents/content/agent.py app/tests/integration/test_content_agent_doc_tools.py
git commit -m "feat(doc-viewer): wire document editor tools into ContentCreationAgent"
```

---

## Task 23: Final validation

**Files:** none (pure verification).

- [ ] **Step 1: Run the full backend test suite**

Run: `make test`

Expected: all pass; no new failures relative to baseline before this plan started. Pre-existing failures (if any) noted but not addressed here.

- [ ] **Step 2: Lint + types**

Run: `make lint`

Expected: clean. Fix any new violations introduced by this plan.

- [ ] **Step 3: Manual smoke test in dev**

Run: `make local-backend`

Then in another terminal:
```bash
curl -X POST http://localhost:8000/a2a/app/run_sse \
  -H "Authorization: Bearer $TEST_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test",
    "session_id": "test",
    "message": "Create a test report and then change its summary section to say it shipped on 2026-05-05."
  }'
```

Expected: SSE stream contains:
- `function_response` with `_workspace_command: True` from `edit_report_doc`
- `commands[0].action: "replace_active"` with a `document_viewer` widget definition
- A new row in `document_sources` and at least one row in `document_versions` for the created doc

- [ ] **Step 4: Document any deferred items**

If any task uncovered a real gap (e.g., LibreOffice install on the deploy environment), append a note to `docs/superpowers/specs/2026-05-05-document-viewer-widget-design.md` Section 9 (Open Questions) with what you found and the proposed follow-up.

- [ ] **Step 5: Commit any remaining doc updates**

```bash
git add docs/
git commit -m "docs(doc-viewer): note deferred items from Plan 1 execution"
```

(Skip if nothing changed.)

---

## Verification (skill-required summary)

This plan is complete when:

- [ ] Migration applied locally; `document_sources` and `document_versions` exist with RLS.
- [ ] All seven service files written (source service, version service, extraction service, slide image service, render-from-source helpers, document editor tools, document viewer router).
- [ ] All 12+ unit tests in `test_document_editor_tools.py` pass.
- [ ] Lazy-fork integration test passes.
- [ ] HTTP router test passes (3 endpoints).
- [ ] ContentCreationAgent has all 7 doc tools registered + instruction includes workflow guidance.
- [ ] `make lint` clean, `make test` passes.
- [ ] Manual smoke test produces a `replace_active` command from an `edit_report_doc` call end-to-end.

After this plan ships, **Plan 2 (Frontend viewer + sidebar)** can begin — it consumes the `/documents/{id}/source`, `/documents/{id}/versions`, `/documents/{id}/revert` endpoints and depends on the agent emitting `_workspace_command` envelopes from edit tool returns.
