#!/usr/bin/env python3
"""Migration script to extract skills from auto_mapped_skills.py and load into database.

This script parses the auto_mapped_skills.py file, extracts skill definitions,
and inserts them into the Supabase database using the new skills table schema.

Usage:
    python scripts/migrate_skills.py [--dry-run] [--batch-size N]
"""

import argparse
import ast
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Supabase client
try:
    from supabase import create_client, Client
    HAS_SUPABASE = True
except ImportError:
    HAS_SUPABASE = False


class SkillParser(ast.NodeVisitor):
    """Parse auto_mapped_skills.py to extract skill definitions."""
    
    def __init__(self):
        self.skills: list[dict[str, Any]] = []
        self.current_skill: Optional[dict[str, Any]] = None
        self.in_skill_call = False
        self.current_key: Optional[str] = None
        self.current_value: Any = None
        self.value_buffer: list[str] = []
        self.in_knowledge = False
    
    def visit_Call(self, node: ast.Call):
        # Check if this is a Skill(...) call
        if isinstance(node.func, ast.Name) and node.func.id == "Skill":
            self.in_skill_call = True
            self.current_skill = {
                "name": "",
                "description": "",
                "knowledge": "",
                "category": "general",
                "agent_ids": [],
                "metadata": {},
                "author": "",
                "version": "1.0",
                "source": "builtin",
                "is_restricted": False,
            }
            
            # Process keyword arguments
            for kw in node.keywords:
                if kw.arg == "name":
                    if isinstance(kw.value, ast.Constant):
                        self.current_skill["name"] = kw.value.value
                elif kw.arg == "description":
                    if isinstance(kw.value, ast.Constant):
                        self.current_skill["description"] = kw.value.value
                elif kw.arg == "category":
                    if isinstance(kw.value, ast.Constant):
                        self.current_skill["category"] = kw.value.value
                elif kw.arg == "agent_ids":
                    if isinstance(kw.value, ast.List):
                        self.current_skill["agent_ids"] = [
                            elt.value for elt in kw.value.elts 
                            if isinstance(elt, ast.Attribute)
                        ]
                elif kw.arg == "knowledge":
                    # Knowledge is a long string, extract from Constant or Join
                    if isinstance(kw.value, ast.Constant):
                        self.current_skill["knowledge"] = kw.value.value
                    elif isinstance(kw.value, ast.JoinedStr):
                        # Handle f-strings (simplified - just get the basics)
                        self.current_skill["knowledge"] = "[complex template]"
                elif kw.arg == "metadata":
                    if isinstance(kw.value, ast.Dict):
                        metadata = {}
                        for key, val in zip(kw.value.keys, kw.value.values):
                            if isinstance(key, ast.Constant) and isinstance(val, ast.Constant):
                                metadata[key.value] = val.value
                        self.current_skill["metadata"] = metadata
            
            self.generic_visit(node)
            
            # Save the skill if we have a name
            if self.current_skill and self.current_skill.get("name"):
                self.skills.append(self.current_skill)
            
            self.in_skill_call = False
            self.current_skill = None


def parse_skills_file(file_path: str) -> list[dict[str, Any]]:
    """Parse the auto_mapped_skills.py file and extract skill definitions."""
    
    with open(file_path, 'r', encoding='utf-8') as f:
        source = f.read()
    
    tree = ast.parse(source)
    parser = SkillParser()
    parser.visit(tree)
    
    return parser.skills


def categorize_skill(name: str, description: str) -> str:
    """Determine the category based on skill name and description."""
    
    name_lower = name.lower()
    desc_lower = description.lower()
    
    # Finance-related
    if any(kw in name_lower or kw in desc_lower for kw in [
        'finance', 'financial', 'budget', 'cost', 'revenue', 'pricing', 
        'invoice', 'payment', 'accounting', 'tax', 'roi', 'investment'
    ]):
        return 'finance'
    
    # HR-related
    if any(kw in name_lower or kw in desc_lower for kw in [
        'hr', 'recruit', 'hiring', 'employee', 'onboarding', 'performance',
        'candidate', 'job', 'resume', 'interview', 'staff'
    ]):
        return 'hr'
    
    # Marketing-related
    if any(kw in name_lower or kw in desc_lower for kw in [
        'marketing', 'seo', 'content', 'social', 'campaign', 'brand', 
        'advertising', 'copywriting', 'email', 'conversion'
    ]):
        return 'marketing'
    
    # Sales-related
    if any(kw in name_lower or kw in desc_lower for kw in [
        'sales', 'crm', 'lead', 'customer', 'deal', 'pipeline', 'prospect'
    ]):
        return 'sales'
    
    # Compliance/Legal
    if any(kw in name_lower or kw in desc_lower for kw in [
        'legal', 'compliance', 'security', 'privacy', 'gdpr', 'audit',
        'risk', 'policy', 'regulation', 'contract'
    ]):
        return 'compliance'
    
    # Data/Analytics
    if any(kw in name_lower or kw in desc_lower for kw in [
        'data', 'analytics', 'metric', 'dashboard', 'visualization', 'chart',
        'sql', 'query', 'database', 'analysis'
    ]):
        return 'data'
    
    # Operations
    if any(kw in name_lower or kw in desc_lower for kw in [
        'operation', 'workflow', 'process', 'automation', 'integration',
        'api', 'devops', 'deployment', 'infrastructure'
    ]):
        return 'operations'
    
    # Support
    if any(kw in name_lower or kw in desc_lower for kw in [
        'support', 'customer service', 'help', 'ticket', 'chatbot', 'faq'
    ]):
        return 'support'
    
    # Planning/Strategy
    if any(kw in name_lower or kw in desc_lower for kw in [
        'planning', 'strategy', 'roadmap', 'project', 'initiative', 
        'goal', 'objective', 'kpi'
    ]):
        return 'planning'
    
    return 'content'  # Default category


