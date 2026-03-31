"""Input validation models and utilities for Pikar AI tools.

This module provides Pydantic models for validating tool function parameters,
with built-in length limits, format validation, and security checks.
"""

import html
import re

from pydantic import BaseModel, Field, field_validator

from app.exceptions import ValidationError

# =============================================================================
# Common Validation Constraints
# =============================================================================

# Maximum lengths for common string fields
MAX_USER_ID_LENGTH = 128
MAX_SESSION_ID_LENGTH = 256
MAX_QUERY_LENGTH = 1000
MAX_NAME_LENGTH = 256
MAX_DESCRIPTION_LENGTH = 5000
MAX_EMAIL_LENGTH = 254
MAX_URL_LENGTH = 2048
MAX_CONTENT_LENGTH = 100_000  # 100KB
MAX_LIST_ITEMS = 100

# Valid patterns
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
)
EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
URL_PATTERN = re.compile(r"^https?://[^\s/$.?#].[^\s]*$", re.IGNORECASE)

# Restricted content patterns (for XSS prevention)
SCRIPT_PATTERN = re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL)
EVENT_HANDLER_PATTERN = re.compile(r"\bon\w+\s*=", re.IGNORECASE)


# =============================================================================
# Base Validation Models
# =============================================================================


class BaseToolInput(BaseModel):
    """Base class for all tool input validation models."""

    model_config = {
        "str_strip_whitespace": True,
        "validate_assignment": True,
    }


# =============================================================================
# Common Parameter Models
# =============================================================================


class UserIdInput(BaseToolInput):
    """Validates user ID parameter."""

    user_id: str = Field(..., min_length=1, max_length=MAX_USER_ID_LENGTH)

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        # Check for injection attempts
        if any(char in v for char in [";", "--", "/*", "*/", "xp_", "sp_"]):
            raise ValueError("Invalid characters in user_id")
        return v


class SessionIdInput(BaseToolInput):
    """Validates session ID parameter."""

    session_id: str = Field(..., min_length=1, max_length=MAX_SESSION_ID_LENGTH)

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: str) -> str:
        if any(char in v for char in [";", "--", "/*", "*/"]):
            raise ValueError("Invalid characters in session_id")
        return v


class SearchQueryInput(BaseToolInput):
    """Validates search query parameter."""

    query: str = Field(..., min_length=1, max_length=MAX_QUERY_LENGTH)

    @field_validator("query")
    @classmethod
    def sanitize_query(cls, v: str) -> str:
        # Trim excessive whitespace
        v = " ".join(v.split())
        return v


class PaginationInput(BaseToolInput):
    """Validates pagination parameters."""

    offset: int = Field(default=0, ge=0, le=10000)
    limit: int = Field(default=20, ge=1, le=MAX_LIST_ITEMS)


class UUIDInput(BaseToolInput):
    """Validates UUID parameter."""

    id: str = Field(..., min_length=36, max_length=36)

    @field_validator("id")
    @classmethod
    def validate_uuid(cls, v: str) -> str:
        if not UUID_PATTERN.match(v):
            raise ValueError("Invalid UUID format")
        return v.lower()


class EmailInput(BaseToolInput):
    """Validates email parameter."""

    email: str = Field(..., min_length=3, max_length=MAX_EMAIL_LENGTH)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not EMAIL_PATTERN.match(v):
            raise ValueError("Invalid email format")
        return v.lower()


class URLInput(BaseToolInput):
    """Validates URL parameter."""

    url: str = Field(..., min_length=5, max_length=MAX_URL_LENGTH)

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not URL_PATTERN.match(v):
            raise ValueError("Invalid URL format")
        return v


# =============================================================================
# Content Validation Models
# =============================================================================


class TextContentInput(BaseToolInput):
    """Validates text content with XSS prevention."""

    content: str = Field(..., min_length=1, max_length=MAX_CONTENT_LENGTH)

    @field_validator("content")
    @classmethod
    def sanitize_content(cls, v: str) -> str:
        # Check for script tags
        if SCRIPT_PATTERN.search(v):
            raise ValueError("Script tags not allowed in content")

        # Check for event handlers
        if EVENT_HANDLER_PATTERN.search(v):
            raise ValueError("Event handlers not allowed in content")

        # Escape HTML entities as a precaution
        v = html.escape(v)

        return v


