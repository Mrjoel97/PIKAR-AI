'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Settings } from 'lucide-react';
import PremiumShell from '@/components/layout/PremiumShell';
import DashboardErrorBoundary from '@/components/ui/DashboardErrorBoundary';

// Types for integrations
interface IntegrationField {
    key: string;
    label: string;
    type: 'text' | 'url' | 'email' | 'secret' | 'json';
    placeholder?: string;
}

interface IntegrationTemplate {
    id: string;
    name: string;
    description: string;
    category: string;
    docs_url?: string;
    icon?: string;
    required_fields: IntegrationField[];
    optional_fields: IntegrationField[];
}

interface UserIntegration {
    id: string;
    type: string;
    display_name: string;
    is_active: boolean;
    test_status: 'success' | 'failed' | 'pending' | null;
    last_tested_at: string | null;
}

// Integration templates (matches backend)
const TEMPLATES: IntegrationTemplate[] = [
    {
        id: 'supabase',
        name: 'Supabase',
        description: 'Database, Auth, and Storage',
        category: 'database',
        icon: '🗄️',
        docs_url: 'https://supabase.com/docs',
        required_fields: [
            { key: 'url', label: 'Project URL', type: 'url', placeholder: 'https://xxx.supabase.co' },
            { key: 'anon_key', label: 'Anon/Public Key', type: 'secret' },
            { key: 'service_role_key', label: 'Service Role Key', type: 'secret' },
        ],
        optional_fields: [],
    },
    {
        id: 'resend',
        name: 'Resend',
        description: 'Email API for developers',
        category: 'email',
        icon: '📧',
        docs_url: 'https://resend.com/docs',
        required_fields: [
            { key: 'api_key', label: 'API Key', type: 'secret', placeholder: 're_...' },
        ],
        optional_fields: [
            { key: 'from_email', label: 'Default From Email', type: 'email' },
        ],
    },
    {
        id: 'slack',
        name: 'Slack',
        description: 'Team messaging and notifications',
        category: 'communication',
        icon: '💬',
        docs_url: 'https://api.slack.com/docs',
        required_fields: [
            { key: 'webhook_url', label: 'Webhook URL', type: 'url' },
        ],
        optional_fields: [
            { key: 'bot_token', label: 'Bot Token', type: 'secret' },
        ],
    },
    {
        id: 'notion',
        name: 'Notion',
        description: 'Workspace and documentation',
        category: 'productivity',
        icon: '📝',
        docs_url: 'https://developers.notion.com',
        required_fields: [
            { key: 'api_key', label: 'Integration Token', type: 'secret' },
        ],
        optional_fields: [],
    },
    {
        id: 'stripe',
        name: 'Stripe',
        description: 'Payments and billing',
        category: 'payments',
        icon: '💳',
        docs_url: 'https://stripe.com/docs/api',
        required_fields: [
            { key: 'secret_key', label: 'Secret Key', type: 'secret', placeholder: 'sk_...' },
        ],
        optional_fields: [
            { key: 'webhook_secret', label: 'Webhook Secret', type: 'secret' },
        ],
    },
    {
        id: 'openai',
        name: 'OpenAI',
        description: 'AI models and APIs',
        category: 'ai',
        icon: '🤖',
        docs_url: 'https://platform.openai.com/docs',
        required_fields: [
            { key: 'api_key', label: 'API Key', type: 'secret', placeholder: 'sk-...' },
        ],
        optional_fields: [
            { key: 'org_id', label: 'Organization ID', type: 'text' },
        ],
    },
    {
        id: 'custom',
        name: 'Custom Integration',
        description: 'Configure any API manually',
        category: 'other',
        icon: '⚙️',
        required_fields: [
            { key: 'base_url', label: 'Base URL', type: 'url' },
        ],
        optional_fields: [
            { key: 'api_key', label: 'API Key', type: 'secret' },
            { key: 'headers', label: 'Custom Headers (JSON)', type: 'json' },
        ],
    },
];

// Status badge component
function StatusBadge({ status }: { status: UserIntegration['test_status'] }) {
    if (!status) return null;

    const styles = {
        success: 'bg-green-100 text-green-800',
        failed: 'bg-red-100 text-red-800',
        pending: 'bg-yellow-100 text-yellow-800',
    };

    const labels = {
        success: 'Connected',
        failed: 'Failed',
        pending: 'Pending',
    };

    return (
        <span className={`px-2 py-1 text-xs font-medium rounded-full ${styles[status]}`}>
            {labels[status]}
        </span>
    );
}

// Integration card for templates
function TemplateCard({
    template,
    onSelect
}: {
    template: IntegrationTemplate;
    onSelect: (id: string) => void;
}) {
    return (
        <button
            onClick={() => onSelect(template.id)}
            className="p-4 border border-slate-100/80 rounded-[28px] hover:border-teal-500 shadow-[0_8px_30px_-12px_rgba(15,23,42,0.15)] hover:shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)] transition-all text-left w-full bg-white"
        >
            <div className="flex items-center gap-3 mb-2">
                <span className="text-2xl">{template.icon}</span>
                <div>
                    <h3 className="font-semibold text-gray-900">{template.name}</h3>
                    <p className="text-sm text-gray-500">{template.description}</p>
                </div>
            </div>
            <div className="text-xs text-gray-400 mt-2">
                {template.category}
            </div>
        </button>
    );
}

// User integration card
function IntegrationCard({
    integration,
    template,
    onTest,
    onActivate,
    onDelete,
}: {
    integration: UserIntegration;
    template?: IntegrationTemplate;
    onTest: (id: string) => void;
    onActivate: (id: string) => void;
    onDelete: (id: string) => void;
}) {
    return (
        <div className="p-4 border border-slate-100/80 rounded-[28px] bg-white shadow-[0_8px_30px_-12px_rgba(15,23,42,0.15)]">
            <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                    <span className="text-2xl">{template?.icon || '⚙️'}</span>
                    <div>
                        <h3 className="font-semibold text-gray-900">{integration.display_name}</h3>
                        <p className="text-sm text-gray-500">{template?.description || integration.type}</p>
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    <StatusBadge status={integration.test_status} />
                    {integration.is_active && (
                        <span className="px-2 py-1 text-xs font-medium rounded-full bg-teal-100 text-teal-800">
                            Active
                        </span>
                    )}
                </div>
            </div>

            <div className="flex gap-2 mt-4">
                <button
                    onClick={() => onTest(integration.id)}
                    className="px-3 py-1.5 text-sm border rounded-md hover:bg-gray-50"
                >
                    Test Connection
                </button>
                {integration.test_status === 'success' && !integration.is_active && (
                    <button
                        onClick={() => onActivate(integration.id)}
                        className="px-3 py-1.5 text-sm bg-teal-600 text-white rounded-md hover:bg-teal-700"
                    >
                        Activate
                    </button>
                )}
                <button
                    onClick={() => onDelete(integration.id)}
                    className="px-3 py-1.5 text-sm text-red-600 border border-red-200 rounded-md hover:bg-red-50 ml-auto"
                >
                    Delete
                </button>
            </div>
        </div>
    );
}

