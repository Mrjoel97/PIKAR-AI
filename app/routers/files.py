import logging
import shutil
import tempfile
import os
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from pydantic import BaseModel

from app.middleware.rate_limiter import limiter, get_user_persona_limit

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_CHARS = 50000


class FileUploadResponse(BaseModel):
    filename: str
    content: str
    summary_prompt: str


def _extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text content from PDF file using pypdf.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        Extracted text content.
    """
    try:
        from pypdf import PdfReader
    except ImportError:
        logger.error("pypdf not installed")
        return "[PDF parsing not available. Please install pypdf package.]"

    try:
        reader = PdfReader(pdf_path)
        text_parts = []

        for page_num, page in enumerate(reader.pages):
            try:
                text = page.extract_text()
                if text and text.strip():
                    text_parts.append(text)
                else:
                    logger.warning(f"No text found on page {page_num + 1} in {pdf_path}")
            except Exception as e:
                logger.warning(f"Error extracting text from page {page_num + 1}: {e}")
                continue

        full_text = "\n\n".join(text_parts)

        if not full_text.strip():
            return "[PDF contains no extractable text. It may contain only images or scanned documents. Please upload a text-based version or add it to Knowledge Vault manually.]"

        return full_text

    except Exception as e:
        logger.error(f"Error reading PDF file {pdf_path}: {e}")
        return f"[Error reading PDF: {str(e)}]"


def _extract_text_from_docx(docx_path: str) -> str:
    """Extract text content from DOCX file.

    Args:
        docx_path: Path to the DOCX file.

    Returns:
        Extracted text content.
    """
    try:
        from docx import Document
    except ImportError:
        return "[DOCX parsing not available. Please install python-docx package.]"

    try:
        doc = Document(docx_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs)
    except Exception as e:
        logger.error(f"Error reading DOCX file {docx_path}: {e}")
        return f"[Error reading DOCX: {str(e)}]"


def _truncate_content(content: str, max_chars: int = MAX_CHARS) -> str:
    """Truncate content if it exceeds maximum length.

    Args:
        content: The content to truncate.
        max_chars: Maximum character limit.

    Returns:
        Truncated content with indicator.
    """
    if len(content) > max_chars:
        return content[:max_chars] + f"\n\n... [Truncated - content exceeds {max_chars} character limit. First {max_chars} characters shown.]"
    return content


@router.post("/upload", response_model=FileUploadResponse)
@limiter.limit(get_user_persona_limit)
async def upload_file(request: Request, file: UploadFile = File(...)):
    """
    Uploads a file, extracts its text content, and returns a prompt for the agent.

    Supported file types:
    - Text files: .txt, .md, .csv, .json, .py, .js, .ts, .html, .css, .sql
    - PDF files: .pdf
    - Word documents: .docx (if python-docx is installed)

    Returns:
        FileUploadResponse with extracted content and summary prompt.
    """
    temp_path: Optional[str] = None

    try:
        temp_path = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=f"_{file.filename}"
        ).name

        with open(temp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        content = ""
        filename = file.filename.lower()

        if filename.endswith(('.txt', '.md', '.csv', '.json', '.py', '.js', '.ts', '.html', '.css', '.sql', '.xml', '.yaml', '.yml')):
            content = _extract_text_from_text_file(temp_path)

        elif filename.endswith('.pdf'):
            content = _extract_text_from_pdf(temp_path)

        elif filename.endswith('.docx'):
            content = _extract_text_from_docx(temp_path)

        elif filename.endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
            content = f"[Image file detected: {file.filename}. Image content extraction requires OCR. Please provide a text description or upload a text-based document.]"

        elif filename.endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm')):
            content = f"[Video file detected: {file.filename}. Video content extraction is not supported. Please provide a transcript or description.]"

        elif filename.endswith(('.mp3', '.wav', '.ogg', '.flac', '.m4a')):
            content = f"[Audio file detected: {file.filename}. Audio transcription is not supported in this endpoint. Please use a dedicated transcription service.]"

        else:
            content = f"[Unsupported file type: {file.filename}. Supported types: txt, md, csv, json, py, js, ts, html, css, sql, xml, yaml, yml, pdf, docx]"

        content = _truncate_content(content)

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

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File processing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"File processing failed: {str(e)}")
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except Exception as e:
                logger.warning(f"Failed to clean up temp file {temp_path}: {e}")


def _extract_text_from_text_file(file_path: str) -> str:
    """Extract text content from a plain text file.

    Args:
        file_path: Path to the text file.

    Returns:
        Extracted text content.
    """
    encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']

    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except Exception as e:
            logger.error(f"Error reading text file {file_path}: {e}")
            break

    return f"[Error: Could not decode file. Try saving as UTF-8.]"
