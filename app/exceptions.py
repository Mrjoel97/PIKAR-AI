# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Custom exception hierarchy for Pikar AI.

This module defines the application's custom exception classes with proper
error codes and HTTP status mappings for consistent error handling.

Usage:
    from app.exceptions import PikarError, ValidationError, CacheError, DatabaseError, ErrorResponse

    raise ValidationError(
        message="Invalid input",
        code=ErrorCode.VALIDATION_ERROR,
        details={"field": "email", "reason": "invalid_format"}
    )

Error Code Convention:
    - PIKAR_{DOMAIN}_{CODE}: Uppercase, underscore-separated
    - Example: PIKAR_VALIDATION_INVALID_INPUT, PIKAR_CACHE_CONNECTION_FAILED

HTTP Status Mapping:
    - 4xx: Client errors (validation, authentication, not found)
    - 5xx: Server errors (database, cache, internal)
"""

from datetime import datetime
from enum import Enum
from typing import Any

try:
    from pydantic import BaseModel, Field

    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False

    # Create a minimal BaseModel for when Pydantic is not available
    class BaseModel:
        pass


class ErrorCode(Enum):
    """Standard error codes for the application."""

    # General errors
    UNKNOWN_ERROR = "PIKAR_UNKNOWN_ERROR"
    INTERNAL_ERROR = "PIKAR_INTERNAL_ERROR"

    # Validation errors
    VALIDATION_ERROR = "PIKAR_VALIDATION_ERROR"
    INVALID_INPUT = "PIKAR_INVALID_INPUT"
    MISSING_REQUIRED_FIELD = "PIKAR_MISSING_REQUIRED_FIELD"
    INVALID_FORMAT = "PIKAR_INVALID_FORMAT"
    CONSTRAINT_VIOLATION = "PIKAR_CONSTRAINT_VIOLATION"

    # Authentication/Authorization errors
    AUTHENTICATION_ERROR = "PIKAR_AUTHENTICATION_ERROR"
    AUTHORIZATION_ERROR = "PIKAR_AUTHORIZATION_ERROR"
    TOKEN_EXPIRED = "PIKAR_TOKEN_EXPIRED"
    TOKEN_INVALID = "PIKAR_TOKEN_INVALID"
    INSUFFICIENT_PERMISSIONS = "PIKAR_INSUFFICIENT_PERMISSIONS"

    # Resource errors
    NOT_FOUND = "PIKAR_NOT_FOUND"
    RESOURCE_CONFLICT = "PIKAR_RESOURCE_CONFLICT"
    RESOURCE_DELETED = "PIKAR_RESOURCE_DELETED"
    RESOURCE_LOCKED = "PIKAR_RESOURCE_LOCKED"

    # Database errors
    DATABASE_ERROR = "PIKAR_DATABASE_ERROR"
    DATABASE_CONNECTION_FAILED = "PIKAR_DATABASE_CONNECTION_FAILED"
    DATABASE_QUERY_FAILED = "PIKAR_DATABASE_QUERY_FAILED"
    DATABASE_CONSTRAINT_VIOLATION = "PIKAR_DATABASE_CONSTRAINT_VIOLATION"
    TRANSACTION_FAILED = "PIKAR_TRANSACTION_FAILED"

    # Cache errors
    CACHE_ERROR = "PIKAR_CACHE_ERROR"
    CACHE_CONNECTION_FAILED = "PIKAR_CACHE_CONNECTION_FAILED"
    CACHE_KEY_NOT_FOUND = "PIKAR_CACHE_KEY_NOT_FOUND"
    CACHE_SERIALIZATION_FAILED = "PIKAR_CACHE_SERIALIZATION_FAILED"

    # External service errors
    EXTERNAL_SERVICE_ERROR = "PIKAR_EXTERNAL_SERVICE_ERROR"
    EXTERNAL_SERVICE_UNAVAILABLE = "PIKAR_EXTERNAL_SERVICE_UNAVAILABLE"
    EXTERNAL_SERVICE_TIMEOUT = "PIKAR_EXTERNAL_SERVICE_TIMEOUT"

    # Rate limiting
    RATE_LIMIT_EXCEEDED = "PIKAR_RATE_LIMIT_EXCEEDED"
    QUOTA_EXCEEDED = "PIKAR_QUOTA_EXCEEDED"

    # Workflow errors
    WORKFLOW_ERROR = "PIKAR_WORKFLOW_ERROR"
    WORKFLOW_NOT_FOUND = "PIKAR_WORKFLOW_NOT_FOUND"
    WORKFLOW_EXECUTION_FAILED = "PIKAR_WORKFLOW_EXECUTION_FAILED"
    STEP_FAILED = "PIKAR_STEP_FAILED"

    # Agent errors
    AGENT_ERROR = "PIKAR_AGENT_ERROR"
    AGENT_NOT_FOUND = "PIKAR_AGENT_NOT_FOUND"
    AGENT_EXECUTION_FAILED = "PIKAR_AGENT_EXECUTION_FAILED"
    AGENT_TIMEOUT = "PIKAR_AGENT_TIMEOUT"

    # Skill errors
    SKILL_ERROR = "PIKAR_SKILL_ERROR"
    SKILL_NOT_FOUND = "PIKAR_SKILL_NOT_FOUND"
    SKILL_EXECUTION_FAILED = "PIKAR_SKILL_EXECUTION_FAILED"
    SKILL_RESTRICTED = "PIKAR_SKILL_RESTRICTED"


# Structured Error Response Model
class ErrorDetail(BaseModel):
    """Detailed error information for debugging."""

    field: str | None = Field(None, description="The field that caused the error")
    reason: str | None = Field(None, description="The reason for the error")
    value: Any | None = Field(None, description="The value that caused the error")
    constraint: str | None = Field(None, description="The constraint that was violated")


class ErrorSource(BaseModel):
    """Pointer to the error source in the request."""

    pointer: str | None = Field(None, description="JSON pointer to the error location")
    parameter: str | None = Field(
        None, description="Query parameter that caused the error"
    )
    header: str | None = Field(None, description="Header that caused the error")


class ErrorResponse(BaseModel):
    """Structured error response model for API responses.

    This model provides a consistent format for all error responses
    across the API, including error codes, messages, details, and
    request context for debugging.

    Attributes:
        code: Machine-readable error code (e.g., PIKAR_VALIDATION_ERROR)
        message: Human-readable error message
        details: Additional error details for debugging
        source: Source location of the error in the request
        request_id: Unique identifier for the request (for log correlation)
        timestamp: When the error occurred (ISO 8601 format)
        trace_id: Optional trace ID for distributed tracing
    """

    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: dict[str, Any] | None = Field(None, description="Additional error details")
    source: ErrorSource | None = Field(None, description="Error source location")
    request_id: str | None = Field(None, description="Request ID for correlation")
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Error timestamp",
    )
    trace_id: str | None = Field(None, description="Distributed tracing ID")

    @classmethod
    def from_exception(
        cls, exception: Exception, request_id: str | None = None
    ) -> "ErrorResponse":
        """Create an ErrorResponse from an exception.

        Args:
            exception: The exception to convert
            request_id: Optional request ID for correlation

        Returns:
            ErrorResponse instance
        """
        if isinstance(exception, PikarError):
            return cls(
                code=exception.code.value,
                message=exception.message,
                details=exception.details,
                request_id=request_id,
            )
        else:
            # Generic error for unknown exceptions
            return cls(
                code=ErrorCode.UNKNOWN_ERROR.value,
                message=str(exception),
                request_id=request_id,
            )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = self.model_dump(exclude_none=True)
        return result


class ValidationErrorResponse(ErrorResponse):
    """Specialized error response for validation errors."""

    errors: list[ErrorDetail] = Field(
        default_factory=list, description="List of validation errors"
    )

    @classmethod
    def from_validation_errors(
        cls,
        errors: list[ErrorDetail],
        message: str = "Validation failed",
        request_id: str | None = None,
    ) -> "ValidationErrorResponse":
        """Create a validation error response from a list of errors."""
        return cls(
            code=ErrorCode.VALIDATION_ERROR.value,
            message=message,
            errors=errors,
            details={"error_count": len(errors)},
            request_id=request_id,
        )


# HTTP Status code mapping
ERROR_CODE_TO_HTTP_STATUS = {
    # 4xx Client Errors
    ErrorCode.VALIDATION_ERROR: 400,
    ErrorCode.INVALID_INPUT: 400,
    ErrorCode.MISSING_REQUIRED_FIELD: 400,
    ErrorCode.INVALID_FORMAT: 400,
    ErrorCode.CONSTRAINT_VIOLATION: 400,
    ErrorCode.AUTHENTICATION_ERROR: 401,
    ErrorCode.TOKEN_EXPIRED: 401,
    ErrorCode.TOKEN_INVALID: 401,
    ErrorCode.AUTHORIZATION_ERROR: 403,
    ErrorCode.INSUFFICIENT_PERMISSIONS: 403,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.RESOURCE_DELETED: 404,
    ErrorCode.RESOURCE_CONFLICT: 409,
    ErrorCode.RESOURCE_LOCKED: 409,
    ErrorCode.RATE_LIMIT_EXCEEDED: 429,
    ErrorCode.QUOTA_EXCEEDED: 429,
    # 5xx Server Errors
    ErrorCode.INTERNAL_ERROR: 500,
    ErrorCode.UNKNOWN_ERROR: 500,
    ErrorCode.DATABASE_ERROR: 500,
    ErrorCode.DATABASE_CONNECTION_FAILED: 503,
    ErrorCode.DATABASE_QUERY_FAILED: 500,
    ErrorCode.TRANSACTION_FAILED: 500,
    ErrorCode.CACHE_ERROR: 500,
    ErrorCode.CACHE_CONNECTION_FAILED: 503,
    ErrorCode.EXTERNAL_SERVICE_ERROR: 502,
    ErrorCode.EXTERNAL_SERVICE_UNAVAILABLE: 503,
    ErrorCode.EXTERNAL_SERVICE_TIMEOUT: 504,
    ErrorCode.WORKFLOW_ERROR: 500,
    ErrorCode.WORKFLOW_NOT_FOUND: 404,
    ErrorCode.WORKFLOW_EXECUTION_FAILED: 500,
    ErrorCode.AGENT_ERROR: 500,
    ErrorCode.AGENT_NOT_FOUND: 404,
    ErrorCode.AGENT_EXECUTION_FAILED: 500,
    ErrorCode.AGENT_TIMEOUT: 504,
    ErrorCode.SKILL_ERROR: 500,
    ErrorCode.SKILL_NOT_FOUND: 404,
    ErrorCode.SKILL_EXECUTION_FAILED: 500,
    ErrorCode.SKILL_RESTRICTED: 403,
}


class PikarError(Exception):
    """Base exception for all Pikar AI errors.

    All custom exceptions should inherit from this class.

    Attributes:
        message: Human-readable error message.
        code: Machine-readable error code (ErrorCode enum).
        details: Additional context about the error.
        status_code: HTTP status code (derived from error code if not provided).
        original_exception: The original exception that was caught (if any).
    """

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        details: dict[str, Any] | None = None,
        status_code: int | None = None,
        original_exception: Exception | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}
        self.status_code = status_code or ERROR_CODE_TO_HTTP_STATUS.get(code, 500)
        self.original_exception = original_exception

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for JSON serialization."""
        result = {
            "error": {
                "code": self.code.value,
                "message": self.message,
            }
        }
        if self.details:
            result["error"]["details"] = self.details
        return result

    def __str__(self) -> str:
        return f"[{self.code.value}] {self.message}"