class NameInput(BaseToolInput):
    """Validates name parameter."""

    name: str = Field(..., min_length=1, max_length=MAX_NAME_LENGTH)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        # Check for HTML/script content
        if SCRIPT_PATTERN.search(v):
            raise ValueError("Script tags not allowed in name")

        # Trim whitespace
        v = v.strip()

        return v


class DescriptionInput(BaseToolInput):
    """Validates description parameter."""

    description: str = Field(..., min_length=1, max_length=MAX_DESCRIPTION_LENGTH)

    @field_validator("description")
    @classmethod
    def sanitize_description(cls, v: str) -> str:
        # Check for script tags
        if SCRIPT_PATTERN.search(v):
            raise ValueError("Script tags not allowed in description")

        # Check for event handlers
        if EVENT_HANDLER_PATTERN.search(v):
            raise ValueError("Event handlers not allowed in description")

        # Normalize whitespace
        v = " ".join(v.split())

        return v


# =============================================================================
# Tool-Specific Validation Models
# =============================================================================


class ListSkillsInput(BaseToolInput):
    """Validates list_skills tool parameters."""

    category: str | None = Field(default=None, max_length=50)

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str | None) -> str | None:
        if v is None:
            return v

        valid_categories = {
            "finance",
            "hr",
            "marketing",
            "sales",
            "compliance",
            "content",
            "data",
            "support",
            "operations",
            "planning",
        }

        v = v.lower().strip()
        if v not in valid_categories:
            raise ValueError(f"Invalid category. Must be one of: {valid_categories}")

        return v


class SearchSkillsInput(BaseToolInput):
    """Validates search_skills tool parameters."""

    query: str = Field(..., min_length=1, max_length=MAX_QUERY_LENGTH)
    category: str | None = Field(default=None, max_length=50)

    @field_validator("query")
    @classmethod
    def sanitize_query(cls, v: str) -> str:
        v = " ".join(v.split())
        if SCRIPT_PATTERN.search(v):
            raise ValueError("Script tags not allowed in query")
        return v


class CreateSkillInput(BaseToolInput):
    """Validates create_skill tool parameters."""

    name: str = Field(..., min_length=1, max_length=MAX_NAME_LENGTH)
    description: str = Field(..., min_length=1, max_length=MAX_DESCRIPTION_LENGTH)
    category: str = Field(..., max_length=50)
    content: str | None = Field(default=None, max_length=MAX_CONTENT_LENGTH)

    @field_validator("name", "category")
    @classmethod
    def sanitize_name_fields(cls, v: str) -> str:
        if SCRIPT_PATTERN.search(v):
            raise ValueError("Script tags not allowed")
        return v.strip()

    @field_validator("description")
    @classmethod
    def sanitize_description(cls, v: str) -> str:
        if SCRIPT_PATTERN.search(v):
            raise ValueError("Script tags not allowed")
        if EVENT_HANDLER_PATTERN.search(v):
            raise ValueError("Event handlers not allowed")
        return " ".join(v.split())


