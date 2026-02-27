import asyncio

from app.agents.tools.workflows import list_workflow_templates


async def main():
    templates = await list_workflow_templates()
    print(templates)


if __name__ == "__main__":
    asyncio.run(main())
