# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0

"""Environment variable validation for Pikar AI.

This module provides startup validation for required environment variables,
ensuring the application fails fast with clear error messages when
critical configuration is missing.

Usage:
    from app.config.validation import validate_environment, EnvironmentError

    # Call at application startup
    validate_environment()
"""

import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class Environment(Enum):
    """Application environment types."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


@dataclass
class EnvironmentVariable:
    """Definition of a required or optional environment variable."""

    name: str
    description: str
    required_in: set[Environment]
    sensitive: bool = False
    default: str | None = None
    validation_pattern: str | None = None  # Regex pattern for validation


@dataclass
class ValidationResult:
    """Result of environment validation."""

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    missing_required: list[str] = field(default_factory=list)
    missing_recommended: list[str] = field(default_factory=list)


class EnvironmentError(Exception):
    """Raised when required environment variables are missing or invalid."""

    pass


# Define all environment variables used by the application
ENVIRONMENT_VARIABLES: list[EnvironmentVariable] = [
    # =============================================================================
    # CRITICAL - Required in all environments
    # =============================================================================
    EnvironmentVariable(
        name="SUPABASE_URL",
        description="Supabase project URL (e.g., https://xxx.supabase.co)",
        required_in={
            Environment.DEVELOPMENT,
            Environment.STAGING,
            Environment.PRODUCTION,
        },
    ),
    EnvironmentVariable(
        name="SUPABASE_SERVICE_ROLE_KEY",
        description="Supabase service role key for backend operations",
        required_in={
            Environment.DEVELOPMENT,
            Environment.STAGING,
            Environment.PRODUCTION,
        },
        sensitive=True,
    ),
    EnvironmentVariable(
        name="SUPABASE_ANON_KEY",
        description="Supabase anonymous key for client-side operations",
        required_in={
            Environment.DEVELOPMENT,
            Environment.STAGING,
            Environment.PRODUCTION,
        },
        sensitive=True,
    ),
    # =============================================================================
    # SECURITY - Required in production
    # =============================================================================
    EnvironmentVariable(
        name="SUPABASE_JWT_SECRET",
        description="JWT secret for token verification (CRITICAL for production security)",
        required_in={Environment.PRODUCTION},
        sensitive=True,
    ),
    EnvironmentVariable(
        name="REQUIRE_STRICT_AUTH",
        description="Enable strict authentication mode (recommended: '1' in production)",
        required_in=set(),  # Optional but recommended
        default="0",
    ),
    # =============================================================================
    # GOOGLE AI - At least one configuration required
    # =============================================================================
    EnvironmentVariable(
        name="GOOGLE_APPLICATION_CREDENTIALS",
        description="Path to Google Cloud service account JSON key (for Vertex AI)",
        required_in=set(),
    ),
    EnvironmentVariable(
        name="GOOGLE_CLOUD_PROJECT",
        description="Google Cloud project ID (required with Vertex AI)",
        required_in=set(),
    ),
    EnvironmentVariable(
        name="GOOGLE_API_KEY",
        description="Gemini Developer API key",
        required_in=set(),
        sensitive=True,
    ),
    # =============================================================================
    # DATABASE - Optional with defaults
    # =============================================================================
    EnvironmentVariable(
        name="SUPABASE_DB_PASSWORD",
        description="Supabase database password for direct connections",
        required_in=set(),
        sensitive=True,
    ),
    EnvironmentVariable(
        name="SUPABASE_MAX_CONNECTIONS",
        description="Maximum database connections",
        required_in=set(),
        default="50",
    ),
    EnvironmentVariable(
        name="SUPABASE_TIMEOUT",
        description="Database query timeout in seconds",
        required_in=set(),
        default="60.0",
    ),
    # =============================================================================
    # REDIS - Optional with defaults
    # =============================================================================
    EnvironmentVariable(
        name="REDIS_HOST",
        description="Redis server hostname",
        required_in=set(),
        default="localhost",
    ),
    EnvironmentVariable(
        name="REDIS_PORT",
        description="Redis server port",
        required_in=set(),
        default="6379",
    ),
    EnvironmentVariable(
        name="REDIS_PASSWORD",
        description="Redis authentication password",
        required_in=set(),
        sensitive=True,
    ),
    # =============================================================================
    # APPLICATION - Optional with defaults
    # =============================================================================
    EnvironmentVariable(
        name="APP_URL",
        description="Public URL of the application",
        required_in={Environment.PRODUCTION},
    ),
    EnvironmentVariable(
        name="ALLOWED_ORIGINS",
        description="Comma-separated CORS allowed origins",
        required_in={Environment.PRODUCTION},
    ),
    EnvironmentVariable(
        name="ALLOW_ANONYMOUS_CHAT",
        description="Allow unauthenticated chat access (development only)",
        required_in=set(),
        default="0",
    ),
    EnvironmentVariable(
        name="LOGS_BUCKET_NAME",
        description="GCS bucket for ADK artifact storage (e.g., gs://pikar-ai-logs)",
        required_in={Environment.PRODUCTION},
    ),
    # =============================================================================
    # WORKFLOW CONFIGURATION
    # =============================================================================
    EnvironmentVariable(
        name="WORKFLOW_STRICT_TOOL_RESOLUTION",
        description="Fail on unresolved workflow tools",
        required_in={Environment.PRODUCTION},
    ),
    EnvironmentVariable(
        name="WORKFLOW_STRICT_CRITICAL_TOOL_GUARD",
        description="Reject execution when critical workflow tools are unresolved",
        required_in={Environment.PRODUCTION},
    ),
    EnvironmentVariable(
        name="WORKFLOW_ALLOW_FALLBACK_SIMULATION",
        description="Allow simulated edge fallback for workflow execution (must be false in production)",
        required_in={Environment.PRODUCTION},
    ),
    EnvironmentVariable(
        name="WORKFLOW_ENFORCE_READINESS_GATE",
        description="Enforce workflow readiness registry checks at workflow start time",
        required_in={Environment.PRODUCTION},
    ),
    EnvironmentVariable(
        name="BACKEND_API_URL",
        description="Backend API URL for internal calls",
        required_in={Environment.PRODUCTION},
        validation_pattern=r"^https?://.+",
    ),
    EnvironmentVariable(
        name="WORKFLOW_SERVICE_SECRET",
        description="Shared secret for service-to-service authentication between edge functions and backend",
        required_in={Environment.STAGING, Environment.PRODUCTION},
        sensitive=True,
    ),
    # =============================================================================
    # SCHEDULER - Required for scheduled tasks
    # =============================================================================
    EnvironmentVariable(
        name="SCHEDULER_SECRET",
        description="Secret for Cloud Scheduler authentication",
        required_in={Environment.PRODUCTION},
        sensitive=True,
    ),
    # =============================================================================
    # TOKEN BUDGET - Optional with default
    # =============================================================================
    EnvironmentVariable(
        name="SESSION_TOKEN_BUDGET",
        description="Maximum token budget per agent session (0 = unlimited)",
        required_in=set(),
        default="1000000",
    ),
    # =============================================================================
    # TELEMETRY - Optional with default
    # =============================================================================
    EnvironmentVariable(
        name="ENABLE_TELEMETRY",
        description="Enable agent/tool telemetry collection (structured logs + Supabase)",
        required_in=set(),
        default="1",
    ),
]


def detect_environment() -> Environment:
    """Detect the current environment from environment variables.

    Returns:
        Environment enum value.
    """
    env_str = os.environ.get(
        "ENVIRONMENT", os.environ.get("ENV", "development")
    ).lower()

    # Map common environment names
    env_mapping = {
        "dev": Environment.DEVELOPMENT,
        "development": Environment.DEVELOPMENT,
        "local": Environment.DEVELOPMENT,
        "staging": Environment.STAGING,
        "stage": Environment.STAGING,
        "prod": Environment.PRODUCTION,
        "production": Environment.PRODUCTION,
        "test": Environment.TEST,
        "testing": Environment.TEST,
    }

    return env_mapping.get(env_str, Environment.DEVELOPMENT)


def validate_environment(
    env: Environment | None = None,
    fail_fast: bool = True,
    log_warnings: bool = True,
) -> ValidationResult:
    """Validate that all required environment variables are set.

    Args:
        env: Environment to validate for. If None, auto-detects.
        fail_fast: If True, raise EnvironmentError on first missing required var.
        log_warnings: If True, log warnings for missing recommended vars.

    Returns:
        ValidationResult with details about missing/invalid variables.

    Raises:
        EnvironmentError: If fail_fast=True and required variables are missing.
    """
    if env is None:
        env = detect_environment()

    result = ValidationResult(valid=True)

    logger.info(f"Validating environment for: {env.value}")

    for var_def in ENVIRONMENT_VARIABLES:
        value = os.environ.get(var_def.name)

        # Check if required in this environment
        is_required = env in var_def.required_in

        if value is None or value == "":
            # Use default if available
            if var_def.default is not None:
                os.environ.setdefault(var_def.name, var_def.default)
                logger.debug(f"Using default value for {var_def.name}")
                continue

            if is_required:
                result.valid = False
                result.missing_required.append(var_def.name)
                result.errors.append(
                    f"Required environment variable '{var_def.name}' is not set. "
                    f"Description: {var_def.description}"
                )
            else:
                result.missing_recommended.append(var_def.name)
                result.warnings.append(
                    f"Optional environment variable '{var_def.name}' is not set. "
                    f"Description: {var_def.description}"
                )
        else:
            # Validate pattern if specified
            if var_def.validation_pattern:
                import re

                if not re.match(var_def.validation_pattern, value):
                    result.valid = False
                    result.errors.append(
                        f"Environment variable '{var_def.name}' has invalid format. "
                        f"Expected pattern: {var_def.validation_pattern}"
                    )

            # Log sensitive variable status (don't log the value)
            if var_def.sensitive:
                logger.debug(f"{var_def.name}: [REDACTED]")
            else:
                logger.debug(f"{var_def.name}: {value}")

    # Production hard requirements for real workflow execution.
    if env == Environment.PRODUCTION:
        required_boolean_values = {
            "WORKFLOW_STRICT_TOOL_RESOLUTION": "true",
            "WORKFLOW_STRICT_CRITICAL_TOOL_GUARD": "true",
            "WORKFLOW_ALLOW_FALLBACK_SIMULATION": "false",
            "WORKFLOW_ENFORCE_READINESS_GATE": "true",
        }
        for var_name, expected in required_boolean_values.items():
            current = (os.environ.get(var_name) or "").strip().lower()
            if current != expected:
                result.valid = False
                result.errors.append(
                    f"In production, environment variable '{var_name}' must be '{expected}'. "
                    f"Found '{os.environ.get(var_name)}'."
                )

        backend_api_url = (os.environ.get("BACKEND_API_URL") or "").strip()
        if backend_api_url:
            parsed = urlparse(backend_api_url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                result.valid = False
                result.errors.append(
                    "In production, 'BACKEND_API_URL' must be a valid absolute HTTP(S) URL."
                )

        workflow_service_secret = (
            os.environ.get("WORKFLOW_SERVICE_SECRET") or ""
        ).strip()
        if not workflow_service_secret or len(workflow_service_secret) < 32:
            result.valid = False
            result.errors.append(
                "WORKFLOW_SERVICE_SECRET must be set in production and be at least 32 characters long for security"
            )

    # Log warnings
    if log_warnings:
        for warning in result.warnings:
            logger.warning(warning)

    # Fail fast if requested
    if fail_fast and not result.valid:
        error_message = (
            f"Environment validation failed!\n"
            f"Missing required variables: {', '.join(result.missing_required)}\n"
            f"Errors:\n" + "\n".join(f"  - {e}" for e in result.errors)
        )
        logger.error(error_message)
        raise EnvironmentError(error_message)

    return result


def validate_jwt_secret() -> bool:
    """Validate that JWT secret is configured for production security.

    This is a critical security check that should be called at startup
    in production environments.

    Returns:
        True if JWT secret is properly configured.

    Raises:
        EnvironmentError: In production without JWT secret.
    """
    env = detect_environment()
    jwt_secret = os.environ.get("SUPABASE_JWT_SECRET")

    if env == Environment.PRODUCTION:
        if not jwt_secret:
            error_msg = (
                "CRITICAL SECURITY ERROR: SUPABASE_JWT_SECRET is not set!\n"
                "JWT token verification is disabled, which allows potential "
                "authentication bypass.\n"
                "Set SUPABASE_JWT_SECRET in your environment before deploying "
                "to production."
            )
            logger.critical(error_msg)
            raise EnvironmentError(error_msg)

        # Validate JWT secret format (should be a valid secret)
        if len(jwt_secret) < 32:
            logger.warning(
                "SUPABASE_JWT_SECRET appears to be too short. "
                "Consider using a secret with at least 32 characters."
            )

        logger.info("JWT secret validation passed")
        return True
    else:
        if not jwt_secret:
            logger.warning(
                f"SUPABASE_JWT_SECRET is not set in {env.value} environment. "
                "JWT verification will be skipped. This is acceptable for "
                "development but MUST be set in production."
            )
        return True


def validate_google_ai_config() -> bool:
    """Validate that at least one Google AI configuration is present.

    Returns:
        True if Google AI is properly configured.

    Raises:
        EnvironmentError: If no Google AI configuration is found.
    """
    has_vertex = bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))
    has_project = bool(os.environ.get("GOOGLE_CLOUD_PROJECT"))
    has_api_key = bool(os.environ.get("GOOGLE_API_KEY"))

    if has_vertex and has_project:
        logger.info("Google AI configured via Vertex AI")
        return True
    if has_api_key:
        logger.info("Google AI configured via Gemini Developer API")
        return True

    error_msg = (
        "No Google AI credentials found!\n"
        "Configure GOOGLE_APPLICATION_CREDENTIALS + GOOGLE_CLOUD_PROJECT or GOOGLE_API_KEY."
    )
    logger.error(error_msg)
    raise EnvironmentError(error_msg)


def get_validation_report() -> str:
    """Generate a human-readable validation report.

    Returns:
        Formatted report of environment configuration status.
    """
    env = detect_environment()
    lines = [
        "Environment Configuration Report",
        "=" * 40,
        f"Detected Environment: {env.value}",
        "",
    ]

    # Group variables by category
    categories = {
        "Critical (Required)": [],
        "Security": [],
        "Google AI": [],
        "Database": [],
        "Redis": [],
        "Application": [],
        "Workflow": [],
        "Other": [],
    }

    for var_def in ENVIRONMENT_VARIABLES:
        value = os.environ.get(var_def.name)
        is_set = value is not None and value != ""
        is_required = env in var_def.required_in

        status = "✓" if is_set else ("✗" if is_required else "○")
        value_display = (
            "[REDACTED]" if (var_def.sensitive and is_set) else (value or "not set")
        )

        # Categorize
        if (
            var_def.name.startswith("SUPABASE_JWT")
            or var_def.name == "REQUIRE_STRICT_AUTH"
        ):
            category = "Security"
        elif var_def.name.startswith("SUPABASE"):
            category = "Database"
        elif var_def.name.startswith("REDIS"):
            category = "Redis"
        elif var_def.name.startswith("GOOGLE"):
            category = "Google AI"
        elif var_def.name.startswith("WORKFLOW_") or var_def.name == "BACKEND_API_URL":
            category = "Workflow"
        elif var_def.name in ("APP_URL", "ALLOWED_ORIGINS", "ALLOW_ANONYMOUS_CHAT"):
            category = "Application"
        elif is_required:
            category = "Critical (Required)"
        else:
            category = "Other"

        categories[category].append(f"  {status} {var_def.name}: {value_display}")

    for category, items in categories.items():
        if items:
            lines.append(f"\n{category}:")
            lines.extend(items)

    return "\n".join(lines)


# Convenience function for startup
def validate_startup() -> None:
    """Perform all startup validations.

    This should be called at application startup to ensure all
    required configuration is present.

    Raises:
        EnvironmentError: If any critical validation fails.
    """
    logger.info("Performing startup environment validation...")

    # Detect and log environment
    env = detect_environment()
    logger.info(f"Running in {env.value} environment")

    # Validate required environment variables
    validate_environment(env=env, fail_fast=True)

    # Validate JWT secret (critical for production)
    validate_jwt_secret()

    # Validate Google AI configuration
    validate_google_ai_config()

    logger.info("Startup validation completed successfully")
