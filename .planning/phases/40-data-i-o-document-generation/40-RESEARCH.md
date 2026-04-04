# Phase 40: Data I/O & Document Generation - Research

**Researched:** 2026-04-04
**Domain:** CSV import/export, PDF generation (HTML->PDF), PowerPoint generation, Supabase Storage
**Confidence:** HIGH

## Summary

Phase 40 adds two major capabilities: (1) CSV data import/export for 9 user-facing tables, and (2) branded document generation (PDF reports via weasyprint + Jinja2, PowerPoint decks via python-pptx). Both capabilities integrate into the existing agent tool system and deliver results via new chat widgets with Supabase Storage signed URLs.

The codebase already has strong patterns for everything needed: media generation via `ai_jobs` queue with SSE progress (`director_service.py`), Supabase Storage bucket creation and file upload (`0018_create_storage.sql`, `20260307184500_restore_worker_media_alignment.sql`), widget registration (`WidgetRegistry.tsx`), agent tool return patterns (`media.py`), and brand profile retrieval (`brand_profile.py`). The main new work is: adding weasyprint system dependencies to the Docker image, adding `polars` and `weasyprint` to `pyproject.toml`, creating the data import/export services, creating the document generation services with Jinja2 templates, and wiring the new agent tools.

**Primary recommendation:** Follow the established `director_service.py` pattern for document generation (Supabase Storage upload, signed URLs, media_assets tracking, progress callbacks) and the established `BaseService` pattern for CSV import/export with RLS-scoped queries.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Import targets:** contacts, financial_records, tasks (department_tasks), initiatives, content_bundles, support_tickets, candidates (recruitment_candidates), risks (compliance_risks), audits (compliance_audits)
- **Import flow:** Upload CSV -> column mapping UI with AI-suggested mappings (Gemini Flash) -> preview first 10 rows -> validation with row-level error reporting -> commit with SSE progress
- **Mapping persistence:** Save successful mappings per table per user for repeat imports
- **File size limit:** 50MB max
- **Backend CSV parsing:** polars library
- **Large file processing:** ai_jobs queue for >1000 rows, SSE progress via existing streaming pattern
- **Export format:** Standard CSV, UTF-8, ISO 8601 timestamps
- **PDF library:** weasyprint (HTML -> PDF) with Jinja2 templates
- **PDF templates:** 4 built-in (Financial Report, Project Proposal, Meeting Summary, Competitive Analysis)
- **PPTX library:** python-pptx
- **Charts in PDF:** Matplotlib renders, embedded as base64 SVG or PNG
- **Storage:** Supabase Storage `generated-documents` bucket, signed URLs in chat
- **Agent tools:** import_csv_data, export_data_to_csv (on DataAnalysisAgent), generate_pdf_report and generate_pitch_deck (on ALL agents)
- **Widget:** New `document` widget type in WidgetRegistry
- **Max 50 pages** per generated PDF document

