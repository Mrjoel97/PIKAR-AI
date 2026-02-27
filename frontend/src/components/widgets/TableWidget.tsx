'use client'
import React, { useState } from 'react';
import { WidgetDefinition, TableDataDefinition, ColumnDefinition, ActionDefinition } from '@/types/widgets';
import { Eye, Trash2, Edit, MoreHorizontal, ArrowUpDown } from 'lucide-react';

interface TableWidgetProps {
    definition: WidgetDefinition;
    onAction?: (action: string, data: any) => void;
}

export default function TableWidget({ definition, onAction }: TableWidgetProps) {
    const data = definition.data as unknown as TableDataDefinition;
    const { columns = [], rows = [], actions = [] } = data;

    const [sortConfig, setSortConfig] = useState<{ key: string; direction: 'asc' | 'desc' } | null>(null);

    const sortedRows = React.useMemo(() => {
        if (!sortConfig) return rows;
        const { key, direction } = sortConfig;

        return [...rows].sort((a, b) => {
            const valA = a[key];
            const valB = b[key];

            if (valA === valB) return 0;
            if (valA === null || valA === undefined) return 1;
            if (valB === null || valB === undefined) return -1;

            if (valA < valB) return direction === 'asc' ? -1 : 1;
            if (valA > valB) return direction === 'asc' ? 1 : -1;
            return 0;
        });
    }, [rows, sortConfig]);

    const handleSort = (key: string) => {
        let direction: 'asc' | 'desc' = 'asc';
        if (sortConfig && sortConfig.key === key && sortConfig.direction === 'asc') {
            direction = 'desc';
        }
        setSortConfig({ key, direction });
    };

    const handleAction = (actionName: string, row: any) => {
        if (onAction) {
            onAction('table_action', {
                action: actionName,
                rowId: row.id,
                row
            });
        }
    };

    const getIcon = (name: string) => {
        switch (name.toLowerCase()) {
            case 'view': return <Eye size={16} />;
            case 'delete': return <Trash2 size={16} />;
            case 'edit': return <Edit size={16} />;
            default: return <MoreHorizontal size={16} />;
        }
    };

    return (
        <div className="w-full overflow-hidden bg-white dark:bg-slate-800 rounded-lg shadow-sm border border-slate-200 dark:border-slate-700">
            <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
                <h3 className="font-semibold text-slate-800 dark:text-slate-200">{definition.title}</h3>
            </div>

            <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                    <thead className="text-xs text-slate-500 uppercase bg-slate-50 dark:bg-slate-700 dark:text-slate-400">
                        <tr>
                            {columns.map((col) => (
                                <th
                                    key={col.key}
                                    scope="col"
                                    className="px-4 py-3 cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-600 transition-colors"
                                    onClick={() => handleSort(col.key)}
                                >
                                    <div className="flex items-center gap-1">
                                        {col.label}
                                        <ArrowUpDown size={12} className="opacity-50" />
                                    </div>
                                </th>
                            ))}
                            {actions.length > 0 && (
                                <th scope="col" className="px-4 py-3 text-right">Actions</th>
                            )}
                        </tr>
                    </thead>
                    <tbody>
                        {sortedRows.length > 0 ? (
                            sortedRows.map((row, idx) => (
                                <tr
                                    key={String(row.id || idx)}
                                    className="border-b dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors"
                                >
                                    {columns.map((col) => (
                                        <td key={`${row.id}-${col.key}`} className="px-4 py-3 font-medium text-slate-900 dark:text-white whitespace-nowrap">
                                            {row[col.key]}
                                        </td>
                                    ))}
                                    {actions.length > 0 && (
                                        <td className="px-4 py-3 text-right">
                                            <div className="flex justify-end gap-2">
                                                {actions.map((action) => (
                                                    <button
                                                        key={action.name}
                                                        onClick={() => handleAction(action.name, row)}
                                                        className="p-1.5 text-slate-500 hover:text-blue-600 dark:text-slate-400 dark:hover:text-blue-400 rounded-md hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                                                        title={action.label}
                                                    >
                                                        {getIcon(action.name)}
                                                        <span className="sr-only">{action.label}</span>
                                                    </button>
                                                ))}
                                            </div>
                                        </td>
                                    )}
                                </tr>
                            ))
                        ) : (
                            <tr>
                                <td colSpan={columns.length + (actions.length > 0 ? 1 : 0)} className="px-4 py-8 text-center text-slate-500 dark:text-slate-400">
                                    No records found
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