# Validation Errors
class ValidationError(PikarError):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        original_exception: Exception | None = None,
    ):
        super().__init__(
            message=message,
            code=ErrorCode.VALIDATION_ERROR,
            details=details,
            original_exception=original_exception,
        )


class InvalidInputError(ValidationError):
    """Raised when input is invalid."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        reason: str | None = None,
        original_exception: Exception | None = None,
    ):
        details = {}
        if field:
            details["field"] = field
        if reason:
            details["reason"] = reason

        super().__init__(
            message=message,
            details=details,
            original_exception=original_exception,
        )
        self.code = ErrorCode.INVALID_INPUT


class MissingFieldError(ValidationError):
    """Raised when a required field is missing."""

    def __init__(
        self,
        field: str,
        original_exception: Exception | None = None,
    ):
        super().__init__(
            message=f"Missing required field: {field}",
            details={"field": field},
            original_exception=original_exception,
        )
        self.code = ErrorCode.MISSING_REQUIRED_FIELD


# Database Errors
class DatabaseError(PikarError):
    """Raised when a database operation fails."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        original_exception: Exception | None = None,
    ):
        super().__init__(
            message=message,
            code=ErrorCode.DATABASE_ERROR,
            details=details,
            original_exception=original_exception,
        )


class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails."""

    def __init__(
        self,
        message: str = "Database connection failed",
        original_exception: Exception | None = None,
    ):
        super().__init__(
            message=message,
            original_exception=original_exception,
        )
        self.code = ErrorCode.DATABASE_CONNECTION_FAILED
        self.status_code = 503


class DatabaseQueryError(DatabaseError):
    """Raised when a database query fails."""

    def __init__(
        self,
        message: str,
        query: str | None = None,
        original_exception: Exception | None = None,
    ):
        details = {}
        if query:
            details["query"] = query[:200]  # Truncate long queries

        super().__init__(
            message=message,
            details=details,
            original_exception=original_exception,
        )
        self.code = ErrorCode.DATABASE_QUERY_FAILED


# Cache Errors
class CacheError(PikarError):
    """Raised when a cache operation fails."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        original_exception: Exception | None = None,
    ):
        super().__init__(
            message=message,
            code=ErrorCode.CACHE_ERROR,
            details=details,
            original_exception=original_exception,
        )


