'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import { useState, useEffect, useCallback } from 'react';
import { PremiumShell } from '@/components/layout/PremiumShell';
import DashboardSkeleton from '@/components/ui/DashboardSkeleton';
import DashboardErrorBoundary from '@/components/ui/DashboardErrorBoundary';
import { usePersona } from '@/contexts/PersonaContext';
import { motion } from 'framer-motion';
import {
    Settings,
    User,
    Bell,
    Shield,
    Plug,
    Save,
    CheckCircle2,
    AlertCircle,
    Building2,
    Target,
    TrendingDown,
    Users,
    Trash2,
    X,
    Cpu,
} from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { fetchWithAuth } from '@/services/api';
import { signOut } from '@/services/auth';

interface UserSettings {
    full_name: string;
    email: string;
    notifications_enabled: boolean;
    revenue_target?: number;
    burn_rate?: number;
    department_count?: number;
    audit_logs_enabled?: boolean;
}

function SettingsSection({
    title,
    icon: Icon,
    gradient,
    delay = 0,
    children,
}: {
    title: string;
    icon: React.ElementType;
    gradient: string;
    delay?: number;
    children: React.ReactNode;
}) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay }}
            className="rounded-[28px] border border-slate-100/80 bg-white p-4 sm:p-6 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]"
        >
            <div className="flex items-center gap-3 mb-6">
                <div className={`flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br ${gradient} shadow-lg`}>
                    <Icon className="h-5 w-5 text-white" />
                </div>
                <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
            </div>
            {children}
        </motion.div>
    );
}

function InputField({
    label,
    id,
    type = 'text',
    value,
    onChange,
    placeholder,
}: {
    label: string;
    id: string;
    type?: string;
    value: string | number;
    onChange: (val: string) => void;
    placeholder?: string;
}) {
    return (
        <div>
            <label htmlFor={id} className="block text-sm font-medium text-slate-700 mb-1.5">
                {label}
            </label>
            <input
                id={id}
                type={type}
                value={value}
                onChange={(e) => onChange(e.target.value)}
                className="w-full rounded-xl border border-slate-200 px-4 py-2.5 min-h-[44px] text-sm text-slate-900 focus:border-teal-500 focus:ring-2 focus:ring-teal-200 outline-none transition-all"
                placeholder={placeholder}
            />
        </div>
    );
}

function DeleteAccountModal({
    confirmText,
    onConfirmTextChange,
    onConfirm,
    onCancel,
    deleting,
    error: deleteError,
}: {
    confirmText: string;
    onConfirmTextChange: (val: string) => void;
    onConfirm: () => void;
    onCancel: () => void;
    deleting: boolean;
    error: string | null;
}) {
    // Close on Escape key
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === 'Escape' && !deleting) onCancel();
        };
        document.addEventListener('keydown', handleKeyDown);
        return () => document.removeEventListener('keydown', handleKeyDown);
    }, [onCancel, deleting]);

    return (
        <div
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
            onClick={(e) => { if (e.target === e.currentTarget && !deleting) onCancel(); }}
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-account-title"
        >
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.2 }}
                className="bg-white rounded-2xl shadow-2xl w-full max-w-md mx-auto overflow-hidden"
            >
                {/* Header */}
                <div className="flex items-center justify-between p-6 border-b border-slate-100">
                    <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-rose-100">
                            <Trash2 className="h-5 w-5 text-rose-600" />
                        </div>
                        <h3 id="delete-account-title" className="text-lg font-bold text-slate-900">Delete Account</h3>
                    </div>
                    <button
                        onClick={onCancel}
                        className="p-2.5 rounded-lg hover:bg-slate-100 transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
                    >
                        <X className="h-4 w-4 text-slate-500" />
                    </button>
                </div>

                {/* Body */}
                <div className="p-6 space-y-4">
                    <div className="p-4 bg-rose-50 rounded-xl border border-rose-200">
                        <p className="text-sm text-rose-800 font-medium">
                            This action is permanent and cannot be undone.
                        </p>
                        <p className="text-sm text-rose-700 mt-1">
                            All your data — including initiatives, workflows, campaigns, documents,
                            connected accounts, and AI history — will be permanently deleted.
                        </p>
                    </div>

                    <div>
                        <label
                            htmlFor="deleteConfirm"
                            className="block text-sm font-medium text-slate-700 mb-1.5"
                        >
                            Type <code className="bg-slate-100 px-1.5 py-0.5 rounded text-rose-600 font-mono text-xs">DELETE</code> to confirm
                        </label>
                        <input
                            id="deleteConfirm"
                            type="text"
                            value={confirmText}
                            onChange={(e) => onConfirmTextChange(e.target.value)}
                            placeholder="DELETE"
                            autoComplete="off"
                            className="w-full rounded-xl border border-slate-200 px-4 py-2.5 h-11 min-h-[44px] text-sm text-slate-900 focus:border-rose-500 focus:ring-2 focus:ring-rose-200 outline-none transition-all font-mono"
                        />
                    </div>

                    {deleteError && (
                        <div className="flex items-center gap-2 p-3 bg-rose-50 rounded-lg border border-rose-200">
                            <AlertCircle className="h-4 w-4 text-rose-500 shrink-0" />
                            <p className="text-sm text-rose-700">{deleteError}</p>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="flex items-center gap-3 p-6 border-t border-slate-100 bg-slate-50">
                    <button
                        onClick={onCancel}
                        disabled={deleting}
                        className="flex-1 px-4 py-2.5 min-h-[44px] text-sm font-semibold text-slate-700 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 transition-colors disabled:opacity-50"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={onConfirm}
                        disabled={confirmText !== 'DELETE' || deleting}
                        className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2.5 min-h-[44px] text-sm font-semibold text-white bg-rose-600 rounded-xl hover:bg-rose-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        <Trash2 className="h-4 w-4" />
                        {deleting ? 'Deleting...' : 'Delete My Account'}
                    </button>
                </div>
            </motion.div>
        </div>
    );
}

