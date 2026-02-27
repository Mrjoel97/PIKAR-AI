#!/usr/bin/env python3
"""Generate workflow implementation baseline report.

Outputs a markdown report to docs/plans/workflow_baseline.md with:
- template count and category distribution,
- validator status,
- placeholder tool coverage snapshot,
- critical tool implementation status.
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from scripts.verify.validate_workflow_templates import (
    CRITICAL_TOOL_IMPLS,
    REGISTRY,
    SEEDS,
    parse_sql_templates,
    validate_templates,
)


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/plans/workflow_baseline.md"


def _collect_templates() -> list[tuple[str, str, list[dict]]]:
    """Return (name, category, phases) tuples for all seeded templates."""
    rows: list[tuple[str, str, list[dict]]] = []
    for seed in SEEDS:
        text = seed.read_text(encoding="utf-8")
        marker = "INSERT INTO workflow_templates (name, description, category, phases)"
        i = text.find(marker)
        if i < 0:
            continue
        j = text.find("VALUES", i)
        if j < 0:
            continue
        s = text[j + 6 :]

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
            category, idx = read_str(idx)

            idx = skip_ws(idx)
            if idx < n and s[idx] == ",":
                idx += 1
            idx = skip_ws(idx)
            phases_raw, idx = read_str(idx)

            while idx < n and s[idx] != ")":
                idx += 1
            if idx < n:
                idx += 1

            phases = __import__("json").loads(phases_raw)
            rows.append((name, category, phases))
    return rows


def _registry_impls() -> dict[str, str]:
    text = REGISTRY.read_text(encoding="utf-8")
    return {
        m.group(1): m.group(2)
        for m in re.finditer(r'"([a-zA-Z0-9_]+)"\s*:\s*([a-zA-Z0-9_]+)', text)
    }


def generate() -> str:
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    total, errors = validate_templates()
    templates = _collect_templates()

    by_category = Counter(cat for _, cat, _ in templates)
    total_phases = sum(len(phases) for _, _, phases in templates)
    total_steps = sum(len(phase.get("steps", [])) for _, _, phases in templates for phase in phases)

    impls = _registry_impls()
    placeholder_mapped = sorted([k for k, v in impls.items() if v == "placeholder_tool"])
    critical_status = {tool: impls.get(tool, "<missing>") for tool in sorted(CRITICAL_TOOL_IMPLS)}

    lines: list[str] = []
    lines.append("# Workflow Baseline Report")
    lines.append("")
    lines.append(f"- Generated at: `{now}`")
    lines.append(f"- Seeds scanned: `{', '.join(str(s.relative_to(ROOT)) for s in SEEDS)}`")
    lines.append("")
    lines.append("## Coverage Snapshot")
    lines.append("")
    lines.append(f"- Templates discovered: `{total}`")
    lines.append(f"- Total phases: `{total_phases}`")
    lines.append(f"- Total steps: `{total_steps}`")
    lines.append(f"- Validator errors: `{len(errors)}`")
    lines.append("")
    lines.append("## Category Distribution")
    lines.append("")
    for cat, count in sorted(by_category.items(), key=lambda x: (x[0].lower(), x[1])):
        lines.append(f"- `{cat}`: `{count}`")
    lines.append("")
    lines.append("## Critical Tool Implementation Status")
    lines.append("")
    for tool, impl in critical_status.items():
        icon = "✅" if impl != "placeholder_tool" and impl != "<missing>" else "❌"
        lines.append(f"- {icon} `{tool}` -> `{impl}`")
    lines.append("")
    lines.append("## Placeholder Mapping Snapshot")
    lines.append("")
    lines.append(f"- Registry entries mapped to `placeholder_tool`: `{len(placeholder_mapped)}`")
    if placeholder_mapped:
        lines.append("- Placeholder tool keys:")
        for name in placeholder_mapped:
            lines.append(f"  - `{name}`")
    lines.append("")
    lines.append("## Validator Errors")
    lines.append("")
    if errors:
        for err in errors:
            lines.append(f"- ❌ {err}")
    else:
        lines.append("- ✅ No validation errors.")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- This baseline is intended for Phase 0 tracking and weekly progress checks.")
    lines.append("- Re-generate with: `uv run python scripts/verify/generate_workflow_baseline.py`")
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    report = generate()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(report, encoding="utf-8")
    print(f"[OK] wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