class CacheConnectionError(CacheError):
    """Raised when cache connection fails."""

    def __init__(
        self,
        message: str = "Cache connection failed",
        original_exception: Exception | None = None,
    ):
        super().__init__(
            message=message,
            original_exception=original_exception,
        )
        self.code = ErrorCode.CACHE_CONNECTION_FAILED
        self.status_code = 503


class CacheMissError(CacheError):
    """Raised when a cache key is not found (distinguished from errors)."""

    def __init__(
        self,
        key: str,
    ):
        super().__init__(
            message=f"Cache key not found: {key}",
            details={"cache_key": key},
        )
        self.code = ErrorCode.CACHE_KEY_NOT_FOUND
        self.status_code = 404


# Resource Errors
class NotFoundError(PikarError):
    """Raised when a requested resource is not found."""

    def __init__(
        self,
        resource: str,
        resource_id: str | None = None,
    ):
        message = f"{resource} not found"
        if resource_id:
            message += f": {resource_id}"

        details = {"resource": resource}
        if resource_id:
            details["resource_id"] = resource_id

        super().__init__(
            message=message,
            code=ErrorCode.NOT_FOUND,
            details=details,
        )


class ConflictError(PikarError):
    """Raised when a resource conflict occurs."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            code=ErrorCode.RESOURCE_CONFLICT,
            details=details,
        )


# Workflow Errors
class WorkflowError(PikarError):
    """Raised when a workflow operation fails."""

    def __init__(
        self,
        message: str,
        workflow_name: str | None = None,
        details: dict[str, Any] | None = None,
        original_exception: Exception | None = None,
    ):
        if workflow_name and "workflow" not in message.lower():
            message = f"Workflow '{workflow_name}': {message}"

        super().__init__(
            message=message,
            code=ErrorCode.WORKFLOW_ERROR,
            details=details,
            original_exception=original_exception,
        )


class WorkflowNotFoundError(WorkflowError):
    """Raised when a workflow is not found."""

    def __init__(self, workflow_name: str):
        super().__init__(
            message=f"Workflow not found: {workflow_name}",
            workflow_name=workflow_name,
        )
        self.code = ErrorCode.WORKFLOW_NOT_FOUND


# Agent Errors
class AgentError(PikarError):
    """Raised when an agent operation fails."""

    def __init__(
        self,
        message: str,
        agent_name: str | None = None,
        details: dict[str, Any] | None = None,
        original_exception: Exception | None = None,
    ):
        if agent_name and "agent" not in message.lower():
            message = f"Agent '{agent_name}': {message}"

        super().__init__(
            message=message,
            code=ErrorCode.AGENT_ERROR,
            details=details,
            original_exception=original_exception,
        )


class AgentNotFoundError(AgentError):
    """Raised when an agent is not found."""

    def __init__(self, agent_name: str):
        super().__init__(
            message=f"Agent not found: {agent_name}",
            agent_name=agent_name,
        )
        self.code = ErrorCode.AGENT_NOT_FOUND


# Skill Errors
class SkillError(PikarError):
    """Raised when a skill operation fails."""

    def __init__(
        self,
        message: str,
        skill_name: str | None = None,
        details: dict[str, Any] | None = None,
        original_exception: Exception | None = None,
    ):
        if skill_name and "skill" not in message.lower():
            message = f"Skill '{skill_name}': {message}"

        super().__init__(
            message=message,
            code=ErrorCode.SKILL_ERROR,
            details=details,
            original_exception=original_exception,
        )


class SkillNotFoundError(SkillError):
    """Raised when a skill is not found."""

    def __init__(self, skill_name: str):
        super().__init__(
            message=f"Skill not found: {skill_name}",
            skill_name=skill_name,
        )
        self.code = ErrorCode.SKILL_NOT_FOUND


class RestrictedSkillError(SkillError):
    """Raised when access to a restricted skill is denied."""

    def __init__(self, skill_name: str, reason: str | None = None):
        message = f"Access to restricted skill '{skill_name}' is denied"
        if reason:
            message += f": {reason}"

        details = {"skill_name": skill_name}
        if reason:
            details["reason"] = reason

        super().__init__(
            message=message,
            skill_name=skill_name,
            details=details,
        )
        self.code = ErrorCode.SKILL_RESTRICTED
        self.status_code = 403


# Authentication Errors
class AuthenticationError(PikarError):
    """Raised when authentication fails."""

    def __init__(
        self,
        message: str = "Authentication failed",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            code=ErrorCode.AUTHENTICATION_ERROR,
            details=details,
        )


class AuthorizationError(PikarError):
    """Raised when authorization fails."""

    def __init__(
        self,
        message: str = "Access denied",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            code=ErrorCode.AUTHORIZATION_ERROR,
            details=details,
        )


# Export commonly used classes
__all__ = [
    # Enums
    "ErrorCode",
    # Base Classes
    "PikarError",
    # Error Response Models
    "ErrorResponse",
    "ErrorDetail",
    "ErrorSource",
    "ValidationErrorResponse",
    # Specific Exceptions
    "ValidationError",
    "InvalidInputError",
    "MissingFieldError",
    "DatabaseError",
    "DatabaseConnectionError",
    "DatabaseQueryError",
    "CacheError",
    "CacheConnectionError",
    "CacheMissError",
    "NotFoundError",
    "ConflictError",
    "WorkflowError",
    "WorkflowNotFoundError",
    "AgentError",
    "AgentNotFoundError",
    "SkillError",
    "SkillNotFoundError",
    "RestrictedSkillError",
    "AuthenticationError",
    "AuthorizationError",
]
