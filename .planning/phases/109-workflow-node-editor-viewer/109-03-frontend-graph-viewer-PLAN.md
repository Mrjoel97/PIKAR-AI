---
phase: 109-workflow-node-editor-viewer
plan: 03
type: execute
wave: 1
depends_on: [109-02]
files_modified:
  - frontend/package.json
  - frontend/package-lock.json
  - frontend/src/app/dashboard/workflows/editor/[id]/page.tsx
  - frontend/src/components/workflows/editor/NodeCanvas.tsx
  - frontend/src/components/workflows/editor/nodes/AgentActionNode.tsx
  - frontend/src/components/workflows/editor/nodes/TriggerNode.tsx
  - frontend/src/components/workflows/editor/nodes/OutputNode.tsx
  - frontend/src/components/workflows/WorkflowTemplateCard.tsx
  - frontend/src/__tests__/workflows/NodeCanvas.test.tsx
autonomous: true
requirements: [NODEEDITOR-VIEWER-01]

must_haves:
  truths:
    - "Visiting /dashboard/workflows/editor/{id} where {id} is a real template id renders a React Flow graph showing the template's nodes (trigger, N agent-action nodes, output) connected by edges in a left-to-right linear layout"
    - "The page is wrapped in <GatedPage featureKey='workflows'> so tier gating fires correctly via useFeatureGate"
    - "The page uses PremiumShell so it gets the standard sidebar + header chrome"
    - "Visiting /dashboard/workflows/editor/{nonexistent-id} returns a 'Template not found' error state (NOT a JS crash; the page's error boundary catches it)"
    - "Pan, zoom, and fit-to-screen controls work — React Flow's default Controls component is mounted"
    - "All nodes are READ-ONLY in Phase 1: no drag, no connect, no delete. React Flow's nodesDraggable={false}, nodesConnectable={false}, elementsSelectable={false} props are set"
    - "AgentActionNode renders the node label and the tool_name from config; TriggerNode and OutputNode render distinct visual treatments (e.g., circle vs rounded-rect)"
    - "Clicking the 'Edit' button on a template card at /dashboard/workflows/templates routes to /dashboard/workflows/editor/{template.id} (was previously routing to /editor/new which 404s)"
    - "Breadcrumb shows: Home > Workflows > Templates > {Template Name}"
    - "@xyflow/react v12+ is added as a dependency in frontend/package.json and its CSS is imported on the page"
  artifacts:
    - path: "frontend/package.json"
      provides: "@xyflow/react ^12 dependency added"
      contains: "@xyflow/react"
    - path: "frontend/src/app/dashboard/workflows/editor/[id]/page.tsx"
      provides: "Next.js dynamic route page component; 'use client'; fetches template via getWorkflowTemplate(id); wraps in GatedPage + DashboardErrorBoundary + PremiumShell; renders NodeCanvas with template prop"
      contains: "NodeCanvas"
    - path: "frontend/src/components/workflows/editor/NodeCanvas.tsx"
      provides: "React Flow wrapper component. Props: { template: WorkflowTemplate }. Maps template.graph_nodes → React Flow nodes (with positions from graph_layout), template.graph_edges → React Flow edges. Sets read-only props. Renders <Controls /> and <Background />. Has internal fallback: if template.graph_nodes is null, projects template.steps inline (this fallback should be dead code post-migration but is kept as a safety net)"
      contains: "ReactFlow"
    - path: "frontend/src/components/workflows/editor/nodes/AgentActionNode.tsx"
      provides: "Custom React Flow node component for kind='agent-action'. Renders label + tool name. Tailwind styling consistent with PremiumShell teal-on-white aesthetic."
      contains: "Handle"
    - path: "frontend/src/components/workflows/editor/nodes/TriggerNode.tsx"
      provides: "Custom node for kind='trigger'. Circular icon + label."
      contains: "Handle"
    - path: "frontend/src/components/workflows/editor/nodes/OutputNode.tsx"
      provides: "Custom node for kind='output'. Distinct from trigger (e.g., flag/checkmark)."
      contains: "Handle"
    - path: "frontend/src/components/workflows/WorkflowTemplateCard.tsx"
      provides: "onEdit handler routes to /dashboard/workflows/editor/{template.id} instead of /editor/new"
      contains: "/editor/"
    - path: "frontend/src/__tests__/workflows/NodeCanvas.test.tsx"
      provides: "Vitest tests: renders 6-node graph for a 4-step template, all nodes are read-only, missing template renders error state, fallback projection runs when graph_nodes is null"
      contains: "NodeCanvas"
  key_links:
    - from: "frontend/src/components/workflows/editor/NodeCanvas.tsx"
      to: "frontend/src/services/workflows.ts:WorkflowTemplate.graph_nodes"
      via: "Props: { template: WorkflowTemplate }. Reads template.graph_nodes (typed list of GraphNode) and template.graph_edges. Maps them into React Flow's Node[] and Edge[] formats."
      pattern: "template.graph_nodes"
    - from: "frontend/src/app/dashboard/workflows/editor/[id]/page.tsx"
      to: "frontend/src/hooks/useFeatureGate.ts via GatedPage"
      via: "<GatedPage featureKey='workflows'>...</GatedPage> reuses the existing tier gate. Pattern matches /dashboard/workflows/templates/page.tsx"
      pattern: "GatedPage featureKey=\"workflows\""
    - from: "frontend/src/components/workflows/WorkflowTemplateCard.tsx:onEdit"
      to: "/dashboard/workflows/editor/{id}"
      via: "Change `router.push('/dashboard/workflows/editor/new')` (currently broken) to `router.push('/dashboard/workflows/editor/${template.id}')` for existing templates. The 'new' path stays 404 in Phase 1 (Phase 2 implements it)"
      pattern: "router.push(`/dashboard/workflows/editor"
