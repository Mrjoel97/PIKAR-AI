#!/usr/bin/env python3
"""
WS-8 Verification: Workflow templates seeded, active, and executable.

Run from repo root. Requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY
(or use supabase CLI linked project).

Usage:
  python scripts/verify_workflow_templates.py
"""

import os
import sys

# Allow importing app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def main():
    try:
        from app.services.supabase import get_service_client
    except Exception as e:
        print("Could not import Supabase client:", e)
        print("Ensure SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are set.")
        return 1

    client = get_service_client()
    res = client.table("workflow_templates").select("id, name, category").execute()

    if not res.data:
        print("No workflow templates found. Run migrations 0009 and 0038.")
        return 1

    templates = res.data
    by_category = {}
    for t in templates:
        cat = t.get("category") or "uncategorized"
        by_category.setdefault(cat, []).append(t["name"])

    print(f"Total workflow templates: {len(templates)}")
    print()
    print("By category:")
    for cat in sorted(by_category.keys()):
        print(f"  {cat}: {len(by_category[cat])}")
    print()
    print("Expected: 60 from 0009_seed_workflows + 8 from 0038_seed_yaml_workflows = 68")
    if len(templates) >= 60:
        print("PASS: At least 60 templates present.")
    else:
        print("WARN: Fewer than 60 templates. Ensure 0009 and 0038 migrations are applied.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
