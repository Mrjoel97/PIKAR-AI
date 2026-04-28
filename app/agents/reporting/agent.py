# Copyright 2025 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Portions copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""DataReportingAgent - Automated spreadsheet analysis and report generation.

This agent specializes in:
1. Connecting to user spreadsheets (Google Sheets)
2. Analyzing data trends (sales, expenses, inventory, KPIs, time tracking)
3. Generating automated reports (daily/weekly/monthly/quarterly/yearly)
4. Creating presentations (PowerPoint) and documents (PDF)
5. Scheduling and delivering reports to authorized recipients
"""

from app.agents.base_agent import PikarAgent as Agent
from app.agents.context_extractor import (
    context_memory_after_tool_callback,
    context_memory_before_model_callback,
)
from app.agents.enhanced_tools import list_available_skills, use_skill
from app.agents.schemas import DataInsight
from app.agents.shared import get_model
from app.agents.shared_instructions import (
    APP_BUILDER_HANDOFF_INSTRUCTION,
    CONVERSATION_MEMORY_INSTRUCTIONS,
    SELF_IMPROVEMENT_INSTRUCTIONS,
    SKILLS_REGISTRY_INSTRUCTIONS,
    get_error_and_escalation_instructions,
)
from app.agents.tools.base import sanitize_tools
from app.agents.tools.calendar_tool import CALENDAR_TOOLS
from app.agents.tools.context_memory import CONTEXT_MEMORY_TOOLS
from app.agents.tools.docs import DOCS_TOOLS
from app.agents.tools.document_generation import DOCUMENT_GENERATION_TOOLS
from app.agents.tools.forms import FORMS_TOOLS
from app.agents.tools.gmail import GMAIL_TOOLS
from app.agents.tools.google_sheets import GOOGLE_SHEETS_TOOLS
from app.agents.tools.report_scheduling import REPORT_SCHEDULING_TOOLS
from app.personas.prompt_fragments import build_persona_policy_block

# =============================================================================
# Report Generator Sub-Agent (Structured Output)
# =============================================================================

REPORT_GENERATOR_INSTRUCTION = """You are a Report Generator that produces structured JSON reports.

When given spreadsheet data, analyze it and produce a comprehensive report with:
1. Executive summary of key findings
2. Trend analysis (growing/stable/declining)
3. Key metrics and KPIs
4. Recommendations for action

Your output MUST be valid JSON matching the DataInsight schema.
Focus on actionable insights, not just data repetition.
"""

report_generator_agent = Agent(
    name="ReportGeneratorAgent",
    model=get_model(),
    description="Generates structured JSON reports from spreadsheet data",
    instruction=REPORT_GENERATOR_INSTRUCTION,
    output_schema=DataInsight,
    output_key="generated_report",
    include_contents="none",
)


# =============================================================================
# Main Data Reporting Agent
# =============================================================================

DATA_REPORTING_AGENT_INSTRUCTION = (
    """You are the Data Reporting Agent, specialized in spreadsheet analysis and automated report generation.

## YOUR CAPABILITIES

### 1. SPREADSHEET CONNECTION
- List user's Google Sheets spreadsheets
- Connect to existing spreadsheets
- Create custom spreadsheets based on user requirements

### 2. CUSTOM SPREADSHEET CREATION
When users want to track something new, design an appropriate structure:
- **Sales Tracking**: Date, Product/Service, Quantity, Unit Price, Total, Customer, Sales Rep
- **Expense Tracking**: Date, Category, Description, Amount, Payment Method, Vendor, Receipt
- **Inventory**: Item, SKU, Quantity, Unit Cost, Reorder Level, Supplier, Last Updated
- **KPI Dashboard**: Date, Metric Name, Target, Actual, Variance, Status
- **Time Tracking**: Date, Project, Task, Hours, Rate, Notes, Status

Ask clarifying questions to understand exactly what they need to track.

### 3. DATA ANALYSIS
- Read and analyze spreadsheet data
- Identify trends and patterns
- Calculate summaries and aggregations
- Detect anomalies or issues

### 4. REPORT GENERATION
Generate reports at various frequencies:
- **Hourly**: Quick status updates for high-frequency tracking
- **Daily**: End-of-day summaries with key metrics
- **Weekly**: Trend analysis with week-over-week comparisons
- **Monthly**: Comprehensive analysis with visualizations
- **Quarterly**: Strategic review with recommendations
- **Yearly**: Annual summary with year-over-year growth

### 5. DOCUMENT CREATION
Use the document generation tools to create:
- PowerPoint presentations for reporting and proposals
- PDF documents for formal reports
- Excel exports with formatted data

## SKILLS SUPPORT
When you need a reusable reporting, analysis, or spreadsheet workflow:
- `list_available_skills`: Discover skills relevant to reporting and spreadsheet analysis
- `use_skill`: Load a skill before generating the report or delivery plan

Use skills to strengthen recurring reporting methodologies, spreadsheet structures, and presentation quality.

## WORKFLOW

1. **Understand Requirements**: Ask what the user wants to track or analyze
2. **Connect/Create**: Connect to existing sheet or create custom spreadsheet
3. **Analyze Data**: Read and analyze the data
4. **Generate Report**: Create appropriate report format (PPTX/PDF)
5. **Schedule or Deliver**: Set up automated scheduling or provide immediate download

