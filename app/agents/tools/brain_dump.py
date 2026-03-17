# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Brain Dump processing tools."""

import logging
import asyncio
import os
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

BRAINSTORM_MAX_HISTORY_CHARS = int(os.environ.get("BRAINSTORM_MAX_HISTORY_CHARS", "250000"))
BRAINSTORM_MAX_CONTEXT_CHARS = int(os.environ.get("BRAINSTORM_MAX_CONTEXT_CHARS", "12000"))


def _truncate_text_for_model(text: Optional[str], *, max_chars: int, label: str) -> str:
    """Trim oversized free-text inputs before sending them to the model."""
    if not text:
        return ""

    normalized = text.strip()
    if len(normalized) <= max_chars:
        return normalized

    head = max(512, max_chars // 5)
    tail = max(2048, max_chars - head - 96)
    if head + tail >= len(normalized):
        return normalized

    omitted = len(normalized) - head - tail
    logger.warning(
        "Truncating %s from %d to %d chars to stay under model context limits",
        label,
        len(normalized),
        max_chars,
    )
    return (
        f"{normalized[:head]}\n\n"
        f"[{label} truncated: {omitted} characters omitted to fit the model context window]\n\n"
        f"{normalized[-tail:]}"
    )

async def get_braindump_transcript(file_path: str, context: Optional[str] = None) -> Dict[str, Any]:
    """Transcribe an audio/video brain dump file into raw text.
    
    Args:
        file_path: The path to the file in Supabase Storage.
        context: Optional additional context.
        
    Returns:
        Dictionary containing the transcript text.
    """
    from app.services.supabase import get_service_client
    from app.agents.shared import get_model
    from google.genai import types

    try:
        supabase = get_service_client()
        bucket_id = "knowledge-vault"
        file_bytes = await asyncio.to_thread(
            lambda: supabase.storage.from_(bucket_id).download(file_path)
        )
        if not file_bytes:
            return {"success": False, "error": "Failed to download file."}

        mime_type = "audio/webm"
        if file_path.endswith(".mp4"): mime_type = "video/mp4"
        elif file_path.endswith(".wav"): mime_type = "audio/wav"
        elif file_path.endswith(".mp3"): mime_type = "audio/mp3"

        media_part = types.Part.from_bytes(data=file_bytes, mime_type=mime_type)
        prompt_text = "Transcribe the following audio/video recording accurately and completely. Include all details mentioned."
        if context: prompt_text += f"\n\nContext: {context}"
        
        model = get_model()
        response = await asyncio.to_thread(
            lambda: model.api_client.models.generate_content(
                model=model.model,
                contents=[types.Content(role="user", parts=[types.Part.from_text(text=prompt_text), media_part])],
                config=types.GenerateContentConfig(temperature=0.0)
            )
        )
        
        return {"success": True, "transcript": response.text, "file_path": file_path}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def save_braindump_analysis(content: str, title: str, category: str = "Brain Dump Analysis") -> Dict[str, Any]:
    """Save formatted brain dump analysis or findings to the Knowledge Vault.
    
    Args:
        content: The Markdown content to save.
        title: Descriptive title for the document.
        category: Category for the UI (default: Brain Dump Analysis).
        
    Returns:
        Result of the ingestion.
    """
    from app.rag.knowledge_vault import ingest_document_content
    from app.services.request_context import get_current_user_id
    
    try:
        user_id = get_current_user_id()
        result = await ingest_document_content(
            content=content,
            title=title,
            document_type=category,
            user_id=user_id,
        )
        return {"success": True, "document": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def process_brain_dump(file_path: str, context: Optional[str] = None) -> Dict[str, Any]:
    """Process a brain dump audio/video file using Gemini Multimodal.
    
    Retrieves the file from Supabase Storage, sends it to Gemini for analysis,
    and returns a structured summary with action items and potential initiatives.
    
    Args:
        file_path: The path to the file in Supabase Storage (knowledge-vault bucket).
        context: Optional additional context provided by the user.
        
    Returns:
        Dictionary containing the analysis result.
    """
    from app.services.supabase import get_service_client
    from app.agents.shared import get_model
    from google.genai import types

    try:
        # 1. Retrieve file from Supabase Storage
        supabase = get_service_client()
        bucket_id = "knowledge-vault"
        
        logger.info(f"Downloading brain dump from {bucket_id}/{file_path}")
        
        # Download file bytes
        file_bytes = await asyncio.to_thread(
            lambda: supabase.storage.from_(bucket_id).download(file_path)
        )
        
        if not file_bytes:
            return {"success": False, "error": "Failed to download file from storage."}

        # 2. Prepare content for Gemini
        # We assume webm for now as that's what the frontend records
        mime_type = "audio/webm"
        if file_path.endswith(".mp4"):
            mime_type = "video/mp4"
        elif file_path.endswith(".wav"):
            mime_type = "audio/wav"
        elif file_path.endswith(".mp3"):
            mime_type = "audio/mp3"

        media_part = types.Part.from_bytes(data=file_bytes, mime_type=mime_type)
        
        prompt_text = """
You are an expert Strategic Planning Agent. The user has recorded a "Brain Dump" - a stream of consciousness audio recording about their business ideas, tasks, or concerns.

Your goal is to organize this chaotic information into a structured, actionable format.

Please analyze the audio and provide the following:

1.  **Title**: A concise, catchy title for this session.
2.  **Executive Summary**: A brief paragraph summarizing the key points.
3.  **Key Topics**: A list of the main topics discussed.
4.  **Action Items**: A checklist of specific tasks mentioned or implied.
5.  **Potential Initiatives**: If the user discussed a large project or goal, outline it as a potential "Initiative" (Title, Objective, Next Steps).
6.  **Sentiment**: Briefly describe the user's tone (e.g., excited, overwhelmed, focused).

Format your response in Markdown.
"""
        if context:
            prompt_text += f"\n\nAdditional Context from User:\n{context}"

        text_part = types.Part.from_text(text=prompt_text)

        # 3. Call Gemini
        logger.info("Sending brain dump to Gemini for analysis...")
        model = get_model()
        
        response = await asyncio.to_thread(
            lambda: model.api_client.models.generate_content(
                model=model.model,
                contents=[types.Content(role="user", parts=[text_part, media_part])],
                config=types.GenerateContentConfig(
                    temperature=0.2, # Low temperature for factual analysis
                    max_output_tokens=2048,
                )
            )
        )
        
        if not response.text:
            return {"success": False, "error": "Gemini returned no text response."}


        # 4. Save analysis to Vault
        analysis_content = response.text
        # file_path is like "brain-dumps/USER_ID/filename.webm"
        try:
            parts = file_path.split("/")
            if len(parts) >= 2:
                user_id = parts[1]
                # Determine title from analysis if possible, else generic
                title = "Brain Dump Analysis"
                for line in analysis_content.split("\n"):
                    if "Title:" in line or "**Title**" in line:
                        title = line.replace("Title:", "").replace("**", "").strip()
                        break
                
                await _save_to_vault(
                    analysis_content, title, "Brain Dump Analysis", user_id
                )
        except Exception as save_err:
            logger.warning(f"Failed to auto-save brain dump analysis: {save_err}")

        # 5. Return Result
        return {
            "success": True,
            "analysis": response.text,
            "file_path": file_path
        }


    except Exception as e:
        logger.error(f"Error processing brain dump: {e}")
        return {"success": False, "error": str(e)}

async def _save_to_vault(
    content: str, title: str, doc_type: str, user_id: str
) -> Dict[str, Optional[str]]:
    """Save content to Knowledge Vault storage and DB.

    Returns:
        Dict with ``file_path`` and ``doc_id`` keys (values may be ``None`` on failure).
    """
    from app.services.supabase_client import get_service_client
    from app.rag.knowledge_vault import ingest_document_content
    import time

    try:
        supabase = get_service_client()
        filename = f"{title.replace(' ', '_').lower()}_{int(time.time())}.md"
        file_path = f"{user_id}/{filename}"

        # 1. Upload to Storage
        supabase.storage.from_("knowledge-vault").upload(
            file_path,
            content.encode("utf-8"),
            {"content-type": "text/markdown", "upsert": "true"},
        )

        # 2. Insert into vault_documents and capture the generated ID
        insert_result = (
            supabase.table("vault_documents")
            .insert(
                {
                    "user_id": user_id,
                    "filename": filename,
                    "file_path": file_path,
                    "file_type": "text/markdown",
                    "size_bytes": len(content),
                    "category": doc_type,
                    "is_processed": True,
                }
            )
            .execute()
        )
        doc_id: Optional[str] = None
        if insert_result.data and len(insert_result.data) > 0:
            doc_id = insert_result.data[0].get("id")

        # 3. Make the saved markdown searchable in the Knowledge Vault (RAG).
        try:
            await ingest_document_content(
                content=content,
                title=title,
                document_type=doc_type,
                user_id=user_id,
                metadata={"file_path": file_path},
            )
        except Exception as rag_err:
            logger.warning(f"Failed to ingest saved brain dump doc into RAG: {rag_err}")

        return {"file_path": file_path, "doc_id": doc_id}
    except Exception as e:
        logger.error(f"Failed to save to vault: {e}")
        return {"file_path": None, "doc_id": None}


async def get_braindump_document(document_id: str) -> Dict[str, Any]:
    """Retrieve a specific Brain Dump / Validation Plan document by vault_documents ID.

    Use this when the user asks to reopen a brain dump in chat by ID so the agent can
    continue validation or research with the exact saved content.
    """
    from app.services.supabase_client import get_service_client
    from app.services.request_context import get_current_user_id

    try:
        user_id = get_current_user_id()
        if not user_id:
            return {"success": False, "error": "No authenticated user in request context"}

        supabase = get_service_client()
        result = (
            supabase.table("vault_documents")
            .select("id, filename, file_path, file_type, category, created_at")
            .eq("id", document_id)
            .eq("user_id", user_id)
            .single()
            .execute()
        )
        doc = getattr(result, "data", None)
        if not doc:
            return {"success": False, "error": "Brain dump document not found"}

        category = doc.get("category")
        if category not in {
            "Brain Dump",
            "Brain Dump Transcript",
            "Validation Plan",
            "Brain Dump Analysis",
            "Research",
        }:
            return {
                "success": False,
                "error": f"Document is not a brain dump artifact (category={category})",
            }

        file_bytes = supabase.storage.from_("knowledge-vault").download(doc["file_path"])
        if not file_bytes:
            return {"success": False, "error": "Document file not found in storage"}

        try:
            content = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            content = file_bytes.decode("latin-1", errors="replace")

        return {
            "success": True,
            "document": doc,
            "content": content,
        }
    except Exception as e:
        logger.error(f"Failed to retrieve brain dump document {document_id}: {e}")
        return {"success": False, "error": str(e)}

async def process_brainstorm_conversation(chat_history: str, context: Optional[str] = None) -> Dict[str, Any]:
    """Process a text-based brainstorming conversation.

    Analyzes a back-and-forth discussion between user and agent to generate:
    1. A clean 'Brain Dump' summary of the user's raw idea.
    2. A structured Validation Plan.
    Both are saved to the Knowledge Vault.

    Args:
        chat_history: The full transcript of the conversation.
        context: Optional additional context (may contain User ID).

    Returns:
        Dictionary containing the formatted Validation Plan (markdown).
    """
    from app.agents.shared import get_model
    from google.genai import types

    try:
        logger.info("Processing brainstorm conversation...")
        model = get_model()
        bounded_chat_history = _truncate_text_for_model(
            chat_history,
            max_chars=BRAINSTORM_MAX_HISTORY_CHARS,
            label="chat history",
        )
        bounded_context = _truncate_text_for_model(
            context,
            max_chars=BRAINSTORM_MAX_CONTEXT_CHARS,
            label="additional context",
        ) if context else None

        # --- Step 1: Extract and save a clean Brain Dump summary ---
        brain_dump_prompt = """You are an expert note-taker. The user just finished a brainstorming session.
Extract ONLY the user's ideas, thoughts, and key points from the conversation below. 
Ignore the agent's questions and prompts — focus purely on what the USER said or meant.

Format the output as a clean Markdown document with:
- **Title**: A short, descriptive title for the idea.
- **Core Idea**: 1-2 paragraph summary of the idea in the user's own words.
- **Key Points**: Bullet list of important details mentioned.
- **Open Questions**: Any unanswered questions the user raised.

--- Chat History ---
""" + bounded_chat_history

        brain_dump_response = await asyncio.to_thread(
            lambda: model.api_client.models.generate_content(
                model=model.model,
                contents=[types.Content(role="user", parts=[types.Part.from_text(text=brain_dump_prompt)])],
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=1024,
                )
            )
        )

        brain_dump_text = brain_dump_response.text if brain_dump_response.text else ""

        # --- Step 2: Generate the Validation Plan ---
        validation_prompt = """
You are an expert Strategic Planning Agent. The user has just completed a "Brainstorming Session" with an AI agent.
Your goal is to synthesize this conversation into a structured "Validation Plan" so the user can take the next steps.

Please analyze the provided Chat History and generate a report in Markdown format.

**Structure of the Validation Plan:**

1.  **Idea Overview**: A concise summary of the business idea or concept discussed.
2.  **Target Audience**: Who is this for? (deduced from conversation).
3.  **Core Value Proposition**: What problem does it solve?
4.  **Key Hypotheses**: What needs to be true for this to succeed?
5.  **Validation Experiments**: Suggest 3 specific, low-cost ways to test these hypotheses (e.g., landing page, interviews, prototype).
6.  **Immediate Next Steps**: A checklist of 3-5 tasks to do right now.

**Tone**: Encouraging, strategic, and action-oriented.
"""
        if bounded_context:
            validation_prompt += f"\n\nAdditional Context:\n{bounded_context}"

        validation_prompt += f"\n\n--- Chat History ---\n{bounded_chat_history}"

        validation_response = await asyncio.to_thread(
            lambda: model.api_client.models.generate_content(
                model=model.model,
                contents=[types.Content(role="user", parts=[types.Part.from_text(text=validation_prompt)])],
                config=types.GenerateContentConfig(
                    temperature=0.4,
                    max_output_tokens=2048,
                )
            )
        )

        if not validation_response.text:
            return {"success": False, "error": "Gemini returned no text response."}

        validation_text = validation_response.text

        # --- Step 3: Save both documents to Vault if user_id available ---
        if context and "User ID:" in context:
            try:
                import re
                match = re.search(r"User ID:\s*([a-f0-9\-]+)", context)
                if match:
                    user_id = match.group(1)

                    # Save Brain Dump summary
                    if brain_dump_text:
                        await _save_to_vault(brain_dump_text, "Brain Dump", "Brain Dump", user_id)

                    # Save Validation Plan
                    await _save_to_vault(validation_text, "Validation Plan", "Validation Plan", user_id)
            except Exception as save_err:
                logger.warning(f"Failed to auto-save brainstorm documents: {save_err}")

        return {
            "success": True,
            "validation_plan": validation_text
        }

    except Exception as e:
        logger.error(f"Error processing brainstorm: {e}")
        return {"success": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Comprehensive single-document brainstorm processor (Phase 2d)
# ---------------------------------------------------------------------------

_COMPREHENSIVE_PROMPT = """\
You are an expert Strategic Planning Agent. The user has just completed a brainstorming \
session with an AI assistant. Your goal is to synthesize the full conversation into a single, \
comprehensive analysis document.

**Output format — STRICTLY follow this Markdown template:**

# Brain Dump Analysis: [Extracted Title]

| Detail | Value |
| --- | --- |
| **Date** | {date} |
| **Topics** | [N] themes identified |

---

## Executive Summary
[2-3 paragraph synthesis of the entire conversation]

## Key Ideas Discussed
### 1. [Idea Title]
[Description with context from the conversation]

(repeat for each idea)

## Decision Points
| Decision | Pro | Con | Recommendation |
| --- | --- | --- | --- |
| ... | ... | ... | ... |

(if no explicit decisions discussed, omit this section)

## Action Items
- [ ] [Item] — *Priority: High*
- [ ] [Item] — *Priority: Medium*

## Resource Requirements
[If discussed, otherwise omit]

## Risk Factors
[If discussed, otherwise omit]

## Suggested Next Steps
1. [Step with rationale]
2. [Step with rationale]

---

**After the Markdown**, output a JSON metadata block on its own line starting with \
`<!-- META:` and ending with `-->`. The JSON must contain:
```
{{"title": "...", "key_themes": ["theme1", "theme2", ...], "action_item_count": N, "executive_summary": "1-2 sentence summary"}}
```

**Tone**: Encouraging, strategic, and action-oriented. Use the user's own language where possible.
"""


async def process_comprehensive_brainstorm(
    chat_history: str,
    context: Optional[str] = None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    turn_count: int = 0,
) -> Dict[str, Any]:
    """Generate a single comprehensive Brain Dump Analysis document.

    Replaces the old two-document flow (Brain Dump + Validation Plan) with one
    unified markdown analysis. Returns the analysis markdown, a parsed summary
    dict, and the ``vault_documents`` ID of the saved artifact.

    Args:
        chat_history: Full transcript of the brainstorming conversation.
        context: Optional extra context (may include User ID, Session ID).
        session_id: Voice session ID for metadata.
        user_id: Authenticated user ID — required for vault persistence.
        turn_count: Number of conversation turns for metadata.

    Returns:
        Dict with ``success``, ``analysis_markdown``, ``summary``, ``analysis_doc_id``.
    """
    import json as _json
    import re
    from datetime import datetime, timezone

    from app.agents.shared import get_model
    from google.genai import types

    try:
        logger.info("Processing comprehensive brainstorm analysis...")
        model = get_model()

        bounded_history = _truncate_text_for_model(
            chat_history,
            max_chars=BRAINSTORM_MAX_HISTORY_CHARS,
            label="chat history",
        )
        bounded_context = (
            _truncate_text_for_model(
                context,
                max_chars=BRAINSTORM_MAX_CONTEXT_CHARS,
                label="additional context",
            )
            if context
            else ""
        )

        now = datetime.now(timezone.utc)
        date_str = now.strftime("%B %d, %Y at %H:%M UTC")

        prompt = _COMPREHENSIVE_PROMPT.format(date=date_str)
        if bounded_context:
            prompt += f"\n\nAdditional Context:\n{bounded_context}"
        prompt += f"\n\n--- Chat History ({turn_count} turns) ---\n{bounded_history}"

        response = await asyncio.to_thread(
            lambda: model.api_client.models.generate_content(
                model=model.model,
                contents=[
                    types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=prompt)],
                    )
                ],
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=4096,
                ),
            )
        )

        if not response.text:
            return {"success": False, "error": "Gemini returned no text response."}

        raw_output = response.text

        # --- Parse metadata from the <!-- META: {...} --> block ---
        summary: Dict[str, Any] = {
            "title": "Brain Dump Analysis",
            "key_themes": [],
            "action_item_count": 0,
            "executive_summary": "",
        }
        analysis_markdown = raw_output

        meta_match = re.search(r"<!--\s*META:\s*(\{.*?\})\s*-->", raw_output, re.DOTALL)
        if meta_match:
            try:
                meta = _json.loads(meta_match.group(1))
                summary["title"] = meta.get("title", summary["title"])
                summary["key_themes"] = meta.get("key_themes", [])
                summary["action_item_count"] = meta.get("action_item_count", 0)
                summary["executive_summary"] = meta.get("executive_summary", "")
            except _json.JSONDecodeError:
                logger.warning("Failed to parse META block from comprehensive analysis")
            # Strip the meta block from the markdown body
            analysis_markdown = raw_output[: meta_match.start()].rstrip()

        # --- Save to vault ---
        analysis_doc_id: Optional[str] = None
        if user_id:
            vault_result = await _save_to_vault(
                analysis_markdown,
                summary["title"],
                "Brain Dump Analysis",
                user_id,
            )
            analysis_doc_id = vault_result.get("doc_id")

        return {
            "success": True,
            "analysis_markdown": analysis_markdown,
            "summary": summary,
            "analysis_doc_id": analysis_doc_id,
        }

    except Exception as e:
        logger.error(f"Error in comprehensive brainstorm processing: {e}")
        return {"success": False, "error": str(e)}
