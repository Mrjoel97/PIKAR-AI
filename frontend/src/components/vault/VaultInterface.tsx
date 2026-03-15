'use client';

import React, { useState, useEffect, useContext } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    FileText,
    UploadCloud,
    FolderOpen,
    Image,
    FileSpreadsheet,
    Search,
    Download,
    Trash2,
    MoreVertical,
    Loader2,
    File,
    Video,
    Music,
    ExternalLink,
    RefreshCw,
    Filter,
    Grid,
    List,
    Maximize2,
    BrainCircuit
} from 'lucide-react';
import { createClient } from '@/lib/supabase/client';
import { dispatchFocusWidget } from '@/services/widgetDisplay';
import { ChatSessionContext } from '@/contexts/ChatSessionContext';

// Types
interface VaultDocument {
    id: string;
    filename: string;
    file_path: string;
    file_type: string | null;
    size_bytes: number | null;
    category: string | null;
    created_at: string;
    is_processed?: boolean;
    source: 'upload' | 'workspace' | 'media' | 'google';
    preview_url?: string;
}


interface TabConfig {
    id: string;
    label: string;
    icon: React.ReactNode;
    description: string;
}

const TABS: TabConfig[] = [
    {
        id: 'uploads',
        label: 'My Uploads',
        icon: <UploadCloud size={18} />,
        description: 'Documents you have uploaded to the Knowledge Vault'
    },
    {
        id: 'workspace',
        label: 'Workspace Docs',
        icon: <FolderOpen size={18} />,
        description: 'Documents created in your workspaces'
    },
    {
        id: 'media',
        label: 'Media Files',
        icon: <Image size={18} />,
        description: 'Images, videos, and other media files'
    },
    {
        id: 'google',
        label: 'Google Docs',
        icon: <FileSpreadsheet size={18} />,
        description: 'Documents created by agents using Google Workspace'
    },
    {
        id: 'braindump',
        label: 'Brain Dumps',
        icon: <BrainCircuit size={18} />,
        description: 'Your recorded ideas and strategic plans'
    },
];

// Helper functions
function formatFileSize(bytes: number | null): string {
    if (!bytes) return 'Unknown';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function formatDate(dateString: string): string {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = diffMs / (1000 * 60 * 60);
    const diffDays = diffMs / (1000 * 60 * 60 * 24);

    if (diffHours < 1) return 'Just now';
    if (diffHours < 24) return `${Math.floor(diffHours)} hours ago`;
    if (diffDays < 7) return `${Math.floor(diffDays)} days ago`;
    return date.toLocaleDateString();
}

function getFileIcon(fileType: string | null, filename: string) {
    const ext = filename.split('.').pop()?.toLowerCase();

    if (fileType?.startsWith('image/') || ['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'].includes(ext || '')) {
        return <Image size={20} className="text-pink-500" />;
    }
    if (fileType?.startsWith('video/') || ['mp4', 'webm', 'mov', 'avi'].includes(ext || '')) {
        return <Video size={20} className="text-purple-500" />;
    }
    if (fileType?.startsWith('audio/') || ['mp3', 'wav', 'ogg'].includes(ext || '')) {
        return <Music size={20} className="text-orange-500" />;
    }
    if (['pdf'].includes(ext || '')) {
        return <FileText size={20} className="text-red-500" />;
    }
    if (['doc', 'docx'].includes(ext || '')) {
        return <FileText size={20} className="text-blue-500" />;
    }
    if (['xls', 'xlsx', 'csv'].includes(ext || '')) {
        return <FileSpreadsheet size={20} className="text-green-500" />;
    }
    return <File size={20} className="text-slate-500" />;
}

// Upload Zone Component
function UploadZone({
    onUpload,
    uploading
}: {
    onUpload: (file: File) => void;
    uploading: boolean;
}) {
    const [dragActive, setDragActive] = useState(false);

    const handleDrag = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === "dragenter" || e.type === "dragover") {
            setDragActive(true);
        } else if (e.type === "dragleave") {
            setDragActive(false);
        }
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            onUpload(e.dataTransfer.files[0]);
        }
    };

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            onUpload(e.target.files[0]);
        }
    };

    return (
        <label
            className={`
                flex flex-col items-center justify-center w-full h-40
                border-2 border-dashed rounded-2xl cursor-pointer
                transition-all duration-200 group
                ${dragActive
                    ? 'border-teal-500 bg-teal-50'
                    : 'border-slate-200 bg-slate-50/50 hover:border-teal-300 hover:bg-teal-50/30'
                }
            `}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
        >
            <div className="flex flex-col items-center justify-center pt-5 pb-6">
                {uploading ? (
                    <div className="flex flex-col items-center gap-3">
                        <Loader2 className="animate-spin text-teal-600 w-10 h-10" />
                        <p className="text-sm font-medium text-slate-600 dark:text-slate-300">Processing file...</p>
                    </div>
                ) : (
                    <>
                        <div className={`
                            p-4 rounded-full mb-3 transition-all duration-200
                            ${dragActive
                                ? 'bg-teal-100 dark:bg-teal-900/40 scale-110'
                                : 'bg-teal-50 dark:bg-teal-900/20 group-hover:scale-110'
                            }
                        `}>
                            <UploadCloud className="w-6 h-6 text-teal-600" />
                        </div>
                        <p className="text-sm text-slate-600 dark:text-slate-300">
                            <span className="font-semibold text-teal-600">Click to upload</span> or drag and drop
                        </p>
                        <p className="text-xs text-slate-400 mt-1">PDF, TXT, DOCX, Markdown, Images, Videos (Max 50MB)</p>
                    </>
                )}
            </div>
            <input
                type="file"
                className="hidden"
                onChange={handleChange}
                disabled={uploading}
                accept=".pdf,.txt,.md,.doc,.docx,.csv,.json,.png,.jpg,.jpeg,.gif,.webp,.mp4,.webm"
            />
        </label>
    );
}

