import asyncio

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from app.agents.workflow_creator_agent import workflow_creator_agent
from google.genai import types as genai_types


async def main():
    """Runs the agent with a sample query."""
    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name="app", user_id="test_user", session_id="test_session"
    )
    runner = Runner(
        agent=workflow_creator_agent, app_name="app", session_service=session_service
    )
    query = """
Create a new workflow template with the following parameters:
- name: "Idea to Initiative"
- description: "A workflow for turning a brain dump into an actionable business initiative."
- category: "custom"
- phases: [
    {
        "name": "Initiative Scoping",
        "steps": [
            {
                "name": "Get Brain Dump Document",
                "description": "Get the brain dump document from the knowledge vault.",
                "tool": "get_braindump_document"
            },
            {
                "name": "Create Initiative",
                "description": "Create a new initiative from the brain dump document.",
                "tool": "create_initiative"
            }
        ]
    },
    {
        "name": "Task Generation",
        "steps": [
            {
                "name": "Generate Tasks",
                "description": "Generate actionable tasks from the initiative.",
                "tool": "create_task"
            }
        ]
    }
]
"""
    async for event in runner.run_async(
        user_id="test_user",
        session_id="test_session",
        new_message=genai_types.Content(
            role="user", 
            parts=[genai_types.Part.from_text(text=query)]
        ),
    ):
        print(event)


if __name__ == "__main__":
    asyncio.run(main())