### 6. REPORT SCHEDULING
Set up automated reports:
- schedule_report: Create recurring report (hourly/daily/weekly/monthly/quarterly/yearly)
- list_report_schedules: View all scheduled reports
- pause/resume/delete schedules: Manage existing schedules

### 7. EMAIL & NOTIFICATIONS (Gmail)
- send_email: Send emails to users
- send_report_email: Deliver reports via email with attachments

### 8. CALENDAR & SCHEDULING (Google Calendar)
- list_events: View upcoming calendar events
- create_calendar_event: Schedule new events
- check_availability: Check if time slots are free
- schedule_meeting: Book meetings with attendees

### 9. DOCUMENT CREATION (Google Docs)
- create_document: Create new Google Docs
- create_report_doc: Create formatted report documents
- append_to_document: Add content to existing docs

### 10. CUSTOMER FEEDBACK (Google Forms)
- create_feedback_form: Create customer satisfaction surveys
- create_custom_form: Build custom survey forms
- get_form_responses: Retrieve survey responses
- analyze_feedback: Analyze customer feedback data

## FEEDBACK COLLECTION WORKFLOW
1. Create feedback form for the business
2. Share form URL with customers
3. Periodically retrieve and analyze responses
4. Generate insights report from feedback
5. Schedule follow-up actions based on feedback

## STRUCTURED REPORTS
When generating detailed reports:
1. Delegate to ReportGeneratorAgent for structured JSON output
2. Present findings in a clear, conversational summary
3. Include the raw JSON in <json>...</json> blocks for frontend rendering

Always prioritize actionable insights over raw data presentation.
"""
    + CONVERSATION_MEMORY_INSTRUCTIONS
    + SKILLS_REGISTRY_INSTRUCTIONS
    + SELF_IMPROVEMENT_INSTRUCTIONS
    + get_error_and_escalation_instructions(
        "Data Reporting Agent",
        """- Escalate to financial agent for financial report interpretation or accounting treatment questions
- Escalate to operations agent for workflow or process-related data that requires operational context
- Never modify source spreadsheet data without explicit user confirmation
- For reports containing sensitive financial or HR data, remind the user about access controls before sharing""",
    )
    + APP_BUILDER_HANDOFF_INSTRUCTION
)

# Tools for the Data Reporting Agent (29 total)
DATA_REPORTING_TOOLS = sanitize_tools(
    [
        use_skill,
        list_available_skills,
        *GOOGLE_SHEETS_TOOLS,  # 7 - Spreadsheet operations
        *DOCUMENT_GENERATION_TOOLS,  # 3 - PPTX/PDF generation
        *REPORT_SCHEDULING_TOOLS,  # 6 - Automated scheduling
        *GMAIL_TOOLS,  # 2 - Email & delivery
        *CALENDAR_TOOLS,  # 4 - Calendar & meetings
        *DOCS_TOOLS,  # 3 - Google Docs
        *FORMS_TOOLS,  # 4 - Customer feedback
        *CONTEXT_MEMORY_TOOLS,  # 2 - Context memory
    ]
)


# Singleton instance
data_reporting_agent = Agent(
    name="DataReportingAgent",
    model=get_model(),
    description="Automated spreadsheet analysis, custom sheet creation, and report generation for sales, expenses, inventory, KPIs, and time tracking",
    instruction=DATA_REPORTING_AGENT_INSTRUCTION,
    tools=DATA_REPORTING_TOOLS,
    sub_agents=[report_generator_agent],
    before_model_callback=context_memory_before_model_callback,
    after_tool_callback=context_memory_after_tool_callback,
)


def create_data_reporting_agent(
    name_suffix: str = "",
    persona: str | None = None,
) -> Agent:
    """Factory function to create DataReportingAgent instances.

    Args:
        name_suffix: Optional suffix for unique naming.
        persona: Optional persona tier (solopreneur, startup, sme, enterprise).
            When provided, persona-specific behavioral instructions are appended
            to the agent's system prompt.

    Returns:
        New DataReportingAgent instance.
    """
    # Create fresh report sub-agent
    report_agent = Agent(
        name=f"ReportGeneratorAgent{name_suffix}"
        if name_suffix
        else "ReportGeneratorAgent",
        model=get_model(),
        description="Generates structured JSON reports from spreadsheet data",
        instruction=REPORT_GENERATOR_INSTRUCTION,
        output_schema=DataInsight,
        output_key="generated_report",
        include_contents="none",
    )

    agent_name = (
        f"DataReportingAgent{name_suffix}" if name_suffix else "DataReportingAgent"
    )
    instruction = DATA_REPORTING_AGENT_INSTRUCTION
    persona_block = build_persona_policy_block(persona, agent_name="DataReportingAgent")
    if persona_block:
        instruction = instruction + "\n\n" + persona_block
    return Agent(
        name=agent_name,
        model=get_model(),
        description="Automated spreadsheet analysis, custom sheet creation, and report generation",
        instruction=instruction,
        tools=DATA_REPORTING_TOOLS,
        sub_agents=[report_agent],
        before_model_callback=context_memory_before_model_callback,
        after_tool_callback=context_memory_after_tool_callback,
    )
