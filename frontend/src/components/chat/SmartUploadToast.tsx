'use client';

import React from 'react';
import {
  FileText,
  Image,
  FileSpreadsheet,
  File as FileIcon,
  Database,
  X,
  BookOpen,
  Search,
  Loader2,
} from 'lucide-react';

export interface SmartUploadResult {
  filename: string;
  content_type: string;
  detected_type: string;
  summary: string;
  size_bytes: number;
  suggested_actions: string[];
}

interface SmartUploadToastProps {
  result: SmartUploadResult;
  onAddToVault: () => void;
  onAnalyzeNow: () => void;
  onDismiss: () => void;
  isProcessing?: boolean;
}

function getDetectedTypeIcon(detectedType: string) {
  switch (detectedType) {
    case 'document':
      return <FileText size={20} className="text-red-500" />;
    case 'spreadsheet':
      return <FileSpreadsheet size={20} className="text-green-500" />;
    case 'image':
      return <Image size={20} className="text-blue-500" />;
    case 'data':
      return <Database size={20} className="text-purple-500" />;
    default:
      return <FileIcon size={20} className="text-slate-500" />;
  }
}

function getDetectedTypeLabel(detectedType: string): string {
  switch (detectedType) {
    case 'document':
      return 'Document';
    case 'spreadsheet':
      return 'Spreadsheet';
    case 'image':
      return 'Image';
    case 'data':
      return 'Data File';
    default:
      return 'File';
  }
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function SmartUploadToast({
  result,
  onAddToVault,
  onAnalyzeNow,
  onDismiss,
  isProcessing = false,
}: SmartUploadToastProps) {
  return (
    <div className="mx-3 mb-2 bg-white border border-slate-200 rounded-xl shadow-lg overflow-hidden animate-in slide-in-from-bottom-2 duration-300">
      {/* Header row */}
      <div className="flex items-start gap-3 p-3 pb-2">
        <div className="flex-shrink-0 p-2 bg-slate-50 rounded-lg">
          {getDetectedTypeIcon(result.detected_type)}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h4 className="text-sm font-semibold text-slate-800 truncate">
              {result.filename}
            </h4>
            <span className="flex-shrink-0 text-[10px] font-medium text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">
              {getDetectedTypeLabel(result.detected_type)}
            </span>
            <span className="flex-shrink-0 text-[10px] text-slate-400">
              {formatBytes(result.size_bytes)}
            </span>
          </div>

          {/* Summary preview */}
          <p className="text-xs text-slate-600 mt-1 line-clamp-2 leading-relaxed">
            {result.summary}
          </p>
        </div>

        <button
          onClick={onDismiss}
          disabled={isProcessing}
          className="flex-shrink-0 p-1 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded transition-colors disabled:opacity-50"
          title="Dismiss"
        >
          <X size={14} />
        </button>
      </div>

      {/* Action buttons */}
      <div className="flex items-center gap-2 px-3 pb-3">
        <button
          onClick={onAddToVault}
          disabled={isProcessing}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-teal-700 bg-teal-50 border border-teal-200 rounded-lg hover:bg-teal-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isProcessing ? (
            <Loader2 size={14} className="animate-spin" />
          ) : (
            <BookOpen size={14} />
          )}
          Add to Knowledge Vault
        </button>

        <button
          onClick={onAnalyzeNow}
          disabled={isProcessing}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-indigo-700 bg-indigo-50 border border-indigo-200 rounded-lg hover:bg-indigo-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isProcessing ? (
            <Loader2 size={14} className="animate-spin" />
          ) : (
            <Search size={14} />
          )}
          Analyze Now
        </button>
      </div>
    </div>
  );
}