export default function SettingsPage() {
    const { persona } = usePersona();
    const router = useRouter();
    const [settings, setSettings] = useState<UserSettings>({
        full_name: '',
        email: '',
        notifications_enabled: false,
    });
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [saveStatus, setSaveStatus] = useState<'idle' | 'success' | 'error'>('idle');
    const [error, setError] = useState<string | null>(null);

    // Account deletion state
    const [showDeleteModal, setShowDeleteModal] = useState(false);
    const [deleteConfirmText, setDeleteConfirmText] = useState('');
    const [deleting, setDeleting] = useState(false);
    const [deleteError, setDeleteError] = useState<string | null>(null);

    const fetchSettings = useCallback(async () => {
        try {
            setError(null);
            const response = await fetchWithAuth('/configuration/settings');
            const data = await response.json();
            setSettings({
                full_name: data.full_name || '',
                email: data.email || '',
                notifications_enabled: data.notifications_enabled ?? false,
                revenue_target: data.revenue_target,
                burn_rate: data.burn_rate,
                department_count: data.department_count,
                audit_logs_enabled: data.audit_logs_enabled,
            });
        } catch {
            // Settings endpoint might not exist yet — use defaults
            setError(null);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchSettings();
    }, [fetchSettings]);

    const handleSave = async () => {
        setSaving(true);
        setSaveStatus('idle');
        try {
            await fetchWithAuth('/configuration/settings', {
                method: 'PATCH',
                body: JSON.stringify(settings),
            });
            setSaveStatus('success');
            setTimeout(() => setSaveStatus('idle'), 3000);
        } catch {
            setSaveStatus('error');
            setTimeout(() => setSaveStatus('idle'), 3000);
        } finally {
            setSaving(false);
        }
    };

    const update = (field: keyof UserSettings, value: string | boolean | number) => {
        setSettings((prev) => ({ ...prev, [field]: value }));
    };

    const handleDeleteAccount = async () => {
        if (deleteConfirmText !== 'DELETE') return;
        setDeleting(true);
        setDeleteError(null);
        try {
            await fetchWithAuth('/account/delete', { method: 'DELETE' });
            await signOut();
            router.push('/');
        } catch {
            setDeleteError(
                'Account deletion failed. Please try again or contact privacy@pikar-ai.com for assistance.',
            );
            setDeleting(false);
        }
    };

    if (loading) {
        return (
            <PremiumShell>
                <DashboardSkeleton rows={3} columns={1} showMetricCards={false} />
            </PremiumShell>
        );
    }

    return (
        <DashboardErrorBoundary fallbackTitle="Settings Error">
            <PremiumShell>
                <div className="max-w-3xl mx-auto space-y-6">
                    {/* Header */}
                    <motion.div
                        initial={{ opacity: 0, y: 18 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.5 }}
                        className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4"
                    >
                        <div className="flex items-center gap-4">
                            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-slate-600 to-slate-800 shadow-lg">
                                <Settings className="h-6 w-6 text-white" />
                            </div>
                            <div>
                                <h1 className="text-3xl font-semibold tracking-tight text-slate-900">
                                    Settings
                                </h1>
                                <p className="mt-0.5 text-sm text-slate-500">
                                    Manage your profile, preferences, and integrations.
                                </p>
                            </div>
                        </div>
                        <button
                            onClick={handleSave}
                            disabled={saving}
                            className={`inline-flex items-center gap-2 rounded-2xl px-6 py-2.5 text-sm font-semibold text-white shadow-lg transition-all active:scale-[0.97] disabled:opacity-50 ${
                                saveStatus === 'success'
                                    ? 'bg-emerald-600 shadow-emerald-600/25'
                                    : saveStatus === 'error'
                                    ? 'bg-rose-600 shadow-rose-600/25'
                                    : 'bg-teal-600 shadow-teal-600/25 hover:bg-teal-700'
                            }`}
                        >
                            {saveStatus === 'success' ? (
                                <>
                                    <CheckCircle2 className="h-4 w-4" />
                                    Saved
                                </>
                            ) : saveStatus === 'error' ? (
                                <>
                                    <AlertCircle className="h-4 w-4" />
                                    Failed
                                </>
                            ) : (
                                <>
                                    <Save className="h-4 w-4" />
                                    {saving ? 'Saving...' : 'Save Changes'}
                                </>
                            )}
                        </button>
                    </motion.div>

                    {/* Quick Links */}
                    <motion.div
                        initial={{ opacity: 0, y: 18 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.5, delay: 0.05 }}
                    >
                        <Link
                            href="/settings/integrations"
                            className="flex items-center gap-4 rounded-[28px] border border-slate-100/80 bg-gradient-to-r from-teal-50 to-blue-50 p-5 shadow-[0_4px_24px_-12px_rgba(15,23,42,0.12)] transition-all hover:shadow-[0_8px_32px_-12px_rgba(15,23,42,0.18)] hover:border-teal-200"
                        >
                            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-teal-400 to-emerald-500 shadow-md">
                                <Plug className="h-5 w-5 text-white" />
                            </div>
                            <div>
                                <p className="text-sm font-semibold text-slate-900">Integrations</p>
                                <p className="text-xs text-slate-500">Connect Google Workspace, social media, and third-party tools</p>
                            </div>
                        </Link>
                    </motion.div>

                    <motion.div
                        initial={{ opacity: 0, y: 18 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.5, delay: 0.07 }}
                    >
                        <Link
                            href="/settings/ai-provider"
                            className="flex items-center gap-4 rounded-[28px] border border-slate-100/80 bg-gradient-to-r from-violet-50 to-purple-50 p-5 shadow-[0_4px_24px_-12px_rgba(15,23,42,0.12)] transition-all hover:shadow-[0_8px_32px_-12px_rgba(15,23,42,0.18)] hover:border-violet-200"
                        >
                            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-400 to-purple-500 shadow-md">
                                <Cpu className="h-5 w-5 text-white" />
                            </div>
                            <div>
                                <p className="text-sm font-semibold text-slate-900">AI Provider</p>
                                <p className="text-xs text-slate-500">Bring your own API key for OpenAI, Anthropic, and more</p>
                            </div>
                        </Link>
                    </motion.div>

                    {error && (
                        <div className="flex items-center gap-3 rounded-[28px] border border-rose-200 bg-rose-50 px-6 py-4">
                            <AlertCircle className="h-5 w-5 text-rose-500" />
                            <p className="text-sm text-rose-700">{error}</p>
                        </div>
                    )}

                    {/* Profile Information */}
                    <SettingsSection title="Profile Information" icon={User} gradient="from-blue-400 to-indigo-500" delay={0.1}>
                        <div className="space-y-4">
                            <InputField
                                label="Full Name"
                                id="fullName"
                                value={settings.full_name}
                                onChange={(val) => update('full_name', val)}
                                placeholder="John Doe"
                            />
                            <InputField
                                label="Email Address"
                                id="email"
                                type="email"
                                value={settings.email}
                                onChange={(val) => update('email', val)}
                                placeholder="john@example.com"
                            />
                        </div>
                    </SettingsSection>

                    {/* Persona-specific settings */}
                    {persona === 'solopreneur' && (
                        <SettingsSection title="Solopreneur Tools" icon={Target} gradient="from-amber-400 to-orange-500" delay={0.15}>
                            <InputField
                                label="Revenue Target (Monthly)"
                                id="revenueTarget"
                                type="number"
                                value={settings.revenue_target || ''}
                                onChange={(val) => update('revenue_target', Number(val))}
                                placeholder="10000"
                            />
                        </SettingsSection>
                    )}

                    {persona === 'startup' && (
                        <SettingsSection title="Startup Settings" icon={TrendingDown} gradient="from-violet-400 to-purple-500" delay={0.15}>
                            <InputField
                                label="Target Burn Rate"
                                id="burnRate"
                                type="number"
                                value={settings.burn_rate || ''}
                                onChange={(val) => update('burn_rate', Number(val))}
                                placeholder="50000"
                            />
                        </SettingsSection>
                    )}

                    {persona === 'sme' && (
                        <SettingsSection title="SME Operations" icon={Building2} gradient="from-emerald-400 to-teal-500" delay={0.15}>
                            <InputField
                                label="Number of Departments"
                                id="deptCount"
                                type="number"
                                value={settings.department_count || ''}
                                onChange={(val) => update('department_count', Number(val))}
                                placeholder="5"
                            />
                        </SettingsSection>
                    )}

                    {persona === 'enterprise' && (
                        <SettingsSection title="Enterprise Compliance" icon={Shield} gradient="from-rose-400 to-red-500" delay={0.15}>
                            <label className="flex items-center gap-3 cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={settings.audit_logs_enabled ?? true}
                                    onChange={(e) => update('audit_logs_enabled', e.target.checked)}
                                    className="h-4 w-4 rounded border-slate-300 text-teal-600 focus:ring-teal-500"
                                />
                                <span className="text-sm text-slate-700">Enable Detailed Audit Logs</span>
                            </label>
                        </SettingsSection>
                    )}

                    {/* Notifications */}
                    <SettingsSection title="Notifications" icon={Bell} gradient="from-sky-400 to-blue-500" delay={0.2}>
                        <label className="flex items-center gap-3 cursor-pointer">
                            <input
                                type="checkbox"
                                checked={settings.notifications_enabled}
                                onChange={(e) => update('notifications_enabled', e.target.checked)}
                                className="h-4 w-4 rounded border-slate-300 text-teal-600 focus:ring-teal-500"
                            />
                            <span className="text-sm text-slate-700">Receive email notifications</span>
                        </label>
                    </SettingsSection>

                    {/* Team (conditional) */}
                    {(persona === 'sme' || persona === 'enterprise') && (
                        <SettingsSection title="Team Management" icon={Users} gradient="from-indigo-400 to-violet-500" delay={0.25}>
                            <p className="text-sm text-slate-500">
                                Team member management and role assignments will be available in a future update.
                            </p>
                        </SettingsSection>
                    )}

                    {/* Danger Zone */}
                    <SettingsSection title="Danger Zone" icon={Trash2} gradient="from-rose-500 to-red-600" delay={0.35}>
                        <p className="text-sm text-slate-600 mb-4">
                            Permanently delete your account and all associated data. This action cannot be undone.
                        </p>
                        <button
                            onClick={() => setShowDeleteModal(true)}
                            className="inline-flex items-center gap-2 rounded-xl border border-rose-200 bg-rose-50 px-5 py-2.5 text-sm font-semibold text-rose-700 hover:bg-rose-100 transition-colors"
                        >
                            <Trash2 className="h-4 w-4" />
                            Delete My Account
                        </button>
                    </SettingsSection>
                </div>

                {/* Delete Account Modal */}
                {showDeleteModal && (
                    <DeleteAccountModal
                        confirmText={deleteConfirmText}
                        onConfirmTextChange={setDeleteConfirmText}
                        onConfirm={handleDeleteAccount}
                        onCancel={() => {
                            setShowDeleteModal(false);
                            setDeleteConfirmText('');
                            setDeleteError(null);
                        }}
                        deleting={deleting}
                        error={deleteError}
                    />
                )}
            </PremiumShell>
        </DashboardErrorBoundary>
    );
}
