# Phase 89 Manual UAT

## Setup

- [ ] Backend running via `make local-backend` or staging deploy
- [ ] Real Gemini / Vertex credentials available
- [ ] Frontend running via `cd frontend && npm run dev`
- [ ] Signed in as a test user with a fresh chat session

## SC1: Video Auto-Ingest

- [ ] Prompt: `Make me a 30-second video about Q4 strategy.`
- [ ] Wait for the video widget to appear in chat
- [ ] Confirm the latest `agent_knowledge` row shows `document_type='video'`
- [ ] Confirm metadata includes `asset_id`, `bucket_id`, `file_path`, `prompt`, and `session_id`

Suggested query:

```sql
SELECT document_type, metadata
FROM agent_knowledge
WHERE document_type = 'video'
ORDER BY created_at DESC
LIMIT 1;
```

## SC2: Image Auto-Ingest

- [ ] Prompt: `Create a hero image for a Q4 strategy campaign.`
- [ ] Wait for the image widget to appear in chat
- [ ] Confirm the latest `agent_knowledge` row shows `document_type='image'`
- [ ] Confirm metadata includes `asset_id`, `bucket_id`, `file_path`, `prompt`, and `session_id`

Suggested query:

```sql
SELECT document_type, metadata
FROM agent_knowledge
WHERE document_type = 'image'
ORDER BY created_at DESC
LIMIT 1;
```

## SC3: Document Auto-Ingest

- [ ] Prompt: `Create a financial report PDF for Q4.`
- [ ] Wait for the PDF widget to appear in chat
- [ ] Confirm the latest `agent_knowledge` row shows `document_type='pdf'`
- [ ] Confirm the stored `content` contains extracted document text, not an empty string

Suggested query:

```sql
SELECT document_type, content, metadata
FROM agent_knowledge
WHERE document_type = 'pdf'
ORDER BY created_at DESC
LIMIT 1;
```

## SC4: Mixed Retrieval

- [ ] After generating the video, image, and PDF, ask: `Find my Q4 strategy materials.`
- [ ] Confirm the agent returns a mixed result set that includes the generated video, image, and PDF
- [ ] Confirm the results remain relevance-ranked rather than split into separate sections

## SC5: Manual Upload Regression

- [ ] Upload a PDF through the `/dashboard/vault` UI
- [ ] Trigger the existing `Add to Vault` / process flow
- [ ] Confirm the new row still lands with `document_type='uploaded_document'`
- [ ] Confirm the uploaded document remains searchable after processing

Suggested query:

```sql
SELECT document_type, metadata
FROM agent_knowledge
WHERE document_type = 'uploaded_document'
ORDER BY created_at DESC
LIMIT 1;
```

## Sign-Off

- [ ] All five scenarios passed
- [ ] Date executed:
- [ ] Executed by:
- [ ] Build / deploy under test:
- [ ] Notes / evidence links:
