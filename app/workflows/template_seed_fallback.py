"""Fallback workflow template metadata loaded from local seed SQL files and YAML definitions."""

from __future__ import annotations

import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception:  # pragma: no cover - fallback remains available without PyYAML
    yaml = None


_PERSONA_FALLBACKS: dict[str, list[str]] = {
    "initiative framework": ["all"],
    "idea-to-venture": ["solopreneur", "startup"],
    "landing page to launch": ["solopreneur", "startup"],
    "lead generation workflow": ["solopreneur", "startup", "sme"],
    "content creation workflow": ["solopreneur", "startup", "sme"],
    "social media campaign workflow": ["solopreneur", "startup", "sme"],
    "email sequence workflow": ["solopreneur", "startup", "sme"],
    "a/b testing workflow": ["startup", "sme"],
    "product launch workflow": ["startup", "sme"],
    "competitor analysis workflow": ["startup", "sme"],
}


@lru_cache(maxsize=1)
def seed_template_metadata() -> list[dict[str, Any]]:
    """Load template metadata from local SQL seeds and YAML definitions."""
    root = Path(__file__).resolve().parents[2]
    seeds = [
        root / "supabase/migrations/0009_seed_workflows.sql",
        root / "supabase/migrations/0038_seed_yaml_workflows.sql",
    ]
    definitions_dir = root / "app/workflows/definitions"
    rows: dict[str, dict[str, Any]] = {}

    def parse_sql(sql_text: str) -> list[dict[str, Any]]:
        marker = "INSERT INTO workflow_templates (name, description, category, phases)"
        i = sql_text.find(marker)
        if i < 0:
            return []
        j = sql_text.find("VALUES", i)
        if j < 0:
            return []
        s = sql_text[j + 6 :]
        idx = 0
        n = len(s)
        out: list[dict[str, Any]] = []

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
            description, idx = read_str(idx)

            idx = skip_ws(idx)
            if idx < n and s[idx] == ",":
                idx += 1
            idx = skip_ws(idx)
            category, idx = read_str(idx)

            idx = skip_ws(idx)
            if idx < n and s[idx] == ",":
                idx += 1
            idx = skip_ws(idx)
            _, idx = read_str(idx)

            while idx < n and s[idx] != ")":
                idx += 1
            if idx < n:
                idx += 1

            out.append({"name": name, "description": description, "category": category})
        return out

    for seed in seeds:
        if not seed.exists():
            continue
        for row in parse_sql(seed.read_text(encoding="utf-8")):
            rows[row["name"].strip().lower()] = row

    if yaml is not None and definitions_dir.exists():
        for definition in definitions_dir.glob("*.yaml"):
            try:
                parsed = yaml.safe_load(definition.read_text(encoding="utf-8")) or {}
            except Exception:
                continue
            name = str(parsed.get("name") or "").strip()
            if not name:
                continue
            personas_allowed = parsed.get("personas_allowed")
            rows[name.lower()] = {
                "name": name,
                "description": str(parsed.get("description") or ""),
                "category": str(parsed.get("category") or "operations"),
                "personas_allowed": personas_allowed,
            }

    output: list[dict[str, Any]] = []
    for row in rows.values():
        name = row["name"]
        personas_allowed = row.get("personas_allowed")
        if not personas_allowed:
            personas_allowed = _PERSONA_FALLBACKS.get(name.strip().lower())
        output.append(
            {
                "id": f"seed-{uuid.uuid5(uuid.NAMESPACE_DNS, name)}",
                "name": name,
                "description": row.get("description", ""),
                "category": row.get("category", "operations"),
                "template_key": None,
                "version": None,
                "lifecycle_status": None,
                "is_generated": None,
                "personas_allowed": personas_allowed,
                "published_at": None,
            }
        )
    return sorted(output, key=lambda x: x["name"].lower())
