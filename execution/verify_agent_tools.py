
import sys
import importlib
from pathlib import Path

# Fix path
sys.path.insert(0, str(Path.cwd()))

AGENTS_TO_CHECK = [
    ("app.agents.marketing.agent", "marketing_agent"),
    ("app.agents.financial.agent", "financial_agent"),
    ("app.agents.operations.agent", "operations_agent"),
    ("app.agents.sales.agent", "sales_agent"),
    ("app.agents.content.agent", "content_agent"),
    ("app.agents.hr.agent", "hr_agent"),
    ("app.agents.compliance.agent", "compliance_agent"), # Legal
    ("app.agents.customer_support.agent", "support_agent"),
    ("app.agents.data.agent", "data_analytics_agent"),
    ("app.agents.strategic.agent", "strategic_agent"),
    ("app.agents.reporting.agent", "data_reporting_agent"),
]

def verify():
    success_count = 0
    for module_name, agent_var_name in AGENTS_TO_CHECK:
        try:
            print(f"Checking {module_name}...")
            module = importlib.import_module(module_name)
            agent = getattr(module, agent_var_name)
            
            # Check if list_available_skills is in tools
            # Tools are often wrapped or functions.
            # We check for function name 'list_available_skills'
            
            found = False
            for tool in agent.tools:
                # Tool might be a function or a Tool object
                tool_name = getattr(tool, "name", None) or getattr(tool, "__name__", None)
                if tool_name == "list_available_skills":
                    found = True
                    break
            
            if found:
                print(f"✅ {agent_var_name}: list_available_skills FOUND")
                success_count += 1
            else:
                print(f"❌ {agent_var_name}: list_available_skills NOT FOUND")
                
        except Exception as e:
            print(f"❌ {agent_var_name}: Error loading - {e}")

    print(f"\nVerification Complete: {success_count}/{len(AGENTS_TO_CHECK)} agents enabled.")

if __name__ == "__main__":
    verify()