### Claude's Discretion
- Exact Jinja2 template HTML/CSS for each of the 4 PDF templates
- Exact PPTX slide layouts and styling
- AI column mapping prompt engineering (how Gemini Flash suggests mappings)
- Chart rendering approach for PDF embeds (matplotlib -> SVG vs matplotlib -> PNG)
- SSE progress message format for import
- Whether to show import preview in a modal or inline
- Exact export CSV column ordering
- Error message wording for validation failures

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DATA-01 | User can upload CSV files with column mapping UI | polars for parsing, new `/api/data-import/upload` endpoint, column mapping UI component, AI-suggested mappings via Gemini Flash |
| DATA-02 | CSV validation with row-level error reporting before commit | polars schema validation, per-row error collection, preview endpoint returning first 10 rows + errors |
| DATA-03 | AI-assisted column mapping (suggest mappings from CSV headers) | Gemini Flash analyzes CSV headers vs target table columns, saved mapping persistence in new `csv_column_mappings` table |
| DATA-04 | User can export any data table to CSV | polars DataFrame write_csv, BaseService RLS-scoped queries, Supabase Storage for output file |
| DATA-05 | Import progress tracking via SSE for large files | Reuse existing SSE streaming pattern from `useBackgroundStream.ts`, progress_callback pattern from `director_service.py` |
| DATA-06 | Agent can trigger data imports and exports via chat commands | New agent tools on DataAnalysisAgent: `import_csv_data`, `export_data_to_csv` |
| DOC-01 | Agent can generate PDF reports from any analysis output | weasyprint + Jinja2 pipeline, `generate_pdf_report` tool on all agents |
| DOC-02 | PDF reports include user's branding (logo, colors) | Brand profile retrieval via existing `get_brand_profile`, inject into Jinja2 context. NOTE: `logo_url` column missing from brand_profiles -- needs migration |
| DOC-03 | Agent can generate pitch deck slides (PowerPoint) | python-pptx (already in deps), `generate_pitch_deck` tool on all agents |
| DOC-04 | Common templates: financial report, project proposal, meeting summary, competitive analysis | 4 Jinja2 HTML templates + 1 PPTX template with branded slide layouts |
| DOC-05 | Generated documents stored in Supabase Storage and linked to conversation | `generated-documents` bucket creation migration, media_assets row, session_id linking |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| polars | latest (>=1.0) | CSV parsing, validation, schema inference | 10-100x faster than pandas for CSV ops, zero-copy, proper null handling, schema enforcement |
| weasyprint | >=62.0 | HTML -> PDF rendering | Only serious Python HTML-to-PDF engine with modern CSS support (flexbox, grid, @page) |
| Jinja2 | >=3.1 (already in deps via FastAPI) | HTML template rendering | Industry standard, already available in the project dependency tree |
| python-pptx | >=1.0.2 (already in deps) | PowerPoint PPTX generation | Already in `pyproject.toml`, only Python library for native PPTX creation |
| matplotlib | latest | Chart rendering for PDF/PPTX embeds | Standard for static chart generation, outputs SVG/PNG for embedding |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| supabase-py | >=2.27.2 (existing) | Storage bucket operations, signed URLs | File upload/download for generated documents and CSV exports |
| google-genai | >=0.2.0 (existing) | AI column mapping suggestions | Gemini Flash for analyzing CSV headers and suggesting column mappings |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| polars | pandas | polars is 10-100x faster for CSV, lower memory, better schema enforcement; pandas would work but is overkill in deps and slower |
| weasyprint | reportlab (already in deps) | reportlab is already installed but requires programmatic layout (no HTML/CSS templates); weasyprint allows branded HTML templates which is far better for professional reports |
| matplotlib SVG | plotly static | matplotlib is simpler for embedded SVG generation; plotly adds JS complexity |

**Installation:**
```bash
uv add polars weasyprint matplotlib
```

**Docker system dependencies (weasyprint):**
```dockerfile
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz-subset0 \
    libcairo2 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*
```

## Architecture Patterns

### Recommended Project Structure
```
app/
  services/
    data_import_service.py     # CSV import pipeline (polars parsing, validation, mapping)
    data_export_service.py     # CSV export pipeline (RLS query -> polars -> CSV -> Storage)
    document_service.py        # PDF + PPTX generation orchestrator
  agents/tools/
    data_io.py                 # Agent tools: import_csv_data, export_data_to_csv
    document_gen.py            # Agent tools: generate_pdf_report, generate_pitch_deck
  templates/
    pdf/
      financial_report.html    # Jinja2 template
      project_proposal.html
      meeting_summary.html
      competitive_analysis.html
      base.html                # Shared base template with brand injection
    pdf/css/
      report.css               # Shared PDF styles
  routers/
    data_io.py                 # REST endpoints: upload, preview, commit, export
supabase/
  migrations/
    YYYYMMDD_data_io_documents.sql  # generated-documents bucket, csv_column_mappings table, logo_url column
frontend/
  src/
    components/widgets/
      DocumentWidget.tsx       # New document download widget
    types/
      widgets.ts               # Add 'document' to WidgetType union
```