---

<objective>
Build a read-only graph viewer at /dashboard/workflows/editor/[id] using React Flow. The viewer fetches a WorkflowTemplate via the existing API (extended in Plan 02), maps its graph_nodes and graph_edges into React Flow's data model, and renders a clean visual graph with pan/zoom but no editing. Three custom node components (trigger, agent-action, output) provide distinct visual treatments. The template-card "Edit" button gets rewired to point at this new route.

Purpose: Satisfy NODEEDITOR-VIEWER-01 (read-only graph view). Phase 1's user-facing deliverable — users can finally SEE the shape of every existing template.

Output: Visiting /dashboard/workflows/editor/{any-real-id} shows a graph. Visiting /dashboard/workflows/templates and clicking Edit on a card lands on the corresponding graph.
</objective>

<execution_context>
@C:/Users/expert/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/expert/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/109-workflow-node-editor-viewer/109-CONTEXT.md
@.planning/phases/109-workflow-node-editor-viewer/109-02-backend-api-extension-PLAN.md
@docs/superpowers/specs/2026-05-11-workflow-node-editor-design.md
@frontend/src/app/dashboard/workflows/templates/page.tsx
@frontend/src/components/workflows/WorkflowTemplateCard.tsx
@frontend/src/services/workflows.ts
@frontend/src/components/layout/PremiumShell.tsx
@frontend/src/components/dashboard/GatedPage.tsx
@frontend/src/components/ui/Breadcrumb.tsx

<interfaces>
<!-- React Flow node shape that NodeCanvas must produce from template.graph_nodes -->

```typescript
import type { Node, Edge } from '@xyflow/react';

// React Flow's Node type (positions required, data for custom rendering)
type RFNode = Node<{ label: string; tool_name?: string }>;

// Mapping from our GraphNode (services/workflows.ts) to RFNode:
function toRFNode(gn: GraphNode, layout: NodePosition): RFNode {
  return {
    id: gn.id,
    type: gn.kind,           // 'trigger' | 'agent-action' | 'output' (Phase 1 only)
    position: layout,
    data: {
      label: gn.label,
      tool_name: gn.config?.tool_name as string | undefined,
    },
  };
}

// Mapping from GraphEdge to RFEdge:
function toRFEdge(ge: GraphEdge): Edge {
  return {
    id: ge.id,
    source: ge.source,
    target: ge.target,
  };
}
```

<!-- Custom node component contract — React Flow custom nodes receive { data, ...rest } -->

```typescript
import { Handle, Position, type NodeProps } from '@xyflow/react';

export function AgentActionNode({ data }: NodeProps<{ label: string; tool_name?: string }>) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
      <Handle type="target" position={Position.Left} />
      <p className="text-sm font-medium text-slate-800">{data.label}</p>
      {data.tool_name && (
        <p className="text-xs text-slate-500 mt-1">{data.tool_name}</p>
      )}
      <Handle type="source" position={Position.Right} />
    </div>
  );
}
```

