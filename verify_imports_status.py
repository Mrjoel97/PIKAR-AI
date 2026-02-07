import sys
print(f"Python executable: {sys.executable}")
print(f"Python version: {sys.version}")

try:
    from a2a.server.apps import A2AFastAPIApplication
    from a2a.server.request_handlers import DefaultRequestHandler
    print("A2A: SUCCESS")
except Exception as e:
    print(f"A2A: FAILED - {e}")

try:
    from google.adk.a2a.executor.a2a_agent_executor import A2aAgentExecutor
    from google.adk.a2a.utils.agent_card_builder import AgentCardBuilder
    print("A2A_COMPONENTS: SUCCESS")
except Exception as e:
    print(f"A2A_COMPONENTS: FAILED - {e}")

try:
    from google.adk.artifacts import GcsArtifactService
    from google.adk.runners import Runner
    print("ADK_CORE: SUCCESS")
except Exception as e:
    print(f"ADK_CORE: FAILED - {e}")