### Pattern 1: Document Generation (follows director_service.py)
**What:** Generate PDF/PPTX -> upload to Supabase Storage -> return signed URL as widget
**When to use:** All document generation flows
**Example:**
```python
# Source: app/services/director_service.py lines 432-461
# Pattern: upload bytes to bucket, get public URL, save to media_assets

from app.services.supabase import get_service_client

supabase = get_service_client()

# 1. Generate document bytes
pdf_bytes = weasyprint.HTML(string=rendered_html).write_pdf()

# 2. Upload to Storage
path = f"{user_id}/{doc_id}.pdf"
supabase.storage.from_("generated-documents").upload(
    path, pdf_bytes, {"content-type": "application/pdf"}
)

# 3. Get download URL (signed, not public -- documents are private)
signed = supabase.storage.from_("generated-documents").create_signed_url(
    path, expires_in=3600  # 1 hour
)

# 4. Track in media_assets (same pattern as director_service line 479-501)
await execute_async(
    supabase.table("media_assets").upsert({
        "id": doc_id,
        "user_id": user_id,
        "bucket_id": "generated-documents",
        "asset_type": "document",
        "title": title,
        "filename": f"{doc_id}.pdf",
        "file_path": path,
        "file_url": signed["signedURL"],
        "file_type": "application/pdf",
        "category": "generated",
        "size_bytes": len(pdf_bytes),
        "metadata": {"template": template_name, "session_id": session_id},
    }, on_conflict="id"),
    op_name="document_service.media_assets.upsert",
)

# 5. Return widget (same pattern as media.py lines 197-208)
return {
    "type": "document",
    "title": title,
    "data": {
        "documentUrl": signed["signedURL"],
        "title": title,
        "fileType": "pdf",
        "sizeBytes": len(pdf_bytes),
        "templateName": template_name,
    },
    "dismissible": True,
    "expandable": False,
}
```

### Pattern 2: CSV Import Pipeline
**What:** Upload -> parse with polars -> validate -> preview -> commit with progress
**When to use:** All CSV import flows

```python
import polars as pl
import io

# 1. Parse CSV with polars (fast, schema-aware)
df = pl.read_csv(
    io.BytesIO(csv_bytes),
    has_header=True,
    try_parse_dates=True,
    truncate_ragged_lines=True,  # Handle messy CSVs
    encoding="utf8-lossy",       # Tolerant encoding
)

# 2. Validate against target schema
errors = []
for row_idx in range(len(df)):
    row = df.row(row_idx, named=True)
    for col, expected_type in target_schema.items():
        if col in column_mapping:
            value = row.get(column_mapping[col])
            if not validate_value(value, expected_type):
                errors.append({
                    "row": row_idx + 1,
                    "column": col,
                    "value": str(value),
                    "reason": f"Expected {expected_type}",
                })

# 3. Preview (first 10 rows)
preview = df.head(10).to_dicts()

# 4. Commit with progress (for >1000 rows, use ai_jobs queue)
batch_size = 100
for i in range(0, len(df), batch_size):
    batch = df.slice(i, batch_size)
    records = batch.to_dicts()
    # Insert via Supabase
    await execute_async(
        supabase.table(target_table).insert(records),
        op_name=f"import.{target_table}.batch",
    )
    # Emit progress
    progress = min(100, int((i + batch_size) / len(df) * 100))
    await emit_progress(progress)
```

### Pattern 3: Widget Registration (follows existing pattern)
**What:** Add `document` widget type to WidgetRegistry
**When to use:** New widget type

```typescript
// Source: frontend/src/components/widgets/WidgetRegistry.tsx lines 172-197
// Pattern: dynamic import + WIDGET_MAP entry

const DocumentWidget = dynamic(() => import('./DocumentWidget'), {
    loading: () => <WidgetSkeleton />,
    ssr: false,
});

// Add to WIDGET_MAP:
document: DocumentWidget,

// Add to WidgetType union in types/widgets.ts (line 314-338):
| 'document'

// Add to WidgetData union (line 457-480):
| { type: 'document'; data: DocumentWidgetData }

// Add to validateWidgetDefinition switch (line 702-728):
case 'document': return typeof (w.data as Record<string, unknown>)?.documentUrl === 'string';
```

### Pattern 4: Agent Tool Registration (follows data agent pattern)
**What:** Add import/export tools to DataAnalysisAgent, doc gen tools to all agents
**When to use:** Tool registration

```python
# Source: app/agents/data/agent.py lines 202-222
# For DataAnalysisAgent -- add to DATA_AGENT_TOOLS list:
from app.agents.tools.data_io import import_csv_data, export_data_to_csv

# For ALL agents -- add to shared_tools or each agent's tool list:
from app.agents.tools.document_gen import generate_pdf_report, generate_pitch_deck
```

