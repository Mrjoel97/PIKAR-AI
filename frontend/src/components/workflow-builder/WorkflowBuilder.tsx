'use client'
import React, { useState, useCallback } from 'react'
import ReactFlow, { 
  addEdge, 
  Background, 
  Controls, 
  Connection, 
  Edge, 
  Node,
  useNodesState,
  useEdgesState,
  Panel
} from 'reactflow'
import 'reactflow/dist/style.css'
import { Play, Save, Plus, GitBranch, Settings, Layers, Box } from 'lucide-react'
import { createWorkflowTemplate } from '@/services/workflows';
import { useRouter } from 'next/navigation';

const initialNodes: Node[] = [
  { 
    id: '1', 
    position: { x: 250, y: 5 }, 
    data: { label: 'User Input' },
    style: { background: '#6366f1', color: '#fff', borderRadius: '12px', border: 'none', padding: '10px' }
  },
  { 
    id: '2', 
    position: { x: 250, y: 150 }, 
    data: { label: 'ExecutiveAgent' },
    style: { background: '#1e293b', color: '#fff', borderRadius: '12px', border: '2px solid #6366f1', padding: '10px' }
  },
];

const initialEdges: Edge[] = [
  { id: 'e1-2', source: '1', target: '2', animated: true, style: { stroke: '#6366f1' } }
];

export function WorkflowBuilder() {
  const router = useRouter();
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)
  const [isSaving, setIsSaving] = useState(false)

  const onConnect = useCallback((params: Connection) => setEdges((eds) => addEdge({ ...params, animated: true, style: { stroke: '#6366f1' } }, eds)), [setEdges]);

  const addAgent = (type: string) => {
    const id = (nodes.length + 1).toString();
    const newNode: Node = {
      id,
      position: { x: Math.random() * 400, y: Math.random() * 400 },
      data: { label: type },
      style: { background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '12px', padding: '10px' }
    };
    setNodes((nds) => nds.concat(newNode));
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      const steps = nodes.map((node, idx) => ({
        name: String((node.data as { label?: string })?.label || `Step ${idx + 1}`),
        tool: 'create_task',
        description: `Generated from visual workflow node ${idx + 1}`,
        required_approval: false,
      }));
      const created = await createWorkflowTemplate({
        name: 'Workflow Builder Draft',
        description: `Generated from visual workflow builder (${nodes.length} nodes, ${edges.length} connections)`,
        category: 'custom',
        phases: [{ name: 'Builder Flow', steps }],
        is_generated: true,
      });
      router.push(`/dashboard/workflows/editor/${created.id}`);
    } catch (error) {
      console.error('Failed to save workflow draft', error);
      alert('Failed to save workflow');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-800 h-[700px] flex flex-col overflow-hidden">
      {/* Toolbar */}
      <div className="p-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50 flex justify-between items-center">
        <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
                <div className="p-2 bg-indigo-600 rounded-lg text-white">
                    <GitBranch size={18} />
                </div>
                <h2 className="font-bold text-slate-800 dark:text-slate-100">Workflow Designer</h2>
            </div>
            <div className="h-6 w-[1px] bg-slate-200 dark:bg-slate-700 mx-2" />
            <div className="flex gap-2">
                <button 
                    onClick={() => addAgent('SpecialistAgent')}
                    className="flex items-center gap-2 px-3 py-1.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-xs font-semibold hover:bg-slate-50 transition"
                >
                    <Plus size={14} /> Add Agent
                </button>
                <button className="flex items-center gap-2 px-3 py-1.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-xs font-semibold hover:bg-slate-50 transition">
                    <Layers size={14} /> Add Logic
                </button>
            </div>
        </div>
        <div className="flex gap-3">
            <button className="flex items-center gap-2 px-4 py-2 bg-emerald-50 text-emerald-600 rounded-xl text-sm font-bold hover:bg-emerald-100 transition">
                <Play size={16} /> Run
            </button>
            <button 
                onClick={handleSave}
                disabled={isSaving}
                className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-xl text-sm font-bold hover:bg-indigo-700 transition shadow-lg shadow-indigo-200 dark:shadow-none"
            >
                <Save size={16} /> {isSaving ? 'Saving...' : 'Save'}
            </button>
        </div>
      </div>

      <div className="flex-1 relative">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          fitView
        >
          <Background color="#cbd5e1" gap={20} />
          <Controls />
          <Panel position="top-right" className="bg-white/80 dark:bg-slate-900/80 backdrop-blur p-4 rounded-xl border border-slate-200 dark:border-slate-800 shadow-lg">
            <h4 className="text-xs font-bold text-slate-400 uppercase mb-3">Components</h4>
            <div className="space-y-2">
                <div className="flex items-center gap-2 text-xs font-medium text-slate-600 dark:text-slate-300">
                    <Box size={14} className="text-indigo-500" /> Executive Node
                </div>
                <div className="flex items-center gap-2 text-xs font-medium text-slate-600 dark:text-slate-300">
                    <Box size={14} className="text-emerald-500" /> Task Node
                </div>
                <div className="flex items-center gap-2 text-xs font-medium text-slate-600 dark:text-slate-300">
                    <Box size={14} className="text-amber-500" /> Data Source
                </div>
            </div>
          </Panel>
        </ReactFlow>
      </div>

      {/* Footer / Status */}
      <div className="p-3 bg-slate-50 dark:bg-slate-800/50 border-t border-slate-200 dark:border-slate-800 flex justify-between items-center px-6">
        <div className="flex gap-4">
            <span className="text-[10px] font-bold text-slate-400 uppercase">Nodes: {nodes.length}</span>
            <span className="text-[10px] font-bold text-slate-400 uppercase">Connections: {edges.length}</span>
        </div>
        <div className="flex items-center gap-2">
            <Settings size={14} className="text-slate-400" />
            <span className="text-[10px] font-medium text-slate-500">Auto-layout enabled</span>
        </div>
      </div>
    </div>
  )
}