<!-- getWorkflowTemplate service function (may need to be added if it doesn't exist) -->

```typescript
// frontend/src/services/workflows.ts
export async function getWorkflowTemplate(id: string): Promise<WorkflowTemplate> {
  const res = await fetchWithAuth(`/workflows/templates/${id}`);
  return res as WorkflowTemplate;
}
```
</interfaces>
</context>

<tasks>

<task id="03-01" desc="Add @xyflow/react dependency">
```bash
cd frontend && npm install @xyflow/react@^12
```

Commit `package.json` and `package-lock.json` changes. Do NOT run `npm audit fix` unrelated changes.
</task>

<task id="03-02" desc="Add getWorkflowTemplate to the service if it doesn't exist">
Inspect `frontend/src/services/workflows.ts`. If a `getWorkflowTemplate(id: string)` function doesn't exist, add it (see Interfaces). If a similarly-named function exists with a different signature, prefer the existing one and adjust Plan 03's consumers.
</task>

<task id="03-03" desc="Build the three custom node components">
Create `frontend/src/components/workflows/editor/nodes/TriggerNode.tsx`, `AgentActionNode.tsx`, `OutputNode.tsx`. Each is a small functional component matching the React Flow `NodeProps` contract. Tailwind styling consistent with the rest of the dashboard:
- TriggerNode: rounded-full background, distinct icon (e.g., Lucide Play)
- AgentActionNode: rounded-2xl card with label + tool_name (see interface example)
- OutputNode: rounded-full background, distinct icon (e.g., Lucide CheckCircle)

Each must have appropriate `<Handle>` placements:
- TriggerNode: only `source` handle (right edge)
- AgentActionNode: both `target` (left) and `source` (right)
- OutputNode: only `target` handle (left)
</task>

<task id="03-04" desc="Build NodeCanvas component">
Create `frontend/src/components/workflows/editor/NodeCanvas.tsx`:

```typescript
'use client';

import { useMemo } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  type Node,
  type Edge,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import type { WorkflowTemplate, GraphNode, GraphEdge, NodePosition } from '@/services/workflows';
import { TriggerNode } from './nodes/TriggerNode';
import { AgentActionNode } from './nodes/AgentActionNode';
import { OutputNode } from './nodes/OutputNode';

const NODE_TYPES = {
  trigger: TriggerNode,
  'agent-action': AgentActionNode,
  output: OutputNode,
  // Phase 3+ kinds (condition/parallel/merge/human-approval) intentionally
  // absent in Phase 1 — they fall back to React Flow's default node renderer.
};

interface NodeCanvasProps {
  template: WorkflowTemplate;
}

export function NodeCanvas({ template }: NodeCanvasProps) {
  const { nodes, edges } = useMemo(() => {
    // If graph fields missing (should not happen post-migration but safe fallback),
    // project on the client. After Phase 1 deploy this branch is dead code.
    if (!template.graph_nodes || !template.graph_edges) {
      return projectStepsToGraph(template.steps);
    }
    const layout = template.graph_layout ?? {};
    const nodes: Node[] = template.graph_nodes.map((gn: GraphNode) => ({
      id: gn.id,
      type: gn.kind,
      position: layout[gn.id] ?? { x: 0, y: 0 },
      data: {
        label: gn.label,
        tool_name: (gn.config as { tool_name?: string } | undefined)?.tool_name,
      },
    }));
    const edges: Edge[] = template.graph_edges.map((ge: GraphEdge) => ({
      id: ge.id,
      source: ge.source,
      target: ge.target,
    }));
    return { nodes, edges };
  }, [template]);

  return (
    <div style={{ width: '100%', height: '70vh' }} className="rounded-2xl border border-slate-200 bg-white">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={NODE_TYPES}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        fitView
        attributionPosition="bottom-left"
      >
        <Background />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}

// Fallback projection for templates where the migration didn't run yet.
// Mirrors the Postgres helpers in 109-01 but in TypeScript.
function projectStepsToGraph(steps: WorkflowTemplate['steps']): { nodes: Node[]; edges: Edge[] } {
  if (!steps || steps.length === 0) return { nodes: [], edges: [] };
  const nodes: Node[] = [
    { id: 'trigger', type: 'trigger', position: { x: 0, y: 0 }, data: { label: 'Start' } },
    ...steps.map((s, i) => ({
      id: `step-${i}`,
      type: 'agent-action' as const,
      position: { x: 200 * (i + 1), y: 0 },
      data: { label: s.name ?? `Step ${i + 1}`, tool_name: s.tool },
    })),
    { id: 'output', type: 'output', position: { x: 200 * (steps.length + 1), y: 0 }, data: { label: 'Done' } },
  ];
  const edges: Edge[] = [
    { id: 'e-trigger-step-0', source: 'trigger', target: 'step-0' },
    ...steps.slice(0, -1).map((_, i) => ({
      id: `e-step-${i}-step-${i + 1}`,
      source: `step-${i}`,
      target: `step-${i + 1}`,
    })),
    { id: `e-step-${steps.length - 1}-output`, source: `step-${steps.length - 1}`, target: 'output' },
  ];
  return { nodes, edges };
}
```
</task>

<task id="03-05" desc="Create the editor page route">
Create `frontend/src/app/dashboard/workflows/editor/[id]/page.tsx`:

```typescript
'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { PremiumShell } from '@/components/layout/PremiumShell';
import { GatedPage } from '@/components/dashboard/GatedPage';
import DashboardErrorBoundary from '@/components/ui/DashboardErrorBoundary';
import { Breadcrumb } from '@/components/ui/Breadcrumb';
import { NodeCanvas } from '@/components/workflows/editor/NodeCanvas';
import { getWorkflowTemplate, type WorkflowTemplate } from '@/services/workflows';

export default function WorkflowEditorPage() {
  const params = useParams<{ id: string }>();
  const [template, setTemplate] = useState<WorkflowTemplate | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!params?.id || params.id === 'new') {
      // Phase 1 doesn't implement /editor/new — show a friendly placeholder
      setError('Creating new templates from this view will be available in Phase 2.');
      setLoading(false);
      return;
    }
    let cancelled = false;
    getWorkflowTemplate(params.id)
      .then((t) => { if (!cancelled) setTemplate(t); })
      .catch((e) => { if (!cancelled) setError(e?.message ?? 'Failed to load template'); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [params?.id]);

  return (
    <GatedPage featureKey="workflows">
      <DashboardErrorBoundary fallbackTitle="Workflow Editor Error">
        <PremiumShell>
          <div className="mx-auto max-w-7xl p-6">
            <Breadcrumb items={[
              { label: 'Home', href: '/dashboard' },
              { label: 'Workflows', href: '/dashboard/workflows/templates' },
              { label: 'Templates', href: '/dashboard/workflows/templates' },
              { label: template?.name ?? 'Editor' },
            ]} />
            <h1 className="mt-4 text-2xl font-semibold text-slate-900">
              {template?.name ?? 'Workflow Editor'}
            </h1>
            {loading && <p className="text-sm text-slate-500 mt-4">Loading...</p>}
            {error && (
              <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-700">
                {error}
              </div>
            )}
            {template && <div className="mt-6"><NodeCanvas template={template} /></div>}
          </div>
        </PremiumShell>
      </DashboardErrorBoundary>
    </GatedPage>
  );
}
```
</task>

<task id="03-06" desc="Update WorkflowTemplateCard.onEdit handler">
Edit `frontend/src/components/workflows/WorkflowTemplateCard.tsx`. Find the existing onEdit handler. Replace the previously-broken `router.push('/dashboard/workflows/editor/new')` with `router.push(\`/dashboard/workflows/editor/${template.id}\`)`. Verify the button label remains "Edit" — Phase 2 will gate it to actual editing.

In the templates page itself (`frontend/src/app/dashboard/workflows/templates/page.tsx` line 146), the "Create Draft" button currently routes to `/dashboard/workflows/editor/new`. In Phase 1, leave this button in place but accept that clicking it lands on the friendly "Creating new templates... Phase 2" message from the new editor page.
</task>

<task id="03-07" desc="Add component tests">
Create `frontend/src/__tests__/workflows/NodeCanvas.test.tsx`. Use the existing vitest + @testing-library/react patterns:

```typescript
// @vitest-environment jsdom

import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { NodeCanvas } from '@/components/workflows/editor/NodeCanvas';

// Mock React Flow because it requires window measurement APIs jsdom lacks
vi.mock('@xyflow/react', () => ({
  ReactFlow: ({ nodes, edges, children }: any) => (
    <div data-testid="react-flow" data-node-count={nodes.length} data-edge-count={edges.length}>
      {children}
    </div>
  ),
  Background: () => <div data-testid="background" />,
  Controls: () => <div data-testid="controls" />,
  Handle: () => <div />,
  Position: { Left: 'left', Right: 'right' },
}));

describe('NodeCanvas', () => {
  it('renders 6 nodes and 5 edges for a 4-step template', () => {
    const template = {
      id: 't1',
      name: 'Test',
      steps: [],
      graph_nodes: [
        { id: 'trigger', kind: 'trigger', label: 'Start' },
        { id: 'step-0', kind: 'agent-action', label: 's1', config: { tool_name: 't1' } },
        { id: 'step-1', kind: 'agent-action', label: 's2', config: { tool_name: 't2' } },
        { id: 'step-2', kind: 'agent-action', label: 's3', config: { tool_name: 't3' } },
        { id: 'step-3', kind: 'agent-action', label: 's4', config: { tool_name: 't4' } },
        { id: 'output', kind: 'output', label: 'Done' },
      ],
      graph_edges: [
        { id: 'e-trigger-step-0', source: 'trigger', target: 'step-0' },
        { id: 'e-step-0-step-1', source: 'step-0', target: 'step-1' },
        { id: 'e-step-1-step-2', source: 'step-1', target: 'step-2' },
        { id: 'e-step-2-step-3', source: 'step-2', target: 'step-3' },
        { id: 'e-step-3-output', source: 'step-3', target: 'output' },
      ],
      graph_layout: {
        trigger: { x: 0, y: 0 },
        'step-0': { x: 200, y: 0 },
        'step-1': { x: 400, y: 0 },
        'step-2': { x: 600, y: 0 },
        'step-3': { x: 800, y: 0 },
        output: { x: 1000, y: 0 },
      },
    } as any;

    render(<NodeCanvas template={template} />);
    const rf = screen.getByTestId('react-flow');
    expect(rf.getAttribute('data-node-count')).toBe('6');
    expect(rf.getAttribute('data-edge-count')).toBe('5');
  });

  it('falls back to client-side projection when graph fields are absent', () => {
    const template = {
      id: 't2',
      name: 'Fallback',
      steps: [
        { name: 's1', tool: 't1' },
        { name: 's2', tool: 't2' },
      ],
      // graph_nodes/graph_edges/graph_layout deliberately omitted
    } as any;

    render(<NodeCanvas template={template} />);
    const rf = screen.getByTestId('react-flow');
    expect(rf.getAttribute('data-node-count')).toBe('4'); // trigger + 2 steps + output
    expect(rf.getAttribute('data-edge-count')).toBe('3');
  });

  it('renders empty when template has no steps and no graph fields', () => {
    const template = { id: 't3', name: 'Empty', steps: [] } as any;
    render(<NodeCanvas template={template} />);
    const rf = screen.getByTestId('react-flow');
    expect(rf.getAttribute('data-node-count')).toBe('0');
  });
});
```
</task>

</tasks>

<verification>
1. `cd frontend && npm install` succeeds.
2. `cd frontend && npx tsc --noEmit` — no type errors.
3. `cd frontend && npx vitest run src/__tests__/workflows/NodeCanvas.test.tsx` — all 3 tests pass.
4. `cd frontend && npm run dev` — start dev server.
5. Manually visit `http://localhost:3000/dashboard/workflows/editor/{any-existing-template-id}` — graph renders with trigger node on the left, agent-action nodes in the middle, output node on the right, edges connecting them. Pan and zoom work. Nodes are NOT draggable.
6. Manually visit `http://localhost:3000/dashboard/workflows/editor/non-existent-id` — friendly error state, not a JS crash.
7. Visit `/dashboard/workflows/templates`, click "Edit" on any template card — lands on `/editor/{id}` and the graph renders for that specific template.
8. Visit `/dashboard/workflows/editor/new` — friendly "Phase 2" message, not a crash.
</verification>
