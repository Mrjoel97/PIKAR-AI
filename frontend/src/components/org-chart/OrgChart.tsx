'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import React, { useEffect, useCallback, useState, useRef } from 'react';
import ReactFlow, {
    Background,
    Controls,
    Node,
    Edge,
    useNodesState,
    useEdgesState,
    MarkerType
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Loader2, User, Bot } from 'lucide-react';
import AgentInspector, { type OrgNodeData } from './AgentInspector';

const nodeTypes = {
    // We can define custom node types if needed, but default is fine for MVP
};

export function OrgChart() {
    const [loading, setLoading] = useState(true);
    const [selectedAgent, setSelectedAgent] = useState<OrgNodeData | null>(null);

    // Keep a stable ref to the raw org data so the click handler can look up
    // the full node data (including tools, model, capabilities) by id.
    const orgDataRef = useRef<OrgNodeData[]>([]);

    // Initial State - ReactFlow handles this
    const [nodes, setNodes, onNodesChange] = useNodesState([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState([]);

    useEffect(() => {
        fetchOrgData();
    }, []);

    const fetchOrgData = async () => {
        try {
            const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
            const res = await fetch(`${API_URL}/org-chart`);
            const data = await res.json();

            orgDataRef.current = data.nodes;
            layoutGraph(data.nodes);
        } catch (err) {
            console.error('Failed to load org chart', err);
        } finally {
            setLoading(false);
        }
    };

    const layoutGraph = (orgNodes: OrgNodeData[]) => {
        // Simple auto-layout:
        // Position the "Director" (reports_to=None) at Top Center
        // Arrange reporting agents in a row below

        const director = orgNodes.find(n => !n.reports_to || n.type === 'user');
        const employees = orgNodes.filter(n => n.id !== director?.id);

        const newNodes: Node[] = [];
        const newEdges: Edge[] = [];

        // 1. Director Node
        if (director) {
            newNodes.push({
                id: director.id,
                type: 'input',
                data: {
                    label: (
                        <div className="flex flex-col items-center cursor-pointer">
                            <div className="w-12 h-12 bg-indigo-600 rounded-full flex items-center justify-center mb-2 shadow-lg">
                                <User className="text-white w-6 h-6" />
                            </div>
                            <div className="font-bold text-slate-900 dark:text-white">{director.label}</div>
                            <div className="text-xs text-slate-500 uppercase tracking-wider">{director.role}</div>
                            {director.tool_count > 0 && (
                                <div className="mt-1 text-[10px] text-indigo-400 font-medium">
                                    {director.tool_count} tools
                                </div>
                            )}
                        </div>
                    )
                },
                position: { x: 400, y: 50 },
                style: {
                    background: '#fff',
                    border: '1px solid #e2e8f0',
                    borderRadius: '12px',
                    padding: '16px',
                    minWidth: '200px',
                    textAlign: 'center',
                    cursor: 'pointer',
                }
            });
        }

        // 2. Employees (Agents)
        const SPACING_X = 250;
        const START_X = 400 - ((employees.length - 1) * SPACING_X) / 2;

        employees.forEach((emp, index) => {
            newNodes.push({
                id: emp.id,
                type: 'default', // 'output' if no children
                data: {
                    label: (
                        <div className="flex flex-col items-center cursor-pointer">
                            <div className="relative">
                                <div className={`w-10 h-10 rounded-full flex items-center justify-center mb-2 ${
                                    emp.status === 'active'
                                        ? 'bg-emerald-100 dark:bg-emerald-900'
                                        : 'bg-slate-100 dark:bg-slate-700'
                                }`}>
                                    <Bot className={`w-5 h-5 ${
                                        emp.status === 'active'
                                            ? 'text-emerald-600 dark:text-emerald-400'
                                            : 'text-slate-400 dark:text-slate-500'
                                    }`} />
                                </div>
                                <span className="absolute -top-1 -right-1 flex h-3 w-3">
                                    {emp.status === 'active' && (
                                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                                    )}
                                    <span className={`relative inline-flex rounded-full h-3 w-3 ${
                                        emp.status === 'active' ? 'bg-emerald-500' : 'bg-slate-400'
                                    }`}></span>
                                </span>
                            </div>
                            <div className="font-bold text-slate-800 dark:text-slate-100 text-sm">{emp.label}</div>
                            <div className="text-xs text-slate-400">{emp.role}</div>
                            {emp.tool_count > 0 && (
                                <div className="mt-1 text-[10px] text-indigo-400 font-medium">
                                    {emp.tool_count} tools
                                </div>
                            )}
                            {emp.active_workflows > 0 && (
                                <div className="mt-0.5 text-[10px] text-amber-400 font-medium">
                                    {emp.active_workflows} workflow{emp.active_workflows !== 1 ? 's' : ''}
                                </div>
                            )}
                        </div>
                    )
                },
                position: { x: START_X + (index * SPACING_X), y: 250 },
                style: {
                    background: '#fff',
                    border: '1px solid #e2e8f0',
                    borderRadius: '12px',
                    padding: '12px',
                    minWidth: '180px',
                    textAlign: 'center',
                    cursor: 'pointer',
                }
            });

            if (director) {
                newEdges.push({
                    id: `e-${director.id}-${emp.id}`,
                    source: director.id,
                    target: emp.id,
                    type: 'smoothstep',
                    animated: true,
                    style: { stroke: '#94a3b8' },
                    markerEnd: { type: MarkerType.ArrowClosed, color: '#94a3b8' },
                });
            }
        });

        setNodes(newNodes);
        setEdges(newEdges);
    };

    const handleNodeClick = useCallback((_event: React.MouseEvent, node: Node) => {
        const orgNode = orgDataRef.current.find(n => n.id === node.id);
        if (orgNode) {
            setSelectedAgent(orgNode);
        }
    }, []);

    if (loading) {
        return <div className="flex h-full items-center justify-center"><Loader2 className="animate-spin text-indigo-500" /></div>;
    }

    return (
        <div style={{ width: '100%', height: '100%' }}>
            <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onNodeClick={handleNodeClick}
                fitView
                attributionPosition="bottom-right"
            >
                <Background color="#ccc" gap={16} />
                <Controls />
            </ReactFlow>

            <AgentInspector
                agent={selectedAgent}
                onClose={() => setSelectedAgent(null)}
            />
        </div>
    );
}

export default OrgChart;
