#!/usr/bin/env python3
"""Validate user journey workflow-template references in SQL migrations."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_SEEDS = [
    ROOT / "supabase/migrations/0009_seed_workflows.sql",
    ROOT / "supabase/migrations/0038_seed_yaml_workflows.sql",
]
JOURNEY_MIGRATIONS = [
    ROOT / "supabase/migrations/0041_enrich_solopreneur_journeys.sql",
    ROOT / "supabase/migrations/0042_enrich_startup_journeys.sql",
    ROOT / "supabase/migrations/0043_enrich_sme_journeys.sql",
    ROOT / "supabase/migrations/0044_enrich_enterprise_journeys.sql",
]
EXPECTED_JOURNEY_COUNT = 160


def parse_sql_templates(sql_text: str) -> set[str]:
    marker = "INSERT INTO workflow_templates (name, description, category, phases)"
    i = sql_text.find(marker)
    if i < 0:
        return set()
    j = sql_text.find("VALUES", i)
    if j < 0:
        return set()
    s = sql_text[j + 6 :]

    out: set[str] = set()
    idx = 0
    n = len(s)

    def skip_ws(k: int) -> int:
        while k < n and s[k].isspace():
            k += 1
        return k

    def read_str(k: int) -> tuple[str, int]:
        if s[k] != "'":
            raise ValueError("expected SQL string")
        k += 1
        buf: list[str] = []
        while k < n:
            ch = s[k]
            if ch == "'":
                if k + 1 < n and s[k + 1] == "'":
                    buf.append("'")
                    k += 2
                    continue
                return "".join(buf), k + 1
            buf.append(ch)
            k += 1
        raise ValueError("unterminated SQL string")

    while idx < n:
        idx = skip_ws(idx)
        if idx >= n or s[idx] == ";":
            break
        if s[idx] != "(":
            idx += 1
            continue

        probe = skip_ws(idx + 1)
        if probe >= n or s[probe] != "'":
            idx += 1
            continue

        idx = probe
        name, idx = read_str(idx)
        out.add(name)

        idx = skip_ws(idx)
        if idx < n and s[idx] == ",":
            idx += 1
        idx = skip_ws(idx)
        _, idx = read_str(idx)  # description

        idx = skip_ws(idx)
        if idx < n and s[idx] == ",":
            idx += 1
        idx = skip_ws(idx)
        _, idx = read_str(idx)  # category

        idx = skip_ws(idx)
        if idx < n and s[idx] == ",":
            idx += 1
        idx = skip_ws(idx)
        _, idx = read_str(idx)  # phases JSON

        while idx < n and s[idx] != ")":
            idx += 1
        if idx < n:
            idx += 1

    return out


def validate_journey_references() -> tuple[int, int, int, list[str]]:
    workflow_names: set[str] = set()
    for seed in WORKFLOW_SEEDS:
        workflow_names.update(parse_sql_templates(seed.read_text(encoding="utf-8")))

    primary_pattern = re.compile(
        r"primary_workflow_template_name\s*=\s*'((?:''|[^'])*)'",
        re.IGNORECASE,
    )
    suggested_pattern = re.compile(
        r"suggested_workflows\s*=\s*'([^']*)'::jsonb",
        re.IGNORECASE,
    )

    errors: list[str] = []
    primary_count = 0
    suggested_count = 0

    for migration in JOURNEY_MIGRATIONS:
        lines = migration.read_text(encoding="utf-8").splitlines()
        for line_no, line in enumerate(lines, start=1):
            primary_match = primary_pattern.search(line)
            if primary_match:
                primary_count += 1
                primary_name = primary_match.group(1).replace("''", "'")
                if primary_name not in workflow_names:
                    errors.append(
                        f"{migration.name}:{line_no} invalid primary_workflow_template_name '{primary_name}'"
                    )

            suggested_match = suggested_pattern.search(line)
            if not suggested_match:
                continue
            try:
                suggested = json.loads(suggested_match.group(1))
            except json.JSONDecodeError:
                errors.append(
                    f"{migration.name}:{line_no} invalid suggested_workflows JSON payload"
                )
                continue

            if not isinstance(suggested, list):
                errors.append(
                    f"{migration.name}:{line_no} suggested_workflows must be a JSON array"
                )
                continue

            for workflow_name in suggested:
                suggested_count += 1
                if not isinstance(workflow_name, str):
                    errors.append(
                        f"{migration.name}:{line_no} suggested_workflows contains non-string value"
                    )
                    continue
                if workflow_name not in workflow_names:
                    errors.append(
                        f"{migration.name}:{line_no} invalid suggested_workflow '{workflow_name}'"
                    )

    if primary_count != EXPECTED_JOURNEY_COUNT:
        errors.append(
            f"expected {EXPECTED_JOURNEY_COUNT} primary journey references, found {primary_count}"
        )

    return len(workflow_names), primary_count, suggested_count, errors


def main() -> int:
    workflow_count, primary_count, suggested_count, errors = validate_journey_references()
    if errors:
        print(
            "[FAIL] journey-workflow reference validation failed "
            f"({len(errors)} errors)"
        )
        for err in errors:
            print(" -", err)
        return 1

    print(
        "[OK] validated journey references: "
        f"{primary_count} primary + {suggested_count} suggested "
        f"against {workflow_count} workflow templates"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
