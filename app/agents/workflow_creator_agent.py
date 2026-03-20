from google.adk.agents import Agent

from app.agents.tools.workflows import create_workflow_template

workflow_creator_agent = Agent(
    name="WorkflowCreatorAgent",
    instruction="""
You are an agent that creates workflow templates.
You have a tool named `create_workflow_template`.
You must call the `create_workflow_template` tool directly with the provided parameters.
Example: create_workflow_template(name="My Workflow", ...)
""",
    model="gemini-2.5-flash",
    tools=[create_workflow_template],
)
