import traceback
import sys
try:
    from app.agents.specialized_agents import SPECIALIZED_AGENTS
    print("loaded", [a.name for a in SPECIALIZED_AGENTS])
    sys.exit(0)
except Exception:
    traceback.print_exc()
    sys.exit(1)
