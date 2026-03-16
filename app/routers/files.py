import logging
import os
import tempfile
from typing import Optional

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from pydantic import BaseModel

from app.middleware.rate_limiter import get_user_persona_limit, limiter

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_CHARS = 50000
DEFAULT_MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024
UPLOAD_CHUNK_SIZE_BYTES = 1024 * 1024


class FileUploadResponse(BaseModel):
    filename: str
    content: str
    summary_prompt: str


def _extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text content from PDF file using pypdf."""
    try:
        from pypdf import PdfReader
    except ImportError:
        logger.error('pypdf not installed')
        return '[PDF parsing not available. Please install pypdf package.]'

    try:
        reader = PdfReader(pdf_path)
        text_parts = []

        for page_num, page in enumerate(reader.pages):
            try:
                text = page.extract_text()
                if text and text.strip():
                    text_parts.append(text)
                else:
                    logger.warning('No text found on page %s in %s', page_num + 1, pdf_path)
            except Exception as exc:
                logger.warning('Error extracting text from page %s: %s', page_num + 1, exc)
                continue

        full_text = '\n\n'.join(text_parts)

        if not full_text.strip():
            return '[PDF contains no extractable text. It may contain only images or scanned documents. Please upload a text-based version or add it to Knowledge Vault manually.]'

        return full_text

    except Exception as exc:
        logger.error('Error reading PDF file %s: %s', pdf_path, exc)
        return f'[Error reading PDF: {str(exc)}]'


def _extract_text_from_docx(docx_path: str) -> str:
    """Extract text content from DOCX file."""
    try:
        from docx import Document
    except ImportError:
        return '[DOCX parsing not available. Please install python-docx package.]'

    try:
        doc = Document(docx_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return '\n\n'.join(paragraphs)
    except Exception as exc:
        logger.error('Error reading DOCX file %s: %s', docx_path, exc)
        return f'[Error reading DOCX: {str(exc)}]'


def _extract_text_from_text_file(file_path: str) -> str:
    """Extract text content from a plain text file."""
    encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']

    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as file_handle:
                return file_handle.read()
        except UnicodeDecodeError:
            continue
        except Exception as exc:
            logger.error('Error reading text file %s: %s', file_path, exc)
            break

    return '[Error: Could not decode file. Try saving as UTF-8.]'


def _truncate_content(content: str, max_chars: int = MAX_CHARS) -> str:
    """Truncate content if it exceeds maximum length."""
    if len(content) > max_chars:
        return content[:max_chars] + f"\n\n... [Truncated - content exceeds {max_chars} character limit. First {max_chars} characters shown.]"
    return content


def _get_max_upload_size_bytes() -> int:
    raw_value = os.getenv('MAX_UPLOAD_SIZE_BYTES', str(DEFAULT_MAX_UPLOAD_SIZE_BYTES)).strip()
    try:
        parsed = int(raw_value)
    except ValueError:
        logger.warning(
            'Invalid MAX_UPLOAD_SIZE_BYTES value %r; falling back to %s bytes',
            raw_value,
            DEFAULT_MAX_UPLOAD_SIZE_BYTES,
        )
        return DEFAULT_MAX_UPLOAD_SIZE_BYTES
    return parsed if parsed > 0 else DEFAULT_MAX_UPLOAD_SIZE_BYTES


def _format_bytes(num_bytes: int) -> str:
    if num_bytes >= 1024 * 1024:
        return f'{num_bytes / (1024 * 1024):.1f} MiB'
    if num_bytes >= 1024:
        return f'{num_bytes / 1024:.1f} KiB'
    return f'{num_bytes} B'


def _raise_file_too_large(max_upload_size_bytes: int) -> None:
    raise HTTPException(
        status_code=413,
        detail=f'File too large. Maximum upload size is {_format_bytes(max_upload_size_bytes)}.',
    )


def _validate_declared_upload_size(content_length: Optional[str], max_upload_size_bytes: int) -> None:
    if not content_length:
        return

    try:
        declared_size = int(content_length)
    except ValueError:
        logger.warning('Ignoring invalid Content-Length header on upload request: %r', content_length)
        return

    if declared_size > max_upload_size_bytes:
        _raise_file_too_large(max_upload_size_bytes)


async def _write_upload_to_temp_file(
    upload: UploadFile,
    temp_path: str,
    max_upload_size_bytes: int,
) -> None:
    bytes_written = 0

    with open(temp_path, 'wb') as temp_file:
        while True:
            chunk = await upload.read(UPLOAD_CHUNK_SIZE_BYTES)
            if not chunk:
                break

            bytes_written += len(chunk)
            if bytes_written > max_upload_size_bytes:
                _raise_file_too_large(max_upload_size_bytes)

            temp_file.write(chunk)


@router.post('/upload', response_model=FileUploadResponse)
@limiter.limit(get_user_persona_limit)
async def upload_file(request: Request, file: UploadFile = File(...)):
    """
    Upload a file, extract its text content, and return a prompt for the agent.
    """
    temp_path: Optional[str] = None
    original_filename = file.filename or 'upload'
    max_upload_size_bytes = _get_max_upload_size_bytes()

    try:
        _validate_declared_upload_size(request.headers.get('content-length'), max_upload_size_bytes)

        temp_path = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=f'_{original_filename}',
        ).name

        await _write_upload_to_temp_file(file, temp_path, max_upload_size_bytes)

        content = ''
        filename = original_filename.lower()

        if filename.endswith(('.txt', '.md', '.csv', '.json', '.py', '.js', '.ts', '.html', '.css', '.sql', '.xml', '.yaml', '.yml')):
            content = _extract_text_from_text_file(temp_path)
        elif filename.endswith('.pdf'):
            content = _extract_text_from_pdf(temp_path)
        elif filename.endswith('.docx'):
            content = _extract_text_from_docx(temp_path)
        elif filename.endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
            content = f'[Image file detected: {original_filename}. Image content extraction requires OCR. Please provide a text description or upload a text-based document.]'
        elif filename.endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm')):
            content = f'[Video file detected: {original_filename}. Video content extraction is not supported. Please provide a transcript or description.]'
        elif filename.endswith(('.mp3', '.wav', '.ogg', '.flac', '.m4a')):
            content = f'[Audio file detected: {original_filename}. Audio transcription is not supported in this endpoint. Please use a dedicated transcription service.]'
        else:
            content = f'[Unsupported file type: {original_filename}. Supported types: txt, md, csv, json, py, js, ts, html, css, sql, xml, yaml, yml, pdf, docx]'

        content = _truncate_content(content)

        summary_prompt = (
            f"I have uploaded a file named '{original_filename}'. "
            f'Here is its content:\n\n'
            f'```\n{content}\n```\n\n'
            'Please analyze this file. Summarize its key points and tell me if I should add it to the Knowledge Vault.'
        )

        return FileUploadResponse(
            filename=original_filename,
            content=content,
            summary_prompt=summary_prompt,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error('File processing failed: %s', exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f'File processing failed: {str(exc)}')
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except Exception as exc:
                logger.warning('Failed to clean up temp file %s: %s', temp_path, exc)
