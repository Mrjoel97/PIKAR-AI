# Agent-to-UI Feature Track

**Track ID:** agent_to_ui_20260131  
**Created:** 2026-01-31  
**Status:** Active  
**Focus:** Generative UI - Agents that produce interactive interfaces on demand

---

## Phase 1: Foundation - Message Protocol & Widget Registry

### 1.1 Extend Message Type with Widget Support
- [x] Update `useAgentChat.ts` Message type to include `widget` property
- [x] Add widget data parsing in SSE message handler
- [x] Create TypeScript interfaces for widget definitions

### 1.2 Create Widget Registry System  
- [x] Create `/frontend/src/components/widgets/WidgetRegistry.tsx`
- [x] Implement `resolveWidget(type: string)` function
- [x] Add lazy loading with `React.lazy()` for each widget
- [x] Create `UnknownWidget.tsx` fallback component
- [ ] Write unit tests for WidgetRegistry

### 1.3 Update ChatInterface to Render Widgets
- [x] Modify `ChatInterface.tsx` to detect widget messages
- [x] Render widgets inline within chat bubbles
- [x] Add collapse/expand functionality for widgets
- [x] Implement widget header with title and close button
- [ ] Write unit tests for widget rendering in chat

---

## Phase 2: Backend - Widget Display Tool

### 2.1 Create Display Widget Tool
- [x] Create `/app/agents/tools/ui_widgets.py`
- [x] Implement `display_dashboard(dashboard_type, title, data)` tool
- [x] Implement `display_chart(chart_type, title, data)` tool
- [x] Implement `display_workflow_builder(title, nodes, edges)` tool
- [ ] Write unit tests for widget tools

### 2.2 Update Executive Agent to Use Widget Tools
- [x] Import widget tools in `agent.py`
- [x] Update EXECUTIVE_INSTRUCTION to document widget capabilities
- [x] Add widget tools to executive agent's tool list
- [ ] Write integration test for agent widget generation

---

## Phase 3: Widget Library - Core Dashboards

### 3.1 Initiative Dashboard Widget
- [ ] Create `/frontend/src/components/widgets/InitiativeDashboard.tsx`
- [ ] Implement status cards (in progress, completed, blocked)
- [ ] Add progress bars and metrics
- [ ] Add action buttons (Mark Complete, Add Note)
- [ ] Register in WidgetRegistry
- [ ] Write unit tests

### 3.2 Revenue Chart Widget
- [ ] Create `/frontend/src/components/widgets/RevenueChart.tsx`
- [ ] Implement line/bar chart visualization
- [ ] Add period selector (daily, weekly, monthly)
- [ ] Include trend indicators
- [ ] Register in WidgetRegistry
- [ ] Write unit tests

### 3.3 Workflow Builder Widget
- [ ] Create `/frontend/src/components/widgets/WorkflowBuilderWidget.tsx`
- [ ] Wrap existing `WorkflowBuilder.tsx` for widget context
- [ ] Add "Expand to Full Screen" functionality
- [ ] Add "Save Workflow" callback to agent
- [ ] Register in WidgetRegistry
- [ ] Write unit tests

---

## Phase 4: Enhanced UX & Notifications

### 4.1 Widget State Management
- [ ] Add `minimized` state to messages in useAgentChat
- [ ] Persist widget expansion state across renders
- [ ] Add widget history in sidebar (optional)

### 4.2 Sidebar Enhancements
- [ ] Add Notifications link to Sidebar.tsx
- [ ] Implement active state styling on current route
- [ ] Add badge indicator for pending notifications

---

## Verification Criteria

### Automated Tests
- All widget components have unit tests
- WidgetRegistry has 100% coverage
- Backend tools have unit tests
- Integration tests for agent → widget → UI flow

### Manual Verification
1. Ask agent: "Show me initiative status"
2. Verify: Dashboard widget appears in chat
3. Click collapse button → widget minimizes
4. Click expand button → widget restores
5. Verify: Chat input remains active during widget display
6. Ask agent: "Now show me revenue"
7. Verify: Second widget appears, first stays collapsed

---

## Quality Gates

- [ ] All new code has >80% test coverage
- [ ] TypeScript strict mode passes
- [ ] ESLint passes with no errors
- [ ] Mobile responsive (widgets work on mobile)
- [ ] Accessibility: widgets are keyboard navigable
