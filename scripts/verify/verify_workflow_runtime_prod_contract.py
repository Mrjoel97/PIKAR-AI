"""Verify production workflow runtime contract from repo configuration."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _check_file_contains(path: Path, required_snippets: list[str]) -> list[str]:
    missing: list[str] = []
    content = path.read_text(encoding="utf-8")
    for snippet in required_snippets:
        if snippet not in content:
            missing.append(snippet)
    return missing


def main() -> int:
    checks: list[tuple[Path, list[str]]] = [
        (
            ROOT / "deployment/terraform/service.tf",
            [
                'name  = "WORKFLOW_STRICT_TOOL_RESOLUTION"',
                'value = "true"',
                'name  = "WORKFLOW_ALLOW_FALLBACK_SIMULATION"',
                'value = "false"',
                'name  = "WORKFLOW_ENFORCE_READINESS_GATE"',
                'name  = "BACKEND_API_URL"',
                'name = "WORKFLOW_SERVICE_SECRET"',
            ],
        ),
        (
            ROOT / "app/config/validation.py",
            [
                '"WORKFLOW_STRICT_TOOL_RESOLUTION": "true"',
                '"WORKFLOW_ALLOW_FALLBACK_SIMULATION": "false"',
                '"WORKFLOW_ENFORCE_READINESS_GATE": "true"',
                "'BACKEND_API_URL' must be a valid absolute HTTP(S) URL",
                "WORKFLOW_SERVICE_SECRET must be set in production and be at least 32 characters long",
            ],
        ),
    ]

    failed = False
    for file_path, snippets in checks:
        if not file_path.exists():
            failed = True
            print(f"[FAIL] Missing file: {file_path}")
            continue
        missing = _check_file_contains(file_path, snippets)
        if missing:
            failed = True
            print(f"[FAIL] {file_path}")
            for snippet in missing:
                print(f"  - missing snippet: {snippet}")
        else:
            print(f"[PASS] {file_path}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