// Check if stored event_data contains a widget with this asset_id
function eventContainsAssetId(eventData: Record<string, unknown> | null, assetId: string): boolean {
    if (!eventData || !assetId) return false;
    const w = eventData.widget as Record<string, unknown> | undefined;
    if (w?.data && typeof w.data === 'object' && (w.data as Record<string, unknown>).asset_id === assetId) return true;
    const parts = (eventData.content as { parts?: Array<Record<string, unknown>> })?.parts;
    if (!Array.isArray(parts)) return false;
    for (const p of parts) {
        const fr = p?.function_response as { response?: Record<string, unknown> } | undefined;
        const resp = fr?.response;
        if (resp?.data && typeof resp.data === 'object' && (resp.data as Record<string, unknown>).asset_id === assetId) return true;
        const result = resp?.result as Record<string, unknown> | undefined;
        if (result?.data && typeof result === 'object' && typeof result.data === 'object' && (result.data as Record<string, unknown>).asset_id === assetId) return true;
    }
    return false;
}

// Document Card Component
function DocumentCard({
    doc,
    onDownload,
    onDelete,
    onViewInWorkspace,
    viewMode
}: {
    doc: VaultDocument;
    onDownload: (doc: VaultDocument) => void;
    onDelete: (doc: VaultDocument) => void;
    onViewInWorkspace?: (doc: VaultDocument) => void;
    viewMode: 'grid' | 'list';
}) {
    const [showMenu, setShowMenu] = useState(false);
    const showViewInWorkspace = doc.source === 'media' && onViewInWorkspace;

    const isImage = doc.file_type?.startsWith('image/') || ['png', 'jpg', 'jpeg', 'gif', 'webp'].includes(doc.filename.split('.').pop()?.toLowerCase() || '');
    const isVideo = doc.file_type?.startsWith('video/') || ['mp4', 'webm', 'mov', 'avi'].includes(doc.filename.split('.').pop()?.toLowerCase() || '');
    const isText = doc.file_type?.startsWith('text/') || ['md', 'txt', 'csv', 'json'].includes(doc.filename.split('.').pop()?.toLowerCase() || '');

    const [snippet, setSnippet] = useState<string | null>(null);

    useEffect(() => {
        if (doc.preview_url && isText && !snippet) {
            let isMounted = true;
            fetch(doc.preview_url, { headers: { Range: 'bytes=0-500' } })
                .then(res => res.text())
                .then(text => {
                    if (isMounted) {
                        const cleanText = text.replace(/[#>*_`-]/g, '').trim().replace(/\s+/g, ' ');
                        setSnippet(cleanText.slice(0, 100) + (cleanText.length > 100 ? '...' : ''));
                    }
                })
                .catch(err => console.error('Failed to fetch snippet:', err));
            return () => { isMounted = false; };
        }
    }, [doc.preview_url, isText, snippet]);

    if (viewMode === 'list') {
        return (
            <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="flex items-center justify-between rounded-xl border border-slate-50 bg-slate-50/50 p-4 transition-all hover:border-teal-200 hover:shadow-sm group"
            >
                <div className="flex items-center gap-4 flex-1 min-w-0">
                    <div className={`rounded-lg shrink-0 overflow-hidden flex items-center justify-center ${doc.preview_url && (isImage || isVideo) ? 'w-12 h-12 bg-black/5 dark:bg-white/5' : 'p-2 bg-slate-100 dark:bg-slate-700'}`}>
                        {doc.preview_url && (isImage || isVideo) ? (
                            isImage ? (
                                <img src={doc.preview_url} alt={doc.filename} className="w-full h-full object-cover" loading="lazy" />
                            ) : (
                                <div className="relative w-full h-full">
                                    <video src={doc.preview_url} className="w-full h-full object-cover" preload="metadata" />
                                    <div className="absolute inset-0 flex items-center justify-center bg-black/20">
                                        <Video className="w-4 h-4 text-white" />
                                    </div>
                                </div>
                            )
                        ) : (
                            getFileIcon(doc.file_type, doc.filename)
                        )}
                    </div>
                    <div className="min-w-0 flex-1">
                        <p className="text-sm font-semibold text-slate-700 dark:text-slate-200 truncate">{doc.filename}</p>
                        <p className="text-xs text-slate-400">
                            {formatFileSize(doc.size_bytes)} • {formatDate(doc.created_at)}
                            {doc.is_processed === false && (
                                <span className="ml-2 text-amber-500">Processing...</span>
                            )}
                        </p>
                        {snippet && (
                            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 line-clamp-1 italic">
                                "{snippet}"
                            </p>
                        )}
                    </div>
                </div>
                <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    {showViewInWorkspace && (
                        <button
                            onClick={() => onViewInWorkspace(doc)}
                            className="p-2 text-slate-400 hover:text-teal-600 hover:bg-teal-50 dark:hover:bg-teal-900/20 rounded-lg transition-colors"
                            title="View in workspace"
                        >
                            <Maximize2 className="w-4 h-4" />
                        </button>
                    )}
                    <button
                        onClick={() => onDownload(doc)}
                        className="p-2 text-slate-400 hover:text-teal-600 hover:bg-teal-50 dark:hover:bg-teal-900/20 rounded-lg transition-colors"
                        title="Download"
                    >
                        <Download className="w-4 h-4" />
                    </button>
                    <button
                        onClick={() => onDelete(doc)}
                        className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                        title="Delete"
                    >
                        <Trash2 className="w-4 h-4" />
                    </button>
                </div>
            </motion.div>
        );
    }

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            whileHover={{ y: -2 }}
            className="rounded-xl border border-slate-100 bg-white p-4 shadow-sm transition-all hover:shadow-md group cursor-pointer relative"
        >
            {doc.preview_url && (isImage || isVideo) ? (
                <div className="w-full h-32 mb-3 rounded-lg overflow-hidden bg-slate-100 dark:bg-slate-800 relative group-hover:opacity-90 transition-opacity">
                    {isImage ? (
                        <img src={doc.preview_url} alt={doc.filename} className="w-full h-full object-cover" loading="lazy" />
                    ) : (
                        <video src={doc.preview_url} className="w-full h-full object-cover" preload="metadata" />
                    )}
                    {isVideo && (
                        <div className="absolute inset-0 flex items-center justify-center bg-black/20">
                            <div className="w-10 h-10 rounded-full bg-white/30 flex items-center justify-center backdrop-blur-sm">
                                <Video className="w-5 h-5 text-white" />
                            </div>
                        </div>
                    )}
                </div>
            ) : null}

            <div className="flex items-start justify-between">
                <div className="flex items-start gap-3 min-w-0 flex-1">
                    {(!doc.preview_url || (!isImage && !isVideo)) && (
                        <div className="w-10 h-10 rounded-lg bg-slate-100 dark:bg-slate-700 flex items-center justify-center shrink-0">
                            {getFileIcon(doc.file_type, doc.filename)}
                        </div>
                    )}
                    <div className="min-w-0">
                        <h3 className="font-semibold text-slate-800 dark:text-slate-200 text-sm truncate" title={doc.filename}>
                            {doc.filename}
                        </h3>
                        <p className="text-xs text-slate-500 mt-1">
                            {formatFileSize(doc.size_bytes)} • {formatDate(doc.created_at)}
                        </p>
                        {doc.is_processed === false && (
                            <p className="text-xs text-amber-500 mt-1 flex items-center gap-1">
                                <Loader2 className="w-3 h-3 animate-spin" /> Processing for RAG...
                            </p>
                        )}
                        {snippet && (
                            <p className="text-xs text-slate-500 dark:text-slate-400 mt-2 line-clamp-2 italic">
                                "{snippet}"
                            </p>
                        )}
                    </div>
                </div>
                <div className="relative">
                    <button
                        onClick={() => setShowMenu(!showMenu)}
                        className="text-slate-300 hover:text-slate-600 dark:hover:text-slate-300 p-1"
                    >
                        <MoreVertical size={18} />
                    </button>
                    {showMenu && (
                        <div className="absolute right-0 top-full mt-1 bg-white dark:bg-slate-800 rounded-lg shadow-lg border border-slate-200 dark:border-slate-700 py-1 z-10 min-w-[140px]">
                            {showViewInWorkspace && (
                                <button
                                    onClick={() => { onViewInWorkspace(doc); setShowMenu(false); }}
                                    className="w-full px-3 py-2 text-left text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 flex items-center gap-2"
                                >
                                    <Maximize2 size={14} /> View in workspace
                                </button>
                            )}
                            <button
                                onClick={() => { onDownload(doc); setShowMenu(false); }}
                                className="w-full px-3 py-2 text-left text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 flex items-center gap-2"
                            >
                                <Download size={14} /> Download
                            </button>
                            <button
                                onClick={() => { onDelete(doc); setShowMenu(false); }}
                                className="w-full px-3 py-2 text-left text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 flex items-center gap-2"
                            >
                                <Trash2 size={14} /> Delete
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </motion.div>
    );
}

// Google Doc Card Component
function GoogleDocCard({ doc }: { doc: VaultDocument }) {
    return (
        <motion.a
            href={doc.file_path}
            target="_blank"
            rel="noopener noreferrer"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            whileHover={{ y: -2 }}
            className="rounded-xl border border-slate-100 bg-white p-4 shadow-sm transition-all hover:shadow-md group cursor-pointer block"
        >
            <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-lg bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center">
                    <FileSpreadsheet className="text-blue-600" size={20} />
                </div>
                <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-slate-800 dark:text-slate-200 text-sm truncate flex items-center gap-2">
                        {doc.filename}
                        <ExternalLink size={12} className="text-slate-400 group-hover:text-blue-500 transition-colors" />
                    </h3>
                    <p className="text-xs text-slate-500 mt-1">
                        Created {formatDate(doc.created_at)}
                    </p>
                    {doc.category && (
                        <span className="inline-block mt-2 px-2 py-0.5 bg-blue-50 dark:bg-blue-900/20 text-blue-600 text-xs rounded-full">
                            {doc.category}
                        </span>
                    )}
                </div>
            </div>
        </motion.a>
    );
}

// Empty State Component
function EmptyState({ tab }: { tab: TabConfig }) {
    return (
        <div className="rounded-2xl border border-slate-100 bg-white p-16 text-center shadow-sm">
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-slate-50 text-slate-400">
                {tab.icon}
            </div>
            <h3 className="mb-2 text-lg font-semibold text-slate-700">No {tab.label} yet</h3>
            <p className="mx-auto max-w-md text-sm text-slate-500">{tab.description}</p>
        </div>
    );
}

// Main Component
export function VaultInterface() {
    const [activeTab, setActiveTab] = useState('uploads');
    const [documents, setDocuments] = useState<VaultDocument[]>([]);
    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');
    const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
    const supabase = createClient();
    const chatContext = useContext(ChatSessionContext);
    const { useRouter } = require('next/navigation');
    const router = useRouter();

    // View media in workspace and optionally open the chat where it was created
    const handleViewMediaInWorkspace = async (doc: VaultDocument) => {
        if (doc.source !== 'media' || !doc.file_path) return;
        const { data: { user } } = await supabase.auth.getUser();
        if (!user) return;

        const path = doc.file_path;
        const { data: signed, error } = await supabase.storage.from('knowledge-vault').createSignedUrl(path, 3600);
        if (error) {
            console.warn('[Vault] Failed to create signed URL for view:', path, error.message);
            return;
        }
        const url = (signed as { signedUrl?: string; signedURL?: string })?.signedUrl ?? (signed as { signedURL?: string })?.signedURL;
        if (!url) return;

        const assetId = doc.id;
        const isVideo = doc.file_type?.startsWith('video/') ?? /\.(mp4|webm|mov|avi)$/i.test(doc.filename || '');
        const widget = isVideo
            ? { type: 'video' as const, title: doc.filename || 'Video', data: { videoUrl: url, asset_id: assetId, caption: doc.filename } }
            : { type: 'image' as const, title: 'Image', data: { imageUrl: url, asset_id: assetId, caption: doc.filename } };

        dispatchFocusWidget(widget, user.id);

        if (chatContext?.selectChat) {
            try {
                const { data: events } = await supabase
                    .from('session_events')
                    .select('session_id, event_data')
                    .eq('user_id', user.id)
                    .eq('app_name', 'agents')
                    .is('superseded_by', null)
                    .order('created_at', { ascending: false })
                    .limit(150);
                const row = events?.find((e: { event_data: Record<string, unknown> }) => eventContainsAssetId(e.event_data, assetId));
                if (row?.session_id) {
                    chatContext.selectChat(row.session_id);
                }
            } catch (e) {
                console.warn('[Vault] Could not find session for asset:', assetId, e);
            }
        }
    };

    // Fetch documents based on active tab
    const fetchDocuments = async () => {
        setLoading(true);
        try {
            const { data: { user } } = await supabase.auth.getUser();
            if (!user) {
                setDocuments([]);
                setLoading(false);
                return;
            }

            let docs: VaultDocument[] = [];

            if (activeTab === 'uploads') {
                // Fetch from vault_documents table
                const { data, error } = await supabase
                    .from('vault_documents')
                    .select('*')
                    .eq('user_id', user.id)
                    .order('created_at', { ascending: false });

                if (!error && data) {
                    docs = data.map((d: VaultDocument) => ({ ...d, source: 'upload' as const }));
                }
            } else if (activeTab === 'workspace') {
                // Fetch landing pages and workspace documents
                const { data, error } = await supabase
                    .from('landing_pages')
                    .select('id, title, created_at, config')
                    .eq('user_id', user.id)
                    .order('created_at', { ascending: false });

                if (!error && data) {
                    docs = data.map((d: { id: string; title: string; created_at: string }) => ({
                        id: d.id,
                        filename: d.title || 'Untitled Landing Page',
                        file_path: `/dashboard/landing-pages/${d.id}`,
                        file_type: 'text/html',
                        size_bytes: null,
                        category: 'Landing Page',
                        created_at: d.created_at,
                        source: 'workspace' as const
                    }));
                }
            } else if (activeTab === 'media') {
                // Fetch from media_assets table
                const { data, error } = await supabase
                    .from('media_assets')
                    .select('*')
                    .eq('user_id', user.id)
                    .order('created_at', { ascending: false });

                if (!error && data) {
                    docs = data.map((d: { id: string; filename: string; file_path: string; file_type: string; size_bytes: number; category: string; created_at: string }) => ({
                        id: d.id,
                        filename: d.filename,
                        file_path: d.file_path,
                        file_type: d.file_type,
                        size_bytes: d.size_bytes,
                        category: d.category,
                        created_at: d.created_at,
                        source: 'media' as const
                    }));
                }
            } else if (activeTab === 'google') {
                // Fetch agent-created Google Docs
                const { data, error } = await supabase
                    .from('agent_google_docs')
                    .select('*')
                    .eq('user_id', user.id)
                    .order('created_at', { ascending: false });

                if (!error && data) {
                    docs = data.map((d: { id: string; title: string; doc_url: string; doc_type: string; created_at: string }) => ({
                        id: d.id,
                        filename: d.title,
                        file_path: d.doc_url,
                        file_type: 'application/vnd.google-apps.document',
                        size_bytes: null,
                        category: d.doc_type,
                        created_at: d.created_at,
                        source: 'google' as const
                    }));
                }
            } else if (activeTab === 'braindump') {
                // Fetch brain dump analyses and validation plans from vault_documents
                const { data, error } = await supabase
                    .from('vault_documents')
                    .select('*')
                    .eq('user_id', user.id)
                    .in('category', ['Brain Dump', 'Brain Dump Transcript', 'Validation Plan', 'Brain Dump Analysis'])
                    .order('created_at', { ascending: false });

                if (!error && data) {
                    docs = data.map((d: VaultDocument) => ({ ...d, source: 'upload' as const }));
                }
            }

            // Fetch signed URLs for files that need previews or snippets
            const needsPreviewDocs = docs.filter(d =>
                d.source !== 'google' && d.source !== 'workspace' &&
                d.file_path && !d.file_path.startsWith('http') && !d.file_path.startsWith('/')
            );

            if (needsPreviewDocs.length > 0) {
                const paths = [...new Set(needsPreviewDocs.map(d => d.file_path))];

                if (paths.length > 0) {
                    const { data: signedUrls } = await supabase.storage.from('knowledge-vault').createSignedUrls(paths, 3600);
                    if (signedUrls) {
                        docs = docs.map(d => {
                            const signedUrl = signedUrls.find((s) => s.path === d.file_path);
                            if (signedUrl && !signedUrl.error) {
                                return { ...d, preview_url: signedUrl.signedUrl };
                            }
                            return d;
                        });
                    }
                }
            }

            setDocuments(docs);
        } catch (error) {
            console.error('Error fetching documents:', error);
            setDocuments([]);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchDocuments();
    }, [activeTab]);

    // Handle file upload
    const handleUpload = async (file: File) => {
        setUploading(true);
        try {
            const { data: { user } } = await supabase.auth.getUser();
            if (!user) {
                alert('Please sign in to upload files');
                return;
            }

            const fileExt = file.name.split('.').pop();
            const fileName = `${user.id}/${Date.now()}_${file.name}`;

            // Upload to storage
            const { error: uploadError } = await supabase.storage
                .from('knowledge-vault')
                .upload(fileName, file);

            if (uploadError) throw uploadError;

            // Create database record
            const { error: dbError } = await supabase
                .from('vault_documents')
                .insert({
                    user_id: user.id,
                    filename: file.name,
                    file_path: fileName,
                    file_type: file.type,
                    size_bytes: file.size,
                    is_processed: false
                });

            if (dbError) throw dbError;

            // Refresh the list
            await fetchDocuments();

            // Trigger RAG processing (fire and forget)
            fetch('/api/vault/process', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ file_path: fileName })
            }).catch(console.error);

        } catch (error: any) {
            console.error('Upload error:', error);
            alert('Error uploading: ' + error.message);
        } finally {
            setUploading(false);
        }
    };

    // Handle download
    const handleDownload = async (doc: VaultDocument) => {
        try {
            if (doc.source === 'google') {
                window.open(doc.file_path, '_blank');
                return;
            }

            const bucket = doc.source === 'media' ? 'knowledge-vault' : 'knowledge-vault';
            const { data, error } = await supabase.storage
                .from(bucket)
                .createSignedUrl(doc.file_path, 60);

            if (error) throw error;
            const signedUrl = (data as { signedUrl?: string; signedURL?: string }).signedUrl
                ?? (data as { signedURL?: string }).signedURL;
            if (!signedUrl) throw new Error('No signed URL returned');

            // Fetch the blob to avoid CORS download issues/prompting
            const response = await fetch(signedUrl);
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);

            // Create download link
            const link = document.createElement('a');
            link.href = url;
            link.download = doc.filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
        } catch (error: any) {
            console.error('Download error:', error);
            alert('Error downloading: ' + error.message);
        }
    };

    // Handle delete
    const handleDelete = async (doc: VaultDocument) => {
        if (!confirm(`Are you sure you want to delete "${doc.filename}"?`)) return;

        try {
            const { data: { user } } = await supabase.auth.getUser();
            if (!user) return;

            if (doc.source === 'upload') {
                // Delete from storage
                await supabase.storage
                    .from('knowledge-vault')
                    .remove([doc.file_path]);

                // Delete from database
                await supabase
                    .from('vault_documents')
                    .delete()
                    .eq('id', doc.id);
            } else if (doc.source === 'media') {
                await supabase.storage
                    .from('knowledge-vault')
                    .remove([doc.file_path]);

                await supabase
                    .from('media_assets')
                    .delete()
                    .eq('id', doc.id);
            }

            await fetchDocuments();
        } catch (error: any) {
            console.error('Delete error:', error);
            alert('Error deleting: ' + error.message);
        }
    };

    // Filter documents by search
    const filteredDocuments = documents.filter(doc =>
        doc.filename.toLowerCase().includes(searchQuery.toLowerCase())
    );

    const activeTabConfig = TABS.find(t => t.id === activeTab)!;

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-slate-900">Knowledge Vault</h1>
                    <p className="text-slate-500 mt-1">Manage your business context, files, and strategic documents.</p>
                </div>
                <button
                    onClick={fetchDocuments}
                    className="inline-flex items-center gap-2 rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-teal-700"
                >
                    <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
                    Refresh
                </button>
            </div>

            {/* Tabs */}
            <div className="rounded-2xl border border-slate-100 bg-white p-2 shadow-sm">
                <div className="flex flex-wrap gap-1">
                    {TABS.map(tab => (
                        <button
                            key={tab.id}
                            onClick={() => {
                                if (tab.id === 'braindump') {
                                    router.push('/dashboard/braindump');
                                } else {
                                    setActiveTab(tab.id);
                                }
                            }}
                            className={`
                                flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-all
                                ${activeTab === tab.id
                                    ? 'bg-teal-600 text-white shadow-sm'
                                    : 'text-slate-600 hover:bg-slate-50'
                                }
                            `}
                        >
                            {tab.icon}
                            <span className="hidden sm:inline">{tab.label}</span>
                        </button>
                    ))}
                </div>
            </div>

            {/* Upload Zone (only for uploads tab) */}
            {activeTab === 'uploads' && (
                <UploadZone onUpload={handleUpload} uploading={uploading} />
            )}

            {/* Search & View Controls */}
            <div className="rounded-2xl border border-slate-100 bg-white p-4 shadow-sm">
                <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
                    <div className="relative flex-1 max-w-md">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                        <input
                            type="text"
                            placeholder={`Search ${activeTabConfig.label.toLowerCase()}...`}
                            className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 bg-white text-slate-700 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-teal-500"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                        />
                    </div>
                    <div className="flex items-center gap-3">
                        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">{filteredDocuments.length} items</span>
                        <div className="flex rounded-xl border border-slate-100 bg-slate-50 p-1">
                            <button
                                onClick={() => setViewMode('grid')}
                                className={`rounded-lg p-2 transition ${viewMode === 'grid' ? 'bg-white shadow-sm' : ''}`}
                            >
                                <Grid size={16} className="text-slate-600" />
                            </button>
                            <button
                                onClick={() => setViewMode('list')}
                                className={`rounded-lg p-2 transition ${viewMode === 'list' ? 'bg-white shadow-sm' : ''}`}
                            >
                                <List size={16} className="text-slate-600" />
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            {/* Content Area */}
            <AnimatePresence mode="wait">
                {loading ? (
                    <motion.div
                        key="loading"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="flex items-center justify-center py-20"
                    >
                        <Loader2 className="w-8 h-8 animate-spin text-teal-600" />
                    </motion.div>
                ) : filteredDocuments.length === 0 ? (
                    <motion.div
                        key="empty"
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -20 }}
                    >
                        <EmptyState tab={activeTabConfig} />
                    </motion.div>
                ) : (
                    <motion.div
                        key="content"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className={viewMode === 'grid'
                            ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'
                            : 'space-y-3'
                        }
                    >
                        {filteredDocuments.map(doc => (
                            activeTab === 'google' ? (
                                <GoogleDocCard key={doc.id} doc={doc} />
                            ) : (
                                <DocumentCard
                                    key={doc.id}
                                    doc={doc}
                                    onDownload={handleDownload}
                                    onDelete={handleDelete}
                                    onViewInWorkspace={activeTab === 'media' ? handleViewMediaInWorkspace : undefined}
                                    viewMode={viewMode}
                                />
                            )
                        ))}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