### Anti-Patterns to Avoid
- **Loading entire CSV into memory at once for huge files:** Use `pl.read_csv_batched()` or `pl.scan_csv()` for files approaching 50MB. Standard `read_csv` is fine for most files but batch processing prevents OOM.
- **Using public buckets for documents:** Documents contain user data -- use private bucket with signed URLs, not public bucket. The `generated-assets` and `generated-videos` buckets are public because they contain generated media, but documents contain sensitive business data.
- **Blocking the event loop during PDF generation:** weasyprint is CPU-intensive. Always use `asyncio.to_thread()` to run weasyprint in a thread pool, matching the `director_service.py` pattern (line 413).
- **Inserting imported rows one-at-a-time:** Always batch insert (100 rows per batch) for performance.
- **Skipping RLS on export queries:** Use `BaseService` with user token for exports so RLS policies filter data correctly. Never use `AdminService` for user-facing data export.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CSV parsing with encoding detection | Custom CSV reader | `polars.read_csv(encoding="utf8-lossy")` | Handles BOM, encoding fallback, ragged lines, null detection |
| PDF layout engine | Manual coordinate-based PDF with reportlab | `weasyprint` + Jinja2 HTML templates | CSS-based layout is far more maintainable than programmatic coordinates |
| Chart generation for reports | Custom SVG builder | `matplotlib` -> `io.BytesIO()` -> base64 embed | Matplotlib handles axes, labels, legends, responsive sizing |
| PPTX slide master/layout | Manual shape positioning for every slide | `python-pptx` SlideMaster + SlideLayout | Built-in layout system handles consistent positioning |
| Column type inference from CSV | Regex-based type detection | `polars` automatic type inference + `df.dtypes` | polars already infers Int64, Float64, Utf8, Date, Datetime, Boolean |
| Progress streaming | Custom WebSocket server | Existing SSE pattern from `useBackgroundStream.ts` | Already battle-tested for video generation progress |

**Key insight:** The codebase already has patterns for every infrastructure need (Storage upload, signed URLs, media tracking, SSE progress, widget rendering). The only truly new work is the CSV validation logic, the Jinja2 templates, and the document generation orchestration.

## Common Pitfalls

### Pitfall 1: Missing logo_url Column on brand_profiles
**What goes wrong:** CONTEXT.md references "logo_url and brand colors from brand_profiles table" but the actual `brand_profiles` schema (migration `20260321000000_brand_profiles.sql`) has NO `logo_url` column. Colors are in the `visual_style` JSONB under `color_palette`.
**Why it happens:** The CONTEXT.md was drafted with an assumed schema.
**How to avoid:** Add a `logo_url TEXT` column to `brand_profiles` via migration. Also extract `color_palette` from `visual_style` JSONB for template injection.
**Warning signs:** Brand profile query returns no `logo_url` field.

### Pitfall 2: weasyprint System Dependencies in Docker
**What goes wrong:** `pip install weasyprint` succeeds but rendering fails at runtime with missing library errors (libpango, libcairo, libharfbuzz).
**Why it happens:** weasyprint is a Python binding to C libraries (Pango, Cairo) that must be installed at the OS level.
**How to avoid:** Add apt-get packages to Dockerfile BEFORE the Python dependency install step. Required packages for python:3.12-slim: `libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 libcairo2 libgdk-pixbuf2.0-0 libffi-dev`.
**Warning signs:** `OSError: cannot load library 'libpango-1.0-0'` at import time.

### Pitfall 3: CSV Import Overwriting Existing Data
**What goes wrong:** User imports a CSV that has the same email/name as existing contacts, creating duplicates.
**Why it happens:** Using INSERT without conflict handling.
**How to avoid:** For tables with natural keys (contacts.email), use UPSERT with `on_conflict` strategy. Let user choose: "skip duplicates" or "update existing".
**Warning signs:** Duplicate records after import.

### Pitfall 4: Blocking Event Loop During Document Generation
**What goes wrong:** weasyprint PDF rendering (especially with charts/images) can take 5-30 seconds, blocking the entire async event loop.
**Why it happens:** weasyprint is synchronous C code.
**How to avoid:** Always wrap in `asyncio.to_thread()`. For large documents, use the `ai_jobs` queue pattern.
**Warning signs:** Other requests start timing out during PDF generation.

### Pitfall 5: RLS Bypass on Export
**What goes wrong:** User A exports contacts and gets User B's data.
**Why it happens:** Using `AdminService` (service role) instead of `BaseService` (user token) for the export query.
**How to avoid:** Always use `BaseService` with user token for data export queries. The RLS policies on every target table already enforce `auth.uid() = user_id`.
**Warning signs:** Export returns more data than expected.

