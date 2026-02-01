# Agent-to-UI (Generative UI) Implementation Guide

> **Feature:** Agents generate interactive UI widgets on-demand within the chat interface  
> **Created:** 2026-01-31  
> **Conductor Track:** `conductor/tracks/agent_to_ui_20260131/plan.md`

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Message Protocol](#message-protocol)
4. [Widget Registry](#widget-registry)
5. [Backend Tools](#backend-tools)
6. [Creating Custom Widgets](#creating-custom-widgets)
7. [Testing Strategy](#testing-strategy)
8. [Scalability Considerations](#scalability-considerations)
9. [Troubleshooting](#troubleshooting)

---

## Overview

### What is Agent-to-UI?

Agent-to-UI (also called "Generative UI" or "Server-Driven UI") is a pattern where AI agents don't just respond with text, but can generate **interactive UI components** on demand. These widgets appear inline within the chat and allow users to interact with business data, workflows, and dashboards without leaving the conversation.

### Key Capabilities

| Capability | Description |
|------------|-------------|
| **On-demand generation** | Widgets are created only when the user requests them |
| **Interactive** | Users can click buttons, edit data, filter views |
| **Agent co-presence** | Chat input remains active; user can keep talking to the agent |
| **Collapsible** | Widgets can be minimized to keep chat history clean |
| **Type-safe** | TypeScript contracts ensure backend/frontend alignment |

### User Experience Flow

```
User: "Show me my initiative status"
         │
         ▼
Agent: Uses display_dashboard() tool
         │
         ▼
Frontend: Receives widget payload via SSE
         │
         ▼
ChatInterface: Renders <InitiativeDashboard /> inline
         │
         ▼
User: Interacts with dashboard, continues chatting
```

---

## Architecture

### System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js)                       │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │ ChatInterface│───▶│WidgetRegistry│───▶│ Widget Components│  │
│  │    .tsx      │    │    .tsx      │    │ (Dashboard, etc) │  │
│  └──────────────┘    └──────────────┘    └──────────────────┘  │
│         ▲                                                       │
│         │ { widget: { type, data } }                           │
├─────────┴───────────────────────────────────────────────────────┤
│                    useAgentChat.ts (SSE)                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ SSE Stream
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Backend (FastAPI)                        │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │ fast_api_app│───▶│A2aAgentExec. │───▶│ ExecutiveAgent   │   │
│  │    .py      │    │ (ADK Runner) │    │ (tools: widgets) │   │
│  └─────────────┘    └──────────────┘    └──────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **User sends message** via ChatInterface
2. **useAgentChat** sends POST to `/a2a/pikar_ai/run_sse`
3. **Agent processes** and decides to use widget tool
4. **Tool returns** widget definition (type + data)
5. **SSE streams** widget payload to frontend
6. **ChatInterface** detects `widget` property in message
7. **WidgetRegistry** resolves type → React component
8. **Widget renders** inline in chat bubble

---

## Message Protocol

### Extended Message Type

```typescript
// frontend/src/hooks/useAgentChat.ts

export type WidgetDefinition = {
  type: string;           // Widget type (e.g., "initiative_dashboard")
  title?: string;         // Header text
  data: Record<string, unknown>;  // Props for the widget
  dismissible?: boolean;  // Can user close it?
  expandable?: boolean;   // Can open full-screen?
};

export type Message = {
  role: 'user' | 'agent' | 'system';
  text?: string;          // Optional (widget-only messages)
  widget?: WidgetDefinition;
  agentName?: string;
  isThinking?: boolean;
  isMinimized?: boolean;  // Widget collapse state
};
```

### SSE Payload Example

```json
{
  "author": "ExecutiveAgent",
  "content": {
    "parts": [
      {
        "text": "Here's your initiative dashboard:",
        "widget": {
          "type": "initiative_dashboard",
          "title": "Q1 2026 Initiatives",
          "data": {
            "initiatives": [
              { "id": "1", "name": "Product Launch", "status": "in_progress", "progress": 65 },
              { "id": "2", "name": "Hiring Sprint", "status": "completed", "progress": 100 }
            ],
            "metrics": {
              "total": 5,
              "completed": 2,
              "in_progress": 2,
              "blocked": 1
            }
          },
          "dismissible": true
        }
      }
    ]
  }
}
```

---

## Widget Registry

### Purpose

The Widget Registry is a **central mapping** from widget type strings to React components. It enables:
- Type-safe widget resolution
- Lazy loading for performance
- Fallback handling for unknown types

### Implementation

```typescript
// frontend/src/components/widgets/WidgetRegistry.tsx

import React, { lazy, Suspense } from 'react';
import { WidgetDefinition } from '@/hooks/useAgentChat';

// Lazy load widgets for performance
const InitiativeDashboard = lazy(() => import('./InitiativeDashboard'));
const RevenueChart = lazy(() => import('./RevenueChart'));
const WorkflowBuilderWidget = lazy(() => import('./WorkflowBuilderWidget'));
const UnknownWidget = lazy(() => import('./UnknownWidget'));

// Widget type → Component mapping
const WIDGET_MAP: Record<string, React.LazyExoticComponent<React.ComponentType<WidgetProps>>> = {
  initiative_dashboard: InitiativeDashboard,
  revenue_chart: RevenueChart,
  workflow_builder: WorkflowBuilderWidget,
};

export interface WidgetProps {
  definition: WidgetDefinition;
  onAction?: (action: string, payload?: unknown) => void;
  onDismiss?: () => void;
}

export function resolveWidget(type: string): React.LazyExoticComponent<React.ComponentType<WidgetProps>> {
  return WIDGET_MAP[type] ?? UnknownWidget;
}

export function Widget({ definition, onAction, onDismiss }: WidgetProps) {
  const WidgetComponent = resolveWidget(definition.type);
  
  return (
    <Suspense fallback={<WidgetSkeleton />}>
      <WidgetComponent definition={definition} onAction={onAction} onDismiss={onDismiss} />
    </Suspense>
  );
}
```

### Adding New Widgets

1. Create component in `/frontend/src/components/widgets/`
2. Export as default
3. Add to `WIDGET_MAP` in `WidgetRegistry.tsx`
4. Update backend tool to support the new type

---

## Backend Tools

### Widget Tool Definition

```python
# app/agents/tools/ui_widgets.py

from typing import Literal

def display_dashboard(
    dashboard_type: Literal["initiative_dashboard", "revenue_chart", "product_launch"],
    title: str,
    data: dict
) -> dict:
    """Display an interactive dashboard widget in the chat.
    
    Use this tool when the user asks to see business metrics, initiative status,
    revenue data, or any visual dashboard that would be better as a UI component
    than as plain text.
    
    Args:
        dashboard_type: Type of dashboard to display. Must be one of:
            - "initiative_dashboard": Shows OKRs, projects, and their statuses
            - "revenue_chart": Shows revenue metrics with charts
            - "product_launch": Shows product launch timeline and status
        title: Header text to display above the widget
        data: JSON data to populate the dashboard. Structure depends on type:
            For initiative_dashboard: { "initiatives": [...], "metrics": {...} }
            For revenue_chart: { "periods": [...], "values": [...] }
            For product_launch: { "milestones": [...], "status": "..." }
    
    Returns:
        Widget definition for frontend rendering
    """
    return {
        "widget": {
            "type": dashboard_type,
            "title": title,
            "data": data,
            "dismissible": True
        },
        "text": f"Here's your {title}:"
    }


def display_workflow_builder(
    title: str,
    initial_nodes: list[dict],
    initial_edges: list[dict]
) -> dict:
    """Generate an interactive workflow builder in the chat.
    
    Use this when the user wants to create, edit, or visualize a workflow.
    The workflow builder allows drag-and-drop node editing.
    
    Args:
        title: Name of the workflow being built
        initial_nodes: List of node definitions with id, position, data
        initial_edges: List of edge connections between nodes
    
    Returns:
        Widget definition for workflow builder
    """
    return {
        "widget": {
            "type": "workflow_builder",
            "title": title,
            "data": {
                "nodes": initial_nodes,
                "edges": initial_edges
            },
            "expandable": True
        },
        "text": f"I've created a workflow builder for '{title}'. You can edit it directly!"
    }


# Export tools for agent registration
UI_WIDGET_TOOLS = [
    display_dashboard,
    display_workflow_builder,
]
```

### Agent Integration

```python
# app/agent.py (additions)

from app.agents.tools.ui_widgets import UI_WIDGET_TOOLS

EXECUTIVE_INSTRUCTION = """...
## WIDGET CAPABILITIES
You can generate interactive UI widgets when users need visual data:

- **display_dashboard**: Show metrics, initiative status, revenue charts
- **display_workflow_builder**: Create editable workflow diagrams

When users ask to "show", "display", or "visualize" data, prefer widgets over text.
..."""

executive_agent = Agent(
    # ... existing config ...
    tools=[
        # ... existing tools ...
        *UI_WIDGET_TOOLS,  # Add widget tools
    ],
)
```

---

## Creating Custom Widgets

### Widget Component Template

```typescript
// frontend/src/components/widgets/MyCustomWidget.tsx

import React from 'react';
import { WidgetProps } from './WidgetRegistry';

interface MyCustomData {
  items: Array<{ id: string; name: string; value: number }>;
}

export default function MyCustomWidget({ definition, onAction, onDismiss }: WidgetProps) {
  const data = definition.data as MyCustomData;
  
  const handleItemClick = (itemId: string) => {
    onAction?.('item_selected', { itemId });
  };
  
  return (
    <div className="bg-white rounded-lg shadow-sm border p-4">
      {/* Header */}
      <div className="flex justify-between items-center mb-4">
        <h3 className="font-semibold text-lg">{definition.title}</h3>
        {definition.dismissible && (
          <button onClick={onDismiss} className="text-gray-400 hover:text-gray-600">
            ✕
          </button>
        )}
      </div>
      
      {/* Content */}
      <div className="space-y-2">
        {data.items.map(item => (
          <div 
            key={item.id}
            onClick={() => handleItemClick(item.id)}
            className="p-3 bg-gray-50 rounded cursor-pointer hover:bg-gray-100"
          >
            <span className="font-medium">{item.name}</span>
            <span className="text-gray-500 ml-2">{item.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
```

### Widget Checklist

- [ ] Create component in `/frontend/src/components/widgets/`
- [ ] Export as `default`
- [ ] Accept `WidgetProps` interface
- [ ] Handle `onDismiss` callback
- [ ] Handle `onAction` for interactions
- [ ] Add loading state if widget fetches data
- [ ] Add error boundary for resilience
- [ ] Register in `WIDGET_MAP`
- [ ] Write unit test
- [ ] Update backend tool types

---

## Testing Strategy

### Unit Tests (Frontend)

```typescript
// frontend/src/components/widgets/InitiativeDashboard.test.tsx

import { render, screen, fireEvent } from '@testing-library/react';
import InitiativeDashboard from './InitiativeDashboard';

const mockDefinition = {
  type: 'initiative_dashboard',
  title: 'Q1 Initiatives',
  data: {
    initiatives: [
      { id: '1', name: 'Launch MVP', status: 'in_progress', progress: 50 }
    ],
    metrics: { total: 1, completed: 0, in_progress: 1, blocked: 0 }
  },
  dismissible: true
};

describe('InitiativeDashboard', () => {
  it('renders title correctly', () => {
    render(<InitiativeDashboard definition={mockDefinition} />);
    expect(screen.getByText('Q1 Initiatives')).toBeInTheDocument();
  });
  
  it('displays all initiatives', () => {
    render(<InitiativeDashboard definition={mockDefinition} />);
    expect(screen.getByText('Launch MVP')).toBeInTheDocument();
  });
  
  it('calls onDismiss when close button clicked', () => {
    const onDismiss = vi.fn();
    render(<InitiativeDashboard definition={mockDefinition} onDismiss={onDismiss} />);
    fireEvent.click(screen.getByRole('button', { name: /close/i }));
    expect(onDismiss).toHaveBeenCalled();
  });
});
```

### Unit Tests (Backend)

```python
# tests/test_ui_widgets.py

import pytest
from app.agents.tools.ui_widgets import display_dashboard, display_workflow_builder

class TestDisplayDashboard:
    def test_returns_widget_structure(self):
        result = display_dashboard(
            dashboard_type="initiative_dashboard",
            title="Test Dashboard",
            data={"initiatives": []}
        )
        
        assert "widget" in result
        assert result["widget"]["type"] == "initiative_dashboard"
        assert result["widget"]["title"] == "Test Dashboard"
        assert result["widget"]["dismissible"] is True
    
    def test_includes_text_response(self):
        result = display_dashboard(
            dashboard_type="revenue_chart",
            title="Revenue Q1",
            data={}
        )
        
        assert "text" in result
        assert "Revenue Q1" in result["text"]


class TestDisplayWorkflowBuilder:
    def test_returns_expandable_widget(self):
        result = display_workflow_builder(
            title="Lead Workflow",
            initial_nodes=[{"id": "1", "position": {"x": 0, "y": 0}, "data": {"label": "Start"}}],
            initial_edges=[]
        )
        
        assert result["widget"]["expandable"] is True
        assert result["widget"]["data"]["nodes"][0]["id"] == "1"
```

### Running Tests

```bash
# Frontend tests
cd frontend
npm test

# Backend tests
cd ..
pytest tests/test_ui_widgets.py -v

# Full test suite with coverage
make test
pytest --cov=app --cov-report=term-missing
```

---

## Scalability Considerations

### Performance

| Concern | Solution |
|---------|----------|
| Many widgets in chat | Virtualize chat history (only render visible) |
| Large widget data | Paginate data in widget; stream in chunks |
| Slow widget load | Lazy loading via `React.lazy()` |
| Memory bloat | Unmount collapsed widgets after timeout |

### Adding New Widget Types

```
Effort per widget:
├── Backend tool update: ~15 min
├── Frontend component: ~30-60 min
├── Tests: ~30 min
├── Registry update: ~5 min
└── Total: ~1-2 hours per widget
```

### Extensibility Patterns

1. **Category-based registration** for 100+ widgets
2. **Widget versioning** for breaking changes
3. **Remote widget loading** for plugin architecture (future)

---

## Troubleshooting

### Widget Not Rendering

1. Check browser console for errors
2. Verify widget type is in `WIDGET_MAP`
3. Confirm SSE payload includes `widget` property
4. Check React Suspense fallback is rendering

### Agent Not Using Widget Tool

1. Verify tool is in agent's `tools` list
2. Check EXECUTIVE_INSTRUCTION mentions the tool
3. Test tool directly in Python REPL

### Widget Data Mismatch

1. Validate TypeScript interface matches backend output
2. Add runtime validation in widget component
3. Use Zod or similar for schema validation

---

## Related Documents

- [Conductor Plan](file:///c:/Users/expert/Documents/PKA/Pikar-Ai/conductor/tracks/agent_to_ui_20260131/plan.md)
- [Frontend Architecture](file:///c:/Users/expert/Documents/PKA/Pikar-Ai/frontend/README.md)
- [ADK Documentation](https://github.com/google/adk-python)
