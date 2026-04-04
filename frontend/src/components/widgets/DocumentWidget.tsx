// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * DocumentWidget - Renders a document download card in the chat UI.
 *
 * Displays file icon, title, type badge, size, and download button for
 * agent-generated documents (PDF, PPTX, CSV).
 */

import { Download, FileSpreadsheet, FileText } from 'lucide-react';
import type { WidgetProps } from './WidgetRegistry';
import type { DocumentWidgetData } from '@/types/widgets';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const FILE_TYPE_CONFIG: Record<string, { label: string; color: string; bgColor: string }> = {
    pdf: { label: 'PDF', color: 'text-red-600 dark:text-red-400', bgColor: 'bg-red-50 dark:bg-red-900/30' },
    pptx: { label: 'PPTX', color: 'text-orange-600 dark:text-orange-400', bgColor: 'bg-orange-50 dark:bg-orange-900/30' },
    csv: { label: 'CSV', color: 'text-green-600 dark:text-green-400', bgColor: 'bg-green-50 dark:bg-green-900/30' },
};

function formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB'];
    const k = 1024;
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    const size = bytes / Math.pow(k, i);
    return `${size.toFixed(i > 0 ? 1 : 0)} ${units[i]}`;
}

function FileIcon({ fileType }: { fileType: string }) {
    const config = FILE_TYPE_CONFIG[fileType];
    const colorClass = config?.color ?? 'text-slate-500';

    if (fileType === 'csv' || fileType === 'pptx') {
        return <FileSpreadsheet className={`w-8 h-8 ${colorClass}`} />;
    }
    return <FileText className={`w-8 h-8 ${colorClass}`} />;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function DocumentWidget({ definition }: WidgetProps) {
    const data = definition.data as unknown as DocumentWidgetData;
    const { documentUrl, title, fileType, sizeBytes, templateName } = data;

    const config = FILE_TYPE_CONFIG[fileType] ?? {
        label: fileType?.toUpperCase() ?? 'FILE',
        color: 'text-slate-600 dark:text-slate-400',
        bgColor: 'bg-slate-50 dark:bg-slate-800',
    };

    function handleDownload() {
        window.open(documentUrl, '_blank', 'noopener,noreferrer');
    }

    return (
        <div className="flex items-center gap-4 p-4 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/60 shadow-sm hover:shadow-md transition-shadow">
            {/* File icon */}
            <div className={`flex-shrink-0 flex items-center justify-center w-12 h-12 rounded-lg ${config.bgColor}`}>
                <FileIcon fileType={fileType} />
            </div>

            {/* Title, badge, size */}
            <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-slate-800 dark:text-slate-100 truncate">
                    {title}
                </p>
                <div className="flex items-center gap-2 mt-1">
                    <span className={`inline-block px-1.5 py-0.5 text-[10px] font-bold uppercase rounded ${config.bgColor} ${config.color}`}>
                        {config.label}
                    </span>
                    <span className="text-xs text-slate-500 dark:text-slate-400">
                        {formatFileSize(sizeBytes)}
                    </span>
                    {templateName && (
                        <span className="text-xs text-slate-400 dark:text-slate-500 truncate">
                            {templateName.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                        </span>
                    )}
                </div>
            </div>

            {/* Download button */}
            <button
                onClick={handleDownload}
                className="flex-shrink-0 flex items-center justify-center w-10 h-10 rounded-lg bg-indigo-50 dark:bg-indigo-900/30 hover:bg-indigo-100 dark:hover:bg-indigo-800/40 transition-colors"
                aria-label={`Download ${title}`}
                title="Download"
            >
                <Download className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
            </button>
        </div>
    );
}
