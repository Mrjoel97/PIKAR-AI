import asyncio
import uuid
from app.workflows.engine import get_workflow_engine


async def main():
    engine = get_workflow_engine()
    result = await engine.create_template(
        user_id=str(uuid.uuid4()),
        name="Idea to Initiative",
        description="A workflow for turning a brain dump into an actionable business initiative.",
        category="custom",
        phases=[
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
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
