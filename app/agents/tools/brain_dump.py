# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Brain Dump processing tools."""

import logging
import asyncio
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

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
                
                await _save_to_vault(analysis_content, title, "Brain Dump Analysis", user_id)
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

async def _save_to_vault(content: str, title: str, doc_type: str, user_id: str) -> Optional[str]:
    """Helper to save content to Knowledge Vault storage and DB."""
    from app.services.supabase_client import get_service_client
    from app.rag.knowledge_vault import ingest_document_content
    import time

    try:
        supabase = get_service_client()
        filename = f"{title.replace(' ', '_').lower()}_{int(time.time())}.md"
        file_path = f"{user_id}/{filename}"
        
        # 1. Upload to Storage
        res = supabase.storage.from_("knowledge-vault").upload(
            file_path,
            content.encode("utf-8"),
            {"content-type": "text/markdown", "upsert": "true"}
        )
        
        # 2. Insert into vault_documents
        # We need the user_id. In a tool we might not have it directly in args unless passed.
        # However, for now we will rely on the fact that these tools run in a context where we might infer it 
        # OR we just use the path. 
        # Wait, the tool doesn't receive user_id. 
        # We will try to extract it from context or pass it. 
        # For now, let's assume valid user_id is passed or we can't save to DB easily without it.
        # Actually, `process_brain_dump` receives `file_path` which usually contains `user_id/filename`.
        
        # Attempt to parse user_id from path if possible, or use a default if running in test
        real_user_id = user_id
        
        supabase.table("vault_documents").insert({
            "user_id": real_user_id,
            "filename": filename,
            "file_path": file_path,
            "file_type": "text/markdown",
            "size_bytes": len(content),
            "category": doc_type,
            "is_processed": True
        }).execute()

        # Make the saved markdown searchable in the Knowledge Vault (RAG).
        try:
            await ingest_document_content(
                content=content,
                title=title,
                document_type=doc_type,
                user_id=real_user_id,
                metadata={"file_path": file_path},
            )
        except Exception as rag_err:
            logger.warning(f"Failed to ingest saved brain dump doc into RAG: {rag_err}")
        
        return file_path
    except Exception as e:
        logger.error(f"Failed to save to vault: {e}")
        return None


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
""" + chat_history

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
        if context:
            validation_prompt += f"\n\nAdditional Context:\n{context}"

        validation_prompt += f"\n\n--- Chat History ---\n{chat_history}"

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
