# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Pydantic models for UI widgets matching frontend TypeScript types."""

from __future__ import annotations

from typing import Any, Literal, Union

from pydantic import BaseModel, Field, model_validator


# =============================================================================
# Widget Data Models
# =============================================================================

# Calendar Widget Models
class CalendarEvent(BaseModel):
    """Event data for the calendar widget."""
    id: str
    title: str
    start: str
    end: str
    color: str | None = None
    location: str | None = None
    description: str | None = None


class CalendarData(BaseModel):
    """Data payload for the calendar widget."""
    view: Literal["month", "week", "day"]
    events: list[CalendarEvent]


# Form Widget Models
class FieldDefinition(BaseModel):
    """Definition of a single form field."""
    name: str
    label: str
    type: Literal["text", "number", "email", "select", "textarea", "date"]
    required: bool | None = None
    options: list[str] | None = None
    default_value: str | None = Field(default=None, alias="defaultValue")
    placeholder: str | None = None

    model_config = {"populate_by_name": True}


class FormDataDefinition(BaseModel):
    """Data payload for the form widget."""
    fields: list[FieldDefinition]
    submit_label: str | None = Field(default=None, alias="submitLabel")

    model_config = {"populate_by_name": True}


# Table Widget Models
class ColumnDefinition(BaseModel):
    """Definition of a table column."""
    key: str
    label: str
    sortable: bool | None = None


class ActionDefinition(BaseModel):
    """Definition of a table row action."""
    name: str
    label: str
    icon: str | None = None


class TableDataDefinition(BaseModel):
    """Data payload for the table widget."""
    columns: list[ColumnDefinition]
    rows: list[dict[str, Any]]
    actions: list[ActionDefinition] | None = None


# Kanban Widget Models
class Column(BaseModel):
    """Column definition for the kanban board."""
    id: str
    title: str
    color: str | None = None


class Card(BaseModel):
    """Card definition for the kanban board."""
    id: str
    column_id: str = Field(alias="columnId")
    title: str
    description: str | None = None
    tags: list[str] | None = None

    model_config = {"populate_by_name": True}


class KanbanData(BaseModel):
    """Data payload for the kanban board widget."""
    columns: list[Column]
    cards: list[Card]


# Revenue Chart Models
class CurrentPeriod(BaseModel):
    """Summary metrics for the current period."""
    revenue: float
    change: float
    change_percent: float = Field(alias="changePercent")

    model_config = {"populate_by_name": True}


class RevenueData(BaseModel):
    """Data payload for the revenue chart widget."""
    periods: list[str]
    values: list[float]
    currency: str | None = None
    current_period: CurrentPeriod | None = Field(default=None, alias="currentPeriod")

    model_config = {"populate_by_name": True}


# Initiative Dashboard Models
class Initiative(BaseModel):
    """Definition of a strategic initiative."""
    id: str
    name: str
    title: str | None = None
    status: Literal["in_progress", "completed", "blocked", "not_started", "on_hold"]
    progress: float = Field(ge=0, le=100)
    phase: Literal["ideation", "validation", "prototype", "build", "scale"] | None = None
    phase_progress: dict[str, float] | None = Field(default=None, alias="phaseProgress")
    owner: str | None = None
    due_date: str | None = Field(default=None, alias="dueDate")
    workflow_execution_id: str | None = None
    goal: str | None = None
    current_phase: str | None = Field(default=None, alias="currentPhase")
    success_criteria: list[str] | None = Field(default=None, alias="successCriteria")
    primary_workflow: str | None = Field(default=None, alias="primaryWorkflow")
    deliverables: list[Any] | None = None
    evidence: list[Any] | None = None
    blockers: list[Any] | None = None
    next_actions: list[Any] | None = Field(default=None, alias="nextActions")
    trust_summary: dict[str, Any] | None = Field(default=None, alias="trustSummary")
    verification_status: str | None = Field(default=None, alias="verificationStatus")

    model_config = {"populate_by_name": True}


class InitiativeMetrics(BaseModel):
    """Aggregate metrics for initiatives."""
    total: int
    completed: int
    in_progress: int
    blocked: int


class InitiativeDashboardData(BaseModel):
    """Data payload for the initiative dashboard widget."""
    initiatives: list[Initiative]
    metrics: InitiativeMetrics

# Product Launch Models
class Milestone(BaseModel):
    """Definition of a product launch milestone."""
    name: str
    date: str
    status: Literal["completed", "in_progress", "pending", "delayed"]