class CalendarEventInput(BaseToolInput):
    """Validates calendar event parameters."""

    title: str = Field(..., min_length=1, max_length=MAX_NAME_LENGTH)
    description: str | None = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)
    start_time: str = Field(..., max_length=50)  # ISO format
    end_time: str | None = Field(default=None, max_length=50)
    attendees: list[str] | None = Field(default=None, max_length=MAX_LIST_ITEMS)

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        if SCRIPT_PATTERN.search(v):
            raise ValueError("Script tags not allowed in title")
        return v.strip()

    @field_validator("attendees")
    @classmethod
    def validate_attendees(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v

        for attendee in v:
            if not EMAIL_PATTERN.match(attendee):
                raise ValueError(f"Invalid email: {attendee}")

        return v


class SendEmailInput(BaseToolInput):
    """Validates email sending parameters."""

    to: str = Field(..., max_length=MAX_EMAIL_LENGTH)
    subject: str = Field(..., min_length=1, max_length=MAX_NAME_LENGTH)
    body: str = Field(..., min_length=1, max_length=MAX_CONTENT_LENGTH)
    cc: list[str] | None = Field(default=None, max_length=MAX_LIST_ITEMS)

    @field_validator("to", "cc")
    @classmethod
    def validate_emails(cls, v) -> str:
        # Handle both string and list inputs
        if isinstance(v, list):
            for email in v:
                if not EMAIL_PATTERN.match(email):
                    raise ValueError(f"Invalid email: {email}")
            return v
        elif isinstance(v, str):
            if not EMAIL_PATTERN.match(v):
                raise ValueError(f"Invalid email: {v}")
            return v
        return v

    @field_validator("subject", "body")
    @classmethod
    def sanitize_content(cls, v: str) -> str:
        if SCRIPT_PATTERN.search(v):
            raise ValueError("Script tags not allowed")
        return v


class FileUploadInput(BaseToolInput):
    """Validates file upload parameters."""

    filename: str = Field(..., min_length=1, max_length=MAX_NAME_LENGTH)
    content_type: str | None = Field(default=None, max_length=100)
    max_size_mb: int = Field(default=10, ge=1, le=100)

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, v: str) -> str:
        # Check for path traversal
        if ".." in v or "/" in v or "\\\\" in v:
            raise ValueError("Invalid filename")

        # Check for dangerous extensions
        dangerous_extensions = {".exe", ".bat", ".cmd", ".sh", ".ps1", ".vbs"}
        ext = v[v.rfind(".") :].lower() if "." in v else ""
        if ext in dangerous_extensions:
            raise ValueError(f"File type not allowed: {ext}")

        return v

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, v: str | None) -> str | None:
        if v is None:
            return v

        allowed_types = {
            "text/",
            "image/",
            "application/pdf",
            "application/json",
            "application/xml",
        }

        v = v.lower()
        if not any(v.startswith(allowed) for allowed in allowed_types):
            raise ValueError("Content type not allowed")

        return v


# =============================================================================
# Validation Utility Functions
# =============================================================================


def validate_tool_input(model_class: type[BaseToolInput], data: dict) -> BaseToolInput:
    """Validate tool input data against a Pydantic model.

    Args:
        model_class: The Pydantic model class to validate against
        data: The input data dictionary

    Returns:
        Validated model instance

    Raises:
        ValidationError: If validation fails
    """
    try:
        return model_class(**data)
    except Exception as e:
        raise ValidationError(
            message=f"Input validation failed: {e!s}", code="VALIDATION_ERROR"
        )


def sanitize_html(user_input: str) -> str:
    """Sanitize user input to prevent XSS attacks.

    Args:
        user_input: Raw user input

    Returns:
        Sanitized string
    """
    # Remove script tags
    sanitized = SCRIPT_PATTERN.sub("", user_input)

    # Remove event handlers
    sanitized = EVENT_HANDLER_PATTERN.sub("", sanitized)

    # Escape HTML entities
    sanitized = html.escape(sanitized)

    return sanitized


def validate_sql_safe(value: str) -> bool:
    """Check if a string is safe from SQL injection.

    Args:
        value: String to check

    Returns:
        True if safe, False otherwise
    """
    dangerous_patterns = [
        r";\s*--",  # Comment injection
        r"/\*.*\*/",  # Block comment injection
        r"exec\s*\(",  # EXEC injection
        r"execute\s*\(",  # EXECUTE injection
        r"union\s+select",  # UNION injection
        r"drop\s+table",  # DROP table
        r"delete\s+from",  # DELETE from
        r"insert\s+into",  # INSERT into
        r"update\s+.*\s+set",  # UPDATE set
        r"xp_",  # Extended procedure prefix
        r"sp_",  # Stored procedure prefix
    ]

    value_lower = value.lower()
    for pattern in dangerous_patterns:
        if re.search(pattern, value_lower):
            return False

    return True