// Setup wizard modal
function SetupWizard({
    template,
    onClose,
    onComplete
}: {
    template: IntegrationTemplate;
    onClose: () => void;
    onComplete: (config: Record<string, string>) => void;
}) {
    const [step, setStep] = useState(0);
    const [config, setConfig] = useState<Record<string, string>>({});
    const [testing, setTesting] = useState(false);
    const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);

    const allFields = [...template.required_fields, ...template.optional_fields];
    const currentField = allFields[step];
    const isLastStep = step === allFields.length - 1;
    const isRequired = step < template.required_fields.length;

    const handleNext = () => {
        if (isRequired && !config[currentField.key]) {
            return; // Don't proceed without required fields
        }

        if (isLastStep) {
            handleTest();
        } else {
            setStep(step + 1);
        }
    };

    const handleTest = async () => {
        setTesting(true);
        setTestResult(null);

        // Simulate API call - in production, this calls the backend
        await new Promise(resolve => setTimeout(resolve, 2000));

        // Mock result
        const success = Math.random() > 0.3; // 70% success rate for demo
        setTestResult({
            success,
            message: success
                ? `Connected to ${template.name} successfully!`
                : 'Connection failed. Please check your credentials.',
        });
        setTesting(false);
    };

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl shadow-xl max-w-md w-full overflow-hidden">
                {/* Header */}
                <div className="p-6 border-b bg-gradient-to-r from-teal-500 to-teal-600">
                    <div className="flex items-center gap-3 text-white">
                        <span className="text-3xl">{template.icon}</span>
                        <div>
                            <h2 className="text-xl font-bold">Connect {template.name}</h2>
                            <p className="text-teal-100 text-sm">Step {step + 1} of {allFields.length}</p>
                        </div>
                    </div>
                </div>

                {/* Content */}
                <div className="p-6">
                    {testResult ? (
                        <div className={`p-4 rounded-lg ${testResult.success ? 'bg-green-50' : 'bg-red-50'}`}>
                            <div className="flex items-center gap-3">
                                <span className="text-2xl">{testResult.success ? '✅' : '❌'}</span>
                                <div>
                                    <h3 className={`font-semibold ${testResult.success ? 'text-green-800' : 'text-red-800'}`}>
                                        {testResult.success ? 'Connection Successful' : 'Connection Failed'}
                                    </h3>
                                    <p className={`text-sm ${testResult.success ? 'text-green-600' : 'text-red-600'}`}>
                                        {testResult.message}
                                    </p>
                                </div>
                            </div>

                            {testResult.success && (
                                <button
                                    onClick={() => onComplete(config)}
                                    className="mt-4 w-full py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700 font-medium"
                                >
                                    Save & Activate
                                </button>
                            )}
                        </div>
                    ) : (
                        <>
                            <label className="block mb-2">
                                <span className="text-sm font-medium text-gray-700">
                                    {currentField.label}
                                    {isRequired && <span className="text-red-500 ml-1">*</span>}
                                </span>
                            </label>

                            <input
                                type={currentField.type === 'secret' ? 'password' : 'text'}
                                value={config[currentField.key] || ''}
                                onChange={(e) => setConfig({ ...config, [currentField.key]: e.target.value })}
                                placeholder={currentField.placeholder}
                                className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
                            />

                            {template.docs_url && (
                                <a
                                    href={template.docs_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-sm text-teal-600 hover:underline mt-2 inline-block"
                                >
                                    📖 Where do I find this?
                                </a>
                            )}
                        </>
                    )}
                </div>

                {/* Footer */}
                <div className="p-4 border-t bg-gray-50 flex justify-between">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 text-gray-600 hover:text-gray-800"
                    >
                        Cancel
                    </button>

                    {!testResult && (
                        <div className="flex gap-2">
                            {step > 0 && (
                                <button
                                    onClick={() => setStep(step - 1)}
                                    className="px-4 py-2 border rounded-lg hover:bg-gray-100"
                                >
                                    Back
                                </button>
                            )}
                            <button
                                onClick={handleNext}
                                disabled={isRequired && !config[currentField.key]}
                                className="px-4 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                            >
                                {testing && <span className="animate-spin">⏳</span>}
                                {isLastStep ? (testing ? 'Testing...' : 'Test Connection') : 'Next'}
                            </button>
                        </div>
                    )}

                    {testResult && !testResult.success && (
                        <button
                            onClick={() => {
                                setTestResult(null);
                                setStep(0);
                            }}
                            className="px-4 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700"
                        >
                            Try Again
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}

export default function IntegrationsPage() {
    const [userIntegrations, setUserIntegrations] = useState<UserIntegration[]>([]);
    const [showTemplates, setShowTemplates] = useState(false);
    const [selectedTemplate, setSelectedTemplate] = useState<IntegrationTemplate | null>(null);

    // Mock user integrations - in production, fetch from API
    useEffect(() => {
        // Simulated existing integrations
        setUserIntegrations([
            // Example: user already has Supabase configured
            // {
            //   id: '1',
            //   type: 'supabase',
            //   display_name: 'Production DB',
            //   is_active: true,
            //   test_status: 'success',
            //   last_tested_at: '2024-01-30T10:00:00Z',
            // },
        ]);
    }, []);

    const handleSelectTemplate = (templateId: string) => {
        const template = TEMPLATES.find(t => t.id === templateId);
        if (template) {
            setSelectedTemplate(template);
            setShowTemplates(false);
        }
    };

    const handleComplete = (config: Record<string, string>) => {
        // In production, call API to save
        const newIntegration: UserIntegration = {
            id: Date.now().toString(),
            type: selectedTemplate!.id,
            display_name: selectedTemplate!.name,
            is_active: true,
            test_status: 'success',
            last_tested_at: new Date().toISOString(),
        };
        setUserIntegrations([...userIntegrations, newIntegration]);
        setSelectedTemplate(null);
    };

    return (
        <DashboardErrorBoundary fallbackTitle="Integrations Error">
        <PremiumShell>
        <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: [0.21, 0.47, 0.32, 0.98] }}
        >
        <div className="max-w-4xl mx-auto p-6">
            {/* Header */}
            <div className="flex items-center justify-between mb-8">
                <div>
                    <div className="flex items-center gap-2 mb-2">
                        <Link href="/settings" className="text-gray-500 hover:text-gray-700">
                            Settings
                        </Link>
                        <span className="text-gray-400">/</span>
                        <span className="text-gray-900">Integrations</span>
                    </div>
                    <div className="flex items-center gap-3 mb-1">
                        <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-slate-400 to-slate-600 shadow-lg">
                            <Settings className="h-5 w-5 text-white" />
                        </div>
                        <h1 className="text-2xl font-bold text-gray-900">Connected Apps</h1>
                    </div>
                    <p className="text-gray-600">Connect external services to enhance your AI agents</p>
                </div>

                <button
                    onClick={() => setShowTemplates(true)}
                    className="px-4 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700 font-medium flex items-center gap-2"
                >
                    <span>+</span> Add Integration
                </button>
            </div>

            {/* User's integrations */}
            {userIntegrations.length > 0 ? (
                <div className="space-y-4 mb-8">
                    {userIntegrations.map(integration => (
                        <IntegrationCard
                            key={integration.id}
                            integration={integration}
                            template={TEMPLATES.find(t => t.id === integration.type)}
                            onTest={() => { /* TODO: implement test integration */ }}
                            onActivate={() => { /* TODO: implement activate integration */ }}
                            onDelete={(id) => setUserIntegrations(prev => prev.filter(i => i.id !== id))}
                        />
                    ))}
                </div>
            ) : (
                <div className="text-center py-12 border-2 border-dashed rounded-xl bg-gray-50 mb-8">
                    <div className="text-4xl mb-4">🔌</div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">No integrations yet</h3>
                    <p className="text-gray-600 mb-4">Connect apps like Supabase, Slack, or Stripe</p>
                    <button
                        onClick={() => setShowTemplates(true)}
                        className="px-4 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700"
                    >
                        Add Your First Integration
                    </button>
                </div>
            )}

            {/* Available integrations grid (shown when adding) */}
            {showTemplates && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[80vh] overflow-hidden">
                        <div className="p-6 border-b">
                            <h2 className="text-xl font-bold">Choose an Integration</h2>
                            <p className="text-gray-600">Select a service to connect</p>
                        </div>
                        <div className="p-6 grid grid-cols-2 gap-4 overflow-y-auto max-h-96">
                            {TEMPLATES.map(template => (
                                <TemplateCard
                                    key={template.id}
                                    template={template}
                                    onSelect={handleSelectTemplate}
                                />
                            ))}
                        </div>
                        <div className="p-4 border-t bg-gray-50">
                            <button
                                onClick={() => setShowTemplates(false)}
                                className="w-full py-2 border rounded-lg hover:bg-gray-100"
                            >
                                Cancel
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Setup wizard modal */}
            {selectedTemplate && (
                <SetupWizard
                    template={selectedTemplate}
                    onClose={() => setSelectedTemplate(null)}
                    onComplete={handleComplete}
                />
            )}

            {/* AI Assistant hint */}
            <div className="bg-gradient-to-r from-teal-50 to-blue-50 p-6 rounded-xl border border-teal-200">
                <div className="flex items-start gap-4">
                    <div className="text-3xl">🤖</div>
                    <div>
                        <h3 className="font-semibold text-gray-900 mb-1">Need help setting up?</h3>
                        <p className="text-gray-600 text-sm mb-3">
                            Ask our AI assistant to guide you through the setup process.
                            Just say "Help me connect Supabase" in the chat.
                        </p>
                        <Link
                            href="/dashboard"
                            className="text-teal-600 hover:underline text-sm font-medium"
                        >
                            Open Chat Assistant →
                        </Link>
                    </div>
                </div>
            </div>
        </div>
        </motion.div>
        </PremiumShell>
        </DashboardErrorBoundary>
    );
}
