import shutil
import tempfile
import os
from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from app.middleware.rate_limiter import limiter, get_user_persona_limit

from pydantic import BaseModel

router = APIRouter()

class FileUploadResponse(BaseModel):
    filename: str
    content: str
    summary_prompt: str

@router.post("/upload", response_model=FileUploadResponse)
@limiter.limit(get_user_persona_limit)
async def upload_file(request: Request, file: UploadFile = File(...)):
    """
    Uploads a file, extracts its text content, and returns a prompt for the agent.
    Currently acts as a 'Context Sniffer' for text/markdown files.
    """
    try:
        # 1. Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        # 2. Extract content based on extension
        content = ""
        filename = file.filename.lower()
        
        if filename.endswith(('.txt', '.md', '.csv', '.json', '.py', '.js', '.ts', '.html', '.css', '.sql')):
            # Text-based files
            try:
                with open(tmp_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                # Fallback to latin-1 if utf-8 fails
                with open(tmp_path, 'r', encoding='latin-1') as f:
                    content = f.read()
        
        elif filename.endswith('.pdf'):
            # TODO: Add pypdf dependency for PDF support
            content = "[PDF parsing not yet implemented. Please upload text/markdown for now.]"
        
        else:
            content = f"[Binary or unsupported file type: {filename}]"

        # 3. Cleanup
        os.unlink(tmp_path)

        # 4. Truncate if too large (simple safety)
        MAX_CHARS = 50000 
        if len(content) > MAX_CHARS:
            content = content[:MAX_CHARS] + "\n...[Truncated]..."

        # 5. Construct Agent Prompt
        summary_prompt = (
            f"I have uploaded a file named '{file.filename}'. "
            f"Here is its content:\n\n"
            f"```\n{content}\n```\n\n"
            "Please analyze this file. Summarize its key points and tell me if I should add it to the Knowledge Vault."
        )

        return FileUploadResponse(
            filename=file.filename,
            content=content,
            summary_prompt=summary_prompt
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File processing failed: {str(e)}")
