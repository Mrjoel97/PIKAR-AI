'use client';

import React from 'react';
import {
    Lightbulb,
    Target,
    FlaskConical,
    Hammer,
    Rocket,
    CheckCircle2,
    Play,
} from 'lucide-react';

export type InitiativePhase = 'ideation' | 'validation' | 'prototype' | 'build' | 'scale';

const PHASES: { key: InitiativePhase; label: string; icon: React.ReactNode; color: string; bgColor: string }[] = [
    { key: 'ideation', label: 'Ideation & Empathy', icon: <Lightbulb size={20} />, color: 'text-amber-600', bgColor: 'bg-amber-50 border-amber-200' },
    { key: 'validation', label: 'Validation & Research', icon: <Target size={20} />, color: 'text-blue-600', bgColor: 'bg-blue-50 border-blue-200' },
    { key: 'prototype', label: 'Prototype & Test', icon: <FlaskConical size={20} />, color: 'text-purple-600', bgColor: 'bg-purple-50 border-purple-200' },
    { key: 'build', label: 'Build Product/Service', icon: <Hammer size={20} />, color: 'text-indigo-600', bgColor: 'bg-indigo-50 border-indigo-200' },
    { key: 'scale', label: 'Scale Business', icon: <Rocket size={20} />, color: 'text-emerald-600', bgColor: 'bg-emerald-50 border-emerald-200' },
];

const PHASE_ACTIVITIES: Record<InitiativePhase, string[]> = {
    ideation: [
        'Define the core problem you are solving',
        'Identify your target audience and their pain points',
        'Create an empathy map for your ideal customer',
        'Brainstorm at least 10 potential solutions',
        'Narrow down to the top 3 most viable ideas',
    ],
    validation: [
        'Conduct market research on the opportunity',
        'Analyze 3-5 competitors in the space',
        'Interview 10+ potential customers',
        'Assess technical and business feasibility',
        'Document key findings and assumptions',
    ],
    prototype: [
        'Create an MVP specification document',
        'Build a basic prototype or mockup',
        'Test with 5-10 users and collect feedback',
        'Iterate based on user feedback',
        'Define success metrics for the prototype',
    ],
    build: [
        'Create a detailed project plan with tasks',
        'Allocate resources and set timelines',
        'Build the core product/service features',
        'Set up quality assurance and testing',
        'Prepare for launch with marketing materials',
    ],
    scale: [
        'Define your growth strategy',
        'Launch marketing and acquisition campaigns',
        'Monitor key metrics and KPIs',
        'Analyze and fix bottlenecks',
        'Plan next iteration and expansion',
    ],
};

export interface InitiativePhaseTrackerProps {
    phase: InitiativePhase;
    phaseProgress?: Record<string, number>;
    status: string;
    onAdvancePhase?: () => void | Promise<void>;
    updating?: boolean;
    /** Template phase steps (from initiative metadata) for current phase */
    templatePhaseSteps?: string[];
    compact?: boolean;
}