def transform_skill(skill: dict[str, Any]) -> dict[str, Any]:
    """Transform a parsed skill to match database schema."""
    
    # Auto-categorize if not set
    if not skill.get('category') or skill['category'] == 'general':
        skill['category'] = categorize_skill(
            skill.get('name', ''), 
            skill.get('description', '')
        )
    
    # Convert agent_ids list to PostgreSQL array format
    agent_ids = skill.get('agent_ids', [])
    if isinstance(agent_ids, list):
        agent_ids = [str(a) for a in agent_ids]
    skill['agent_ids'] = agent_ids
    
    # Mark security-related skills as restricted
    restricted_keywords = ['security', 'pentest', 'penetration', 'exploit', 'hack']
    name_lower = skill.get('name', '').lower()
    desc_lower = skill.get('description', '').lower()
    if any(kw in name_lower or kw in desc_lower for kw in restricted_keywords):
        skill['is_restricted'] = True
    
    # Set source
    skill['source'] = 'builtin'
    
    # Truncate knowledge if too large (DB has TEXT limit ~1GB but we want reasonable size)
    knowledge = skill.get('knowledge', '')
    if len(knowledge) > 500000:  # 500KB limit
        skill['knowledge'] = knowledge[:500000] + "\n\n[Content truncated]"
    
    return skill


async def migrate_skills(
    skills: list[dict[str, Any]], 
    supabase_url: str, 
    supabase_key: str,
    dry_run: bool = False,
    batch_size: int = 50
) -> dict[str, Any]:
    """Migrate skills to Supabase database."""
    
    if not HAS_SUPABASE:
        return {"error": "Supabase client not available"}
    
    client: Client = create_client(supabase_url, supabase_key)
    
    # Transform skills
    transformed_skills = [transform_skill(s) for s in skills]
    
    if dry_run:
        return {
            "dry_run": True,
            "total_skills": len(transformed_skills),
            "sample_skills": transformed_skills[:3]
        }
    
    # Insert in batches
    results = {
        "inserted": 0,
        "errors": [],
        "batch_count": 0
    }
    
    for i in range(0, len(transformed_skills), batch_size):
        batch = transformed_skills[i:i + batch_size]
        
        try:
            response = client.table("skills").insert(batch).execute()
            
            if response.data:
                results["inserted"] += len(response.data)
            results["batch_count"] += 1
            
        except Exception as e:
            results["errors"].append({
                "batch_start": i,
                "error": str(e)
            })
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Migrate skills to database")
    parser.add_argument(
        "--file", 
        default="app/skills/custom/auto_mapped_skills.py",
        help="Path to auto_mapped_skills.py"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true",
        help="Parse and show skills without inserting"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Number of skills to insert per batch"
    )
    parser.add_argument(
        "--output-json",
        help="Output parsed skills to JSON file"
    )
    
    args = parser.parse_args()
    
    # Parse skills
    print(f"Parsing skills from {args.file}...")
    skills = parse_skills_file(args.file)
    print(f"Found {len(skills)} skills")
    
    # Optionally output to JSON
    if args.output_json:
        with open(args.output_json, 'w') as f:
            json.dump(skills, f, indent=2)
        print(f"Skills exported to {args.output_json}")
    
    # Transform skills
    transformed = [transform_skill(s) for s in skills]
    
    # Show category distribution
    categories: dict[str, int] = {}
    for s in transformed:
        cat = s.get('category', 'unknown')
        categories[cat] = categories.get(cat, 0) + 1
    
    print("\nCategory distribution:")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count}")
    
    # Check for restricted skills
    restricted = sum(1 for s in transformed if s.get('is_restricted'))
    print(f"\nRestricted skills: {restricted}")
    
    # Migrate if not dry run and Supabase is available
    if not args.dry_run:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        if supabase_url and supabase_key:
            import asyncio
            results = asyncio.run(migrate_skills(
                transformed, 
                supabase_url, 
                supabase_key,
                batch_size=args.batch_size
            ))
            print(f"\nMigration results: {json.dumps(results, indent=2)}")
        else:
            print("\nSUPABASE_URL and SUPABASE_SERVICE_KEY not set. Skipping migration.")
            print("Set these environment variables to perform migration.")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