### Pitfall 6: Signed URL Expiration
**What goes wrong:** User clicks download link in chat history hours later, gets 403.
**Why it happens:** Signed URLs have a fixed expiration (default is often short).
**How to avoid:** Set generous expiration (24 hours for documents). Alternatively, regenerate the signed URL when the widget is rendered (frontend calls a refresh endpoint).
**Warning signs:** "Access Denied" on download from old chat messages.

### Pitfall 7: Enum Types on contacts Table
**What goes wrong:** CSV import for contacts fails because `lifecycle_stage` and `source` are PostgreSQL ENUM types, not free text.
**Why it happens:** The `contacts` table uses `contact_lifecycle_stage` and `contact_source` custom ENUM types.
**How to avoid:** Validate enum values during the validation step. Provide the valid enum values in the column mapping UI. Map common CSV values to enum values (e.g., "Lead" -> "lead", "Customer" -> "customer").
**Warning signs:** PostgreSQL error: `invalid input value for enum contact_lifecycle_stage`.

## Code Examples

### Existing Supabase Storage Upload Pattern
```python
# Source: app/services/director_service.py lines 432-461
# Upload bytes to bucket with retry
upload_success = False
for attempt in range(3):
    try:
        await asyncio.to_thread(
            self.supabase.storage.from_(BUCKET).upload,
            path,
            file_bytes,
            {"content-type": content_type},
        )
        upload_success = True
        break
    except Exception as e:
        logger.warning(f"Upload failed (attempt {attempt + 1}/3): {e}")
        if attempt < 2:
            await asyncio.sleep(2)
```

### Existing Brand Profile Retrieval
```python
# Source: app/agents/tools/brand_profile.py lines 41-80
async def get_brand_profile(user_id=None, brand_profile_id=None):
    supabase = _get_supabase_client()
    if brand_profile_id:
        result = supabase.table("brand_profiles").select("*") \
            .eq("id", brand_profile_id).eq("user_id", user_id).single().execute()
    else:
        result = supabase.table("brand_profiles").select("*") \
            .eq("user_id", user_id).eq("is_default", True).single().execute()
    return result.data
```

### Existing Widget Return Pattern
```python
# Source: app/agents/tools/media.py lines 197-208
widget = {
    "type": "video",
    "title": "Generated video",
    "data": {
        "videoUrl": url,
        "title": title,
        "asset_id": asset_id,
        "caption": prompt,
    },
    "dismissible": True,
    "expandable": True,
}
```

### Existing Media Contract Registration
```python
# Source: app/agents/tools/media.py lines 75-114
contract = await _register_media_contract(
    user_id=user_id,
    asset_id=asset_id,
    asset_type="document",  # new type
    title=title,
    prompt=prompt,
    file_url=signed_url,
    source="document_gen",
    metadata={"template": template_name},
)
widget = _attach_contract_to_widget(widget, contract)
```

### WeasyPrint + Jinja2 PDF Generation Pattern
```python
# Source: verified from official WeasyPrint docs + Jinja2 docs
import io
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

async def generate_pdf(template_name, data, brand_profile):
    # Load template
    env = Environment(loader=FileSystemLoader("app/templates/pdf"))
    template = env.get_template(f"{template_name}.html")
    
    # Inject brand data
    context = {
        **data,
        "brand_name": brand_profile.get("brand_name", ""),
        "logo_url": brand_profile.get("logo_url", ""),  # needs migration
        "color_palette": brand_profile.get("visual_style", {}).get("color_palette", []),
        "primary_color": _get_primary_color(brand_profile),
    }
    
    rendered_html = template.render(context)
    
    # Render PDF in thread pool (weasyprint is sync/CPU-intensive)
    font_config = FontConfiguration()
    pdf_bytes = await asyncio.to_thread(
        HTML(string=rendered_html).write_pdf,
        font_config=font_config,
    )
    
    return pdf_bytes
```