class ProductLaunchData(BaseModel):
    """Data payload for the product launch widget."""
    milestones: list[Milestone]
    status: Literal["on_track", "at_risk", "delayed"]


# Workflow Builder Models
class Position(BaseModel):
    """Position coordinates for a workflow node."""
    x: float
    y: float


class WorkflowNodeData(BaseModel):
    """Data payload for a workflow node."""
    label: str


class WorkflowNode(BaseModel):
    """Node definition for the workflow builder."""
    id: str
    position: Position
    data: WorkflowNodeData
    style: dict[str, str] | None = None

    model_config = {"extra": "forbid"}


class WorkflowEdge(BaseModel):
    """Edge definition for the workflow builder."""
    id: str
    source: str
    target: str
    animated: bool | None = None
    style: dict[str, str] | None = None

    model_config = {"extra": "forbid"}


class WorkflowBuilderData(BaseModel):
    """Data payload for the workflow builder widget."""
    nodes: list[WorkflowNode] | None = None
    edges: list[WorkflowEdge] | None = None


# Morning Briefing Models
class PendingApproval(BaseModel):
    """Item requiring approval."""
    id: str
    action_type: str
    created_at: str
    token: str


class BriefingData(BaseModel):
    """Data payload for the morning briefing widget."""
    greeting: str
    pending_approvals: list[PendingApproval]
    online_agents: int
    system_status: str


# Boardroom Models
class TranscriptItem(BaseModel):
    """Single entry in the boardroom transcript."""
    speaker: str
    content: str
    sentiment: str = "neutral"
    round: int = 1
    stance: str = ""


class BoardPacket(BaseModel):
    """Structured synthesis produced after a boardroom debate."""
    topic: str = ""
    recommendation: str = ""
    confidence: float = 0.0
    pros: list[str] = []
    cons: list[str] = []
    risks: list[str] = []
    estimated_impact: str = ""
    next_steps: list[str] = []
    dissenting_views: list[str] = []


class BoardroomData(BaseModel):
    """Data payload for the boardroom widget."""
    topic: str
    transcript: list[TranscriptItem]
    verdict: str
    board_packet: BoardPacket | None = None
    vote_summary: dict[str, str] = {}


# Suggested Workflows Models
class Suggestion(BaseModel):
    """Workflow suggestion."""
    id: str
    pattern_description: str
    suggested_goal: str
    suggested_context: str
    status: str


class SuggestedWorkflowsData(BaseModel):
    """Data payload for the suggested workflows widget."""
    suggestions: list[Suggestion]


# =============================================================================
# Union and Base Types
# =============================================================================

WidgetType = Literal[
    "initiative_dashboard",
    "revenue_chart",
    "product_launch",
    "kanban_board",
    "workflow_builder",
    "morning_briefing",
    "boardroom",
    "suggested_workflows",
    "form",
    "table",
    "calendar",
    "workflow",
    "image",
    "video",
    "video_spec",
]

# Discriminated Union for Type-Safe Widget Data
WidgetDataUnion = Union[
    CalendarData,
    FormDataDefinition,
    TableDataDefinition,
    KanbanData,
    RevenueData,
    InitiativeDashboardData,
    ProductLaunchData,
    WorkflowBuilderData,
    BriefingData,
    BoardroomData,
    SuggestedWorkflowsData,
]


class WidgetWorkspace(BaseModel):
    """Workspace rendering hints and durable references for a widget."""

    mode: Literal["embedded", "focus", "grid", "split", "compare"] | None = None
    bundle_id: str | None = Field(default=None, alias="bundleId")
    deliverable_id: str | None = Field(default=None, alias="deliverableId")
    workspace_item_id: str | None = Field(default=None, alias="workspaceItemId")
    session_id: str | None = Field(default=None, alias="sessionId")
    workflow_execution_id: str | None = Field(default=None, alias="workflowExecutionId")

    model_config = {"populate_by_name": True}