export function InitiativePhaseTracker({
    phase,
    phaseProgress = {},
    status,
    onAdvancePhase,
    updating = false,
    templatePhaseSteps,
    compact = false,
}: InitiativePhaseTrackerProps) {
    const currentPhaseIdx = PHASES.findIndex((p) => p.key === phase);
    const activities = templatePhaseSteps?.length
        ? templatePhaseSteps
        : (PHASE_ACTIVITIES[phase] || []);

    return (
        <div className="bg-white rounded-3xl border border-slate-100 shadow-sm p-6 sm:p-8">
            <h2 className="text-lg font-semibold text-slate-800 mb-6">Initiative Framework</h2>

            {/* Horizontal stepper */}
            <div className={`flex items-center justify-between overflow-x-auto pb-2 ${compact ? 'mb-4' : 'mb-8'}`}>
                {PHASES.map((p, idx) => {
                    const phaseProgressVal = phaseProgress[p.key] ?? 0;
                    const isCurrent = phase === p.key;
                    const isCompleted = phaseProgressVal >= 100;
                    const isPast = idx < currentPhaseIdx;

                    return (
                        <React.Fragment key={p.key}>
                            <div className="flex flex-col items-center gap-2 min-w-[80px]">
                                <div
                                    className={`w-12 h-12 rounded-2xl flex items-center justify-center border-2 transition-all ${
                                        isCompleted || isPast
                                            ? 'bg-emerald-50 border-emerald-300 text-emerald-600'
                                            : isCurrent
                                            ? `${p.bgColor} ${p.color} ring-2 ring-offset-2 ring-slate-200`
                                            : 'bg-slate-50 border-slate-200 text-slate-400'
                                    }`}
                                >
                                    {isCompleted || isPast ? <CheckCircle2 size={20} /> : p.icon}
                                </div>
                                <div className="text-center">
                                    <p
                                        className={`text-xs font-semibold ${
                                            isCurrent ? p.color : isCompleted || isPast ? 'text-emerald-600' : 'text-slate-400'
                                        }`}
                                    >
                                        {p.label}
                                    </p>
                                    <p className="text-[10px] text-slate-400">{phaseProgressVal}%</p>
                                </div>
                            </div>
                            {idx < PHASES.length - 1 && (
                                <div className="flex-1 h-0.5 mx-1 min-w-[20px]">
                                    <div
                                        className={`h-full rounded-full ${
                                            isPast || isCompleted ? 'bg-emerald-300' : 'bg-slate-200'
                                        }`}
                                    />
                                </div>
                            )}
                        </React.Fragment>
                    );
                })}
            </div>

            {/* Current phase detail */}
            {status !== 'completed' && (
                <div
                    className={`rounded-2xl border p-6 ${
                        PHASES[currentPhaseIdx]?.bgColor || 'bg-slate-50 border-slate-200'
                    }`}
                >
                    <div className="flex items-start justify-between gap-4 mb-4">
                        <div className="flex items-center gap-3">
                            <div className={PHASES[currentPhaseIdx]?.color || 'text-slate-600'}>
                                {PHASES[currentPhaseIdx]?.icon}
                            </div>
                            <div>
                                <h3 className="text-base font-semibold text-slate-800">
                                    Phase {currentPhaseIdx + 1}: {PHASES[currentPhaseIdx]?.label}
                                </h3>
                                <p className="text-xs text-slate-500">Current phase activities and tasks</p>
                            </div>
                        </div>

                        {onAdvancePhase && (
                            <button
                                onClick={onAdvancePhase}
                                disabled={updating}
                                className="flex items-center gap-1.5 px-4 py-2 bg-white text-slate-700 rounded-xl text-sm font-semibold border border-slate-200 hover:bg-slate-50 transition-colors disabled:opacity-50 shrink-0"
                            >
                                {updating ? (
                                    <div className="animate-spin rounded-full h-4 w-4 border-2 border-slate-400 border-t-transparent" />
                                ) : currentPhaseIdx < PHASES.length - 1 ? (
                                    <>
                                        <Play size={14} />
                                        Advance to Next Phase
                                    </>
                                ) : (
                                    <>
                                        <CheckCircle2 size={14} />
                                        Complete Initiative
                                    </>
                                )}
                            </button>
                        )}
                    </div>

                    {!compact && (
                        <div className="space-y-2">
                            {activities.map((activity, i) => (
                                <div
                                    key={i}
                                    className="flex items-start gap-2.5 px-3 py-2 bg-white/60 rounded-xl"
                                >
                                    <div className="w-5 h-5 rounded-full border-2 border-slate-300 shrink-0 mt-0.5" />
                                    <span className="text-sm text-slate-700">{activity}</span>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {status === 'completed' && (
                <div className="bg-emerald-50 rounded-2xl border border-emerald-200 p-8 text-center">
                    <CheckCircle2 size={48} className="text-emerald-500 mx-auto mb-4" />
                    <h3 className="text-xl font-semibold text-emerald-700 mb-2">Initiative Completed!</h3>
                    <p className="text-sm text-emerald-600">All 5 phases have been successfully completed.</p>
                </div>
            )}
        </div>
    );
}

export default InitiativePhaseTracker;
