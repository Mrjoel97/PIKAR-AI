import json
from pathlib import Path

# Agent IDs
EXEC = "EXEC"
FIN = "FIN"
CONT = "CONT"
STRAT = "STRAT"
SALES = "SALES"
MKT = "MKT"
OPS = "OPS"
HR = "HR"
LEGAL = "LEGAL"
SUPP = "SUPP"
DATA = "DATA"

# Mapping Rules (Keyword -> Agent)
KEYWORD_MAPPING = {
    # Marketing
    "marketing": MKT, "seo": MKT, "ad": MKT, "ads": MKT, "viral": MKT, "growth": MKT,
    "hubspot": MKT, "campaign": MKT, "brand": MKT,
    
    # Content
    "content": CONT, "blog": CONT, "writing": CONT, "video": CONT, "image": CONT,
    "design": CONT, "canvas": CONT, "art": CONT, "podcast": CONT, "social": CONT,
    "gif": CONT, "scroll": CONT, "web-experience": CONT, "ui": CONT, "ux": CONT,
    "frontend": CONT, "theme": CONT, "interactive": CONT, "3d": CONT,
    
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
    "support": SUPP, "ticket": SUPP, "customer": SUPP, "help": SUPP,
    "churn": SUPP,
    
    # Strategy
    "strategy": STRAT, "plan": STRAT, "business": STRAT, "roadmap": STRAT,
    "sprint": STRAT, "product": STRAT, "manager": STRAT, "brainstorm": STRAT,
}

# Fallback defaults
DEFAULT_AGENT = OPS # Most technical skills default to Ops if unsure

def classify_skills():
    with open("execution/unmapped_skills.json", "r") as f:
        skills = json.load(f)
    
    proposal = {}
    
    for skill in skills:
        norm_skill = skill.lower().replace("-", " ")
        assigned_agent = DEFAULT_AGENT
        
        # Check specific keywords
        best_match_len = 0
        
        for keyword, agent in KEYWORD_MAPPING.items():
            if keyword in norm_skill:
                # Prefer longer keyword matches (e.g. "marketing" over "mar")
                if len(keyword) > best_match_len:
                    assigned_agent = agent
                    best_match_len = len(keyword)
        
        # Specific overrides based on common sense
        if "react" in norm_skill and "design" in norm_skill: assigned_agent = CONT
        if "frontend" in norm_skill: assigned_agent = CONT
        if "security" in norm_skill or "pentest" in norm_skill or "red-team" in norm_skill: assigned_agent = OPS
        if "manager" in norm_skill: assigned_agent = STRAT
        if "agent" in norm_skill and "build" in norm_skill: assigned_agent = DATA # Agent builders
        if "voice" in norm_skill: assigned_agent = CONT 
        
        if assigned_agent not in proposal:
            proposal[assigned_agent] = []
        proposal[assigned_agent].append(skill)
        
    # Generate Markdown
    md = "# Skill Matching Proposal\n\n"
    md += "This document proposes mappings for the 191 unmapped skills to the core Pikar AI agents.\n\n"
    
    agents = [EXEC, STRAT, FIN, CONT, MKT, SALES, OPS, HR, LEGAL, SUPP, DATA]
    
    for agent in agents:
        agent_skills = proposal.get(agent, [])
        if not agent_skills:
            continue
            
        md += f"## {agent} Agent ({len(agent_skills)} skills)\n"
        md += "| Skill Name | Category (Inferred) |\n"
        md += "|------------|---------------------|\n"
        for skill in sorted(agent_skills):
            category = "General"
            md += f"| {skill} | {category} |\n"
        md += "\n"
        
    with open("skill_matching_proposal.md", "w") as f:
        f.write(md)
        
    print("Generated skill_matching_proposal.md")

if __name__ == "__main__":
    classify_skills()
