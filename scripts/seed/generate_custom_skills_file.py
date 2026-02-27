
import os
import json
import re
from pathlib import Path

# Config
PROJECT_ROOT = Path(r"c:\Users\expert\Documents\PKA\Pikar-Ai")
FS_SKILLS_DIR = PROJECT_ROOT / "antigravity-awesome-skills" / "skills"
OUTPUT_FILE = PROJECT_ROOT / "app" / "skills" / "custom" / "auto_mapped_skills.py"
UNMAPPED_LIST = PROJECT_ROOT / "execution" / "unmapped_skills.json"

# Agent IDs (Strings for code generation)
EXEC = "AgentID.EXEC"
FIN = "AgentID.FIN"
CONT = "AgentID.CONT"
STRAT = "AgentID.STRAT"
SALES = "AgentID.SALES"
MKT = "AgentID.MKT"
OPS = "AgentID.OPS"
HR = "AgentID.HR"
LEGAL = "AgentID.LEGAL"
SUPP = "AgentID.SUPP"
DATA = "AgentID.DATA"

# Keyword Mapping (Same as classifier)
KEYWORD_MAPPING = {
    # Marketing
    "marketing": MKT, "seo": MKT, "ad": MKT, "ads": MKT, "viral": MKT, "growth": MKT,
    "hubspot": MKT, "campaign": MKT, "brand": MKT,
    # Content
    "content": CONT, "blog": CONT, "writing": CONT, "video": CONT, "image": CONT,
    "design": CONT, "canvas": CONT, "art": CONT, "podcast": CONT, "social": CONT,
    "gif": CONT, "scroll": CONT, "web-experience": CONT, "ui": CONT, "ux": CONT,
    "frontend": CONT, "theme": CONT, "interactive": CONT, "3d": CONT, "voice": CONT,
    # Finance
    "finance": FIN, "budget": FIN, "stripe": FIN, "plaid": FIN, "burn": FIN,
    "revenue": FIN, "fintech": FIN, "invoicing": FIN,
    # Sales
    "sales": SALES, "crm": SALES, "lead": SALES, "deal": SALES, "outreach": SALES,
    "hubspot": SALES, "shopify": SALES,
    # HR
    "recruit": HR, "interview": HR, "onboard": HR, "hiring": HR, "culture": HR,
    "employee": HR, "turnover": HR,
    # Legal / Compliance
    "legal": LEGAL, "gdpr": LEGAL, "compliance": LEGAL, "risk": LEGAL, "audit": LEGAL,
    "security": LEGAL, "pentest": OPS, "hack": OPS, "vulnerability": OPS,
    "red-team": OPS, "attack": OPS, "scanner": OPS,
    # Operations / Dev
    "docker": OPS, "server": OPS, "deploy": OPS, "aws": OPS, "gcp": OPS, "azure": OPS,
    "linux": OPS, "shell": OPS, "bash": OPS, "git": OPS, "workflow": OPS,
    "automation": OPS, "process": OPS, "network": OPS, "system": OPS,
    "react-best": OPS, "nextjs": OPS, "node": OPS, "typescript": OPS,
    "backend": OPS, "api": OPS, "testing": OPS, "debug": OPS,
    # Data
    "data": DATA, "analytics": DATA, "sql": DATA, "database": DATA, "python": DATA,
    "algorithm": DATA, "rag": DATA, "llm": DATA, "ai": DATA, "scraping": DATA,
    "segment": DATA, "tracking": DATA, "chart": DATA, "d3": DATA,
    # Support
    "support": SUPP, "ticket": SUPP, "customer": SUPP, "help": SUPP, "churn": SUPP,
    # Strategy
    "strategy": STRAT, "plan": STRAT, "business": STRAT, "roadmap": STRAT,
    "sprint": STRAT, "product": STRAT, "manager": STRAT, "brainstorm": STRAT,
}

DEFAULT_AGENT = OPS

def get_agent_id(skill_name):
    norm = skill_name.lower().replace("-", " ")
    match = DEFAULT_AGENT
    best_len = 0
    for kw, agent in KEYWORD_MAPPING.items():
        if kw in norm:
            if len(kw) > best_len:
                match = agent
                best_len = len(kw)
    
    # Overrides
    if "react" in norm and "design" in norm: match = CONT
    if "frontend" in norm: match = CONT
    if "security" in norm or "pentest" in norm or "red-team" in norm: match = OPS
    if "manager" in norm: match = STRAT
    if "agent" in norm and "build" in norm: match = DATA
    
    return match

def parse_skill_content(skill_dir):
    # Try SKILL.md, then README.md
    for fname in ["SKILL.md", "README.md"]:
        fpath = skill_dir / fname
        if fpath.exists():
            try:
                content = fpath.read_text(encoding="utf-8")
                # Parse description from frontmatter or content
                description = f"Skill for {skill_dir.name}"
                
                # Check for frontmatter
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        frontmatter = parts[1]
                        for line in frontmatter.splitlines():
                            if line.startswith("description:"):
                                description = line.split(":", 1)[1].strip().strip('"\'')
                                break
                return content, description
            except Exception as e:
                print(f"Error reading {fpath}: {e}")
                
    return None, f"Skill for {skill_dir.name}"

def generate_file():
    with open(UNMAPPED_LIST, "r") as f:
        skill_names = json.load(f)
        
    code_lines = [
        "# Auto-generated mapped skills",
        "from app.skills.registry import Skill, AgentID",
        "",
    ]
    
    count = 0
    for name in skill_names:
        skill_dir = FS_SKILLS_DIR / name
        if not skill_dir.exists():
            print(f"Warning: {name} not found in FS")
            continue
            
        content, description = parse_skill_content(skill_dir)
        if content is None:
            print(f"Warning: No content for {name}")
            continue
            
        agent = get_agent_id(name)
        
        # Sanitize name for python variable
        var_name = name.replace("-", "_").lower()
        if var_name[0].isdigit(): var_name = f"skill_{var_name}"
        
        code = f"""
{var_name} = Skill(
    name="{name}",
    description={repr(description)},
    category="generated",
    agent_ids=[{agent}],
    knowledge={repr(content)}
)
"""
        code_lines.append(code)
        count += 1

    print(f"Generating code for {count} skills...")
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(code_lines))
        
    print(f"Wrote to {OUTPUT_FILE}")

if __name__ == "__main__":
    generate_file()
