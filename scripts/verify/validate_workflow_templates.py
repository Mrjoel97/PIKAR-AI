#!/usr/bin/env python3
"""Validate workflow template tool resolution from SQL seed files."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SEEDS = [
    ROOT / "supabase/migrations/0009_seed_workflows.sql",
    ROOT / "supabase/migrations/0038_seed_yaml_workflows.sql",
]
REGISTRY = ROOT / "app/agents/tools/registry.py"
DEPRECATED_TOOLS = {"sent_contract"}
CRITICAL_TOOL_IMPLS = {
    "approve_request",
    "send_contract",
    "query_timesheets",
    "execute_payroll",
    "process_payment",
    "send_payment",
    "transfer_money",
}


def parse_sql_templates(sql_text: str) -> list[tuple[str, list[dict]]]:
    marker = "INSERT INTO workflow_templates (name, description, category, phases)"
    i = sql_text.find(marker)
    if i < 0:
        return []
    j = sql_text.find("VALUES", i)
    if j < 0:
        return []
    s = sql_text[j + 6 :]

    out: list[tuple[str, list[dict]]] = []
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
        phases_raw, idx = read_str(idx)

        while idx < n and s[idx] != ")":
            idx += 1
        if idx < n:
            idx += 1

        phases = json.loads(phases_raw)
        out.append((name, phases))

    return out


def validate_templates() -> tuple[int, list[str]]:
    reg_text = REGISTRY.read_text(encoding="utf-8")
    registry_tools = {m.group(1) for m in re.finditer(r'"([a-zA-Z0-9_]+)"\s*:', reg_text)}
    registry_impls = {
        m.group(1): m.group(2)
        for m in re.finditer(r'"([a-zA-Z0-9_]+)"\s*:\s*([a-zA-Z0-9_]+)', reg_text)
    }

    errors: list[str] = []
    total = 0
    for seed in SEEDS:
        data = parse_sql_templates(seed.read_text(encoding="utf-8"))
        for name, phases in data:
            total += 1
            for p in phases:
                for st in p.get("steps", []):
                    step_name = st.get("name", "<unnamed>")
                    tool = st.get("tool") or st.get("action_type")
                    if not tool:
                        errors.append(f"{name}: step '{step_name}' missing tool")
                        continue
                    if tool in DEPRECATED_TOOLS:
                        errors.append(f"{name}: step '{step_name}' uses deprecated tool '{tool}'")
                    if tool not in registry_tools:
                        errors.append(f"{name}: step '{step_name}' unresolved tool '{tool}'")

    # Critical workflows must not rely on generic placeholders.
    for tool in sorted(CRITICAL_TOOL_IMPLS):
        impl = registry_impls.get(tool)
        if impl is None:
            errors.append(f"critical tool '{tool}' missing from registry")
        elif impl == "placeholder_tool":
            errors.append(f"critical tool '{tool}' mapped to placeholder_tool")

    return total, errors


def main() -> int:
    total, errors = validate_templates()
    if errors:
        print(f"[FAIL] workflow template validation failed ({len(errors)} errors)")
        for err in errors:
            print(" -", err)
        return 1

    print(f"[OK] validated {total} templates; all tools resolved and non-deprecated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
