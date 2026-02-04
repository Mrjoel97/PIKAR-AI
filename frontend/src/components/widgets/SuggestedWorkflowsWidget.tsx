import React from 'react';
import { WidgetProps } from './WidgetRegistry';
import { WidgetDefinition, SuggestedWorkflowsData, Suggestion } from '@/types/widgets';
import { Sparkles, ArrowRight, Play } from 'lucide-react';

export default function SuggestedWorkflowsWidget({ definition, onAction }: WidgetProps) {
    const data = definition.data as unknown as SuggestedWorkflowsData;
    const suggestions = data?.suggestions || [];

    if (suggestions.length === 0) {
        return (
            <div className="p-6 text-center text-slate-500">
                <Sparkles className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p>No new suggestions yet. Keep using Pikar AI and we'll discover new ways to help you!</p>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-full bg-white dark:bg-slate-900">
            <div className="p-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <Sparkles className="w-5 h-5 text-indigo-500" />
                    <div>
                        <h3 className="font-semibold text-slate-900 dark:text-slate-100">
                            New Ways to Use Pikar
                        </h3>
                        <p className="text-xs text-slate-500">
                            AI-discovered workflows based on your activity
                        </p>
                    </div>
                </div>
                <div className="text-xs font-medium px-2 py-1 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 rounded-full">
                    {suggestions.length} New
                </div>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-3">
                {suggestions.map((suggestion) => (
                    <div
                        key={suggestion.id}
                        className="group p-4 rounded-xl border border-slate-200 dark:border-slate-800 hover:border-indigo-300 dark:hover:border-indigo-700 hover:shadow-sm transition-all bg-slate-50/50 dark:bg-slate-800/50"
                    >
                        <div className="flex items-start justify-between mb-2">
                            <h4 className="font-medium text-slate-900 dark:text-white">
                                {suggestion.suggested_goal}
                            </h4>
                            <span className="text-[10px] uppercase tracking-wider font-semibold text-slate-400">
                                Discovered
                            </span>
                        </div>

                        <p className="text-sm text-slate-600 dark:text-slate-400 mb-3">
                            {suggestion.pattern_description}
                        </p>

                        <div className="flex items-center justify-between mt-3">
                            <span className="text-xs text-slate-500 italic">
                                "{suggestion.suggested_context}"
                            </span>

                            <button
                                onClick={() => onAction?.('activate_workflow', { id: suggestion.id })}
                                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition-colors shadow-sm"
                            >
                                <Play className="w-3 h-3" />
                                Activate Workflow
                            </button>
                        </div>
                    </div>
                ))}
            </div>

            <div className="p-3 bg-slate-50 dark:bg-slate-800/80 text-center border-t border-slate-100 dark:border-slate-800">
                <button className="text-xs text-slate-500 hover:text-indigo-600 flex items-center justify-center gap-1 mx-auto transition-colors">
                    View all discoveries <ArrowRight className="w-3 h-3" />
                </button>
            </div>
        </div>
    );
}