### python-pptx Slide Generation Pattern
```python
# Source: verified from python-pptx docs (v1.0.0)
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
import io

def generate_pitch_deck(slides_data, brand_profile):
    prs = Presentation()
    prs.slide_width = Inches(16)
    prs.slide_height = Inches(9)
    
    primary_color = RGBColor.from_string(
        brand_profile.get("visual_style", {}).get("color_palette", ["4F46E5"])[0]
    )
    
    for slide_data in slides_data:
        slide_layout = prs.slide_layouts[6]  # Blank layout
        slide = prs.slides.add_slide(slide_layout)
        
        # Title
        txBox = slide.shapes.add_textbox(Inches(1), Inches(0.5), Inches(14), Inches(1.5))
        tf = txBox.text_frame
        tf.text = slide_data["title"]
        tf.paragraphs[0].font.size = Pt(36)
        tf.paragraphs[0].font.bold = True
        tf.paragraphs[0].font.color.rgb = primary_color
        
        # Content
        if slide_data.get("content"):
            content_box = slide.shapes.add_textbox(
                Inches(1), Inches(2.5), Inches(14), Inches(5)
            )
            content_tf = content_box.text_frame
            content_tf.word_wrap = True
            for bullet in slide_data["content"]:
                p = content_tf.add_paragraph()
                p.text = bullet
                p.font.size = Pt(18)
        
        # Chart image (if provided)
        if slide_data.get("chart_image_bytes"):
            slide.shapes.add_picture(
                io.BytesIO(slide_data["chart_image_bytes"]),
                Inches(1), Inches(3), Inches(14), Inches(5.5),
            )
    
    buffer = io.BytesIO()
    prs.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()
```

### Polars CSV Import Pattern
```python
# Source: verified from Polars docs (https://docs.pola.rs/user-guide/io/csv/)
import polars as pl
import io

def parse_csv(csv_bytes: bytes) -> pl.DataFrame:
    return pl.read_csv(
        io.BytesIO(csv_bytes),
        has_header=True,
        try_parse_dates=True,
        truncate_ragged_lines=True,
        encoding="utf8-lossy",
        n_rows=None,  # read all
    )

def validate_csv_for_table(df: pl.DataFrame, column_mapping: dict, target_schema: dict):
    errors = []
    for row_idx in range(len(df)):
        row = df.row(row_idx, named=True)
        for target_col, csv_col in column_mapping.items():
            value = row.get(csv_col)
            expected_type = target_schema[target_col]
            if value is not None and not _validate_type(value, expected_type):
                errors.append({
                    "row": row_idx + 2,  # +2 for 1-indexed + header row
                    "column": target_col,
                    "csv_column": csv_col,
                    "value": str(value)[:100],
                    "reason": f"Expected {expected_type}, got {type(value).__name__}",
                })
    return errors

def export_to_csv(records: list[dict]) -> bytes:
    df = pl.DataFrame(records)
    buffer = io.BytesIO()
    df.write_csv(buffer)
    buffer.seek(0)
    return buffer.getvalue()
```

## Table Schema Reference (Import Targets)

### contacts
| Column | Type | Required | Notes |
|--------|------|----------|-------|
| name | TEXT | YES | |
| email | TEXT | no | |
| phone | TEXT | no | |
| company | TEXT | no | |
| lifecycle_stage | ENUM | no | Values: lead, qualified, opportunity, customer, churned, inactive. Default: lead |
| source | ENUM | no | Values: form_submission, stripe_payment, manual, import, referral, social, other. Default: import (for CSV imports) |
| source_detail | TEXT | no | |
| estimated_value | NUMERIC(12,2) | no | Default: 0 |
| currency | TEXT | no | Default: USD |
| notes | TEXT | no | |
| tags | TEXT[] | no | |

### financial_records
| Column | Type | Required | Notes |
|--------|------|----------|-------|
| transaction_type | TEXT | YES | CHECK: revenue, expense, refund, adjustment |
| amount | NUMERIC(15,2) | YES | CHECK: >= 0 |
| currency | TEXT | no | Default: USD |
| category | TEXT | no | |
| subcategory | TEXT | no | |
| description | TEXT | no | |
| source_type | TEXT | no | |
| source_id | TEXT | no | |
| transaction_date | TIMESTAMPTZ | no | Default: now() |

### department_tasks (referred to as "tasks" in CONTEXT.md)
| Column | Type | Required | Notes |
|--------|------|----------|-------|
| title | TEXT | YES | |
| description | TEXT | no | |
| from_department_id | UUID | YES | FK to departments |
| to_department_id | UUID | YES | FK to departments |
| status | TEXT | no | CHECK: pending, in_progress, completed, cancelled. Default: pending |
| priority | TEXT | no | CHECK: low, medium, high, urgent. Default: medium |
| due_date | TIMESTAMPTZ | no | |

### initiatives
| Column | Type | Required | Notes |
|--------|------|----------|-------|
| title | TEXT | YES | |
| description | TEXT | no | |
| priority | TEXT | no | Default: medium |
| status | TEXT | no | Default: draft |
| progress | INTEGER | no | Default: 0 |

