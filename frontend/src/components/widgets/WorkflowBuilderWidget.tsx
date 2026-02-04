/**
 * Workflow Builder Widget
 * 
 * Wrapper around the main WorkflowBuilder component for inline chat display.
 * Used when agent responds to workflow creation/editing requests.
 */

import React from 'react';
import { WidgetProps } from './WidgetRegistry';
import { WidgetDefinition, WorkflowBuilderData, WorkflowNode, WorkflowEdge } from '@/types/widgets';

// Import the existing WorkflowBuilder component
// Using dynamic import to avoid circular dependencies
const WorkflowBuilder = React.lazy(() =>
    import('@/components/workflow-builder/WorkflowBuilder').then(mod => ({
        default: mod.WorkflowBuilder
    }))
);

// =============================================================================
// Data Types
// =============================================================================


// =============================================================================
// Main Component
// =============================================================================

export default function WorkflowBuilderWidget({ definition, onAction }: WidgetProps) {
    const data = definition.data as unknown as WorkflowBuilderData;

    // For now, render a simplified placeholder since the full WorkflowBuilder
    // uses ReactFlow which needs specific container sizing
    const nodes = data?.nodes ?? [];
    const edges = data?.edges ?? [];

    const handleSave = () => {
        onAction?.('save_workflow', { nodes, edges });
    };

    const handleExpand = () => {
        onAction?.('expand_workflow', { nodes, edges });
    };

    return (
        <div className="space-y-4">
            {/* Workflow Preview */}
            <div className="bg-slate-50 dark:bg-slate-800/50 rounded-lg p-4 border-2 border-dashed border-slate-200 dark:border-slate-700">
                <div className="text-center text-sm text-slate-500 dark:text-slate-400 mb-3">
                    Workflow: {definition.title}
                </div>

                {/* Simple node visualization */}
                <div className="flex flex-col items-center gap-2">
                    {nodes.map((node, index) => (
                        <React.Fragment key={node.id}>
                            <div className="px-4 py-2 bg-white dark:bg-slate-700 rounded-lg border border-slate-200 dark:border-slate-600 shadow-sm">
                                <span className="text-sm font-medium text-slate-700 dark:text-slate-200">
                                    {node.data.label}
                                </span>
                            </div>
                            {index < nodes.length - 1 && (
                                <div className="w-0.5 h-4 bg-indigo-500"></div>
                            )}
                        </React.Fragment>
                    ))}

                    {nodes.length === 0 && (
                        <p className="text-slate-400 text-sm py-4">
                            Empty workflow - add nodes to get started
                        </p>
                    )}
                </div>
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-2">
                <button
                    onClick={handleExpand}
                    className="px-3 py-1.5 text-sm font-medium text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 rounded-lg transition-colors"
                >
                    Open Full Editor
                </button>
                <button
                    onClick={handleSave}
                    className="px-3 py-1.5 text-sm font-medium bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
                >
                    Save Workflow
                </button>
            </div>
        </div>
    );
}
