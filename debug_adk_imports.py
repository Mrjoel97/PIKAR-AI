
print("Start debugging imports...")
try:
    print("Importing specialized_agents...")
    from app.agents import specialized_agents
    print("Imported specialized_agents.")
except Exception as e:
    print(f"Failed specialized_agents: {e}")

try:
    print("Importing knowledge_tools...")
    from app.orchestration import knowledge_tools
    print("Imported knowledge_tools.")
except Exception as e:
    print(f"Failed knowledge_tools: {e}")

try:
    print("Importing notification_tools...")
    from app.agents.tools import notifications
    print("Imported notifications.")
except Exception as e:
    print(f"Failed notifications: {e}")

try:
    print("Importing workflow_tools...")
    from app.agents.tools import workflows
    print("Imported workflows.")
except Exception as e:
    print(f"Failed workflows: {e}")

try:
    print("Importing ui_widget_tools...")
    from app.agents.tools import ui_widgets
    print("Imported ui_widgets.")
except Exception as e:
    print(f"Failed ui_widgets: {e}")

try:
    print("Importing agent module...")
    from app import agent
    print("Imported agent module.")
except Exception as e:
    print(f"Failed agent module: {e}")