### content_bundles
| Column | Type | Required | Notes |
|--------|------|----------|-------|
| source | TEXT | no | Default: agent_media |
| title | TEXT | no | |
| prompt | TEXT | no | |
| bundle_type | TEXT | no | CHECK: image, video, audio, mixed, campaign. Default: mixed |
| status | TEXT | no | CHECK: draft, processing, ready, failed, archived. Default: ready |

### support_tickets
| Column | Type | Required | Notes |
|--------|------|----------|-------|
| subject | TEXT | YES | |
| description | TEXT | no | |
| customer_email | TEXT | no | |
| priority | TEXT | no | Default: normal |
| status | TEXT | no | Default: new |
| assigned_to | TEXT | no | |
| resolution | TEXT | no | |

### recruitment_candidates (referred to as "candidates" in CONTEXT.md)
| Column | Type | Required | Notes |
|--------|------|----------|-------|
| job_id | UUID | YES | FK to recruitment_jobs -- must exist |
| name | TEXT | YES | |
| email | TEXT | no | |
| resume_url | TEXT | no | |
| status | TEXT | no | Default: applied |

### compliance_risks (referred to as "risks" in CONTEXT.md)
| Column | Type | Required | Notes |
|--------|------|----------|-------|
| title | TEXT | YES | |
| description | TEXT | no | |
| severity | TEXT | no | |
| mitigation_plan | TEXT | no | |
| owner | TEXT | no | |
| status | TEXT | no | Default: active |

### compliance_audits (referred to as "audits" in CONTEXT.md)
| Column | Type | Required | Notes |
|--------|------|----------|-------|
| title | TEXT | YES | |
| scope | TEXT | no | |
| auditor | TEXT | no | |
| scheduled_date | TIMESTAMPTZ | no | |
| status | TEXT | no | Default: scheduled |
| findings | TEXT | no | |

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| pandas for CSV | polars | 2023-2024 | 10-100x faster, native Rust engine, better memory |
| reportlab for PDF | weasyprint + Jinja2 | 2020+ | HTML/CSS templates instead of coordinate-based layout |
| wkhtmltopdf for HTML->PDF | weasyprint | 2022+ | Pure Python, no external binary needed, better CSS support |
| python-pptx 0.x | python-pptx 1.0+ | 2024 | Stable API, better layout support |

**Deprecated/outdated:**
- `xhtml2pdf`: Very limited CSS support, replaced by weasyprint
- `wkhtmltopdf`: External binary dependency, harder to Docker, replaced by weasyprint
- `pandas` for simple CSV I/O: polars is dramatically faster and has better schema enforcement

## Open Questions

1. **"tasks" table identity**
   - What we know: There is no standalone `tasks` table. `ai_jobs` is used by `TaskService` for internal job tracking. `department_tasks` is for cross-department handoffs.
   - What's unclear: Does the CONTEXT.md "tasks" refer to `department_tasks` or `ai_jobs`?
   - Recommendation: Use `department_tasks` since it has user-meaningful columns (title, description, priority, status) that make sense for CSV import. `ai_jobs` is an internal system table that users should not directly import into.

2. **Logo storage location**
   - What we know: `brand_profiles` has no `logo_url` column. The `visual_style` JSONB has no logo field either.
   - What's unclear: Where should logos be uploaded and referenced?
   - Recommendation: Add `logo_url TEXT` column to `brand_profiles` via migration. Logos get uploaded to the existing `brand-assets` bucket. Reference the public URL in `logo_url`.

3. **Document bucket privacy model**
   - What we know: `generated-assets` and `generated-videos` are public buckets. Documents contain sensitive business data.
   - What's unclear: Should `generated-documents` be public or private?
   - Recommendation: Private bucket with signed URLs. Documents contain financial reports, competitive analysis, etc. -- they should NOT be publicly accessible. Use `create_signed_url` with 24-hour expiry.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio |
