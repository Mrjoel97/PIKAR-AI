'use client';

import React, { useEffect, useCallback, useState } from 'react';
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

interface OrgNode {
    id: string;
    type: 'user' | 'agent';
    label: string;
    role?: string;
    reports_to?: string;
    status: 'active' | 'offline';
}

const nodeTypes = {
    // We can define custom node types if needed, but default is fine for MVP
};

export function OrgChart() {
    const [loading, setLoading] = useState(true);

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

            layoutGraph(data.nodes);
        } catch (err) {
            console.error('Failed to load org chart', err);
        } finally {
            setLoading(false);
        }
    };

    const layoutGraph = (orgNodes: OrgNode[]) => {
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
                        <div className="flex flex-col items-center">
                            <div className="w-12 h-12 bg-indigo-600 rounded-full flex items-center justify-center mb-2 shadow-lg">
                                <User className="text-white w-6 h-6" />
                            </div>
                            <div className="font-bold text-slate-900 dark:text-white">{director.label}</div>
                            <div className="text-xs text-slate-500 uppercase tracking-wider">{director.role}</div>
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
                    textAlign: 'center'
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
                        <div className="flex flex-col items-center">
                            <div className="relative">
                                <div className="w-10 h-10 bg-emerald-100 dark:bg-emerald-900 rounded-full flex items-center justify-center mb-2">
                                    <Bot className="text-emerald-600 dark:text-emerald-400 w-5 h-5" />
                                </div>
                                <span className="absolute -top-1 -right-1 flex h-3 w-3">
                                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                                    <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
                                </span>
                            </div>
                            <div className="font-bold text-slate-800 dark:text-slate-100 text-sm">{emp.label}</div>
                            <div className="text-xs text-slate-400">{emp.role}</div>
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
                    textAlign: 'center'
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
                fitView
                attributionPosition="bottom-right"
            >
                <Background color="#ccc" gap={16} />
                <Controls />
            </ReactFlow>
        </div>
    );
}

export default OrgChart;
