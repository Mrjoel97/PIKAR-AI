'use client';

import React, { useEffect, useState } from 'react';
import { Play, Pause, Activity, RefreshCw } from 'lucide-react';

interface Department {
    id: string;
    name: string;
    type: string;
    status: 'RUNNING' | 'PAUSED' | 'ERROR';
    state: any;
    last_heartbeat: string;
}

export default function DepartmentsPage() {
    const [departments, setDepartments] = useState<Department[]>([]);
    const [loading, setLoading] = useState(true);
    const [ticking, setTicking] = useState(false);

    const fetchDepartments = async () => {
        try {
            const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
            const res = await fetch(`${API_URL}/departments`);
            const data = await res.json();
            setDepartments(data);
        } catch (error) {
            console.error(error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchDepartments();
        const interval = setInterval(fetchDepartments, 5000); // Poll every 5s
        return () => clearInterval(interval);
    }, []);

    const toggleStatus = async (id: string) => {
        try {
            const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
            await fetch(`${API_URL}/departments/${id}/toggle`, { method: 'POST' });
            fetchDepartments();
        } catch (error) {
            console.error(error);
        }
    };

    const manualTick = async () => {
        setTicking(true);
        try {
            const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
            await fetch(`${API_URL}/departments/tick`, { method: 'POST' });
            fetchDepartments();
        } catch (error) {
            console.error(error);
        } finally {
            setTicking(false);
        }
    };

    if (loading) return <div className="p-8 text-center">Loading Departments...</div>;

    return (
        <div className="min-h-screen bg-slate-50 dark:bg-slate-900 p-8">
            <div className="max-w-4xl mx-auto">
                <div className="flex items-center justify-between mb-8">
                    <div>
                        <h1 className="text-3xl font-bold text-slate-800 dark:text-white">Autonomous Departments</h1>
                        <p className="text-slate-500">Manage your 24/7 AI workforce.</p>
                    </div>
                    <button
                        onClick={manualTick}
                        disabled={ticking}
                        className="flex items-center gap-2 px-4 py-2 bg-slate-200 dark:bg-slate-700 rounded-lg hover:bg-slate-300 transition"
                    >
                        <RefreshCw size={18} className={ticking ? "animate-spin" : ""} />
                        Force Heartbeat
                    </button>
                </div>

                <div className="grid grid-cols-1 gap-6">
                    {departments.map(dept => (
                        <div key={dept.id} className="bg-white dark:bg-slate-800 rounded-xl shadow-lg border border-slate-200 dark:border-slate-700 overflow-hidden">
                            <div className="p-6 flex items-center justify-between border-b border-slate-100 dark:border-slate-700">
                                <div className="flex items-center gap-4">
                                    <div className={`w-3 h-3 rounded-full ${dept.status === 'RUNNING' ? 'bg-green-500 animate-pulse' : 'bg-amber-500'}`}></div>
                                    <div>
                                        <h2 className="text-xl font-bold text-slate-900 dark:text-white">{dept.name}</h2>
                                        <span className="text-xs font-mono text-slate-400 bg-slate-100 dark:bg-slate-900 px-2 py-1 rounded">TYPE: {dept.type}</span>
                                    </div>
                                </div>
                                <button
                                    onClick={() => toggleStatus(dept.id)}
                                    className={`flex items-center gap-2 px-4 py-2 rounded-lg font-semibold transition ${dept.status === 'RUNNING'
                                            ? 'bg-amber-100 text-amber-700 hover:bg-amber-200'
                                            : 'bg-green-100 text-green-700 hover:bg-green-200'
                                        }`}
                                >
                                    {dept.status === 'RUNNING' ? <Pause size={18} /> : <Play size={18} />}
                                    {dept.status === 'RUNNING' ? 'Pause Operations' : 'Start Operations'}
                                </button>
                            </div>

                            <div className="p-6 bg-slate-50 dark:bg-slate-900/50">
                                <div className="grid grid-cols-2 gap-8">
                                    <div>
                                        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-3">Live State</h3>
                                        <pre className="text-xs font-mono bg-slate-900 text-green-400 p-4 rounded-lg overflow-x-auto">
                                            {JSON.stringify(dept.state, null, 2)}
                                        </pre>
                                    </div>
                                    <div>
                                        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-3">Activity Log</h3>
                                        <div className="flex items-start gap-3 text-sm text-slate-600 dark:text-slate-300">
                                            <Activity size={16} className="mt-1 text-indigo-500" />
                                            <div>
                                                <p>{dept.state.last_activity || "No activity yet."}</p>
                                                <p className="text-xs text-slate-400 mt-1">Last Heartbeat: {new Date(dept.last_heartbeat).toLocaleTimeString()}</p>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    ))}

                    {departments.length === 0 && (
                        <div className="text-center py-12 text-slate-400">
                            No departments configured. Check database seeds.
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
