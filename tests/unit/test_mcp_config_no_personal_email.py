# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Guardrail test: ensure no personal email is hardcoded in app/mcp/config.py.

The default for RESEND_FORWARD_TO must come from the environment, not be
baked into the source. This prevents config leaks if the env var is unset.
"""

from pathlib import Path


def test_mcp_config_has_no_hardcoded_personal_email() -> None:
    """The MCP config source must not contain the literal personal email."""
    config_path = (
        Path(__file__).resolve().parents[2] / "app" / "mcp" / "config.py"
    )
    assert config_path.exists(), f"Expected config file at {config_path}"

    source = config_path.read_text(encoding="utf-8")
    assert "joel.feruzi@gmail.com" not in source, (
        "app/mcp/config.py must not hardcode a personal email address; "
        "RESEND_FORWARD_TO should default to an empty string and be sourced "
        "from the environment."
    )