| Config file | pyproject.toml |
| Quick run command | `uv run pytest tests/unit/ -x -q` |
| Full suite command | `uv run pytest tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DATA-01 | CSV upload + column mapping | unit | `uv run pytest tests/unit/services/test_data_import_service.py -x` | Wave 0 |
| DATA-02 | Row-level validation | unit | `uv run pytest tests/unit/services/test_data_import_service.py::test_validation -x` | Wave 0 |
| DATA-03 | AI column mapping | unit | `uv run pytest tests/unit/services/test_data_import_service.py::test_ai_mapping -x` | Wave 0 |
| DATA-04 | CSV export | unit | `uv run pytest tests/unit/services/test_data_export_service.py -x` | Wave 0 |
| DATA-05 | SSE progress for imports | unit | `uv run pytest tests/unit/services/test_data_import_service.py::test_progress -x` | Wave 0 |
| DATA-06 | Agent tools for import/export | unit | `uv run pytest tests/unit/test_data_io_tools.py -x` | Wave 0 |
| DOC-01 | PDF generation from analysis | unit | `uv run pytest tests/unit/services/test_document_service.py::test_pdf -x` | Wave 0 |
| DOC-02 | Branded PDF with logo/colors | unit | `uv run pytest tests/unit/services/test_document_service.py::test_branding -x` | Wave 0 |
| DOC-03 | PPTX pitch deck generation | unit | `uv run pytest tests/unit/services/test_document_service.py::test_pptx -x` | Wave 0 |
| DOC-04 | 4 PDF templates render correctly | unit | `uv run pytest tests/unit/services/test_document_service.py::test_templates -x` | Wave 0 |
| DOC-05 | Document storage + conversation linking | unit | `uv run pytest tests/unit/services/test_document_service.py::test_storage -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/unit/ -x -q`
- **Per wave merge:** `uv run pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/services/test_data_import_service.py` -- covers DATA-01 through DATA-05
- [ ] `tests/unit/services/test_data_export_service.py` -- covers DATA-04
- [ ] `tests/unit/test_data_io_tools.py` -- covers DATA-06
- [ ] `tests/unit/services/test_document_service.py` -- covers DOC-01 through DOC-05

## Sources

### Primary (HIGH confidence)
- `app/services/director_service.py` -- Supabase Storage upload pattern, progress callback, media_assets tracking
- `app/agents/tools/media.py` -- Widget return pattern, media contract registration
- `app/agents/tools/brand_profile.py` -- Brand profile retrieval pattern
- `frontend/src/components/widgets/WidgetRegistry.tsx` -- Widget registration pattern (24 existing widgets)
- `frontend/src/types/widgets.ts` -- WidgetType union, WidgetData types, validation guards
- `app/services/base_service.py` -- BaseService/AdminService RLS pattern
- `supabase/migrations/20260321000000_brand_profiles.sql` -- Brand profile schema (no logo_url!)
- `supabase/migrations/20260301111801_create_contacts_crm.sql` -- Contacts table with ENUM types
- `supabase/migrations/20260313103000_schema_truth_alignment.sql` -- financial_records schema
- `supabase/migrations/0003_complete_schema.sql` -- initiatives, support_tickets, compliance tables
- `supabase/migrations/20260308120000_content_bundle_workspace_contract.sql` -- content_bundles schema
- `supabase/migrations/20260403400000_department_tasks.sql` -- department_tasks schema
- `supabase/migrations/0018_create_storage.sql` -- Storage bucket creation pattern
- `supabase/migrations/20260307184500_restore_worker_media_alignment.sql` -- generated-assets/videos bucket config
- [WeasyPrint First Steps](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html) -- System dependencies for Debian/Ubuntu
- [Polars CSV Guide](https://docs.pola.rs/user-guide/io/csv/) -- read_csv, write_csv, scan_csv API

### Secondary (MEDIUM confidence)
- [WeasyPrint + Jinja2 Pattern](https://dantebytes.com/generating-pdfs-from-html-with-weasyprint-and-jinja2-python/) -- Complete PDF generation workflow
- [python-pptx Getting Started](https://python-pptx.readthedocs.io/en/latest/user/quickstart.html) -- Slide creation, text frames, images
- [GeeksforGeeks python-pptx Guide](https://www.geeksforgeeks.org/python/creating-and-updating-powerpoint-presentations-in-python-using-python-pptx/) -- Code examples for presentation creation

### Tertiary (LOW confidence)
- Docker weasyprint dependency lists from community Dockerfiles -- exact package names may vary by Debian version

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- python-pptx already in deps, polars/weasyprint well-documented
- Architecture: HIGH -- all patterns exist in codebase (director_service, media tools, widget registry)
- Pitfalls: HIGH -- verified against actual schemas (found missing logo_url, found ENUM types on contacts)
- Table schemas: HIGH -- read directly from migration SQL files

**Research date:** 2026-04-04
**Valid until:** 2026-05-04 (stable libraries, no fast-moving APIs)