class WidgetDefinition(BaseModel):
    """Generic definition of a widget as sent to the frontend."""
    type: WidgetType
    title: str | None = None
    data: dict[str, Any]
    workspace: WidgetWorkspace | None = None
    dismissible: bool = True
    expandable: bool = False

    model_config = {"populate_by_name": True, "use_enum_values": True, "extra": "forbid"}

    @model_validator(mode="after")
    def validate_data_content(self) -> WidgetDefinition:
        """Validate that the data matches the type."""
        # This acts as a runtime type guard similar to the frontend
        try:
            if self.type == "calendar":
                self.data = CalendarData.model_validate(self.data).model_dump(by_alias=True, exclude_none=True)
            elif self.type == "form":
                self.data = FormDataDefinition.model_validate(self.data).model_dump(by_alias=True, exclude_none=True)
            elif self.type == "table":
                self.data = TableDataDefinition.model_validate(self.data).model_dump(by_alias=True, exclude_none=True)
            elif self.type == "kanban_board":
                self.data = KanbanData.model_validate(self.data).model_dump(by_alias=True, exclude_none=True)
            elif self.type == "revenue_chart":
                self.data = RevenueData.model_validate(self.data).model_dump(by_alias=True, exclude_none=True)
            elif self.type == "initiative_dashboard":
                self.data = InitiativeDashboardData.model_validate(self.data).model_dump(by_alias=True, exclude_none=True)
            elif self.type == "product_launch":
                self.data = ProductLaunchData.model_validate(self.data).model_dump(by_alias=True, exclude_none=True)
            elif self.type == "workflow_builder":
                self.data = WorkflowBuilderData.model_validate(self.data).model_dump(by_alias=True, exclude_none=True)
            elif self.type == "morning_briefing":
                self.data = BriefingData.model_validate(self.data).model_dump(by_alias=True, exclude_none=True)
            elif self.type == "boardroom":
                self.data = BoardroomData.model_validate(self.data).model_dump(by_alias=True, exclude_none=True)
            elif self.type == "suggested_workflows":
                self.data = SuggestedWorkflowsData.model_validate(self.data).model_dump(by_alias=True, exclude_none=True)
            elif self.type == "workflow":
                execution_id = self.data.get("execution_id")
                if execution_id is not None and not isinstance(execution_id, str):
                    raise ValueError("workflow widgets require execution_id to be a string when provided")
            elif self.type == "image":
                if not isinstance(self.data.get("imageUrl"), str):
                    raise ValueError("image widgets require imageUrl")
            elif self.type == "video":
                if not isinstance(self.data.get("videoUrl"), str):
                    raise ValueError("video widgets require videoUrl")
            elif self.type == "video_spec":
                if not isinstance(self.data.get("title") or self.data.get("remotion_code"), str):
                    raise ValueError("video_spec widgets require title or remotion_code")
        except Exception as e:
            raise ValueError(f"Invalid data for widget type '{self.type}': {str(e)}") from e
        
        return self


# =============================================================================
# Utility Functions
# =============================================================================

def to_widget_dict(widget: WidgetDefinition) -> dict[str, Any]:
    """Serialize a widget definition to a dictionary compatible with the frontend.
    
    Handles camelCase conversion via alias population.
    """
    return widget.model_dump(by_alias=True, exclude_none=True)


def is_valid_widget_type(type_str: str) -> bool:
    """Check if a string is a valid widget type."""
    return type_str in list(WidgetType.__args__)  # type: ignore


def validate_widget_data(widget_type: WidgetType, data: dict) -> bool:
    """Validate data against the appropriate model for the given widget type."""
    try:
        WidgetDefinition(type=widget_type, data=data)
        return True
    except ValueError:
        return False


__all__ = [
    # Calendar
    "CalendarEvent",
    "CalendarData",
    # Form
    "FieldDefinition",
    "FormDataDefinition",
    # Table
    "ColumnDefinition",
    "ActionDefinition",
    "TableDataDefinition",
    # Kanban
    "Column",
    "Card",
    "KanbanData",
    # Revenue
    "CurrentPeriod",
    "RevenueData",
    # Initiative
    "Initiative",
    "InitiativeMetrics",
    "InitiativeDashboardData",
    # Product Launch
    "Milestone",
    "ProductLaunchData",
    # Workflow
    "WorkflowNode",
    "WorkflowEdge",
    "WorkflowBuilderData",
    # Briefing
    "PendingApproval",
    "BriefingData",
    # Boardroom
    "TranscriptItem",
    "BoardroomData",
    # Suggested Workflows
    "Suggestion",
    "SuggestedWorkflowsData",
    # Base
    "WidgetType",
    "WidgetWorkspace",
    "WidgetDefinition",
    # Utils
    "to_widget_dict",
    "is_valid_widget_type",
    "validate_widget_data",
]
