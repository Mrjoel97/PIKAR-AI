'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    FileText,
    Search,
    Filter,
    BrainCircuit,
    Inbox,
    Loader2,
    ChevronRight,
    Clock,
    Download,
    ExternalLink,
    ArrowUpDown,
    Brain,
    FlaskConical,
    ClipboardList,
    BookOpen
} from 'lucide-react';
import Link from 'next/link';
import { createClient } from '@/lib/supabase/client';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface VaultDocument {
    id: string;
    filename: string;
    file_path: string;
    file_type: string | null;
    size_bytes: number | null;
    category: string | null;
    created_at: string;
    is_processed?: boolean;
}

type SortOption = 'newest' | 'oldest' | 'category';

const CATEGORY_STYLES: Record<string, { bg: string; text: string; border: string; icon: React.ReactNode }> = {
    'Brain Dump': { bg: 'bg-purple-50', text: 'text-purple-700', border: 'border-purple-200', icon: <Brain size={14} /> },
    'Brain Dump Transcript': { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200', icon: <ClipboardList size={14} /> },
    'Validation Plan': { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200', icon: <FlaskConical size={14} /> },
    'Brain Dump Analysis': { bg: 'bg-indigo-50', text: 'text-indigo-700', border: 'border-indigo-200', icon: <BrainCircuit size={14} /> },
    'Research': { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200', icon: <BookOpen size={14} /> },
};
const DEFAULT_STYLE = { bg: 'bg-slate-50', text: 'text-slate-600', border: 'border-slate-200', icon: <FileText size={14} /> };

export function BrainDumpInterface() {
    const [documents, setDocuments] = useState<VaultDocument[]>([]);
    const [selectedId, setSelectedId] = useState<string | null>(null);
    const [selectedDoc, setSelectedDoc] = useState<VaultDocument | null>(null);
    const [content, setContent] = useState<string>('');
    const [loading, setLoading] = useState(true);
    const [loadingContent, setLoadingContent] = useState(false);
    const [search, setSearch] = useState('');
    const [searchDebounce, setSearchDebounce] = useState('');
    const [sortBy, setSortBy] = useState<SortOption>('newest');
    const [previews, setPreviews] = useState<Record<string, string>>({});
    const [isCreatingInitiative, setIsCreatingInitiative] = useState(false);
    const supabase = createClient();
    const selectedIdRef = useRef<string | null>(selectedId);

    const handleCreateInitiative = async () => {
        if (!selectedDoc) return;
        setIsCreatingInitiative(true);
        try {
            // I will need to add a new function to the initiatives service
            // to trigger the workflow. For now, I will just log a message.
            console.log("Creating initiative from braindump:", selectedDoc.id);
            // After the workflow is completed, redirect the user.
            // I will add this later.
        } catch (error) {
            console.error("Failed to create initiative", error);
        } finally {
            setIsCreatingInitiative(false);
        }
    };

    useEffect(() => {
        selectedIdRef.current = selectedId;
    }, [selectedId]);

    const loadDocuments = useCallback(async () => {
        setLoading(true);
        try {
            const { data: { user } } = await supabase.auth.getUser();
            if (!user) return;

            const { data, error } = await supabase
                .from('vault_documents')
                .select('*')
                .eq('user_id', user.id)
                .in('category', ['Brain Dump', 'Brain Dump Transcript', 'Validation Plan', 'Brain Dump Analysis', 'Research'])
                .order('created_at', { ascending: sortBy === 'oldest' });

            if (error) throw error;

            let filteredData = data || [];
            if (searchDebounce) {
                filteredData = filteredData.filter((d: VaultDocument) => d.filename.toLowerCase().includes(searchDebounce.toLowerCase()));
            }
            // Secondary sort by category if selected
            if (sortBy === 'category') {
                filteredData.sort((a: VaultDocument, b: VaultDocument) => (a.category || '').localeCompare(b.category || ''));
            }

            setDocuments(filteredData);

            const currentId = selectedIdRef.current;
            const currentInList = filteredData.some((r: VaultDocument) => r.id === currentId);
            if (filteredData.length === 0) {
                setSelectedId(null);
                setSelectedDoc(null);
            } else if (!currentInList) {
                setSelectedId(filteredData[0]?.id ?? null);
            }
        } catch (e) {
            console.error('Failed to load brain dumps', e);
            setDocuments([]);
            setSelectedId(null);
            setSelectedDoc(null);
        } finally {
            setLoading(false);
        }
    }, [searchDebounce, sortBy, supabase]);

    useEffect(() => {
        loadDocuments();
    }, [loadDocuments]);

    useEffect(() => {
        const t = setTimeout(() => setSearchDebounce(search.trim()), 300);
        return () => clearTimeout(t);
    }, [search]);

    useEffect(() => {
        if (!selectedId) {
            setSelectedDoc(null);
            setContent('');
            setLoadingContent(false);
            return;
        }
        const doc = documents.find(d => d.id === selectedId);
        if (!doc) return;

        setSelectedDoc(doc);
        setLoadingContent(true);

        const fetchContent = async () => {
            try {
                const { data, error } = await supabase.storage
                    .from('knowledge-vault')
                    .createSignedUrl(doc.file_path, 3600);

                if (error) throw error;

                const signedUrl = (data as { signedUrl?: string; signedURL?: string }).signedUrl
                    ?? (data as { signedURL?: string }).signedURL;

                if (!signedUrl) throw new Error('Failed to get signed URL');

                const response = await fetch(signedUrl);
                const text = await response.text();
                setContent(text);

                // Save preview snippet for this document
                const snippet = text
                    .split('\n')
                    .filter(l => l.trim() && !l.startsWith('#') && !l.startsWith('|') && !l.startsWith('---'))
                    .slice(0, 2)
                    .join(' ')
                    .substring(0, 120);
                if (snippet) {
                    setPreviews(prev => ({ ...prev, [doc.id]: snippet + (snippet.length >= 120 ? '…' : '') }));
                }
            } catch (err) {
                console.error('Failed to load document content', err);
                setContent('Failed to load content.');
            } finally {
                setLoadingContent(false);
            }
        };

        fetchContent();
    }, [selectedId, documents, supabase]);

    const handleDownload = async () => {
        if (!selectedDoc) return;
        try {
            const { data, error } = await supabase.storage
                .from('knowledge-vault')
                .createSignedUrl(selectedDoc.file_path, 60);

            if (error) throw error;
            const signedUrl = (data as { signedUrl?: string; signedURL?: string }).signedUrl
                ?? (data as { signedURL?: string }).signedURL;
            if (!signedUrl) throw new Error('No signed URL returned');

            const response = await fetch(signedUrl);
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);

            const link = document.createElement('a');
            link.href = url;
            link.download = selectedDoc.filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
        } catch (error: any) {
            console.error('Download error:', error);
            alert('Error downloading: ' + error.message);
        }
    };

    return (
        <div className="min-h-screen flex flex-col pb-10">
            <div className="flex items-center gap-4 mb-6 flex-shrink-0 flex-wrap">
                <div className="flex-1 min-w-0">
                    <h1 className="text-3xl font-outfit font-bold text-slate-900 dark:text-white">Brain Dumps</h1>
                    <p className="text-slate-500 mt-1">Review your recorded ideas, analyses, and validation plans.</p>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                    {/* Sort dropdown */}
                    <div className="relative">
                        <select
                            value={sortBy}
                            onChange={(e) => setSortBy(e.target.value as SortOption)}
                            className="appearance-none pl-8 pr-6 py-2.5 bg-white border border-slate-200 rounded-xl text-sm text-slate-600 focus:outline-none focus:ring-2 focus:ring-teal-500/20 cursor-pointer shadow-sm"
                        >
                            <option value="newest">Newest first</option>
                            <option value="oldest">Oldest first</option>
                            <option value="category">By category</option>
                        </select>
                        <ArrowUpDown className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" size={14} />
                    </div>
                    {selectedDoc && (
                        <Link
                            href={`/dashboard/workspace?braindump_id=${selectedId}`}
                            className="flex items-center gap-2 px-4 py-2.5 bg-teal-600 border border-teal-600 rounded-xl text-white hover:bg-teal-700 transition-colors shadow-sm"
                        >
                            <ExternalLink size={18} />
                            <span>Open in Chat</span>
                        </Link>
                    )}
                    {selectedDoc?.category === 'Brain Dump Analysis' && (
                        <button
                            onClick={handleCreateInitiative}
                            disabled={isCreatingInitiative}
                            className="flex items-center gap-2 px-4 py-2.5 bg-green-600 border border-green-600 rounded-xl text-white hover:bg-green-700 transition-colors shadow-sm disabled:opacity-50"
                        >
                            {isCreatingInitiative ? (
                                <Loader2 className="w-5 h-5 animate-spin" />
                            ) : (
                                <BrainCircuit size={18} />
                            )}
                            <span>{isCreatingInitiative ? 'Creating...' : 'Create Initiative'}</span>
                        </button>
                    )}
                    <button
                        onClick={handleDownload}
                        disabled={!selectedDoc}
                        className="flex items-center gap-2 px-4 py-2.5 bg-white border border-slate-200 rounded-xl text-slate-600 hover:bg-slate-50 transition-colors shadow-sm disabled:opacity-50"
                    >
                        <Download size={18} />
                        <span>Download</span>
                    </button>
                </div>
            </div>

            <div className="flex-1 flex gap-8 items-start">
                {/* Left Side: Document List (30%) */}
                <div className="w-[30%] min-w-[280px] flex flex-col gap-4 sticky top-6 max-h-[calc(100vh-3rem)] overflow-y-auto pr-2 pb-4">
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                        <input
                            type="text"
                            placeholder="Search braindumps..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className="w-full pl-10 pr-4 py-3 bg-white border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-teal-500/20 text-slate-700 shadow-sm"
                        />
                    </div>

                    {loading ? (
                        <div className="flex items-center justify-center py-12">
                            <Loader2 className="w-8 h-8 animate-spin text-teal-600" />
                        </div>
                    ) : documents.length === 0 ? (
                        <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-8 text-center">
                            <Inbox className="w-12 h-12 text-slate-300 mx-auto mb-3" />
                            <p className="text-slate-600 font-medium">No brain dumps yet</p>
                            <p className="text-slate-500 text-sm mt-1">Use the <span className="font-semibold text-indigo-600">Brain icon</span> in chat and select <span className="font-semibold">&quot;Discuss with Agent&quot;</span> to start.</p>
                        </div>
                    ) : (
                        <div className="space-y-3">
                            {documents.map((doc) => {
                                const isSelected = selectedId === doc.id;
                                const d = new Date(doc.created_at);
                                const dateString = `${d.toLocaleDateString()} ${d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
                                const catStyle = CATEGORY_STYLES[doc.category || ''] || DEFAULT_STYLE;

                                return (
                                    <motion.button
                                        key={doc.id}
                                        layoutId={`bd-card-${doc.id}`}
                                        onClick={() => setSelectedId(doc.id)}
                                        className={`w-full text-left p-4 rounded-xl border transition-all duration-200 group relative overflow-hidden
                                            ${isSelected ? 'bg-teal-50 border-teal-200 shadow-md ring-1 ring-teal-500/30' : 'bg-white border-slate-200 hover:border-teal-200 hover:shadow-sm'}
                                        `}
                                    >
                                        <div className="flex justify-between items-start mb-2">
                                            <div className={`p-1.5 rounded-lg ${catStyle.bg} ${catStyle.text}`}>
                                                {catStyle.icon}
                                            </div>
                                            <span className="text-[10px] text-slate-400 font-medium text-right leading-tight max-w-[80px]">{dateString}</span>
                                        </div>
                                        <h3 className={`font-bold text-sm mb-1 truncate ${isSelected ? 'text-teal-900' : 'text-slate-700'}`}>
                                            {doc.filename.replace(/\.[^/.]+$/, '').replace(/_/g, ' ')}
                                        </h3>
                                        {previews[doc.id] && (
                                            <p className="text-[11px] text-slate-500 leading-snug line-clamp-2 mb-1.5">
                                                {previews[doc.id]}
                                            </p>
                                        )}
                                        <div className="flex items-center gap-2">
                                            <span className={`px-2 py-0.5 rounded-full ${catStyle.bg} ${catStyle.text} text-[10px] uppercase font-bold tracking-wider border ${catStyle.border}`}>
                                                {doc.category}
                                            </span>
                                        </div>
                                        {isSelected && <div className="absolute right-0 top-0 bottom-0 w-1 bg-teal-500" />}
                                    </motion.button>
                                );
                            })}
                        </div>
                    )}
                </div>

                {/* Right Side: Document Content (70%) */}
                <div className="flex-1 bg-white rounded-3xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-slate-100 flex flex-col relative min-h-[480px]">
                    <AnimatePresence mode="wait">
                        {!selectedId ? (
                            <motion.div
                                key="empty"
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                exit={{ opacity: 0 }}
                                className="flex flex-col items-center justify-center flex-1 py-20 text-slate-400"
                            >
                                <FileText className="w-16 h-16 mb-4 opacity-40" />
                                <p className="font-medium text-slate-500">Select a brain dump</p>
                                <p className="text-sm mt-1">Choose an item from the list to read it.</p>
                            </motion.div>
                        ) : loadingContent || !selectedDoc ? (
                            <motion.div
                                key="loading"
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                exit={{ opacity: 0 }}
                                className="flex items-center justify-center flex-1 py-20"
                            >
                                <Loader2 className="w-10 h-10 animate-spin text-teal-600" />
                            </motion.div>
                        ) : (
                            <motion.div
                                key={selectedId}
                                initial={{ opacity: 0, x: 20 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: -20 }}
                                transition={{ duration: 0.2 }}
                                className="flex flex-col flex-1 bg-white relative z-10 rounded-3xl overflow-hidden h-full max-h-[85vh]"
                            >
                                <div className="p-8 border-b border-slate-100 bg-slate-50/50 flex-shrink-0">
                                    <div className="flex items-start justify-between">
                                        <div>
                                            <div className="flex items-center gap-3 mb-3 flex-wrap">
                                                <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${(CATEGORY_STYLES[selectedDoc.category || ''] || DEFAULT_STYLE).bg} ${(CATEGORY_STYLES[selectedDoc.category || ''] || DEFAULT_STYLE).text}`}>
                                                    {selectedDoc.category}
                                                </span>
                                                <span className="text-slate-400 text-sm">·</span>
                                                <span className="text-slate-500 text-sm font-medium">{new Date(selectedDoc.created_at).toLocaleString()}</span>
                                            </div>
                                            <h2 className="text-2xl font-outfit font-bold text-slate-800 leading-tight">
                                                {selectedDoc.filename.replace(/\.[^/.]+$/, '').replace(/_/g, ' ')}
                                            </h2>
                                        </div>
                                    </div>
                                </div>

                                <div className="p-8 flex-1 overflow-y-auto">
                                    <div className="prose prose-slate prose-lg max-w-none prose-h1:text-2xl prose-h2:text-xl prose-h3:text-lg prose-a:text-teal-600 prose-headings:font-outfit prose-img:rounded-xl">
                                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                            {content || 'No content available.'}
                                        </ReactMarkdown>
                                    </div>
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            </div>
        </div>
    );
}
