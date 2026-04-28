'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import { useCallback, useRef, useState } from 'react';
import { Upload } from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/** All agent scope options available in the selector. */
const AGENT_SCOPES = [
  { value: '', label: 'Global (all agents)' },
  { value: 'financial', label: 'Financial' },
  { value: 'content', label: 'Content' },
  { value: 'marketing', label: 'Marketing' },
  { value: 'strategic', label: 'Strategic' },
  { value: 'sales', label: 'Sales' },
  { value: 'operations', label: 'Operations' },
  { value: 'hr', label: 'HR' },
  { value: 'compliance', label: 'Compliance' },
  { value: 'customer_support', label: 'Customer Support' },
  { value: 'data', label: 'Data' },
] as const;

/** MIME types and file extensions accepted by the upload panel. */
const ACCEPTED_MIME =
  'application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,text/plain,text/markdown,text/csv,image/png,image/jpeg,image/svg+xml,video/mp4,video/quicktime,video/webm,.pdf,.docx,.xlsx,.csv,.txt,.md,.png,.jpg,.jpeg,.svg,.mp4,.mov,.webm';

type UploadStatus = 'idle' | 'uploading' | 'processing' | 'done' | 'error';

interface UploadPanelProps {
  /** Supabase auth token — attached to Authorization header. */
  token: string;
  /** Called after a successful upload so parent can refresh data. */
  onUploadComplete: () => void;
}

/**
 * UploadPanel provides a drag-and-drop / click-to-browse file upload area
 * with an agent scope selector and progress feedback.
 */
export function UploadPanel({ token, onUploadComplete }: UploadPanelProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [agentScope, setAgentScope] = useState('');
  const [status, setStatus] = useState<UploadStatus>('idle');
  const [statusMessage, setStatusMessage] = useState('');
  const [isDragOver, setIsDragOver] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFiles = useCallback((files: FileList | null) => {
    if (!files || files.length === 0) return;
    setSelectedFile(files[0]);
    setStatus('idle');
    setStatusMessage('');
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      handleFiles(e.dataTransfer.files);
    },
    [handleFiles],
  );

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      handleFiles(e.target.files);
    },
    [handleFiles],
  );

  const handleUpload = useCallback(async () => {
    if (!selectedFile) return;

    setStatus('uploading');
    setStatusMessage('Uploading…');

    const formData = new FormData();
    formData.append('file', selectedFile);
    if (agentScope) {
      formData.append('agent_scope', agentScope);
    }
    formData.append('uploaded_by', 'admin');

    try {
      const res = await fetch(`${API_URL}/admin/knowledge/upload`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      if (!res.ok) {
        const text = await res.text();
        setStatus('error');
        setStatusMessage(`Upload failed (${res.status}): ${text}`);
        return;
      }

      // 202 = video queued for background processing
      if (res.status === 202) {
        setStatus('done');
        setStatusMessage(
          'Video queued for background processing. It will appear in the table once complete.',
        );
      } else {
        setStatus('processing');
        setStatusMessage('Processing complete. Knowledge base updated.');
        // Brief delay so user reads the message before reset
        setTimeout(() => {
          setStatus('done');
        }, 800);
      }

      // Reset form after success
      setSelectedFile(null);
      setAgentScope('');
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      onUploadComplete();
    } catch {
      setStatus('error');
      setStatusMessage('Upload failed. Check that the backend is running.');
    }
  }, [selectedFile, agentScope, token, onUploadComplete]);

  const isUploading = status === 'uploading' || status === 'processing';

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg p-5 space-y-4">
      <h2 className="text-sm font-semibold text-gray-200 uppercase tracking-wide">
        Upload Knowledge File
      </h2>

      {/* Drop zone */}
      <div
        role="button"
        tabIndex={0}
        onClick={() => fileInputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') fileInputRef.current?.click();
        }}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
          isDragOver
            ? 'border-indigo-500 bg-indigo-500/10'
            : 'border-gray-600 hover:border-gray-500 hover:bg-gray-700/30'
        }`}
        aria-label="Drop a file here or click to browse"
      >
        <Upload
          size={24}
          className={`mx-auto mb-2 ${isDragOver ? 'text-indigo-400' : 'text-gray-500'}`}
        />
        {selectedFile ? (
          <p className="text-sm text-gray-200 font-medium">{selectedFile.name}</p>
        ) : (
          <>
            <p className="text-sm text-gray-300">
              Drag and drop a file, or{' '}
              <span className="text-indigo-400 font-medium">browse</span>
            </p>
            <p className="text-xs text-gray-500 mt-1">
              PDF, DOCX, XLSX, CSV, TXT, MD, PNG, JPG, SVG, MP4, MOV, WEBM
            </p>
          </>
        )}
      </div>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept={ACCEPTED_MIME}
        onChange={handleFileInput}
        className="hidden"
        aria-hidden="true"
      />

      {/* Agent scope selector */}
      <div>
        <label
          htmlFor="knowledge-agent-scope"
          className="block text-xs font-medium text-gray-400 mb-1"
        >
          Agent Scope
        </label>
        <select
          id="knowledge-agent-scope"
          value={agentScope}
          onChange={(e) => setAgentScope(e.target.value)}
          className="w-full bg-gray-700 border border-gray-600 text-gray-100 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
        >
          {AGENT_SCOPES.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Upload button */}
      <button
        type="button"
        onClick={handleUpload}
        disabled={!selectedFile || isUploading}
        className="w-full px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
      >
        {isUploading ? statusMessage : 'Upload File'}
      </button>

      {/* Status message */}
      {status === 'done' && statusMessage && (
        <p className="text-xs text-green-400">{statusMessage}</p>
      )}
      {status === 'error' && statusMessage && (
        <p className="text-xs text-red-400">{statusMessage}</p>
      )}
    </div>
  );
}
