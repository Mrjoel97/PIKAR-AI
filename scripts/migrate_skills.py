#!/usr/bin/env python3
"""Migrate Python-defined skills into the Supabase skills table.

This script extracts Skill(...) definitions from the Python source file,
normalizes them to the canonical Supabase schema, and upserts them by name.
"""

import argparse
import ast
import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from supabase import Client, create_client

    HAS_SUPABASE = True
except ImportError:
    HAS_SUPABASE = False


class SkillParser(ast.NodeVisitor):
    """Parse Skill(...) calls from a Python module."""

    def __init__(self) -> None:
        self.skills: list[dict[str, Any]] = []

    def visit_Call(self, node: ast.Call) -> None:
        if not isinstance(node.func, ast.Name) or node.func.id != "Skill":
            self.generic_visit(node)
            return

        parsed: dict[str, Any] = {
            "name": "",
            "description": "",
            "knowledge": "",
            "category": "general",
            "agent_ids": [],
            "metadata": {},
            "author": "",
            "version": "1.0.0",
            "source": "builtin",
            "is_restricted": False,
        }

        for kw in node.keywords:
            if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                parsed["name"] = kw.value.value
            elif kw.arg == "description" and isinstance(kw.value, ast.Constant):
                parsed["description"] = kw.value.value
            elif kw.arg == "category" and isinstance(kw.value, ast.Constant):
                parsed["category"] = kw.value.value
            elif kw.arg == "agent_ids" and isinstance(kw.value, ast.List):
                parsed["agent_ids"] = [
                    elt.attr
                    for elt in kw.value.elts
                    if isinstance(elt, ast.Attribute)
                ]
            elif kw.arg == "knowledge":
                if isinstance(kw.value, ast.Constant):
                    parsed["knowledge"] = kw.value.value
                elif isinstance(kw.value, ast.JoinedStr):
                    parsed["knowledge"] = "[complex template]"
            elif kw.arg == "metadata" and isinstance(kw.value, ast.Dict):
                metadata: dict[str, Any] = {}
                for key, value in zip(kw.value.keys, kw.value.values):
                    if isinstance(key, ast.Constant) and isinstance(value, ast.Constant):
                        metadata[key.value] = value.value
                parsed["metadata"] = metadata

        if parsed["name"]:
            self.skills.append(parsed)

        self.generic_visit(node)


def parse_skills_file(file_path: str) -> list[dict[str, Any]]:
    source = Path(file_path).read_text(encoding="utf-8")
    tree = ast.parse(source)
    parser = SkillParser()
    parser.visit(tree)
    return parser.skills


def categorize_skill(name: str, description: str) -> str:
    name_lower = name.lower()
    desc_lower = description.lower()

    buckets = {
        "finance": ["finance", "financial", "budget", "revenue", "pricing", "invoice", "payment", "tax"],
        "hr": ["hr", "recruit", "hiring", "employee", "candidate", "interview", "staff"],
        "marketing": ["marketing", "seo", "social", "campaign", "brand", "email", "conversion"],
        "sales": ["sales", "crm", "lead", "deal", "pipeline", "prospect"],
        "compliance": ["legal", "compliance", "security", "privacy", "audit", "risk", "policy"],
        "data": ["data", "analytics", "metric", "dashboard", "sql", "database", "analysis"],
        "operations": ["operation", "workflow", "process", "automation", "integration", "deployment"],
        "support": ["support", "ticket", "faq", "customer service"],
        "planning": ["planning", "strategy", "roadmap", "initiative", "goal", "objective", "kpi"],
    }

    for category, keywords in buckets.items():
        if any(keyword in name_lower or keyword in desc_lower for keyword in keywords):
            return category
    return "content"


def transform_skill(skill: dict[str, Any]) -> dict[str, Any]:
    category = skill.get("category") or "general"
    if category == "general":
        category = categorize_skill(skill.get("name", ""), skill.get("description", ""))

    agent_ids = [str(agent).upper() for agent in skill.get("agent_ids", []) if str(agent).strip()]
    metadata = dict(skill.get("metadata") or {})
    metadata.update(
        {
            "author": skill.get("author") or "",
            "version": skill.get("version") or "1.0.0",
            "source": skill.get("source") or "builtin",
            "is_restricted": bool(skill.get("is_restricted", False)),
        }
    )

    content = skill.get("knowledge") or ""
    if len(content) > 500_000:
        content = content[:500_000] + "\n\n[Content truncated]"

    return {
        "name": skill.get("name", ""),
        "description": skill.get("description", ""),
        "category": category,
        "content": content,
        "metadata": metadata,
        "agent_ids": agent_ids,
    }


async def migrate_skills(
    skills: list[dict[str, Any]],
    supabase_url: str,
    supabase_key: str,
    dry_run: bool = False,
    batch_size: int = 50,
) -> dict[str, Any]:
    if not HAS_SUPABASE:
        return {"error": "Supabase client not available"}

    client: Client = create_client(supabase_url, supabase_key)
    transformed_skills = [transform_skill(skill) for skill in skills]

    if dry_run:
        return {
            "dry_run": True,
            "total_skills": len(transformed_skills),
            "sample_skills": transformed_skills[:3],
        }

    results = {"upserted": 0, "errors": [], "batch_count": 0}
    for start in range(0, len(transformed_skills), batch_size):
        batch = transformed_skills[start : start + batch_size]
        try:
            response = client.table("skills").upsert(batch, on_conflict="name").execute()
            results["upserted"] += len(response.data or [])
            results["batch_count"] += 1
        except Exception as exc:
            results["errors"].append({"batch_start": start, "error": str(exc)})

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate skills to the database")
    parser.add_argument(
        "--file",
        default="app/skills/custom/auto_mapped_skills.py",
        help="Path to the source Python file containing Skill(...) definitions",
    )
    parser.add_argument("--dry-run", action="store_true", help="Parse and show skills without inserting")
    parser.add_argument("--batch-size", type=int, default=50, help="Number of skills per upsert batch")
    parser.add_argument("--output-json", help="Optional path to export parsed skills as JSON")
    args = parser.parse_args()

    print(f"Parsing skills from {args.file}...")
    skills = parse_skills_file(args.file)
    print(f"Found {len(skills)} skills")

    if args.output_json:
        Path(args.output_json).write_text(json.dumps(skills, indent=2), encoding="utf-8")
        print(f"Skills exported to {args.output_json}")

    transformed = [transform_skill(skill) for skill in skills]
    categories: dict[str, int] = {}
    for skill in transformed:
        category = skill.get("category", "unknown")
        categories[category] = categories.get(category, 0) + 1

    print("\nCategory distribution:")
    for category, count in sorted(categories.items()):
        print(f"  {category}: {count}")

    if args.dry_run:
        return

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not supabase_url or not supabase_key:
        print("\nSUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY not set. Skipping migration.")
        return

    import asyncio

    results = asyncio.run(
        migrate_skills(
            transformed,
            supabase_url,
            supabase_key,
            batch_size=args.batch_size,
        )
    )
    print(f"\nMigration results: {json.dumps(results, indent=2)}")


if __name__ == "__main__":
    main()
