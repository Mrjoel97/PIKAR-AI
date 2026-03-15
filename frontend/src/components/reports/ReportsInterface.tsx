'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Save,
  Clock,
  CheckCircle2,
  AlertCircle,
  FileText,
  ChevronRight,
  Search,
  Filter,
  FileDown,
  Inbox,
  Loader2,
} from 'lucide-react';
import { listReports, getReport, getReportCategories, type Report, type ReportStatus } from '@/services/reports';
import { buildReportPrintHtml } from './reportPrintHtml';

const STATUS_CONFIG: Record<ReportStatus, { icon: typeof CheckCircle2; label: string; className: string }> = {
  Completed: { icon: CheckCircle2, label: 'Completed', className: 'bg-emerald-100 text-emerald-700' },
  Processing: { icon: Clock, label: 'Processing', className: 'bg-blue-100 text-blue-700' },
  Failed: { icon: AlertCircle, label: 'Failed', className: 'bg-red-100 text-red-700' },
};

export function ReportsInterface() {
  const [reports, setReports] = useState<Report[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('');
  const [filterOpen, setFilterOpen] = useState(false);
  const [searchDebounce, setSearchDebounce] = useState('');
  const [savingToVault, setSavingToVault] = useState(false);
  const [vaultMessage, setVaultMessage] = useState<'idle' | 'success' | 'error'>('idle');
  const filterRef = useRef<HTMLDivElement>(null);
  const selectedIdRef = useRef<string | null>(selectedId);
  useEffect(() => {
    selectedIdRef.current = selectedId;
  }, [selectedId]);

  useEffect(() => {
    const onMouseDown = (e: MouseEvent) => {
      if (filterRef.current && !filterRef.current.contains(e.target as Node)) setFilterOpen(false);
    };
    document.addEventListener('mousedown', onMouseDown);
    return () => document.removeEventListener('mousedown', onMouseDown);
  }, []);

  const loadReports = useCallback(async () => {
    setLoading(true);
    try {
      const [data, cats] = await Promise.all([
        listReports({
          category: categoryFilter || undefined,
          search: searchDebounce || undefined,
          limit: 100,
        }),
        getReportCategories(),
      ]);
      setReports(data);
      setCategories(cats);
      const currentId = selectedIdRef.current;
      const currentInList = data.length > 0 && currentId && data.some((r) => r.id === currentId);
      if (data.length === 0) {
        setSelectedId(null);
        setSelectedReport(null);
      } else if (!currentInList) {
        setSelectedId(data[0]?.id ?? null);
      }
    } catch (e) {
      console.error('Failed to load reports', e);
      setReports([]);
      setCategories([]);
      setSelectedId(null);
      setSelectedReport(null);
    } finally {
      setLoading(false);
    }
  }, [categoryFilter, searchDebounce]);

  useEffect(() => {
    loadReports();
  }, [loadReports]);

  useEffect(() => {
    const t = setTimeout(() => setSearchDebounce(search.trim()), 300);
    return () => clearTimeout(t);
  }, [search]);

  useEffect(() => {
    setVaultMessage('idle');
  }, [selectedId]);

  useEffect(() => {
    if (!selectedId) {
      setSelectedReport(null);
      setLoadingDetail(false);
      return;
    }
    setLoadingDetail(true);
    getReport(selectedId)
      .then((r) => setSelectedReport({ ...r, content: r.content ?? r.summary ?? '' }))
      .catch(() => setSelectedReport(null))
      .finally(() => setLoadingDetail(false));
  }, [selectedId]);

  const handleExportPdf = () => {
    if (!selectedReport) return;
    const title = selectedReport.title.replace(/</g, '&lt;').replace(/"/g, '&quot;');
    const summary = (selectedReport.summary ?? '').replace(/</g, '&lt;').replace(/\n/g, '<br/>');
    const content = (selectedReport.content ?? '').replace(/</g, '&lt;').replace(/\n/g, '<br/>');
    const html = buildReportPrintHtml({
      title,
      summary,
      content,
      category: selectedReport.category,
      date: selectedReport.date ?? '',
    });
    const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const w = window.open(url, '_blank', 'noopener,noreferrer');
    if (w) {
      w.onload = () => {
        w.print();
        URL.revokeObjectURL(url);
      };
    } else {
    // Pop-up blocked: fallback to current window print
      const iframe = document.createElement('iframe');
      iframe.style.cssText = 'position:absolute;width:0;height:0;border:0;';
      document.body.appendChild(iframe);
      const doc = iframe.contentWindow!.document;
      doc.open();
      doc.write(html);
      doc.close();
      iframe.contentWindow!.onload = () => {
        iframe.contentWindow!.print();
        setTimeout(() => document.body.removeChild(iframe), 500);
      };
      URL.revokeObjectURL(url);
    }
  };

  const handleSaveToVault = async () => {
    if (!selectedReport) return;
    setSavingToVault(true);
    setVaultMessage('idle');
    try {
      const { createClient } = await import('@/lib/supabase/client');
      const supabase = createClient();
      const { data: { user } } = await supabase.auth.getUser();
      if (!user) {
        setVaultMessage('error');
        return;
      }
      const slug = selectedReport.title.replace(/[^a-zA-Z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 60) || 'report';
      const fileName = `${user.id}/reports/${Date.now()}_${slug}.txt`;
      const text = `${selectedReport.title}\n\n${'='.repeat(60)}\nSummary\n${'='.repeat(60)}\n${selectedReport.summary ?? ''}\n\nDetails\n${'='.repeat(60)}\n${selectedReport.content ?? ''}`;
      const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
      const { error: uploadError } = await supabase.storage.from('knowledge-vault').upload(fileName, blob, { contentType: 'text/plain', upsert: true });
      if (uploadError) throw uploadError;
      const { error: dbError } = await supabase.from('vault_documents').insert({
        user_id: user.id,
        filename: `${slug}.txt`,
        file_path: fileName,
        file_type: 'text/plain',
        size_bytes: blob.size,
        category: 'report',
        is_processed: false,
      });
      if (dbError) throw dbError;
      const res = await fetch('/api/vault/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file_path: fileName }),
        credentials: 'include',
      });
      if (!res.ok) {
        // Document is saved; RAG processing may fail
      }
      setVaultMessage('success');
    } catch (e) {
      console.error('Save to Vault error', e);
      setVaultMessage('error');
    } finally {
      setSavingToVault(false);
    }
  };

  return (
    <div className="flex flex-col pb-10">
      {/* Header: title + actions (Filter, Export PDF, Save to Vault) */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8 flex-shrink-0">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Reports</h1>
          <p className="text-slate-500 mt-1">Workflow and initiative summaries, searchable and categorized.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative" ref={filterRef}>
            <button
              onClick={() => setFilterOpen((o) => !o)}
              className="flex items-center gap-2 px-4 py-2.5 bg-white border border-slate-200 rounded-xl text-slate-600 hover:bg-slate-50 transition-colors shadow-sm"
            >
              <Filter size={18} />
              <span>Filter</span>
            </button>
            {filterOpen && (
              <div className="absolute top-full left-0 mt-1 py-2 bg-white border border-slate-200 rounded-xl shadow-lg z-10 min-w-[180px]">
                <button
                  onClick={() => {
                    setCategoryFilter('');
                    setFilterOpen(false);
                  }}
                  className={`block w-full text-left px-4 py-2 text-sm ${!categoryFilter ? 'bg-teal-50 text-teal-800 font-medium' : 'text-slate-700 hover:bg-slate-50'}`}
                >
                  All categories
                </button>
                {categories.map((c) => {
                  return (
                    <button
                      key={c}
                      onClick={() => {
                        setCategoryFilter(c);
                        setFilterOpen(false);
                      }}
                      className={`block w-full text-left px-4 py-2 text-sm capitalize ${categoryFilter === c ? 'bg-teal-50 text-teal-800 font-medium' : 'text-slate-700 hover:bg-slate-50'}`}
                    >
                      {c}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
          <button
            type="button"
            className="flex items-center gap-2 px-4 py-2.5 bg-white border border-slate-200 rounded-xl text-slate-600 hover:bg-slate-50 transition-colors shadow-sm"
            onClick={handleExportPdf}
            disabled={!selectedReport}
          >
            <FileDown size={18} />
            <span>Export PDF</span>
          </button>
          <button
            type="button"
            className="flex items-center gap-2 px-4 py-2.5 bg-white border border-slate-200 rounded-xl text-slate-600 hover:bg-slate-50 transition-colors shadow-sm disabled:opacity-60"
            onClick={handleSaveToVault}
            disabled={!selectedReport || savingToVault}
          >
            {savingToVault ? <Loader2 size={18} className="animate-spin" /> : <Save size={18} />}
            <span>{savingToVault ? 'Saving…' : vaultMessage === 'success' ? 'Saved' : 'Save to Vault'}</span>
          </button>
          {vaultMessage === 'error' && (
            <span className="text-red-600 text-sm">Failed to save. Try again.</span>
          )}
        </div>
      </div>

      {/* Main: list + detail */}
      <div className="flex-1 flex gap-6 items-start">
        {/* Left: list */}
        <div className="w-[30%] min-w-[280px] flex flex-col gap-4 sticky top-6 max-h-[calc(100vh-3rem)] overflow-y-auto pr-2 pb-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
            <input
              type="text"
              placeholder="Search reports..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-3 bg-white border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent text-slate-700"
            />
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-teal-600" />
            </div>
          ) : reports.length === 0 ? (
            <div className="rounded-2xl border border-slate-100 bg-white p-8 text-center shadow-sm">
              <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-50">
                <Inbox className="w-8 h-8 text-slate-300" />
              </div>
              <p className="text-slate-700 font-semibold">No reports yet</p>
              <p className="text-slate-500 text-sm mt-1">Workflow and initiative summaries will appear here when completed.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {reports.map((report) => {
                const cfg = STATUS_CONFIG[report.status] || STATUS_CONFIG.Completed;
                const Icon = cfg.icon;
                const isSelected = selectedId === report.id;
                return (
                  <motion.button
                    key={report.id}
                    layoutId={`card-${report.id}`}
                    onClick={() => setSelectedId(report.id)}
                    className={`w-full text-left p-4 rounded-xl border transition-all duration-200 group relative overflow-hidden
                      ${isSelected ? 'bg-teal-50 border-teal-200 shadow-md ring-1 ring-teal-500/30' : 'bg-white border-slate-200 hover:border-teal-200 hover:shadow-sm'}
                    `}
                  >
                    <div className="flex justify-between items-start mb-2">
                      <div className={`p-1.5 rounded-lg ${cfg.className}`}>
                        <Icon size={16} />
                      </div>
                      <span className="text-xs text-slate-400 font-medium">{report.date}</span>
                    </div>
                    <h3 className={`font-bold text-sm mb-1 line-clamp-1 ${isSelected ? 'text-teal-900' : 'text-slate-700'}`}>
                      {report.title}
                    </h3>
                    <div className="flex items-center gap-2 mb-2">
                      <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-500 text-[10px] uppercase font-bold tracking-wider">
                        {report.category}
                      </span>
                      {report.source_type !== 'manual' && (
                        <span className="text-[10px] text-slate-400">{report.source_type}</span>
                      )}
                    </div>
                    <p className={`text-xs line-clamp-2 ${isSelected ? 'text-teal-800/70' : 'text-slate-500'}`}>
                      {report.summary || 'No summary'}
                    </p>
                    {isSelected && <div className="absolute right-0 top-0 bottom-0 w-1 bg-teal-500" />}
                  </motion.button>
                );
              })}
            </div>
          )}
        </div>

        {/* Right: detail */}
        <div className="flex-1 rounded-2xl border border-slate-100 bg-white shadow-sm flex flex-col relative min-h-[480px]">
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
                <p className="font-medium text-slate-500">Select a report</p>
                <p className="text-sm mt-1">Choose one from the list or run a workflow to generate new reports.</p>
              </motion.div>
            ) : loadingDetail || !selectedReport ? (
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
                className="flex flex-col flex-1 bg-white relative z-10 rounded-2xl"
              >
                <div className="p-8 border-b border-slate-100 bg-slate-50/50">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-3 mb-3 flex-wrap">
                        {(() => {
                          const cfg = STATUS_CONFIG[selectedReport.status] || STATUS_CONFIG.Completed;
                          const Icon = cfg.icon;
                          return (
                            <>
                              <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider flex items-center gap-2 ${cfg.className}`}>
                                <Icon size={14} />
                                {selectedReport.status}
                              </span>
                              <span className="text-slate-400 text-sm">·</span>
                              <span className="text-slate-500 text-sm font-medium capitalize">{selectedReport.category}</span>
                              <span className="text-slate-400 text-sm">·</span>
                              <span className="text-slate-500 text-sm">{selectedReport.date}</span>
                            </>
                          );
                        })()}
                      </div>
                      <h2 className="text-2xl font-bold text-slate-900 leading-tight">
                        {selectedReport.title}
                      </h2>
                    </div>
                    <button
                      type="button"
                      className="p-2 hover:bg-slate-100 rounded-xl text-slate-400 hover:text-slate-600 transition-colors"
                      aria-label="Expand"
                    >
                      <ChevronRight size={24} className="rotate-90 md:rotate-0" />
                    </button>
                  </div>
                </div>

                <div className="p-8 flex-1 overflow-y-auto">
                  <div className="prose prose-slate prose-lg max-w-none">
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3">Summary</h3>
                    <p className="text-slate-600 text-base leading-relaxed mb-8">
                      {selectedReport.summary || 'No summary available.'}
                    </p>
                    <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3">Details</h3>
                    <div className="p-6 bg-slate-50 rounded-2xl border border-slate-100 text-slate-700 leading-relaxed whitespace-pre-line">
                      {selectedReport.content || selectedReport.summary || 'No additional content.'}
                    </div>
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
