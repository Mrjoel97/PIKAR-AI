'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { PremiumShell } from '@/components/layout/PremiumShell';
import DashboardErrorBoundary from '@/components/ui/DashboardErrorBoundary';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Settings,
    Search,
    Globe,
    FileText,
    Mail,
    Users,
    Zap,
    CheckCircle2,
    XCircle,
    ExternalLink,
    Twitter,
    Linkedin,
    Facebook,
    Instagram,
    Youtube,
    Link2,
    Unlink,
    Loader2,
    AlertCircle,
    Info,
    Sparkles,
    MessageCircle,
    X,
    Copy,
    Eye,
    EyeOff,
    ChevronRight,
    ChevronDown,
    HelpCircle,
    Rocket,
    Plug,
    BarChart3,
    DollarSign,
    Briefcase,
    MessageSquare,
    Clock,
    Database,
    Radar,
    Plus,
    Trash2,
    ToggleLeft,
    ToggleRight,
} from 'lucide-react';
import {
    fetchProviders,
    fetchIntegrationStatus,
    disconnectProvider as disconnectIntegration,
    type IntegrationProvider,
    type IntegrationStatus,
} from '@/services/integrations';
import { API_BASE_URL, fetchWithAuth } from '@/services/api';

// ============================================================================
// Types
// ============================================================================

interface MCPTool {
    id: string;
    name: string;
    description: string;
    configured: boolean;
    env_var?: string;
    docs_url?: string;
    is_built_in?: boolean;
}

interface BuiltInTool {
    id: string;
    name: string;
    description: string;
    is_built_in: boolean;
    configured: boolean;
    status: string;
}

interface SchedulerReadiness {
    configuration_ready: boolean;
    worker_schedule_tick_enabled: boolean;
    secure_endpoints_enabled: boolean;
    deployment_required: boolean;
    status: string;
    message: string;
}

interface SocialPlatform {
    platform: string;
    display_name: string;
    icon: string;
    connected: boolean;
    username?: string;
    connected_at?: string;
    requires_config: boolean;
    config_keys: string[];
}

interface GoogleWorkspaceStatus {
    connected: boolean;
    email?: string;
    provider?: string;
    features: string[];
    message: string;
}

interface SetupWizardStep {
    title: string;
    description: string;
    action?: string;
    link?: string;
}

interface MonitoringJob {
    id: string;
    topic: string;
    monitoring_type: 'competitor' | 'market' | 'topic';
    importance: 'critical' | 'normal' | 'low';
    is_active: boolean;
    keyword_triggers: string[];
    pinned_urls: string[];
    excluded_urls: string[];
    last_run_at: string | null;
    created_at: string;
}

interface DBConnection {
    provider: string;
    account_name: string;
    connected_at: string;
}

interface WebhookEndpoint {
    id: string;
    url: string;
    events: string[];
    active: boolean;
    description: string;
    consecutive_failures: number;
    created_at: string;
    secret_preview?: string;
}

interface WebhookEvent {
    event_type: string;
    description: string;
    schema?: object;
}

interface WebhookDelivery {
    id: string;
    event_type: string;
    status: 'delivered' | 'failed' | 'pending';
    attempts: number;
    response_code: number | null;
    created_at: string;
}

// Tool setup guides for the wizard
const TOOL_SETUP_GUIDES: Record<string, { 
    name: string; 
    steps: SetupWizardStep[]; 
    freeTier: string;
    signupUrl: string;
}> = {
    tavily: {
        name: "Tavily Web Search",
        freeTier: "1,000 searches/month free",
        signupUrl: "https://tavily.com",
        steps: [
            { title: "Create Account", description: "Go to Tavily and create a free account", link: "https://tavily.com" },
            { title: "Find API Keys", description: "Navigate to your dashboard and find the API Keys section" },
            { title: "Generate Key", description: "Click 'Create API Key' to generate a new key" },
            { title: "Copy Key", description: "Copy your API key (starts with 'tvly-')" },
            { title: "Enter Below", description: "Paste your API key in the field below" },
        ]
    },
    firecrawl: {
        name: "Firecrawl Web Scraping",
        freeTier: "500 pages/month free",
        signupUrl: "https://firecrawl.dev",
        steps: [
            { title: "Sign Up", description: "Visit Firecrawl and create an account", link: "https://firecrawl.dev" },
            { title: "Dashboard", description: "Go to Dashboard and find API Keys" },
            { title: "Generate", description: "Generate a new API key" },
            { title: "Copy", description: "Copy your API key" },
            { title: "Enter Below", description: "Paste your API key in the field below" },
        ]
    },
    stitch: {
        name: "Stitch Landing Pages",
        freeTier: "10 pages/month free",
        signupUrl: "https://stitch.withgoogle.com",
        steps: [
            { title: "Sign In", description: "Visit Stitch and sign in with Google", link: "https://stitch.withgoogle.com" },
            { title: "Settings", description: "Go to Settings > API Access" },
            { title: "Generate", description: "Generate a new API key" },
            { title: "Copy", description: "Copy your API key" },
            { title: "Enter Below", description: "Paste your API key in the field below" },
        ]
    },
    resend: {
        name: "Resend Email",
        freeTier: "3,000 emails/month free, 100/day",
        signupUrl: "https://resend.com",
        steps: [
            { title: "Create Account", description: "Go to Resend and create a free account", link: "https://resend.com" },
            { title: "Verify Domain", description: "Add and verify your domain in Settings > Domains" },
            { title: "API Keys", description: "Navigate to API Keys in the sidebar" },
            { title: "Create Key", description: "Click 'Create API Key'" },
            { title: "Copy & Save", description: "Copy the key (starts with 're_')" },
            { title: "Enter Below", description: "Paste your API key in the field below" },
        ]
    },
    hubspot: {
        name: "HubSpot CRM",
        freeTier: "Free CRM with unlimited contacts",
        signupUrl: "https://www.hubspot.com",
        steps: [
            { title: "Sign Up", description: "Go to HubSpot and sign up (free CRM available)", link: "https://www.hubspot.com" },
            { title: "Settings", description: "Go to Settings (gear icon) > Integrations > Private Apps" },
            { title: "Create App", description: "Click 'Create a private app'" },
            { title: "Name & Scopes", description: "Name it 'Pikar AI' and select CRM scopes" },
            { title: "Copy Token", description: "Copy the access token after creation" },
            { title: "Enter Below", description: "Paste your access token in the field below" },
        ]
    },
    stripe: {
        name: "Stripe Payments",
        freeTier: "No monthly fees, 2.9% + 30¢ per transaction",
        signupUrl: "https://stripe.com",
        steps: [
            { title: "Create Account", description: "Go to Stripe and create an account", link: "https://stripe.com" },
            { title: "Dashboard", description: "Go to Developers > API Keys in the dashboard" },
            { title: "Get Key", description: "Copy your Secret Key (starts with 'sk_')" },
            { title: "Test Mode", description: "For testing, use your test mode key (sk_test_...)" },
            { title: "Enter Below", description: "Paste your API key in the field below" },
        ]
    },
    canva: {
        name: "Canva Media Creation",
        freeTier: "Free tier with limited exports",
        signupUrl: "https://www.canva.com/developers",
        steps: [
            { title: "Developer Portal", description: "Go to Canva Developers and sign in", link: "https://www.canva.com/developers" },
            { title: "Create App", description: "Create a new integration/app" },
            { title: "Credentials", description: "Go to the Credentials section" },
            { title: "Generate Key", description: "Generate an API key" },
            { title: "Enter Below", description: "Paste your API key in the field below" },
        ]
    },
};

// ============================================================================
// Icon Mapping
// ============================================================================

const mcpToolIcons: Record<string, React.ReactNode> = {
    tavily: <Search className="w-5 h-5" />,
    firecrawl: <Globe className="w-5 h-5" />,
    stitch: <Sparkles className="w-5 h-5" />,
    stripe: <Zap className="w-5 h-5" />,
    canva: <FileText className="w-5 h-5" />,
    resend: <Mail className="w-5 h-5" />,
    hubspot: <Users className="w-5 h-5" />,
};

const socialIcons: Record<string, React.ReactNode> = {
    twitter: <Twitter className="w-5 h-5" />,
    linkedin: <Linkedin className="w-5 h-5" />,
    facebook: <Facebook className="w-5 h-5" />,
    instagram: <Instagram className="w-5 h-5" />,
    youtube: <Youtube className="w-5 h-5" />,
    tiktok: <Zap className="w-5 h-5" />, // Using Zap as TikTok placeholder
};

const socialColors: Record<string, string> = {
    twitter: 'bg-black text-white',
    linkedin: 'bg-[#0A66C2] text-white',
    facebook: 'bg-[#1877F2] text-white',
    instagram: 'bg-gradient-to-r from-[#833AB4] via-[#FD1D1D] to-[#F77737] text-white',
    youtube: 'bg-[#FF0000] text-white',
    tiktok: 'bg-black text-white',
};

// ============================================================================
// Components
// ============================================================================

function SectionHeader({ 
    icon, 
    title, 
    description 
}: { 
    icon: React.ReactNode; 
    title: string; 
    description: string;
}) {
    return (
        <div className="flex items-start gap-4 mb-6">
            <div className="p-3 bg-gradient-to-br from-teal-500 to-cyan-600 rounded-2xl text-white shadow-lg">
                {icon}
            </div>
            <div>
                <h2 className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">{title}</h2>
                <p className="text-slate-500 text-sm mt-1">{description}</p>
            </div>
        </div>
    );
}

// Setup Wizard Modal Component
function SetupWizardModal({
    tool,
    isOpen,
    onClose,
    onSave,
}: {
    tool: MCPTool | null;
    isOpen: boolean;
    onClose: () => void;
    onSave: (toolId: string, apiKey: string) => Promise<void>;
}) {
    const [currentStep, setCurrentStep] = useState(0);
    const [apiKey, setApiKey] = useState('');
    const [showKey, setShowKey] = useState(false);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    if (!isOpen || !tool) return null;

    const guide = TOOL_SETUP_GUIDES[tool.id];
    if (!guide) return null;

    const handleSave = async () => {
        if (!apiKey.trim()) {
            setError('Please enter your API key');
            return;
        }
        
        setSaving(true);
        setError(null);
        
        try {
            await onSave(tool.id, apiKey);
            setApiKey('');
            setCurrentStep(0);
            onClose();
        } catch (e) {
            setError('Failed to save API key. Please try again.');
        } finally {
            setSaving(false);
        }
    };

    const handleClose = () => {
        setApiKey('');
        setCurrentStep(0);
        setError(null);
        onClose();
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="bg-white rounded-[28px] shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)] w-full max-w-lg mx-4 overflow-hidden"
            >
                {/* Header */}
                <div className="bg-gradient-to-r from-teal-500 to-cyan-600 px-6 py-4">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-white/20 rounded-lg">
                                {mcpToolIcons[tool.id] || <Zap className="w-5 h-5 text-white" />}
                            </div>
                            <div>
                                <h3 className="font-semibold text-white">{guide.name} Setup</h3>
                                <p className="text-white/80 text-sm">{guide.freeTier}</p>
                            </div>
                        </div>
                        <button onClick={handleClose} className="p-2 hover:bg-white/20 rounded-lg transition-colors">
                            <X className="w-5 h-5 text-white" />
                        </button>
                    </div>
                </div>

                {/* Steps Progress */}
                <div className="px-6 py-4 border-b border-slate-100">
                    <div className="flex items-center gap-1">
                        {guide.steps.map((_, index) => (
                            <div 
                                key={index}
                                className={`h-1.5 flex-1 rounded-full transition-colors ${
                                    index <= currentStep ? 'bg-teal-500' : 'bg-slate-200'
                                }`}
                            />
                        ))}
                    </div>
                    <p className="text-xs text-slate-500 mt-2">
                        Step {currentStep + 1} of {guide.steps.length}
                    </p>
                </div>

                {/* Current Step Content */}
                <div className="px-6 py-6">
                    <div className="mb-6">
                        <h4 className="font-medium text-slate-800 mb-2">
                            {guide.steps[currentStep].title}
                        </h4>
                        <p className="text-slate-600">
                            {guide.steps[currentStep].description}
                        </p>
                        {guide.steps[currentStep].link && (
                            <a
                                href={guide.steps[currentStep].link}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-2 mt-3 px-4 py-2 bg-teal-50 text-teal-600 rounded-2xl hover:bg-teal-100 transition-colors"
                            >
                                <ExternalLink className="w-4 h-4" />
                                Open {guide.name.split(' ')[0]}
                            </a>
                        )}
                    </div>

                    {/* API Key Input (shown on last step) */}
                    {currentStep === guide.steps.length - 1 && (
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-2">
                                    Your API Key
                                </label>
                                <div className="relative">
                                    <input
                                        type={showKey ? 'text' : 'password'}
                                        value={apiKey}
                                        onChange={(e) => setApiKey(e.target.value)}
                                        placeholder="Paste your API key here..."
                                        className="w-full px-4 py-3 border-2 border-slate-200 rounded-2xl focus:border-teal-500 focus:outline-none font-mono text-sm"
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setShowKey(!showKey)}
                                        className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-slate-600"
                                    >
                                        {showKey ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                                    </button>
                                </div>
                            </div>
                            {error && (
                                <p className="text-red-500 text-sm flex items-center gap-2">
                                    <AlertCircle className="w-4 h-4" />
                                    {error}
                                </p>
                            )}
                        </div>
                    )}
                </div>

                {/* Footer Actions */}
                <div className="px-6 py-4 bg-slate-50 flex items-center justify-between">
                    <button
                        onClick={() => setCurrentStep(Math.max(0, currentStep - 1))}
                        disabled={currentStep === 0}
                        className="px-4 py-2 text-slate-600 hover:text-slate-800 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        Back
                    </button>
                    
                    {currentStep < guide.steps.length - 1 ? (
                        <button
                            onClick={() => setCurrentStep(currentStep + 1)}
                            className="flex items-center gap-2 px-6 py-2.5 bg-teal-600 text-white rounded-2xl hover:bg-teal-700 transition-colors"
                        >
                            Next
                            <ChevronRight className="w-4 h-4" />
                        </button>
                    ) : (
                        <button
                            onClick={handleSave}
                            disabled={saving || !apiKey.trim()}
                            className="flex items-center gap-2 px-6 py-2.5 bg-emerald-600 text-white rounded-2xl hover:bg-emerald-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {saving ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                                <CheckCircle2 className="w-4 h-4" />
                            )}
                            Save & Activate
                        </button>
                    )}
                </div>
            </motion.div>
        </div>
    );
}

// Ask AI Help Banner
function AskAIHelpBanner({ onAskAI }: { onAskAI: () => void }) {
    return (
        <div className="bg-gradient-to-r from-teal-500 via-cyan-500 to-sky-500 rounded-[28px] p-6 text-white shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <div className="p-3 bg-white/20 rounded-2xl backdrop-blur-sm">
                        <MessageCircle className="w-6 h-6" />
                    </div>
                    <div>
                        <h3 className="font-semibold text-lg">Need help setting things up?</h3>
                        <p className="text-white/80 text-sm mt-1">
                            I can guide you through configuration step by step. Just ask!
                        </p>
                    </div>
                </div>
                <button
                    onClick={onAskAI}
                    className="flex items-center gap-2 px-5 py-2.5 bg-white text-teal-600 font-medium rounded-2xl hover:bg-white/90 transition-colors shadow-lg"
                >
                    <HelpCircle className="w-5 h-5" />
                    Ask AI for Help
                </button>
            </div>
        </div>
    );
}

function MCPToolCard({ 
    tool, 
    onSetup 
}: { 
    tool: MCPTool; 
    onSetup: (tool: MCPTool) => void;
}) {
    const guide = TOOL_SETUP_GUIDES[tool.id];
    
    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="group bg-white border border-slate-100/80 rounded-2xl p-5 hover:border-teal-200 hover:shadow-[0_8px_30px_-15px_rgba(15,23,42,0.2)] hover:-translate-y-0.5 transition-all duration-200"
        >
            <div className="flex items-start justify-between">
                <div className="flex items-start gap-4 flex-1">
                    <div className={`p-2.5 rounded-lg ${tool.configured ? 'bg-emerald-100 text-emerald-600' : 'bg-slate-100 text-slate-400'}`}>
                        {mcpToolIcons[tool.id] || <Zap className="w-5 h-5" />}
                    </div>
                    <div className="flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                            <h3 className="font-medium text-slate-800">{tool.name}</h3>
                            {tool.configured ? (
                                <span className="flex items-center gap-1 text-xs font-medium text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">
                                    <CheckCircle2 className="w-3 h-3" />
                                    Active
                                </span>
                            ) : (
                                <span className="flex items-center gap-1 text-xs font-medium text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">
                                    <XCircle className="w-3 h-3" />
                                    Not Configured
                                </span>
                            )}
                            {guide && (
                                <span className="text-xs text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">
                                    {guide.freeTier}
                                </span>
                            )}
                        </div>
                        <p className="text-sm text-slate-500 mt-1">{tool.description}</p>
                        <div className="flex items-center gap-3 mt-3">
                            {tool.docs_url && (
                                <a
                                    href={tool.docs_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="flex items-center gap-1 text-xs text-teal-600 hover:text-teal-800 transition-colors"
                                >
                                    <ExternalLink className="w-3 h-3" />
                                    Documentation
                                </a>
                            )}
                        </div>
                    </div>
                </div>
                <div className="ml-4">
                    {tool.configured ? (
                        <button
                            onClick={() => onSetup(tool)}
                            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-2xl transition-colors"
                        >
                            <Settings className="w-4 h-4" />
                            Update
                        </button>
                    ) : (
                        <button
                            onClick={() => onSetup(tool)}
                            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-teal-600 hover:bg-teal-700 rounded-2xl transition-colors"
                        >
                            <Rocket className="w-4 h-4" />
                            Set Up
                        </button>
                    )}
                </div>
            </div>
        </motion.div>
    );
}

function SocialPlatformCard({ 
    platform, 
    onConnect, 
    onDisconnect,
    isLoading 
}: { 
    platform: SocialPlatform; 
    onConnect: (platform: string) => void;
    onDisconnect: (platform: string) => void;
    isLoading: boolean;
}) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="group bg-white border border-slate-100/80 rounded-2xl p-5 hover:border-teal-200 hover:shadow-[0_8px_30px_-15px_rgba(15,23,42,0.2)] hover:-translate-y-0.5 transition-all duration-200"
        >
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <div className={`p-2.5 rounded-lg ${socialColors[platform.platform] || 'bg-slate-100 text-slate-600'}`}>
                        {socialIcons[platform.icon] || <Globe className="w-5 h-5" />}
                    </div>
                    <div>
                        <div className="flex items-center gap-2">
                            <h3 className="font-medium text-slate-800">{platform.display_name}</h3>
                            {platform.connected && (
                                <span className="flex items-center gap-1 text-xs font-medium text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">
                                    <CheckCircle2 className="w-3 h-3" />
                                    Connected
                                </span>
                            )}
                        </div>
                        {platform.connected && platform.username && (
                            <p className="text-sm text-slate-500 mt-0.5">@{platform.username}</p>
                        )}
                        {platform.requires_config && !platform.connected && (
                            <p className="text-xs text-amber-600 mt-1 flex items-center gap-1">
                                <AlertCircle className="w-3 h-3" />
                                OAuth credentials required
                            </p>
                        )}
                    </div>
                </div>
                <div>
                    {platform.connected ? (
                        <button
                            onClick={() => onDisconnect(platform.platform)}
                            disabled={isLoading}
                            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-red-600 bg-red-50 hover:bg-red-100 rounded-2xl transition-colors disabled:opacity-50"
                        >
                            {isLoading ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                                <Unlink className="w-4 h-4" />
                            )}
                            Disconnect
                        </button>
                    ) : (
                        <button
                            onClick={() => onConnect(platform.platform)}
                            disabled={isLoading || platform.requires_config}
                            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-teal-600 hover:bg-teal-700 rounded-2xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {isLoading ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                                <Link2 className="w-4 h-4" />
                            )}
                            Connect
                        </button>
                    )}
                </div>
            </div>
        </motion.div>
    );
}

function InfoBanner({ type, message }: { type: 'success' | 'error' | 'info'; message: string }) {
    const styles = {
        success: 'bg-emerald-50 border-emerald-200 text-emerald-800',
        error: 'bg-red-50 border-red-200 text-red-800',
        info: 'bg-blue-50 border-blue-200 text-blue-800',
    };

    const icons = {
        success: <CheckCircle2 className="w-5 h-5 text-emerald-600" />,
        error: <XCircle className="w-5 h-5 text-red-600" />,
        info: <Info className="w-5 h-5 text-blue-600" />,
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className={`flex items-center gap-3 p-4 rounded-2xl border ${styles[type]}`}
        >
            {icons[type]}
            <p className="text-sm font-medium">{message}</p>
        </motion.div>
    );
}

// ============================================================================
// Ad Platform Budget Cap Helpers
// ============================================================================

const AD_PLATFORM_KEYS = new Set(['google_ads', 'meta_ads']);

interface BudgetCapData {
    monthly_cap: number | null;
    used_this_month?: number | null;
}

/** Thin wrapper around the backend budget-cap API. Uses fetchWithAuth for JWT. */
async function fetchBudgetCap(provider: string): Promise<BudgetCapData> {
    try {
        const res = await fetchWithAuth(`/integrations/${provider}/budget-cap`);
        if (!res.ok) return { monthly_cap: null };
        const data = await res.json();
        return {
            monthly_cap: typeof data.monthly_cap === 'number' ? data.monthly_cap : null,
            used_this_month: typeof data.used_this_month === 'number' ? data.used_this_month : null,
        };
    } catch {
        return { monthly_cap: null };
    }
}

async function saveBudgetCap(provider: string, monthly_cap: number): Promise<void> {
    const res = await fetchWithAuth(`/integrations/${provider}/budget-cap`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ monthly_cap }),
    });
    if (!res.ok) throw new Error('Failed to save budget cap');
}

/** Progress bar color based on spend-to-cap ratio. */
function capProgressColor(ratio: number): string {
    if (ratio >= 0.9) return 'bg-red-500';
    if (ratio >= 0.7) return 'bg-amber-400';
    return 'bg-emerald-500';
}

/**
 * Budget cap section rendered inside expanded ad platform provider cards.
 * Shows current cap, spend progress bar, and a save input.
 */
function BudgetCapSection({
    providerKey,
    capData,
    inputValue,
    onInputChange,
    onSave,
    saving,
}: {
    providerKey: string;
    capData: BudgetCapData | undefined;
    inputValue: string;
    onInputChange: (val: string) => void;
    onSave: () => void;
    saving: boolean;
}) {
    const cap = capData?.monthly_cap ?? null;
    const used = capData?.used_this_month ?? null;
    const ratio = cap && used != null ? Math.min(used / cap, 1) : null;

    return (
        <div className="mt-4 pt-4 border-t border-slate-100">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400 mb-3">
                Monthly Budget Cap
            </p>

            {/* Spend progress bar (only when connected and cap is set) */}
            {cap != null && used != null && (
                <div className="mb-3">
                    <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
                        <span>${used.toFixed(0)} spent</span>
                        <span>${cap.toFixed(0)} cap</span>
                    </div>
                    <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
                        <div
                            className={`h-full rounded-full transition-all ${capProgressColor(ratio ?? 0)}`}
                            style={{ width: `${((ratio ?? 0) * 100).toFixed(1)}%` }}
                        />
                    </div>
                    {ratio != null && ratio >= 0.9 && (
                        <p className="text-xs text-red-600 mt-1 flex items-center gap-1">
                            <AlertCircle className="w-3 h-3" />
                            Approaching cap — consider pausing campaigns
                        </p>
                    )}
                </div>
            )}

            {cap == null && (
                <p className="text-xs text-amber-600 flex items-center gap-1 mb-3">
                    <AlertCircle className="w-3 h-3" />
                    No budget cap set. A cap is required before connecting.
                </p>
            )}

            {/* Cap input + save */}
            <div className="flex items-center gap-2">
                <div className="relative flex-1">
                    <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <input
                        type="number"
                        min="1"
                        step="50"
                        value={inputValue}
                        onChange={(e) => onInputChange(e.target.value)}
                        placeholder={cap != null ? cap.toFixed(0) : 'e.g. 500'}
                        className="w-full pl-8 pr-3 py-2 text-sm border border-slate-200 rounded-xl focus:border-teal-500 focus:outline-none"
                    />
                </div>
                <button
                    onClick={onSave}
                    disabled={saving || !inputValue.trim()}
                    className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-teal-600 hover:bg-teal-700 rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    {saving ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                        <CheckCircle2 className="w-3.5 h-3.5" />
                    )}
                    {cap != null ? 'Update' : 'Set Cap'}
                </button>
            </div>
            <p className="text-xs text-slate-400 mt-1.5">
                {cap != null
                    ? `Current cap: $${cap.toFixed(0)}/month. Update above to change.`
                    : `Set a monthly spending ceiling before connecting ${providerKey === 'google_ads' ? 'Google Ads' : 'Meta Ads'}.`}
            </p>
        </div>
    );
}

// ============================================================================
// PM Sync Helpers
// ============================================================================

const PM_PROVIDER_KEYS = new Set(['linear', 'asana']);

const NOTIF_PROVIDER_KEYS = new Set(['slack', 'teams']);

// ============================================================================
// Notification Rule Helpers
// ============================================================================

interface NotificationRule {
    id: string;
    provider: string;
    event_type: string;
    channel_id: string;
    channel_name: string;
    enabled: boolean;
}

interface NotificationChannel {
    id: string;
    name: string;
    is_private: boolean;
}

interface NotificationConfig {
    daily_briefing: boolean;
    briefing_channel_id: string;
    briefing_channel_name: string;
    briefing_time_utc: string;
}

interface SupportedEvent {
    type: string;
    label: string;
}

async function fetchNotificationRules(provider: string): Promise<NotificationRule[]> {
    try {
        const res = await fetchWithAuth(`/integrations/${provider}/notification-rules`);
        if (!res.ok) return [];
        return await res.json();
    } catch {
        return [];
    }
}

async function fetchNotificationChannels(provider: string): Promise<NotificationChannel[]> {
    try {
        const res = await fetchWithAuth(`/integrations/${provider}/notification-channels`);
        if (!res.ok) return [];
        return await res.json();
    } catch {
        return [];
    }
}

async function fetchNotificationConfig(provider: string): Promise<NotificationConfig | null> {
    try {
        const res = await fetchWithAuth(`/integrations/${provider}/notification-config`);
        if (!res.ok) return null;
        return await res.json();
    } catch {
        return null;
    }
}

async function fetchSupportedEvents(): Promise<SupportedEvent[]> {
    try {
        const res = await fetchWithAuth('/integrations/notification-events');
        if (!res.ok) return [];
        return await res.json();
    } catch {
        return [];
    }
}

/** Notification rules + daily briefing section rendered inside Slack/Teams cards. */
function NotificationRulesSection({
    provider,
    rules,
    channels,
    config,
    events,
    onSaveRule,
    onToggleRule,
    onDeleteRule,
    onSaveConfig,
    onTestNotification,
}: {
    provider: string;
    rules: NotificationRule[];
    channels: NotificationChannel[];
    config: NotificationConfig | null;
    events: SupportedEvent[];
    onSaveRule: (provider: string, event_type: string, channel_id: string, channel_name: string) => Promise<void>;
    onToggleRule: (provider: string, ruleId: string, enabled: boolean) => Promise<void>;
    onDeleteRule: (provider: string, ruleId: string) => Promise<void>;
    onSaveConfig: (provider: string, cfg: Partial<NotificationConfig>) => Promise<void>;
    onTestNotification: (provider: string) => Promise<void>;
}) {
    const isTeams = provider === 'teams';

    // Local form state for daily briefing
    const [briefingEnabled, setBriefingEnabled] = useState(config?.daily_briefing ?? false);
    const [briefingChannel, setBriefingChannel] = useState(config?.briefing_channel_id ?? '');
    const [briefingChannelName, setBriefingChannelName] = useState(config?.briefing_channel_name ?? '');
    const [briefingTime, setBriefingTime] = useState(config?.briefing_time_utc ?? '08:00');
    const [savingConfig, setSavingConfig] = useState(false);
    const [testing, setTesting] = useState(false);

    // Inline add-rule form
    const [addingRule, setAddingRule] = useState(false);
    const [newEventType, setNewEventType] = useState('');
    const [newChannelId, setNewChannelId] = useState('');
    const [newChannelName, setNewChannelName] = useState('');
    const [savingRule, setSavingRule] = useState(false);

    // Sync local config state when prop changes
    useEffect(() => {
        setBriefingEnabled(config?.daily_briefing ?? false);
        setBriefingChannel(config?.briefing_channel_id ?? '');
        setBriefingChannelName(config?.briefing_channel_name ?? '');
        setBriefingTime(config?.briefing_time_utc ?? '08:00');
    }, [config]);

    const handleSaveConfig = async () => {
        setSavingConfig(true);
        try {
            await onSaveConfig(provider, {
                daily_briefing: briefingEnabled,
                briefing_channel_id: isTeams ? 'webhook' : briefingChannel,
                briefing_channel_name: briefingChannelName || (isTeams ? 'Teams Webhook' : ''),
                briefing_time_utc: briefingTime,
            });
        } finally {
            setSavingConfig(false);
        }
    };

    const handleAddRule = async () => {
        if (!newEventType) return;
        const channelId = isTeams ? 'webhook' : newChannelId;
        const channelName = isTeams ? 'Teams Webhook' : newChannelName;
        setSavingRule(true);
        try {
            await onSaveRule(provider, newEventType, channelId, channelName);
            setAddingRule(false);
            setNewEventType('');
            setNewChannelId('');
            setNewChannelName('');
        } finally {
            setSavingRule(false);
        }
    };

    const handleTest = async () => {
        setTesting(true);
        try {
            await onTestNotification(provider);
        } finally {
            setTesting(false);
        }
    };

    return (
        <div className="mt-4 space-y-4">
            {/* Notification Rules */}
            <div className="border border-slate-200 rounded-lg p-4 space-y-3">
                <div className="flex items-center justify-between">
                    <h4 className="text-sm font-semibold text-slate-700">Notification Rules</h4>
                    <button
                        onClick={handleTest}
                        disabled={testing}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-teal-700 bg-teal-50 hover:bg-teal-100 rounded-lg transition-colors disabled:opacity-50"
                    >
                        {testing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Zap className="w-3.5 h-3.5" />}
                        Test Notification
                    </button>
                </div>

                {/* Existing rules table */}
                {rules.length > 0 ? (
                    <div className="space-y-2">
                        {rules.map((rule) => {
                            const eventLabel = events.find(e => e.type === rule.event_type)?.label ?? rule.event_type;
                            return (
                                <div key={rule.id} className="flex items-center gap-3 bg-slate-50 rounded-lg px-3 py-2">
                                    <div className="flex-1 min-w-0">
                                        <p className="text-sm font-medium text-slate-700 truncate">{eventLabel}</p>
                                        {!isTeams && (
                                            <p className="text-xs text-slate-500 truncate">#{rule.channel_name || rule.channel_id}</p>
                                        )}
                                    </div>
                                    {/* Enabled toggle */}
                                    <button
                                        onClick={() => onToggleRule(provider, rule.id, !rule.enabled)}
                                        className={`relative inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full transition-colors duration-200 ease-in-out focus:outline-none ${rule.enabled ? 'bg-teal-500' : 'bg-slate-300'}`}
                                        title={rule.enabled ? 'Disable' : 'Enable'}
                                    >
                                        <span className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow transition duration-200 ease-in-out mt-0.5 ${rule.enabled ? 'translate-x-4' : 'translate-x-0.5'}`} />
                                    </button>
                                    {/* Delete */}
                                    <button
                                        onClick={() => onDeleteRule(provider, rule.id)}
                                        className="p-1 text-slate-400 hover:text-red-500 rounded transition-colors"
                                        title="Delete rule"
                                    >
                                        <X className="w-3.5 h-3.5" />
                                    </button>
                                </div>
                            );
                        })}
                    </div>
                ) : (
                    <p className="text-sm text-slate-400">No rules configured yet.</p>
                )}

                {/* Add rule form */}
                {addingRule ? (
                    <div className="border border-teal-200 rounded-lg p-3 space-y-2 bg-teal-50/30">
                        <select
                            value={newEventType}
                            onChange={e => setNewEventType(e.target.value)}
                            className="w-full text-sm border border-slate-200 rounded-lg px-3 py-1.5 focus:border-teal-400 focus:outline-none bg-white"
                        >
                            <option value="">Select event...</option>
                            {events.map(ev => (
                                <option key={ev.type} value={ev.type}>{ev.label}</option>
                            ))}
                        </select>
                        {!isTeams && (
                            <select
                                value={newChannelId}
                                onChange={e => {
                                    const ch = channels.find(c => c.id === e.target.value);
                                    setNewChannelId(e.target.value);
                                    setNewChannelName(ch?.name ?? '');
                                }}
                                className="w-full text-sm border border-slate-200 rounded-lg px-3 py-1.5 focus:border-teal-400 focus:outline-none bg-white"
                            >
                                <option value="">Select channel...</option>
                                {channels.map(ch => (
                                    <option key={ch.id} value={ch.id}>#{ch.name}{ch.is_private ? ' (private)' : ''}</option>
                                ))}
                            </select>
                        )}
                        <div className="flex gap-2">
                            <button
                                onClick={handleAddRule}
                                disabled={savingRule || !newEventType || (!isTeams && !newChannelId)}
                                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-teal-600 hover:bg-teal-700 rounded-lg transition-colors disabled:opacity-50"
                            >
                                {savingRule ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
                                Save Rule
                            </button>
                            <button
                                onClick={() => setAddingRule(false)}
                                className="px-3 py-1.5 text-xs text-slate-500 hover:text-slate-700 rounded-lg transition-colors"
                            >
                                Cancel
                            </button>
                        </div>
                    </div>
                ) : (
                    <button
                        onClick={() => setAddingRule(true)}
                        className="flex items-center gap-1.5 text-xs font-medium text-teal-600 hover:text-teal-800 transition-colors"
                    >
                        <span className="text-base leading-none">+</span> Add Rule
                    </button>
                )}
            </div>

            {/* Daily Briefing */}
            <div className="border border-slate-200 rounded-lg p-4 space-y-3">
                <h4 className="text-sm font-semibold text-slate-700">Daily Briefing</h4>
                <p className="text-xs text-slate-500">Receive a morning summary of pending approvals, tasks, and key metrics.</p>

                {/* Enable toggle */}
                <div className="flex items-center gap-3">
                    <button
                        onClick={() => setBriefingEnabled(v => !v)}
                        className={`relative inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full transition-colors duration-200 ease-in-out focus:outline-none ${briefingEnabled ? 'bg-teal-500' : 'bg-slate-300'}`}
                    >
                        <span className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow transition duration-200 ease-in-out mt-0.5 ${briefingEnabled ? 'translate-x-4' : 'translate-x-0.5'}`} />
                    </button>
                    <span className="text-sm text-slate-600">Enable daily briefing</span>
                </div>

                {briefingEnabled && (
                    <div className="space-y-2">
                        {/* Channel selector (Slack only) */}
                        {!isTeams && (
                            <div>
                                <label className="block text-xs text-slate-500 mb-1">Briefing channel</label>
                                <select
                                    value={briefingChannel}
                                    onChange={e => {
                                        const ch = channels.find(c => c.id === e.target.value);
                                        setBriefingChannel(e.target.value);
                                        setBriefingChannelName(ch?.name ?? '');
                                    }}
                                    className="w-full text-sm border border-slate-200 rounded-lg px-3 py-1.5 focus:border-teal-400 focus:outline-none bg-white"
                                >
                                    <option value="">Select channel...</option>
                                    {channels.map(ch => (
                                        <option key={ch.id} value={ch.id}>#{ch.name}</option>
                                    ))}
                                </select>
                            </div>
                        )}
                        {/* Time picker */}
                        <div>
                            <label className="block text-xs text-slate-500 mb-1">Send at (UTC)</label>
                            <input
                                type="time"
                                value={briefingTime}
                                onChange={e => setBriefingTime(e.target.value)}
                                className="text-sm border border-slate-200 rounded-lg px-3 py-1.5 focus:border-teal-400 focus:outline-none bg-white"
                            />
                        </div>
                    </div>
                )}

                <button
                    onClick={handleSaveConfig}
                    disabled={savingConfig}
                    className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-teal-600 hover:bg-teal-700 rounded-xl transition-colors disabled:opacity-50"
                >
                    {savingConfig ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                    Save Briefing Settings
                </button>
            </div>
        </div>
    );
}

interface PMProject {
    id: string;
    name: string;
    key?: string;
    workspace?: string;
}

interface PMStatusMapping {
    external_state_id: string;
    external_state_name: string;
    pikar_status: string;
}

const PIKAR_STATUSES = ['pending', 'in_progress', 'completed', 'cancelled'];

async function fetchPMProjects(provider: string): Promise<PMProject[]> {
    try {
        const res = await fetchWithAuth(`/integrations/${provider}/projects`);
        if (!res.ok) return [];
        const data = await res.json();
        return data.projects ?? data ?? [];
    } catch {
        return [];
    }
}

async function fetchPMSyncConfig(provider: string): Promise<{ project_ids: string[]; last_sync_at?: string }> {
    try {
        const res = await fetchWithAuth(`/integrations/${provider}/sync-config`);
        if (!res.ok) return { project_ids: [] };
        const data = await res.json();
        return { project_ids: data.project_ids ?? [], last_sync_at: data.last_sync_at };
    } catch {
        return { project_ids: [] };
    }
}

async function fetchPMStatusMappings(provider: string): Promise<PMStatusMapping[]> {
    try {
        const res = await fetchWithAuth(`/integrations/${provider}/status-mappings`);
        if (!res.ok) return [];
        const data = await res.json();
        return data.mappings ?? data ?? [];
    } catch {
        return [];
    }
}

async function savePMSyncConfig(provider: string, project_ids: string[]): Promise<void> {
    const res = await fetchWithAuth(`/integrations/${provider}/sync-config`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_ids }),
    });
    if (!res.ok) throw new Error('Failed to save sync config');
}

async function savePMStatusMappings(provider: string, mappings: PMStatusMapping[]): Promise<void> {
    const res = await fetchWithAuth(`/integrations/${provider}/status-mappings`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mappings }),
    });
    if (!res.ok) throw new Error('Failed to save status mappings');
}

/** Project picker + status mapping section for Linear/Asana cards. */
function PMSyncSection({
    providerKey,
    connected,
    projects,
    syncedProjectIds,
    onProjectToggle,
    onSaveSync,
    savingSync,
    statusMappings,
    onMappingChange,
    onSaveMappings,
    savingMappings,
}: {
    providerKey: string;
    connected: boolean;
    projects: PMProject[];
    syncedProjectIds: string[];
    onProjectToggle: (id: string) => void;
    onSaveSync: () => void;
    savingSync: boolean;
    statusMappings: PMStatusMapping[];
    onMappingChange: (external_state_id: string, pikar_status: string) => void;
    onSaveMappings: () => void;
    savingMappings: boolean;
}) {
    const [mappingsOpen, setMappingsOpen] = useState(false);
    const providerLabel = providerKey === 'linear' ? 'Linear' : 'Asana';

    if (!connected) {
        return (
            <div className="mt-4 pt-4 border-t border-slate-100">
                <p className="text-xs text-slate-400">
                    Connect {providerLabel} to configure project sync.
                </p>
            </div>
        );
    }

    return (
        <div className="mt-4 pt-4 border-t border-slate-100 space-y-4">
            {/* Project picker */}
            <div>
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400 mb-3">
                    Sync Projects
                </p>
                {projects.length === 0 ? (
                    <p className="text-xs text-slate-400">
                        No projects found. Make sure your {providerLabel} account has projects.
                    </p>
                ) : (
                    <div className="space-y-2">
                        {projects.map((project) => {
                            const checked = syncedProjectIds.includes(project.id);
                            return (
                                <label
                                    key={project.id}
                                    className="flex items-center gap-3 cursor-pointer group"
                                >
                                    <input
                                        type="checkbox"
                                        checked={checked}
                                        onChange={() => onProjectToggle(project.id)}
                                        className="w-4 h-4 rounded border-slate-300 text-teal-600 focus:ring-teal-500 cursor-pointer"
                                    />
                                    <span className="text-sm text-slate-700 group-hover:text-slate-900">
                                        {project.name}
                                        {project.key && (
                                            <span className="ml-1.5 text-xs text-slate-400">{project.key}</span>
                                        )}
                                        {project.workspace && (
                                            <span className="ml-1.5 text-xs text-slate-400">({project.workspace})</span>
                                        )}
                                    </span>
                                </label>
                            );
                        })}
                    </div>
                )}
                <button
                    onClick={onSaveSync}
                    disabled={savingSync || projects.length === 0}
                    className="mt-3 flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-teal-600 hover:bg-teal-700 rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    {savingSync ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                        <CheckCircle2 className="w-3.5 h-3.5" />
                    )}
                    Save &amp; Sync
                </button>
            </div>

            {/* Status mapping collapsible */}
            {statusMappings.length > 0 && (
                <div>
                    <button
                        onClick={() => setMappingsOpen((o) => !o)}
                        className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-400 hover:text-slate-600 transition-colors"
                    >
                        {mappingsOpen ? (
                            <ChevronDown className="w-3.5 h-3.5" />
                        ) : (
                            <ChevronRight className="w-3.5 h-3.5" />
                        )}
                        Status Mapping (customize)
                    </button>

                    <AnimatePresence>
                        {mappingsOpen && (
                            <motion.div
                                initial={{ height: 0, opacity: 0 }}
                                animate={{ height: 'auto', opacity: 1 }}
                                exit={{ height: 0, opacity: 0 }}
                                transition={{ duration: 0.2 }}
                                className="overflow-hidden"
                            >
                                <div className="mt-3 space-y-2">
                                    {statusMappings.map((mapping) => (
                                        <div
                                            key={mapping.external_state_id}
                                            className="flex items-center gap-3"
                                        >
                                            <span className="text-sm text-slate-600 w-32 truncate flex-shrink-0">
                                                {mapping.external_state_name}
                                            </span>
                                            <span className="text-slate-300 text-xs">→</span>
                                            <select
                                                value={mapping.pikar_status}
                                                onChange={(e) =>
                                                    onMappingChange(
                                                        mapping.external_state_id,
                                                        e.target.value,
                                                    )
                                                }
                                                className="flex-1 text-sm border border-slate-200 rounded-lg px-2 py-1 text-slate-700 focus:border-teal-500 focus:outline-none bg-white"
                                            >
                                                {PIKAR_STATUSES.map((s) => (
                                                    <option key={s} value={s}>
                                                        {s.replace('_', ' ')}
                                                    </option>
                                                ))}
                                            </select>
                                        </div>
                                    ))}
                                    <button
                                        onClick={onSaveMappings}
                                        disabled={savingMappings}
                                        className="mt-2 flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-teal-600 hover:bg-teal-700 rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                    >
                                        {savingMappings ? (
                                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                        ) : (
                                            <CheckCircle2 className="w-3.5 h-3.5" />
                                        )}
                                        Save Mappings
                                    </button>
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            )}
        </div>
    );
}

// ============================================================================
// Integration Provider Helpers & Card
// ============================================================================

const CATEGORY_LABELS: Record<string, string> = {
    crm_sales: 'CRM & Sales',
    finance_commerce: 'Finance & Commerce',
    productivity: 'Productivity',
    communication: 'Communication',
    analytics: 'Analytics',
};

const CATEGORY_ICONS: Record<string, React.ReactNode> = {
    crm_sales: <Briefcase className="w-5 h-5" />,
    finance_commerce: <DollarSign className="w-5 h-5" />,
    productivity: <Zap className="w-5 h-5" />,
    communication: <MessageSquare className="w-5 h-5" />,
    analytics: <BarChart3 className="w-5 h-5" />,
};

/** Fallback lucide icon when icon_url is not available / fails to load. */
const PROVIDER_FALLBACK_ICONS: Record<string, React.ReactNode> = {
    hubspot: <Users className="w-5 h-5" />,
    stripe: <DollarSign className="w-5 h-5" />,
    shopify: <Globe className="w-5 h-5" />,
    linear: <Zap className="w-5 h-5" />,
    asana: <CheckCircle2 className="w-5 h-5" />,
    slack: <MessageSquare className="w-5 h-5" />,
    teams: <MessageSquare className="w-5 h-5" />,
    bigquery: <BarChart3 className="w-5 h-5" />,
};

function IntegrationProviderCard({
    provider,
    status,
    expanded,
    onToggleExpand,
    onConnect,
    onDisconnect,
    isDisconnecting,
    capData,
    capInputValue,
    onCapInputChange,
    onCapSave,
    savingCap,
    pmProjects,
    syncedProjectIds,
    onProjectToggle,
    onSavePMSync,
    savingPMSync,
    statusMappings,
    onMappingChange,
    onSaveMappings,
    savingMappings,
    notifRules,
    notifChannels,
    notifConfig,
    notifEvents,
    onSaveNotifRule,
    onToggleNotifRule,
    onDeleteNotifRule,
    onSaveNotifConfig,
    onTestNotification,
}: {
    provider: IntegrationProvider;
    status: IntegrationStatus | undefined;
    expanded: boolean;
    onToggleExpand: () => void;
    onConnect: (key: string) => void;
    onDisconnect: (key: string) => void;
    isDisconnecting: boolean;
    capData?: BudgetCapData;
    capInputValue?: string;
    onCapInputChange?: (val: string) => void;
    onCapSave?: () => void;
    savingCap?: boolean;
    pmProjects?: PMProject[];
    syncedProjectIds?: string[];
    onProjectToggle?: (id: string) => void;
    onSavePMSync?: () => void;
    savingPMSync?: boolean;
    statusMappings?: PMStatusMapping[];
    onMappingChange?: (external_state_id: string, pikar_status: string) => void;
    onSaveMappings?: () => void;
    savingMappings?: boolean;
    notifRules?: NotificationRule[];
    notifChannels?: NotificationChannel[];
    notifConfig?: NotificationConfig | null;
    notifEvents?: SupportedEvent[];
    onSaveNotifRule?: (provider: string, event_type: string, channel_id: string, channel_name: string) => Promise<void>;
    onToggleNotifRule?: (provider: string, ruleId: string, enabled: boolean) => Promise<void>;
    onDeleteNotifRule?: (provider: string, ruleId: string) => Promise<void>;
    onSaveNotifConfig?: (provider: string, cfg: Partial<NotificationConfig>) => Promise<void>;
    onTestNotification?: (provider: string) => Promise<void>;
}) {
    const connected = status?.connected ?? false;
    const hasError = (status?.error_count ?? 0) > 0;

    // Determine status dot
    let statusDot: React.ReactNode;
    let statusLabel: string;
    if (connected && hasError) {
        statusDot = <AlertCircle className="w-3.5 h-3.5 text-red-500" />;
        statusLabel = 'Error';
    } else if (connected) {
        statusDot = <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />;
        statusLabel = 'Connected';
    } else {
        statusDot = <XCircle className="w-3.5 h-3.5 text-slate-400" />;
        statusLabel = 'Disconnected';
    }

    const statusColorClass = connected && hasError
        ? 'text-red-600 bg-red-50'
        : connected
            ? 'text-emerald-600 bg-emerald-50'
            : 'text-slate-400 bg-slate-100';

    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="group bg-white border border-slate-100/80 rounded-2xl p-5 hover:border-teal-200 hover:shadow-[0_8px_30px_-15px_rgba(15,23,42,0.2)] hover:-translate-y-0.5 transition-all duration-200"
        >
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-4 flex-1 min-w-0">
                    <div className={`p-2.5 rounded-lg flex-shrink-0 ${connected ? 'bg-emerald-100 text-emerald-600' : 'bg-slate-100 text-slate-400'}`}>
                        {PROVIDER_FALLBACK_ICONS[provider.key] || <Plug className="w-5 h-5" />}
                    </div>
                    <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                            <h3 className="font-medium text-slate-800">{provider.name}</h3>
                            <span className={`flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${statusColorClass}`}>
                                {statusDot}
                                {statusLabel}
                            </span>
                        </div>
                        {connected && status?.account_name && (
                            <p className="text-sm text-slate-500 mt-0.5 truncate">{status.account_name}</p>
                        )}
                    </div>
                </div>

                <div className="flex items-center gap-2 ml-4 flex-shrink-0">
                    {connected ? (
                        <>
                            <button
                                onClick={onToggleExpand}
                                className="p-2 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition-colors"
                                title="Show details"
                            >
                                <ChevronDown className={`w-4 h-4 transition-transform ${expanded ? 'rotate-180' : ''}`} />
                            </button>
                            <button
                                onClick={() => onDisconnect(provider.key)}
                                disabled={isDisconnecting}
                                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-red-600 bg-red-50 hover:bg-red-100 rounded-2xl transition-colors disabled:opacity-50"
                            >
                                {isDisconnecting ? (
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                ) : (
                                    <Unlink className="w-4 h-4" />
                                )}
                                Disconnect
                            </button>
                        </>
                    ) : (
                        <>
                            <button
                                onClick={onToggleExpand}
                                className="p-2 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition-colors"
                                title="Show details"
                            >
                                <ChevronDown className={`w-4 h-4 transition-transform ${expanded ? 'rotate-180' : ''}`} />
                            </button>
                            {/* Ad platforms require a budget cap before OAuth */}
                            {AD_PLATFORM_KEYS.has(provider.key) && !capData?.monthly_cap ? (
                                <button
                                    onClick={onToggleExpand}
                                    className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-amber-700 bg-amber-50 hover:bg-amber-100 rounded-2xl transition-colors"
                                    title="Set a budget cap first"
                                >
                                    <DollarSign className="w-4 h-4" />
                                    Set Cap First
                                </button>
                            ) : (
                            <button
                                onClick={() => onConnect(provider.key)}
                                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-teal-600 hover:bg-teal-700 rounded-2xl transition-colors"
                            >
                                <Link2 className="w-4 h-4" />
                                Connect
                            </button>
                            )}
                        </>
                    )}
                </div>
            </div>

            {/* Expandable details */}
            <AnimatePresence>
                {expanded && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.2 }}
                        className="overflow-hidden"
                    >
                        <div className="mt-4 pt-4 border-t border-slate-100 space-y-2">
                            {status?.last_sync_at && (
                                <div className="flex items-center gap-2 text-sm text-slate-500">
                                    <Clock className="w-3.5 h-3.5" />
                                    <span>Last synced: {new Date(status.last_sync_at).toLocaleString()}</span>
                                </div>
                            )}
                            {status?.last_error && (
                                <div className="flex items-start gap-2 text-sm text-red-600">
                                    <AlertCircle className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
                                    <span>Error: {status.last_error}</span>
                                </div>
                            )}
                            {status && !status.last_sync_at && !status.last_error && connected && (
                                <p className="text-sm text-slate-400">No sync activity yet.</p>
                            )}
                            {!connected && (
                                <p className="text-sm text-slate-400">
                                    Click Connect to authorize Pikar AI to access your {provider.name} account.
                                </p>
                            )}
                            <div className="flex flex-wrap gap-1 mt-1">
                                {provider.scopes.slice(0, 4).map((scope) => (
                                    <span key={scope} className="text-xs text-slate-400 bg-slate-50 px-2 py-0.5 rounded-full">
                                        {scope}
                                    </span>
                                ))}
                                {provider.scopes.length > 4 && (
                                    <span className="text-xs text-slate-400 bg-slate-50 px-2 py-0.5 rounded-full">
                                        +{provider.scopes.length - 4} more
                                    </span>
                                )}
                            </div>

                            {/* Budget cap section for ad platforms */}
                            {AD_PLATFORM_KEYS.has(provider.key) && onCapSave && onCapInputChange && (
                                <BudgetCapSection
                                    providerKey={provider.key}
                                    capData={capData}
                                    inputValue={capInputValue ?? ''}
                                    onInputChange={onCapInputChange}
                                    onSave={onCapSave}
                                    saving={savingCap ?? false}
                                />
                            )}

                            {/* PM project picker + status mapping for Linear/Asana */}
                            {PM_PROVIDER_KEYS.has(provider.key) && onSavePMSync && onProjectToggle && onMappingChange && onSaveMappings && (
                                <PMSyncSection
                                    providerKey={provider.key}
                                    connected={connected}
                                    projects={pmProjects ?? []}
                                    syncedProjectIds={syncedProjectIds ?? []}
                                    onProjectToggle={onProjectToggle}
                                    onSaveSync={onSavePMSync}
                                    savingSync={savingPMSync ?? false}
                                    statusMappings={statusMappings ?? []}
                                    onMappingChange={onMappingChange}
                                    onSaveMappings={onSaveMappings}
                                    savingMappings={savingMappings ?? false}
                                />
                            )}

                            {/* Notification rules + daily briefing for Slack/Teams */}
                            {NOTIF_PROVIDER_KEYS.has(provider.key) && onSaveNotifRule && onToggleNotifRule && onDeleteNotifRule && onSaveNotifConfig && onTestNotification && (
                                <NotificationRulesSection
                                    provider={provider.key}
                                    rules={notifRules ?? []}
                                    channels={notifChannels ?? []}
                                    config={notifConfig ?? null}
                                    events={notifEvents ?? []}
                                    onSaveRule={onSaveNotifRule}
                                    onToggleRule={onToggleNotifRule}
                                    onDeleteRule={onDeleteNotifRule}
                                    onSaveConfig={onSaveNotifConfig}
                                    onTestNotification={onTestNotification}
                                />
                            )}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.div>
    );
}

// ============================================================================
// DBConnectionsSection
// ============================================================================

const IMPORTANCE_SCHEDULE: Record<string, string> = {
    critical: 'daily',
    normal: 'weekly',
    low: 'biweekly',
};

const IMPORTANCE_COLORS: Record<string, string> = {
    critical: 'bg-red-100 text-red-700',
    normal: 'bg-blue-100 text-blue-700',
    low: 'bg-slate-100 text-slate-600',
};

const MONITORING_TYPE_COLORS: Record<string, string> = {
    competitor: 'bg-purple-100 text-purple-700',
    market: 'bg-teal-100 text-teal-700',
    topic: 'bg-amber-100 text-amber-700',
};

function DBConnectionsSection() {
    const [connections, setConnections] = useState<DBConnection[]>([]);
    const [loading, setLoading] = useState(true);
    const [showForm, setShowForm] = useState(false);
    const [provider, setProvider] = useState<'postgresql' | 'bigquery'>('postgresql');
    // PostgreSQL guided fields
    const [pgHost, setPgHost] = useState('');
    const [pgPort, setPgPort] = useState('5432');
    const [pgDatabase, setPgDatabase] = useState('');
    const [pgUsername, setPgUsername] = useState('');
    const [pgPassword, setPgPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    // Connection string paste mode
    const [pasteMode, setPasteMode] = useState(false);
    const [connectionString, setConnectionString] = useState('');
    const [testing, setTesting] = useState(false);
    const [saving, setSaving] = useState(false);
    const [testResult, setTestResult] = useState<{ ok: boolean; message: string } | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        fetchConnections();
    }, []);

    async function fetchConnections() {
        setLoading(true);
        try {
            const data = await fetchWithAuth('/integrations/status');
            const creds = (data as { integrations?: DBConnection[] }).integrations ?? [];
            setConnections(
                creds.filter((c: DBConnection) =>
                    c.provider === 'postgresql' || c.provider === 'bigquery'
                )
            );
        } catch {
            // Silently handle — connections may not exist yet
        } finally {
            setLoading(false);
        }
    }

    function parseDSN(dsn: string) {
        try {
            const url = new URL(dsn);
            setPgHost(url.hostname);
            setPgPort(url.port || '5432');
            setPgDatabase(url.pathname.replace(/^\//, ''));
            setPgUsername(url.username);
            setPgPassword(url.password);
            setPasteMode(false);
        } catch {
            setError('Invalid connection string. Expected: postgresql://user:pass@host:port/dbname');
        }
    }

    function buildConnectionString() {
        if (pgHost && pgDatabase && pgUsername) {
            return `postgresql://${pgUsername}:${pgPassword}@${pgHost}:${pgPort}/${pgDatabase}`;
        }
        return '';
    }

    async function handleTestConnection() {
        setTesting(true);
        setTestResult(null);
        setError(null);
        try {
            const result = await fetchWithAuth('/integrations/postgresql/test', {
                method: 'POST',
                body: JSON.stringify({
                    connection_string: pasteMode ? connectionString : buildConnectionString(),
                }),
            }) as { ok?: boolean; success?: boolean; message?: string; error?: string };
            const ok = result.ok ?? result.success ?? false;
            setTestResult({
                ok,
                message: ok
                    ? 'Connection successful'
                    : (result.message ?? result.error ?? 'Connection failed'),
            });
        } catch (e) {
            setTestResult({ ok: false, message: 'Connection test failed' });
        } finally {
            setTesting(false);
        }
    }

    async function handleSave() {
        setSaving(true);
        setError(null);
        try {
            const dsn = pasteMode ? connectionString : buildConnectionString();
            if (!dsn) {
                setError('Please fill in all required connection fields.');
                return;
            }
            await fetchWithAuth('/integrations/postgresql/credentials', {
                method: 'POST',
                body: JSON.stringify({
                    access_token: dsn,
                    account_name: `${pgHost || 'db'}:${pgPort || '5432'}/${pgDatabase || 'db'}`,
                }),
            });
            setShowForm(false);
            resetForm();
            await fetchConnections();
        } catch {
            setError('Failed to save connection. Please try again.');
        } finally {
            setSaving(false);
        }
    }

    async function handleDisconnect(conn: DBConnection) {
        try {
            await fetchWithAuth(`/integrations/${conn.provider}/disconnect`, { method: 'DELETE' });
            await fetchConnections();
        } catch {
            // ignore
        }
    }

    function resetForm() {
        setPgHost(''); setPgPort('5432'); setPgDatabase(''); setPgUsername(''); setPgPassword('');
        setConnectionString(''); setPasteMode(false); setTestResult(null); setError(null);
    }

    return (
        <div>
            {loading ? (
                <div className="flex items-center justify-center py-8">
                    <Loader2 className="w-6 h-6 animate-spin text-teal-500" />
                </div>
            ) : (
                <div className="space-y-4">
                    {/* Connected databases */}
                    {connections.length > 0 && (
                        <div className="space-y-3">
                            {connections.map((conn, i) => (
                                <div key={i} className="flex items-center gap-3 bg-slate-50 rounded-xl p-4 border border-slate-100">
                                    <div className="p-2 bg-teal-100 rounded-lg">
                                        <Database className="w-5 h-5 text-teal-600" />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <p className="text-sm font-medium text-slate-700 truncate">{conn.account_name}</p>
                                        <p className="text-xs text-slate-500 capitalize">{conn.provider}</p>
                                    </div>
                                    <span className="flex items-center gap-1 text-xs font-medium text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full">
                                        <CheckCircle2 className="w-3 h-3" /> Connected
                                    </span>
                                    <button
                                        onClick={() => handleDisconnect(conn)}
                                        className="p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                                        title="Disconnect"
                                    >
                                        <Unlink className="w-4 h-4" />
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Add connection button */}
                    {!showForm && (
                        <button
                            onClick={() => { setShowForm(true); resetForm(); }}
                            className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-teal-700 bg-teal-50 hover:bg-teal-100 rounded-xl border border-teal-200 transition-colors"
                        >
                            <Plus className="w-4 h-4" />
                            Add Database Connection
                        </button>
                    )}

                    {/* Connection form */}
                    {showForm && (
                        <div className="border border-slate-200 rounded-2xl p-5 space-y-4 bg-slate-50/50">
                            {/* Provider selector */}
                            <div>
                                <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2 block">Provider</label>
                                <div className="flex gap-2">
                                    {(['postgresql', 'bigquery'] as const).map((p) => (
                                        <button
                                            key={p}
                                            onClick={() => setProvider(p)}
                                            className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors border ${
                                                provider === p
                                                    ? 'bg-teal-600 text-white border-teal-600'
                                                    : 'bg-white text-slate-600 border-slate-200 hover:border-teal-400'
                                            }`}
                                        >
                                            {p === 'postgresql' ? 'PostgreSQL' : 'BigQuery'}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {provider === 'postgresql' && (
                                <>
                                    {/* Paste mode toggle */}
                                    <div className="flex items-center gap-2">
                                        <button
                                            onClick={() => setPasteMode(!pasteMode)}
                                            className="text-xs text-teal-600 hover:text-teal-700 underline"
                                        >
                                            {pasteMode ? 'Switch to guided form' : 'Paste connection string instead'}
                                        </button>
                                    </div>

                                    {pasteMode ? (
                                        <div>
                                            <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1 block">Connection String</label>
                                            <input
                                                type="text"
                                                value={connectionString}
                                                onChange={(e) => setConnectionString(e.target.value)}
                                                placeholder="postgresql://user:password@host:5432/dbname"
                                                className="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:border-teal-500 focus:outline-none font-mono"
                                            />
                                            {connectionString && (
                                                <button
                                                    onClick={() => parseDSN(connectionString)}
                                                    className="mt-1.5 text-xs text-teal-600 hover:underline"
                                                >
                                                    Parse into fields
                                                </button>
                                            )}
                                        </div>
                                    ) : (
                                        <div className="grid grid-cols-2 gap-3">
                                            <div className="col-span-2">
                                                <label className="text-xs font-semibold text-slate-500 mb-1 block">Host</label>
                                                <input type="text" value={pgHost} onChange={(e) => setPgHost(e.target.value)} placeholder="db.example.com" className="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:border-teal-500 focus:outline-none" />
                                            </div>
                                            <div>
                                                <label className="text-xs font-semibold text-slate-500 mb-1 block">Port</label>
                                                <input type="text" value={pgPort} onChange={(e) => setPgPort(e.target.value)} placeholder="5432" className="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:border-teal-500 focus:outline-none" />
                                            </div>
                                            <div>
                                                <label className="text-xs font-semibold text-slate-500 mb-1 block">Database</label>
                                                <input type="text" value={pgDatabase} onChange={(e) => setPgDatabase(e.target.value)} placeholder="mydb" className="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:border-teal-500 focus:outline-none" />
                                            </div>
                                            <div>
                                                <label className="text-xs font-semibold text-slate-500 mb-1 block">Username</label>
                                                <input type="text" value={pgUsername} onChange={(e) => setPgUsername(e.target.value)} placeholder="postgres" className="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:border-teal-500 focus:outline-none" />
                                            </div>
                                            <div>
                                                <label className="text-xs font-semibold text-slate-500 mb-1 block">Password</label>
                                                <div className="relative">
                                                    <input type={showPassword ? 'text' : 'password'} value={pgPassword} onChange={(e) => setPgPassword(e.target.value)} placeholder="••••••••" className="w-full px-3 py-2 pr-9 text-sm border border-slate-200 rounded-xl focus:border-teal-500 focus:outline-none" />
                                                    <button onClick={() => setShowPassword(!showPassword)} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
                                                        {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    )}
                                </>
                            )}

                            {provider === 'bigquery' && (
                                <div className="p-4 bg-blue-50 rounded-xl border border-blue-100">
                                    <p className="text-sm text-blue-800">
                                        BigQuery uses your connected Google account. Make sure Google Workspace is connected above, then ask the AI to &quot;query my BigQuery dataset&quot;.
                                    </p>
                                </div>
                            )}

                            {error && (
                                <p className="text-xs text-red-600 flex items-center gap-1">
                                    <AlertCircle className="w-3.5 h-3.5" /> {error}
                                </p>
                            )}

                            {testResult && (
                                <p className={`text-xs flex items-center gap-1 ${testResult.ok ? 'text-emerald-600' : 'text-red-600'}`}>
                                    {testResult.ok ? <CheckCircle2 className="w-3.5 h-3.5" /> : <XCircle className="w-3.5 h-3.5" />}
                                    {testResult.message}
                                </p>
                            )}

                            {provider === 'postgresql' && (
                                <div className="flex items-center gap-2 pt-1">
                                    <button
                                        onClick={handleTestConnection}
                                        disabled={testing}
                                        className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-slate-700 bg-white hover:bg-slate-50 rounded-xl border border-slate-200 transition-colors disabled:opacity-50"
                                    >
                                        {testing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Zap className="w-3.5 h-3.5" />}
                                        Test Connection
                                    </button>
                                    <button
                                        onClick={handleSave}
                                        disabled={saving}
                                        className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-teal-600 hover:bg-teal-700 rounded-xl transition-colors disabled:opacity-50"
                                    >
                                        {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
                                        Save Connection
                                    </button>
                                    <button
                                        onClick={() => { setShowForm(false); resetForm(); }}
                                        className="px-3 py-2 text-sm text-slate-500 hover:text-slate-700 rounded-xl hover:bg-slate-100 transition-colors"
                                    >
                                        Cancel
                                    </button>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

// ============================================================================
// MonitoringJobsSection
// ============================================================================

function MonitoringJobsSection() {
    const [jobs, setJobs] = useState<MonitoringJob[]>([]);
    const [loading, setLoading] = useState(true);
    const [showForm, setShowForm] = useState(false);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [deletingId, setDeletingId] = useState<string | null>(null);

    // Create form state
    const [topic, setTopic] = useState('');
    const [monitoringType, setMonitoringType] = useState<'competitor' | 'market' | 'topic'>('competitor');
    const [importance, setImportance] = useState<'critical' | 'normal' | 'low'>('normal');
    const [keywordInput, setKeywordInput] = useState('');
    const [pinnedInput, setPinnedInput] = useState('');
    const [excludedInput, setExcludedInput] = useState('');

    useEffect(() => {
        fetchJobs();
    }, []);

    async function fetchJobs() {
        setLoading(true);
        try {
            const data = await fetchWithAuth('/monitoring-jobs') as { jobs?: MonitoringJob[] };
            setJobs(data.jobs ?? []);
        } catch {
            // Silently handle
        } finally {
            setLoading(false);
        }
    }

    async function handleCreate() {
        if (!topic.trim()) {
            setError('Topic is required.');
            return;
        }
        setSaving(true);
        setError(null);
        try {
            await fetchWithAuth('/monitoring-jobs', {
                method: 'POST',
                body: JSON.stringify({
                    topic: topic.trim(),
                    monitoring_type: monitoringType,
                    importance,
                    keyword_triggers: keywordInput
                        ? keywordInput.split(',').map((k) => k.trim()).filter(Boolean)
                        : [],
                    pinned_urls: pinnedInput
                        ? pinnedInput.split('\n').map((u) => u.trim()).filter(Boolean)
                        : [],
                    excluded_urls: excludedInput
                        ? excludedInput.split('\n').map((u) => u.trim()).filter(Boolean)
                        : [],
                }),
            });
            setShowForm(false);
            resetForm();
            await fetchJobs();
        } catch {
            setError('Failed to create monitoring job. Please try again.');
        } finally {
            setSaving(false);
        }
    }

    async function handleToggle(job: MonitoringJob) {
        try {
            await fetchWithAuth(`/monitoring-jobs/${job.id}`, {
                method: 'PATCH',
                body: JSON.stringify({ is_active: !job.is_active }),
            });
            setJobs((prev) =>
                prev.map((j) => (j.id === job.id ? { ...j, is_active: !j.is_active } : j))
            );
        } catch {
            // ignore
        }
    }

    async function handleDelete(job: MonitoringJob) {
        if (!confirm(`Delete monitoring job for "${job.topic}"?`)) return;
        setDeletingId(job.id);
        try {
            await fetchWithAuth(`/monitoring-jobs/${job.id}`, { method: 'DELETE' });
            setJobs((prev) => prev.filter((j) => j.id !== job.id));
        } catch {
            // ignore
        } finally {
            setDeletingId(null);
        }
    }

    function resetForm() {
        setTopic(''); setMonitoringType('competitor'); setImportance('normal');
        setKeywordInput(''); setPinnedInput(''); setExcludedInput('');
        setError(null);
    }

    return (
        <div>
            {loading ? (
                <div className="flex items-center justify-center py-8">
                    <Loader2 className="w-6 h-6 animate-spin text-teal-500" />
                </div>
            ) : (
                <div className="space-y-4">
                    {/* Job list */}
                    {jobs.length > 0 && (
                        <div className="space-y-3">
                            {jobs.map((job) => (
                                <div key={job.id} className="flex items-start gap-3 bg-slate-50 rounded-xl p-4 border border-slate-100">
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 flex-wrap mb-1.5">
                                            <p className="text-sm font-medium text-slate-800 truncate">{job.topic}</p>
                                            <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${MONITORING_TYPE_COLORS[job.monitoring_type] ?? 'bg-slate-100 text-slate-600'}`}>
                                                {job.monitoring_type}
                                            </span>
                                            <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${IMPORTANCE_COLORS[job.importance] ?? 'bg-slate-100 text-slate-600'}`}>
                                                {job.importance} · {IMPORTANCE_SCHEDULE[job.importance]}
                                            </span>
                                        </div>
                                        {job.last_run_at && (
                                            <p className="text-xs text-slate-400">
                                                Last run: {new Date(job.last_run_at).toLocaleDateString()}
                                            </p>
                                        )}
                                        {job.keyword_triggers.length > 0 && (
                                            <p className="text-xs text-slate-400 mt-0.5">
                                                Keywords: {job.keyword_triggers.slice(0, 3).join(', ')}
                                                {job.keyword_triggers.length > 3 && ` +${job.keyword_triggers.length - 3} more`}
                                            </p>
                                        )}
                                    </div>
                                    <div className="flex items-center gap-2 flex-shrink-0">
                                        {/* Active toggle */}
                                        <button
                                            onClick={() => handleToggle(job)}
                                            title={job.is_active ? 'Pause monitoring' : 'Resume monitoring'}
                                            className={`transition-colors ${job.is_active ? 'text-teal-500 hover:text-teal-700' : 'text-slate-300 hover:text-slate-500'}`}
                                        >
                                            {job.is_active
                                                ? <ToggleRight className="w-6 h-6" />
                                                : <ToggleLeft className="w-6 h-6" />
                                            }
                                        </button>
                                        {/* Delete button */}
                                        <button
                                            onClick={() => handleDelete(job)}
                                            disabled={deletingId === job.id}
                                            className="p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
                                            title="Delete monitoring job"
                                        >
                                            {deletingId === job.id
                                                ? <Loader2 className="w-4 h-4 animate-spin" />
                                                : <Trash2 className="w-4 h-4" />
                                            }
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}

                    {jobs.length === 0 && !showForm && (
                        <div className="text-center py-8 text-slate-400">
                            <Radar className="w-10 h-10 mx-auto mb-3 opacity-40" />
                            <p className="text-sm">No monitoring jobs yet.</p>
                            <p className="text-xs mt-1">Create a job to track competitors, markets, or topics automatically.</p>
                        </div>
                    )}

                    {/* Create button */}
                    {!showForm && (
                        <button
                            onClick={() => { setShowForm(true); resetForm(); }}
                            className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-teal-700 bg-teal-50 hover:bg-teal-100 rounded-xl border border-teal-200 transition-colors"
                        >
                            <Plus className="w-4 h-4" />
                            Create Monitoring Job
                        </button>
                    )}

                    {/* Create form */}
                    {showForm && (
                        <div className="border border-slate-200 rounded-2xl p-5 space-y-4 bg-slate-50/50">
                            <div>
                                <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1 block">Topic *</label>
                                <input
                                    type="text"
                                    value={topic}
                                    onChange={(e) => setTopic(e.target.value)}
                                    placeholder="e.g. Acme Corp pricing strategy, SaaS market trends"
                                    className="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:border-teal-500 focus:outline-none"
                                />
                            </div>

                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1 block">Type</label>
                                    <select
                                        value={monitoringType}
                                        onChange={(e) => setMonitoringType(e.target.value as 'competitor' | 'market' | 'topic')}
                                        className="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:border-teal-500 focus:outline-none bg-white"
                                    >
                                        <option value="competitor">Competitor</option>
                                        <option value="market">Market</option>
                                        <option value="topic">Topic</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1 block">Importance</label>
                                    <select
                                        value={importance}
                                        onChange={(e) => setImportance(e.target.value as 'critical' | 'normal' | 'low')}
                                        className="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:border-teal-500 focus:outline-none bg-white"
                                    >
                                        <option value="critical">Critical (runs daily)</option>
                                        <option value="normal">Normal (runs weekly)</option>
                                        <option value="low">Low (runs biweekly)</option>
                                    </select>
                                </div>
                            </div>

                            <div>
                                <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1 block">Keyword Triggers (optional)</label>
                                <input
                                    type="text"
                                    value={keywordInput}
                                    onChange={(e) => setKeywordInput(e.target.value)}
                                    placeholder="layoffs, acquisition, pricing — comma separated"
                                    className="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:border-teal-500 focus:outline-none"
                                />
                                <p className="text-xs text-slate-400 mt-1">Alert fires immediately when these words appear in findings.</p>
                            </div>

                            <div>
                                <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1 block">Pinned URLs (optional)</label>
                                <textarea
                                    value={pinnedInput}
                                    onChange={(e) => setPinnedInput(e.target.value)}
                                    placeholder="https://competitor.com&#10;https://blog.competitor.com"
                                    rows={2}
                                    className="w-full px-3 py-2 text-sm border border-slate-200 rounded-xl focus:border-teal-500 focus:outline-none resize-none"
                                />
                            </div>

                            {error && (
                                <p className="text-xs text-red-600 flex items-center gap-1">
                                    <AlertCircle className="w-3.5 h-3.5" /> {error}
                                </p>
                            )}

                            <div className="flex items-center gap-2 pt-1">
                                <button
                                    onClick={handleCreate}
                                    disabled={saving || !topic.trim()}
                                    className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-teal-600 hover:bg-teal-700 rounded-xl transition-colors disabled:opacity-50"
                                >
                                    {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />}
                                    Create Job
                                </button>
                                <button
                                    onClick={() => { setShowForm(false); resetForm(); }}
                                    className="px-3 py-2 text-sm text-slate-500 hover:text-slate-700 rounded-xl hover:bg-slate-100 transition-colors"
                                >
                                    Cancel
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

// ============================================================================
// WebhooksSection
// ============================================================================

const VERIFICATION_SNIPPETS = {
    node_js: `const crypto = require('crypto');

function verifyWebhook(rawBody, signature, secret) {
    const expected = 'sha256=' + crypto
        .createHmac('sha256', secret)
        .update(rawBody)
        .digest('hex');
    return crypto.timingSafeEqual(
        Buffer.from(signature),
        Buffer.from(expected)
    );
}`,
    python: `import hashlib
import hmac

def verify_webhook(raw_body: bytes, signature: str, secret: str) -> bool:
    expected = 'sha256=' + hmac.new(
        secret.encode(), raw_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, expected)`,
    curl: `# Compute the expected signature
BODY='{"event":"task.created",...}'
SECRET='whsec_your_secret'
SIG=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "$SECRET" -hex | awk '{print "sha256="$2}')
# Compare with X-Pikar-Signature header value
echo "Expected: $SIG"`,
} as const;

type SnippetLang = keyof typeof VERIFICATION_SNIPPETS;

const DELIVERY_STATUS_COLORS: Record<string, string> = {
    delivered: 'bg-emerald-100 text-emerald-700',
    failed: 'bg-red-100 text-red-700',
    pending: 'bg-amber-100 text-amber-700',
};

function WebhooksSection() {
    const [endpoints, setEndpoints] = useState<WebhookEndpoint[]>([]);
    const [eventCatalog, setEventCatalog] = useState<WebhookEvent[]>([]);
    const [loading, setLoading] = useState(true);
    const [showCreateForm, setShowCreateForm] = useState(false);
    const [saving, setSaving] = useState(false);
    const [createdSecret, setCreatedSecret] = useState<string | null>(null);
    const [secretCopied, setSecretCopied] = useState(false);

    // Create form state
    const [newUrl, setNewUrl] = useState('');
    const [newEvents, setNewEvents] = useState<string[]>([]);
    const [newDescription, setNewDescription] = useState('');
    const [createError, setCreateError] = useState<string | null>(null);

    // Delivery log state
    const [selectedEndpoint, setSelectedEndpoint] = useState<WebhookEndpoint | null>(null);
    const [deliveries, setDeliveries] = useState<WebhookDelivery[]>([]);
    const [deliveriesLoading, setDeliveriesLoading] = useState(false);

    // Signing snippets
    const [snippetLang, setSnippetLang] = useState<SnippetLang>('node_js');
    const [showSnippets, setShowSnippets] = useState(false);

    // Delete confirmation
    const [deletingId, setDeletingId] = useState<string | null>(null);
    const [testingId, setTestingId] = useState<string | null>(null);
    const [togglingId, setTogglingId] = useState<string | null>(null);

    useEffect(() => {
        void loadAll();
    }, []);

    async function loadAll() {
        setLoading(true);
        try {
            const [epData, evData] = await Promise.all([
                fetchWithAuth('/outbound-webhooks/endpoints').then(r => r.json()) as Promise<WebhookEndpoint[]>,
                fetchWithAuth('/outbound-webhooks/events').then(r => r.json()).then((d: unknown) => (d as { events?: WebhookEvent[] }).events ?? d as WebhookEvent[]),
            ]);
            setEndpoints(Array.isArray(epData) ? epData : []);
            setEventCatalog(Array.isArray(evData) ? evData : []);
        } catch {
            // silently handle
        } finally {
            setLoading(false);
        }
    }

    async function handleCreate() {
        if (!newUrl.trim()) { setCreateError('URL is required.'); return; }
        if (newEvents.length === 0) { setCreateError('Select at least one event.'); return; }
        setSaving(true);
        setCreateError(null);
        try {
            const result = await fetchWithAuth('/outbound-webhooks/endpoints', {
                method: 'POST',
                body: JSON.stringify({ url: newUrl.trim(), events: newEvents, description: newDescription.trim() }),
            }) as { secret?: string };
            setCreatedSecret(result.secret ?? null);
            setShowCreateForm(false);
            setNewUrl(''); setNewEvents([]); setNewDescription('');
            await loadAll();
        } catch {
            setCreateError('Failed to create endpoint. Check the URL and try again.');
        } finally {
            setSaving(false);
        }
    }

    async function handleDelete(ep: WebhookEndpoint) {
        if (!confirm(`Delete webhook endpoint for "${ep.url}"?`)) return;
        setDeletingId(ep.id);
        try {
            await fetchWithAuth(`/outbound-webhooks/endpoints/${ep.id}`, { method: 'DELETE' });
            setEndpoints((prev) => prev.filter((e) => e.id !== ep.id));
            if (selectedEndpoint?.id === ep.id) setSelectedEndpoint(null);
        } catch {
            // ignore
        } finally {
            setDeletingId(null);
        }
    }

    async function handleToggleActive(ep: WebhookEndpoint) {
        setTogglingId(ep.id);
        try {
            const updated = await fetchWithAuth(`/outbound-webhooks/endpoints/${ep.id}`, {
                method: 'PATCH',
                body: JSON.stringify({ active: !ep.active }),
            }).then((r) => r.json()) as WebhookEndpoint;
            setEndpoints((prev) => prev.map((e) => (e.id === ep.id ? { ...e, active: updated.active } : e)));
        } catch {
            // ignore
        } finally {
            setTogglingId(null);
        }
    }

    async function handleViewLogs(ep: WebhookEndpoint) {
        setSelectedEndpoint(ep);
        setDeliveriesLoading(true);
        setDeliveries([]);
        try {
            const data = await fetchWithAuth(`/outbound-webhooks/endpoints/${ep.id}/deliveries`) as WebhookDelivery[] | { deliveries?: WebhookDelivery[] };
            setDeliveries(Array.isArray(data) ? data : (data.deliveries ?? []));
        } catch {
            // ignore
        } finally {
            setDeliveriesLoading(false);
        }
    }

    async function handleTestSend(ep: WebhookEndpoint) {
        setTestingId(ep.id);
        try {
            await fetchWithAuth(`/outbound-webhooks/endpoints/${ep.id}/test`, { method: 'POST' });
        } catch {
            // ignore
        } finally {
            setTestingId(null);
        }
    }

    function toggleEvent(eventType: string) {
        setNewEvents((prev) =>
            prev.includes(eventType) ? prev.filter((e) => e !== eventType) : [...prev, eventType]
        );
    }

    function copySecret(secret: string) {
        void navigator.clipboard.writeText(secret);
        setSecretCopied(true);
        setTimeout(() => setSecretCopied(false), 2000);
    }

    if (loading) {
        return (
            <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin text-teal-500" />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Created secret alert */}
            {createdSecret && (
                <div className="rounded-2xl border-2 border-amber-300 bg-amber-50 p-4">
                    <p className="text-sm font-semibold text-amber-800 mb-2">
                        Save this signing secret — it will not be shown again.
                    </p>
                    <div className="flex items-center gap-2 bg-white rounded-xl border border-amber-200 px-3 py-2">
                        <code className="flex-1 text-xs font-mono text-slate-800 break-all">{createdSecret}</code>
                        <button
                            onClick={() => copySecret(createdSecret)}
                            className="shrink-0 p-1.5 rounded-lg hover:bg-amber-100 transition-colors"
                            title="Copy secret"
                        >
                            {secretCopied ? <CheckCircle2 className="w-4 h-4 text-emerald-500" /> : <Copy className="w-4 h-4 text-amber-700" />}
                        </button>
                    </div>
                    <button
                        onClick={() => setCreatedSecret(null)}
                        className="mt-2 text-xs text-amber-700 underline hover:text-amber-900"
                    >
                        I have saved the secret, dismiss
                    </button>
                </div>
            )}

            {/* Endpoint list */}
            {endpoints.length === 0 && !showCreateForm ? (
                <div className="text-center py-8 text-slate-400">
                    <Zap className="w-10 h-10 mx-auto mb-3 opacity-40" />
                    <p className="text-sm">No webhook endpoints configured.</p>
                    <p className="text-xs mt-1">Add an endpoint to receive real-time events from Pikar.</p>
                </div>
            ) : (
                <div className="space-y-3">
                    {endpoints.map((ep) => (
                        <div key={ep.id} className="rounded-2xl border border-slate-100 bg-slate-50 p-4">
                            <div className="flex items-start gap-3">
                                <div className="flex-1 min-w-0">
                                    <p className="text-sm font-medium text-slate-800 truncate" title={ep.url}>{ep.url}</p>
                                    <div className="flex items-center gap-2 mt-1 flex-wrap">
                                        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${ep.active ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-200 text-slate-500'}`}>
                                            {ep.active ? 'active' : 'paused'}
                                        </span>
                                        <span className="text-xs text-slate-500">{ep.events.length} event{ep.events.length !== 1 ? 's' : ''}</span>
                                        {ep.description && <span className="text-xs text-slate-400 truncate">{ep.description}</span>}
                                        {ep.consecutive_failures > 0 && (
                                            <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-red-100 text-red-700">
                                                {ep.consecutive_failures} failure{ep.consecutive_failures !== 1 ? 's' : ''}
                                            </span>
                                        )}
                                        {ep.secret_preview && (
                                            <span className="text-xs font-mono text-slate-400">{ep.secret_preview}</span>
                                        )}
                                    </div>
                                </div>
                                <div className="flex items-center gap-1 shrink-0">
                                    <button
                                        onClick={() => handleToggleActive(ep)}
                                        disabled={togglingId === ep.id}
                                        title={ep.active ? 'Pause' : 'Resume'}
                                        className={`p-1.5 rounded-lg transition-colors ${ep.active ? 'text-teal-500 hover:bg-teal-50' : 'text-slate-400 hover:bg-slate-100'}`}
                                    >
                                        {togglingId === ep.id
                                            ? <Loader2 className="w-4 h-4 animate-spin" />
                                            : ep.active ? <ToggleRight className="w-5 h-5" /> : <ToggleLeft className="w-5 h-5" />
                                        }
                                    </button>
                                    <button
                                        onClick={() => void handleViewLogs(ep)}
                                        title="View delivery logs"
                                        className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100 transition-colors text-xs"
                                    >
                                        <Clock className="w-4 h-4" />
                                    </button>
                                    <button
                                        onClick={() => void handleTestSend(ep)}
                                        disabled={testingId === ep.id}
                                        title="Send test event"
                                        className="p-1.5 rounded-lg text-slate-400 hover:bg-blue-50 hover:text-blue-600 transition-colors"
                                    >
                                        {testingId === ep.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
                                    </button>
                                    <button
                                        onClick={() => void handleDelete(ep)}
                                        disabled={deletingId === ep.id}
                                        title="Delete endpoint"
                                        className="p-1.5 rounded-lg text-slate-400 hover:bg-red-50 hover:text-red-600 transition-colors"
                                    >
                                        {deletingId === ep.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                                    </button>
                                </div>
                            </div>

                            {/* Inline delivery log */}
                            {selectedEndpoint?.id === ep.id && (
                                <div className="mt-4 border-t border-slate-200 pt-4">
                                    <div className="flex items-center justify-between mb-2">
                                        <p className="text-xs font-semibold text-slate-600 uppercase tracking-wide">Recent Deliveries</p>
                                        <button onClick={() => void handleTestSend(ep)} className="text-xs text-blue-600 hover:underline">Send test</button>
                                    </div>
                                    {deliveriesLoading ? (
                                        <div className="flex items-center gap-2 py-3 text-slate-400 text-xs">
                                            <Loader2 className="w-3 h-3 animate-spin" /> Loading...
                                        </div>
                                    ) : deliveries.length === 0 ? (
                                        <p className="text-xs text-slate-400 py-2">No deliveries yet.</p>
                                    ) : (
                                        <div className="space-y-1">
                                            {deliveries.map((d, idx) => (
                                                <div key={idx} className="flex items-center gap-3 text-xs py-1">
                                                    <span className={`px-2 py-0.5 rounded-full font-medium ${DELIVERY_STATUS_COLORS[d.status] ?? 'bg-slate-100 text-slate-600'}`}>
                                                        {d.status}
                                                    </span>
                                                    <span className="text-slate-600 font-mono">{d.event_type}</span>
                                                    <span className="text-slate-400">{d.attempts} attempt{d.attempts !== 1 ? 's' : ''}</span>
                                                    {d.response_code && <span className="text-slate-400">HTTP {d.response_code}</span>}
                                                    <span className="text-slate-400 ml-auto">{new Date(d.created_at).toLocaleString()}</span>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                    <button
                                        onClick={() => setSelectedEndpoint(null)}
                                        className="mt-2 text-xs text-slate-400 hover:text-slate-600"
                                    >
                                        Close
                                    </button>
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}

            {/* Add endpoint form */}
            {showCreateForm ? (
                <div className="rounded-2xl border border-teal-200 bg-teal-50 p-5 space-y-4">
                    <h3 className="text-sm font-semibold text-slate-800">New Webhook Endpoint</h3>
                    <div>
                        <label className="block text-xs font-medium text-slate-600 mb-1">Destination URL</label>
                        <input
                            type="url"
                            value={newUrl}
                            onChange={(e) => setNewUrl(e.target.value)}
                            placeholder="https://your-server.com/webhook"
                            className="w-full text-sm rounded-xl border border-slate-200 bg-white px-3 py-2 focus:outline-none focus:ring-2 focus:ring-teal-400"
                        />
                    </div>
                    <div>
                        <label className="block text-xs font-medium text-slate-600 mb-2">Events to subscribe</label>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                            {eventCatalog.map((ev) => (
                                <label key={ev.event_type} className="flex items-start gap-2 cursor-pointer">
                                    <input
                                        type="checkbox"
                                        checked={newEvents.includes(ev.event_type)}
                                        onChange={() => toggleEvent(ev.event_type)}
                                        className="mt-0.5 accent-teal-500"
                                    />
                                    <span className="text-xs">
                                        <span className="font-mono text-slate-700">{ev.event_type}</span>
                                        <span className="block text-slate-400">{ev.description}</span>
                                    </span>
                                </label>
                            ))}
                        </div>
                    </div>
                    <div>
                        <label className="block text-xs font-medium text-slate-600 mb-1">Description (optional)</label>
                        <input
                            type="text"
                            value={newDescription}
                            onChange={(e) => setNewDescription(e.target.value)}
                            placeholder="e.g. Zapier integration"
                            className="w-full text-sm rounded-xl border border-slate-200 bg-white px-3 py-2 focus:outline-none focus:ring-2 focus:ring-teal-400"
                        />
                    </div>
                    {createError && (
                        <p className="text-xs text-red-600 flex items-center gap-1">
                            <AlertCircle className="w-3 h-3" /> {createError}
                        </p>
                    )}
                    <div className="flex gap-2">
                        <button
                            onClick={() => void handleCreate()}
                            disabled={saving}
                            className="flex items-center gap-1.5 px-4 py-2 bg-teal-600 text-white text-sm rounded-xl hover:bg-teal-700 disabled:opacity-50 transition-colors"
                        >
                            {saving ? <Loader2 className="w-3 h-3 animate-spin" /> : <Plus className="w-3 h-3" />}
                            Create endpoint
                        </button>
                        <button
                            onClick={() => { setShowCreateForm(false); setCreateError(null); }}
                            className="px-4 py-2 text-sm text-slate-600 rounded-xl hover:bg-slate-100 transition-colors"
                        >
                            Cancel
                        </button>
                    </div>
                </div>
            ) : (
                <button
                    onClick={() => setShowCreateForm(true)}
                    className="flex items-center gap-2 px-4 py-2 text-sm text-teal-700 border border-teal-200 rounded-xl hover:bg-teal-50 transition-colors"
                >
                    <Plus className="w-4 h-4" /> Add endpoint
                </button>
            )}

            {/* Signing verification snippets */}
            <div className="rounded-2xl border border-slate-100 bg-white">
                <button
                    onClick={() => setShowSnippets((v) => !v)}
                    className="flex items-center justify-between w-full px-5 py-3 text-left"
                >
                    <span className="text-sm font-medium text-slate-700">Signature Verification Code</span>
                    {showSnippets ? <ChevronDown className="w-4 h-4 text-slate-400" /> : <ChevronRight className="w-4 h-4 text-slate-400" />}
                </button>
                {showSnippets && (
                    <div className="px-5 pb-5 border-t border-slate-100">
                        <p className="text-xs text-slate-500 mt-3 mb-3">
                            Verify the <code className="font-mono bg-slate-100 px-1 rounded">X-Pikar-Signature</code> header on every incoming request.
                            Replace <code className="font-mono bg-slate-100 px-1 rounded">SECRET</code> with your webhook signing secret.
                        </p>
                        <div className="flex gap-1 mb-3">
                            {(Object.keys(VERIFICATION_SNIPPETS) as SnippetLang[]).map((lang) => (
                                <button
                                    key={lang}
                                    onClick={() => setSnippetLang(lang)}
                                    className={`px-3 py-1 text-xs rounded-lg transition-colors ${snippetLang === lang ? 'bg-teal-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
                                >
                                    {lang === 'node_js' ? 'Node.js' : lang === 'python' ? 'Python' : 'cURL'}
                                </button>
                            ))}
                        </div>
                        <pre className="text-xs font-mono bg-slate-900 text-slate-100 rounded-xl p-4 overflow-x-auto whitespace-pre-wrap">
                            {VERIFICATION_SNIPPETS[snippetLang]}
                        </pre>
                    </div>
                )}
            </div>
        </div>
    );
}

// ============================================================================
// Main Page Component
// ============================================================================

export default function ConfigurationPage() {
    const router = useRouter();
    const [builtInTools, setBuiltInTools] = useState<BuiltInTool[]>([]);
    const [schedulerReadiness, setSchedulerReadiness] = useState<SchedulerReadiness | null>(null);
    const [mcpTools, setMcpTools] = useState<MCPTool[]>([]);
    const [socialPlatforms, setSocialPlatforms] = useState<SocialPlatform[]>([]);
    const [googleWorkspace, setGoogleWorkspace] = useState<GoogleWorkspaceStatus | null>(null);
    const [loading, setLoading] = useState(true);
    const [connectingPlatform, setConnectingPlatform] = useState<string | null>(null);
    const [notification, setNotification] = useState<{ type: 'success' | 'error' | 'info'; message: string } | null>(null);
    const [wizardTool, setWizardTool] = useState<MCPTool | null>(null);
    const [showWizard, setShowWizard] = useState(false);

    // Integration provider state
    const [integrationProviders, setIntegrationProviders] = useState<IntegrationProvider[]>([]);
    const [integrationStatuses, setIntegrationStatuses] = useState<IntegrationStatus[]>([]);
    const [disconnectingProvider, setDisconnectingProvider] = useState<string | null>(null);
    const [expandedProvider, setExpandedProvider] = useState<string | null>(null);

    // Ad platform budget cap state
    const [budgetCaps, setBudgetCaps] = useState<Record<string, BudgetCapData>>({});
    const [budgetCapInputs, setBudgetCapInputs] = useState<Record<string, string>>({});
    const [savingCap, setSavingCap] = useState<Record<string, boolean>>({});

    // PM sync state (Linear + Asana)
    const [pmProjects, setPmProjects] = useState<Record<string, PMProject[]>>({});
    const [syncedProjectIds, setSyncedProjectIds] = useState<Record<string, string[]>>({});
    const [statusMappings, setStatusMappings] = useState<Record<string, PMStatusMapping[]>>({});
    const [savingPMSync, setSavingPMSync] = useState<Record<string, boolean>>({});
    const [savingMappings, setSavingMappings] = useState<Record<string, boolean>>({});

    // Notification rule state (Slack + Teams)
    const [notifRules, setNotifRules] = useState<Record<string, NotificationRule[]>>({});
    const [notifChannels, setNotifChannels] = useState<Record<string, NotificationChannel[]>>({});
    const [notifConfig, setNotifConfig] = useState<Record<string, NotificationConfig | null>>({});
    const [notifEvents, setNotifEvents] = useState<SupportedEvent[]>([]);

    // Check for URL params on mount (OAuth callback results)
    useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        const success = params.get('success');
        const error = params.get('error');

        if (success) {
            setNotification({ 
                type: 'success', 
                message: `Successfully connected ${success}!` 
            });
            // Clean URL
            window.history.replaceState({}, '', '/dashboard/configuration');
        } else if (error) {
            setNotification({ 
                type: 'error', 
                message: `Failed to connect: ${error}` 
            });
            window.history.replaceState({}, '', '/dashboard/configuration');
        }
    }, []);

    // Auto-dismiss notifications
    useEffect(() => {
        if (notification) {
            const timer = setTimeout(() => setNotification(null), 5000);
            return () => clearTimeout(timer);
        }
    }, [notification]);

    // Fetch data on mount
    useEffect(() => {
        async function fetchData() {
            setLoading(true);
            try {
                // Fetch MCP tools status
                const mcpResponse = await fetch('/api/configuration/mcp-status');
                if (mcpResponse.ok) {
                    const mcpData = await mcpResponse.json();
                    setBuiltInTools(mcpData.built_in_tools || []);
                    setSchedulerReadiness(mcpData.scheduler_readiness || null);
                    setMcpTools(mcpData.configurable_tools || mcpData.tools || []);
                }

                // Fetch social platforms status
                const socialResponse = await fetch('/api/configuration/social-status');
                if (socialResponse.ok) {
                    const socialData = await socialResponse.json();
                    setSocialPlatforms(socialData.platforms || []);
                }

                // Fetch Google Workspace status
                const googleResponse = await fetch('/api/configuration/google-workspace-status');
                if (googleResponse.ok) {
                    const googleData = await googleResponse.json();
                    setGoogleWorkspace(googleData);
                }

                // Fetch integration providers and status
                try {
                    const [providers, statuses] = await Promise.all([
                        fetchProviders(),
                        fetchIntegrationStatus(),
                    ]);
                    setIntegrationProviders(providers);
                    setIntegrationStatuses(statuses);

                    // Fetch budget caps for connected ad platforms
                    const caps: Record<string, BudgetCapData> = {};
                    await Promise.allSettled(
                        Array.from(AD_PLATFORM_KEYS).map(async (key) => {
                            try {
                                caps[key] = await fetchBudgetCap(key);
                            } catch {
                                caps[key] = { monthly_cap: null };
                            }
                        })
                    );
                    setBudgetCaps(caps);

                    // Fetch PM project lists and sync config for connected Linear/Asana
                    const connectedPMProviders = Array.from(PM_PROVIDER_KEYS).filter(
                        (key) => statuses.find((s) => s.provider === key)?.connected
                    );
                    if (connectedPMProviders.length > 0) {
                        const pmProjectsMap: Record<string, PMProject[]> = {};
                        const syncedIdsMap: Record<string, string[]> = {};
                        const mappingsMap: Record<string, PMStatusMapping[]> = {};
                        await Promise.allSettled(
                            connectedPMProviders.map(async (key) => {
                                try {
                                    const [projects, syncConfig, mappings] = await Promise.all([
                                        fetchPMProjects(key),
                                        fetchPMSyncConfig(key),
                                        fetchPMStatusMappings(key),
                                    ]);
                                    pmProjectsMap[key] = projects;
                                    syncedIdsMap[key] = syncConfig.project_ids;
                                    mappingsMap[key] = mappings;
                                } catch {
                                    pmProjectsMap[key] = [];
                                    syncedIdsMap[key] = [];
                                    mappingsMap[key] = [];
                                }
                            })
                        );
                        setPmProjects(pmProjectsMap);
                        setSyncedProjectIds(syncedIdsMap);
                        setStatusMappings(mappingsMap);
                    }

                    // Fetch notification rules/config for connected Slack/Teams
                    const connectedNotifProviders = Array.from(NOTIF_PROVIDER_KEYS).filter(
                        (key) => statuses.find((s) => s.provider === key)?.connected
                    );
                    // Fetch supported events once (static list)
                    const events = await fetchSupportedEvents();
                    setNotifEvents(events);

                    if (connectedNotifProviders.length > 0) {
                        const rulesMap: Record<string, NotificationRule[]> = {};
                        const channelsMap: Record<string, NotificationChannel[]> = {};
                        const configMap: Record<string, NotificationConfig | null> = {};
                        await Promise.allSettled(
                            connectedNotifProviders.map(async (key) => {
                                try {
                                    const [rules, channels, cfg] = await Promise.all([
                                        fetchNotificationRules(key),
                                        fetchNotificationChannels(key),
                                        fetchNotificationConfig(key),
                                    ]);
                                    rulesMap[key] = rules;
                                    channelsMap[key] = channels;
                                    configMap[key] = cfg;
                                } catch {
                                    rulesMap[key] = [];
                                    channelsMap[key] = [];
                                    configMap[key] = null;
                                }
                            })
                        );
                        setNotifRules(rulesMap);
                        setNotifChannels(channelsMap);
                        setNotifConfig(configMap);
                    }
                } catch {
                    // Integration endpoints may not be deployed yet — degrade gracefully
                    console.warn('Integration endpoints not available');
                }
            } catch (error) {
                console.error('Error fetching configuration data:', error);
                setNotification({
                    type: 'error',
                    message: 'Failed to load configuration data'
                });
            } finally {
                setLoading(false);
            }
        }

        fetchData();
    }, []);

    // Refresh integration status (reusable after connect/disconnect)
    const refreshIntegrationStatus = useCallback(async () => {
        try {
            const statuses = await fetchIntegrationStatus();
            setIntegrationStatuses(statuses);
        } catch {
            console.warn('Failed to refresh integration status');
        }
    }, []);

    // Listen for OAuth popup callback postMessage
    useEffect(() => {
        function handleOAuthMessage(event: MessageEvent) {
            if (
                event.data &&
                typeof event.data === 'object' &&
                event.data.type === 'oauth-callback'
            ) {
                const { provider, success, error } = event.data;
                if (success) {
                    setNotification({
                        type: 'success',
                        message: `Successfully connected ${provider}!`,
                    });
                    refreshIntegrationStatus();
                } else {
                    setNotification({
                        type: 'error',
                        message: `Failed to connect ${provider}${error ? `: ${error}` : ''}`,
                    });
                }
            }
        }

        window.addEventListener('message', handleOAuthMessage);
        return () => window.removeEventListener('message', handleOAuthMessage);
    }, [refreshIntegrationStatus]);

    // Budget cap handlers for ad platforms
    const handleCapInputChange = useCallback((providerKey: string, value: string) => {
        setBudgetCapInputs((prev) => ({ ...prev, [providerKey]: value }));
    }, []);

    const handleSaveBudgetCap = useCallback(async (providerKey: string) => {
        const inputVal = budgetCapInputs[providerKey] ?? '';
        const cap = parseFloat(inputVal);
        if (!isFinite(cap) || cap <= 0) {
            setNotification({ type: 'error', message: 'Enter a valid monthly cap amount.' });
            return;
        }
        setSavingCap((prev) => ({ ...prev, [providerKey]: true }));
        try {
            await saveBudgetCap(providerKey, cap);
            const updated = await fetchBudgetCap(providerKey);
            setBudgetCaps((prev) => ({ ...prev, [providerKey]: updated }));
            setBudgetCapInputs((prev) => ({ ...prev, [providerKey]: '' }));
            setNotification({ type: 'success', message: `Budget cap saved: $${cap.toFixed(0)}/month` });
        } catch {
            setNotification({ type: 'error', message: 'Failed to save budget cap. Try again.' });
        } finally {
            setSavingCap((prev) => ({ ...prev, [providerKey]: false }));
        }
    }, [budgetCapInputs]);

    // PM sync handlers
    const handleProjectToggle = useCallback((providerKey: string, projectId: string) => {
        setSyncedProjectIds((prev) => {
            const current = prev[providerKey] ?? [];
            const updated = current.includes(projectId)
                ? current.filter((id) => id !== projectId)
                : [...current, projectId];
            return { ...prev, [providerKey]: updated };
        });
    }, []);

    const handleSavePMSync = useCallback(async (providerKey: string) => {
        const ids = syncedProjectIds[providerKey] ?? [];
        setSavingPMSync((prev) => ({ ...prev, [providerKey]: true }));
        try {
            await savePMSyncConfig(providerKey, ids);
            // Refresh status mappings after sync (seeded from selected projects)
            const mappings = await fetchPMStatusMappings(providerKey);
            setStatusMappings((prev) => ({ ...prev, [providerKey]: mappings }));
            setNotification({
                type: 'success',
                message: `Sync configured for ${ids.length} project(s). Initial sync started.`,
            });
        } catch {
            setNotification({ type: 'error', message: 'Failed to save sync config. Try again.' });
        } finally {
            setSavingPMSync((prev) => ({ ...prev, [providerKey]: false }));
        }
    }, [syncedProjectIds]);

    const handleMappingChange = useCallback(
        (providerKey: string, external_state_id: string, pikar_status: string) => {
            setStatusMappings((prev) => {
                const current = prev[providerKey] ?? [];
                return {
                    ...prev,
                    [providerKey]: current.map((m) =>
                        m.external_state_id === external_state_id
                            ? { ...m, pikar_status }
                            : m
                    ),
                };
            });
        },
        []
    );

    const handleSaveMappings = useCallback(async (providerKey: string) => {
        const mappings = statusMappings[providerKey] ?? [];
        setSavingMappings((prev) => ({ ...prev, [providerKey]: true }));
        try {
            await savePMStatusMappings(providerKey, mappings);
            setNotification({ type: 'success', message: 'Status mappings saved.' });
        } catch {
            setNotification({ type: 'error', message: 'Failed to save mappings. Try again.' });
        } finally {
            setSavingMappings((prev) => ({ ...prev, [providerKey]: false }));
        }
    }, [statusMappings]);

    // Notification rule handlers (Slack + Teams)
    const handleSaveNotifRule = useCallback(async (
        providerKey: string,
        event_type: string,
        channel_id: string,
        channel_name: string,
    ) => {
        try {
            await fetchWithAuth(`/integrations/${providerKey}/notification-rules`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ provider: providerKey, event_type, channel_id, channel_name }),
            });
            const rules = await fetchNotificationRules(providerKey);
            setNotifRules((prev) => ({ ...prev, [providerKey]: rules }));
            setNotification({ type: 'success', message: 'Notification rule saved.' });
        } catch {
            setNotification({ type: 'error', message: 'Failed to save notification rule.' });
        }
    }, []);

    const handleToggleNotifRule = useCallback(async (
        providerKey: string,
        ruleId: string,
        enabled: boolean,
    ) => {
        try {
            await fetchWithAuth(`/integrations/${providerKey}/notification-rules/${ruleId}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enabled }),
            });
            setNotifRules((prev) => ({
                ...prev,
                [providerKey]: (prev[providerKey] ?? []).map((r) =>
                    r.id === ruleId ? { ...r, enabled } : r
                ),
            }));
        } catch {
            setNotification({ type: 'error', message: 'Failed to update rule.' });
        }
    }, []);

    const handleDeleteNotifRule = useCallback(async (providerKey: string, ruleId: string) => {
        try {
            await fetchWithAuth(`/integrations/${providerKey}/notification-rules/${ruleId}`, {
                method: 'DELETE',
            });
            setNotifRules((prev) => ({
                ...prev,
                [providerKey]: (prev[providerKey] ?? []).filter((r) => r.id !== ruleId),
            }));
            setNotification({ type: 'success', message: 'Rule deleted.' });
        } catch {
            setNotification({ type: 'error', message: 'Failed to delete rule.' });
        }
    }, []);

    const handleSaveNotifConfig = useCallback(async (
        providerKey: string,
        cfg: Partial<NotificationConfig>,
    ) => {
        try {
            await fetchWithAuth(`/integrations/${providerKey}/notification-config`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(cfg),
            });
            const updated = await fetchNotificationConfig(providerKey);
            setNotifConfig((prev) => ({ ...prev, [providerKey]: updated }));
            setNotification({ type: 'success', message: 'Briefing settings saved.' });
        } catch {
            setNotification({ type: 'error', message: 'Failed to save briefing settings.' });
        }
    }, []);

    const handleTestNotification = useCallback(async (providerKey: string) => {
        try {
            await fetchWithAuth(`/integrations/${providerKey}/test-notification`, {
                method: 'POST',
            });
            setNotification({ type: 'success', message: `Test notification sent via ${providerKey}!` });
        } catch {
            setNotification({ type: 'error', message: 'Failed to send test notification.' });
        }
    }, []);

    // Integration connect via OAuth popup
    // For ad platforms, require a budget cap to be set first.
    const handleConnectIntegration = useCallback((providerKey: string) => {
        if (AD_PLATFORM_KEYS.has(providerKey)) {
            const cap = budgetCaps[providerKey]?.monthly_cap;
            if (!cap) {
                // Expand the card so user can set the cap inline
                setExpandedProvider(providerKey);
                setNotification({
                    type: 'info',
                    message: `Set a monthly budget cap for ${providerKey === 'google_ads' ? 'Google Ads' : 'Meta Ads'} before connecting.`,
                });
                return;
            }
        }
        const popupUrl = `/api/integrations/${providerKey}/authorize`;
        window.open(popupUrl, 'oauth-popup', 'width=600,height=700,scrollbars=yes');
    }, [budgetCaps]);

    // Integration disconnect
    const handleDisconnectIntegration = useCallback(async (providerKey: string) => {
        setDisconnectingProvider(providerKey);
        try {
            await disconnectIntegration(providerKey);
            setNotification({
                type: 'success',
                message: `Disconnected from ${providerKey}`,
            });
            await refreshIntegrationStatus();
        } catch {
            setNotification({
                type: 'error',
                message: `Failed to disconnect ${providerKey}`,
            });
        } finally {
            setDisconnectingProvider(null);
        }
    }, [refreshIntegrationStatus]);

    const handleOpenSetupWizard = (tool: MCPTool) => {
        setWizardTool(tool);
        setShowWizard(true);
    };

    const handleSaveApiKey = async (toolId: string, apiKey: string) => {
        // Save API key via backend
        const response = await fetch('/api/configuration/save-api-key', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tool_id: toolId, api_key: apiKey }),
        });

        if (!response.ok) {
            throw new Error('Failed to save API key');
        }

        setNotification({ 
            type: 'success', 
            message: `${TOOL_SETUP_GUIDES[toolId]?.name || toolId} has been configured successfully!` 
        });

        // Refresh the tools list
        const mcpResponse = await fetch('/api/configuration/mcp-status');
        if (mcpResponse.ok) {
            const mcpData = await mcpResponse.json();
            setBuiltInTools(mcpData.built_in_tools || []);
            setSchedulerReadiness(mcpData.scheduler_readiness || null);
            setMcpTools(mcpData.configurable_tools || mcpData.tools || []);
        }
    };

    const handleAskAIForHelp = () => {
        // Navigate to command center with a pre-filled configuration help message
        const helpMessage = encodeURIComponent("I need help setting up my tools and integrations. Can you guide me through the configuration process?");
        router.push(`/dashboard/command-center?message=${helpMessage}`);
    };

    const handleConnectSocial = async (platform: string) => {
        setConnectingPlatform(platform);
        try {
            const response = await fetch('/api/configuration/connect-social', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ platform }),
            });

            const data = await response.json();

            if (data.authorization_url) {
                // Redirect to OAuth provider
                window.location.href = data.authorization_url;
            } else if (data.error) {
                setNotification({ 
                    type: 'error', 
                    message: data.error 
                });
            }
        } catch (error) {
            setNotification({ 
                type: 'error', 
                message: 'Failed to initiate connection' 
            });
        } finally {
            setConnectingPlatform(null);
        }
    };

    const handleDisconnectSocial = async (platform: string) => {
        setConnectingPlatform(platform);
        try {
            const response = await fetch('/api/configuration/disconnect-social', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ platform }),
            });

            const data = await response.json();

            if (data.success) {
                setNotification({ 
                    type: 'success', 
                    message: `Disconnected from ${platform}` 
                });
                // Refresh social platforms
                const socialResponse = await fetch('/api/configuration/social-status');
                if (socialResponse.ok) {
                    const socialData = await socialResponse.json();
                    setSocialPlatforms(socialData.platforms || []);
                }
            } else {
                setNotification({ 
                    type: 'error', 
                    message: data.message || 'Failed to disconnect' 
                });
            }
        } catch (error) {
            setNotification({ 
                type: 'error', 
                message: 'Failed to disconnect account' 
            });
        } finally {
            setConnectingPlatform(null);
        }
    };

    // Calculate stats
    const researchProvidersReadyCount = builtInTools.filter(t => t.configured).length;
    const configuredToolsCount = mcpTools.filter(t => t.configured).length;
    const connectedPlatformsCount = socialPlatforms.filter(p => p.connected).length;
    const scheduledJobsLabel = schedulerReadiness?.configuration_ready ? 'Ready to deploy' : 'Needs secret';

    return (
        <DashboardErrorBoundary fallbackTitle="Configuration Error">
        <PremiumShell>
            <motion.div
                initial={{ opacity: 0, y: 18 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
                className="space-y-8 max-w-4xl mx-auto"
            >
                {/* Header */}
                <div>
                    <h1 className="text-3xl font-semibold tracking-tight text-slate-900">Configuration</h1>
                    <p className="text-slate-500 mt-1">
                        Manage your MCP tools, integrations, and connected accounts.
                    </p>
                </div>

                {/* Ask AI for Help Banner */}
                <AskAIHelpBanner onAskAI={handleAskAIForHelp} />

                {/* Notification Banner */}
                <AnimatePresence>
                    {notification && (
                        <InfoBanner type={notification.type} message={notification.message} />
                    )}
                </AnimatePresence>

                                {/* Stats Overview */}
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
                    <div className="rounded-[28px] border border-slate-100/80 bg-white p-5 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]">
                        <div className="flex items-center gap-3">
                            <div className="rounded-2xl bg-gradient-to-br from-sky-400 to-cyan-500 p-2.5 shadow-sm">
                                <Search className="h-5 w-5 text-white" />
                            </div>
                            <div>
                                <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">Research Providers</p>
                                <p className="text-2xl font-semibold text-slate-900">
                                    {researchProvidersReadyCount} / {builtInTools.length}
                                </p>
                            </div>
                        </div>
                    </div>
                    <div className="rounded-[28px] border border-slate-100/80 bg-white p-5 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]">
                        <div className="flex items-center gap-3">
                            <div className="rounded-2xl bg-gradient-to-br from-teal-400 to-cyan-500 p-2.5 shadow-sm">
                                <Zap className="h-5 w-5 text-white" />
                            </div>
                            <div>
                                <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">Tools Configured</p>
                                <p className="text-2xl font-semibold text-slate-900">
                                    {configuredToolsCount} / {mcpTools.length}
                                </p>
                            </div>
                        </div>
                    </div>
                    <div className="rounded-[28px] border border-slate-100/80 bg-white p-5 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]">
                        <div className="flex items-center gap-3">
                            <div className={`rounded-2xl p-2.5 shadow-sm ${schedulerReadiness?.configuration_ready ? 'bg-gradient-to-br from-emerald-400 to-teal-500' : 'bg-gradient-to-br from-amber-400 to-orange-500'}`}>
                                <Rocket className="h-5 w-5 text-white" />
                            </div>
                            <div>
                                <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">Scheduled Jobs</p>
                                <p className="text-lg font-semibold text-slate-900">{scheduledJobsLabel}</p>
                            </div>
                        </div>
                    </div>
                    <div className="rounded-[28px] border border-slate-100/80 bg-white p-5 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]">
                        <div className="flex items-center gap-3">
                            <div className="rounded-2xl bg-gradient-to-br from-emerald-400 to-green-500 p-2.5 shadow-sm">
                                <Link2 className="h-5 w-5 text-white" />
                            </div>
                            <div>
                                <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">Social Accounts</p>
                                <p className="text-2xl font-semibold text-slate-900">
                                    {connectedPlatformsCount} / {socialPlatforms.length}
                                </p>
                            </div>
                        </div>
                    </div>
                </div>

                {loading ? (
                    <div className="flex items-center justify-center py-16">
                        <Loader2 className="w-8 h-8 text-teal-600 animate-spin" />
                    </div>
                ) : (
                    <>
                        {/* Integrations — Provider Cards by Category */}
                        {integrationProviders.length > 0 && (() => {
                            // Group providers by category
                            const groups: Record<string, IntegrationProvider[]> = {};
                            for (const p of integrationProviders) {
                                (groups[p.category] ??= []).push(p);
                            }
                            // Build a status lookup for quick access
                            const statusMap = new Map(
                                integrationStatuses.map((s) => [s.provider, s]),
                            );
                            const connectedCount = integrationStatuses.filter((s) => s.connected).length;

                            const categoryOrder = ['crm_sales', 'finance_commerce', 'productivity', 'communication', 'analytics'];

                            return (
                                <section className="rounded-[28px] border border-slate-100/80 bg-white p-6 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]">
                                    <SectionHeader
                                        icon={<Plug className="w-6 h-6" />}
                                        title="Integrations"
                                        description={`Connect your business tools. ${connectedCount} of ${integrationProviders.length} providers connected.`}
                                    />

                                    <div className="space-y-8">
                                        {categoryOrder.map((cat) => {
                                            const providersInCat = groups[cat];
                                            if (!providersInCat || providersInCat.length === 0) return null;
                                            return (
                                                <div key={cat}>
                                                    <div className="flex items-center gap-2 mb-3">
                                                        <span className="text-slate-400">
                                                            {CATEGORY_ICONS[cat] || <Plug className="w-4 h-4" />}
                                                        </span>
                                                        <h3 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">
                                                            {CATEGORY_LABELS[cat] || cat}
                                                        </h3>
                                                    </div>
                                                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                                                        {providersInCat.map((p) => (
                                                            <IntegrationProviderCard
                                                                key={p.key}
                                                                provider={p}
                                                                status={statusMap.get(p.key)}
                                                                expanded={expandedProvider === p.key}
                                                                onToggleExpand={() =>
                                                                    setExpandedProvider(
                                                                        expandedProvider === p.key ? null : p.key,
                                                                    )
                                                                }
                                                                onConnect={handleConnectIntegration}
                                                                onDisconnect={handleDisconnectIntegration}
                                                                isDisconnecting={disconnectingProvider === p.key}
                                                                capData={AD_PLATFORM_KEYS.has(p.key) ? budgetCaps[p.key] : undefined}
                                                                capInputValue={AD_PLATFORM_KEYS.has(p.key) ? (budgetCapInputs[p.key] ?? '') : undefined}
                                                                onCapInputChange={AD_PLATFORM_KEYS.has(p.key) ? (val) => handleCapInputChange(p.key, val) : undefined}
                                                                onCapSave={AD_PLATFORM_KEYS.has(p.key) ? () => handleSaveBudgetCap(p.key) : undefined}
                                                                savingCap={AD_PLATFORM_KEYS.has(p.key) ? (savingCap[p.key] ?? false) : undefined}
                                                                pmProjects={PM_PROVIDER_KEYS.has(p.key) ? (pmProjects[p.key] ?? []) : undefined}
                                                                syncedProjectIds={PM_PROVIDER_KEYS.has(p.key) ? (syncedProjectIds[p.key] ?? []) : undefined}
                                                                onProjectToggle={PM_PROVIDER_KEYS.has(p.key) ? (id) => handleProjectToggle(p.key, id) : undefined}
                                                                onSavePMSync={PM_PROVIDER_KEYS.has(p.key) ? () => handleSavePMSync(p.key) : undefined}
                                                                savingPMSync={PM_PROVIDER_KEYS.has(p.key) ? (savingPMSync[p.key] ?? false) : undefined}
                                                                statusMappings={PM_PROVIDER_KEYS.has(p.key) ? (statusMappings[p.key] ?? []) : undefined}
                                                                onMappingChange={PM_PROVIDER_KEYS.has(p.key) ? (id, status) => handleMappingChange(p.key, id, status) : undefined}
                                                                onSaveMappings={PM_PROVIDER_KEYS.has(p.key) ? () => handleSaveMappings(p.key) : undefined}
                                                                savingMappings={PM_PROVIDER_KEYS.has(p.key) ? (savingMappings[p.key] ?? false) : undefined}
                                                                notifRules={NOTIF_PROVIDER_KEYS.has(p.key) ? (notifRules[p.key] ?? []) : undefined}
                                                                notifChannels={NOTIF_PROVIDER_KEYS.has(p.key) ? (notifChannels[p.key] ?? []) : undefined}
                                                                notifConfig={NOTIF_PROVIDER_KEYS.has(p.key) ? (notifConfig[p.key] ?? null) : undefined}
                                                                notifEvents={NOTIF_PROVIDER_KEYS.has(p.key) ? notifEvents : undefined}
                                                                onSaveNotifRule={NOTIF_PROVIDER_KEYS.has(p.key) ? handleSaveNotifRule : undefined}
                                                                onToggleNotifRule={NOTIF_PROVIDER_KEYS.has(p.key) ? handleToggleNotifRule : undefined}
                                                                onDeleteNotifRule={NOTIF_PROVIDER_KEYS.has(p.key) ? handleDeleteNotifRule : undefined}
                                                                onSaveNotifConfig={NOTIF_PROVIDER_KEYS.has(p.key) ? handleSaveNotifConfig : undefined}
                                                                onTestNotification={NOTIF_PROVIDER_KEYS.has(p.key) ? handleTestNotification : undefined}
                                                            />
                                                        ))}
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </div>
                                </section>
                            );
                        })()}

                        {/* Built-in Research Providers */}
                        {builtInTools.length > 0 && (
                            <section className="rounded-[28px] border border-slate-100/80 bg-white p-6 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]">
                                <SectionHeader
                                    icon={<Search className="w-6 h-6" />}
                                    title="Built-in Research Providers"
                                    description="These providers are built into the platform, but each one still needs its server-side API key before the research pipeline can use it."
                                />

                                <div className="space-y-3">
                                    {builtInTools.map((tool) => (
                                        <div
                                            key={tool.id}
                                            className={`flex items-center gap-4 rounded-xl border p-4 backdrop-blur ${tool.configured ? 'border-emerald-100 bg-white/85' : 'border-amber-200 bg-white/75'}`}
                                        >
                                            <div className={`rounded-lg p-2.5 ${tool.configured ? 'bg-emerald-100 text-emerald-600' : 'bg-amber-100 text-amber-700'}`}>
                                                {mcpToolIcons[tool.id] || <Zap className="w-5 h-5" />}
                                            </div>
                                            <div className="flex-1">
                                                <div className="flex flex-wrap items-center gap-2">
                                                    <h3 className="font-medium text-slate-800">{tool.name}</h3>
                                                    <span className={`flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${tool.configured ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-800'}`}>
                                                        {tool.configured ? <CheckCircle2 className="w-3 h-3" /> : <AlertCircle className="w-3 h-3" />}
                                                        {tool.status}
                                                    </span>
                                                </div>
                                                <p className="mt-0.5 text-sm text-slate-500">{tool.description}</p>
                                            </div>
                                        </div>
                                    ))}
                                </div>

                                <div className="mt-4 rounded-lg border border-sky-100 bg-white/70 p-3">
                                    <p className="text-sm text-sky-800">
                                        <strong>What users now see:</strong> research responses can show confidence, citations, contradictions, and suggested next questions directly in chat whenever these providers return structured research results.
                                    </p>
                                </div>
                            </section>
                        )}

                        {/* Scheduled Jobs Readiness */}
                        {schedulerReadiness && (
                            <section className="rounded-[28px] border border-slate-100/80 bg-white p-6 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]">
                                <SectionHeader
                                    icon={<Rocket className="w-6 h-6" />}
                                    title="Scheduled Jobs"
                                    description="Server-side readiness for recurring reports and unattended automation."
                                />

                                <div className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
                                    <div className="rounded-xl border border-white/70 bg-white/75 p-4">
                                        <div className="flex flex-wrap items-center gap-2">
                                            <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${schedulerReadiness.configuration_ready ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-800'}`}>
                                                {schedulerReadiness.status}
                                            </span>
                                        </div>
                                        <p className="mt-3 text-sm leading-relaxed text-slate-700">
                                            {schedulerReadiness.message}
                                        </p>
                                        <p className="mt-3 text-xs text-slate-500">
                                            To run while users are offline, keep both the API and at least one worker deployed on always-on infrastructure, then trigger the scheduler endpoint from Cloud Scheduler or Supabase cron.
                                        </p>
                                    </div>

                                    <div className="space-y-3">
                                        <div className="flex items-start gap-3 rounded-xl border border-white/70 bg-white/75 p-3">
                                            <div className={`mt-0.5 rounded-full p-1 ${schedulerReadiness.configuration_ready ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-800'}`}>
                                                {schedulerReadiness.configuration_ready ? <CheckCircle2 className="h-4 w-4" /> : <AlertCircle className="h-4 w-4" />}
                                            </div>
                                            <div>
                                                <p className="text-sm font-medium text-slate-800">Scheduler secret configured</p>
                                                <p className="text-xs text-slate-500">Required to authenticate external scheduler calls safely.</p>
                                            </div>
                                        </div>
                                        <div className="flex items-start gap-3 rounded-xl border border-white/70 bg-white/75 p-3">
                                            <div className="mt-0.5 rounded-full bg-emerald-100 p-1 text-emerald-700">
                                                <CheckCircle2 className="h-4 w-4" />
                                            </div>
                                            <div>
                                                <p className="text-sm font-medium text-slate-800">Worker schedule tick enabled</p>
                                                <p className="text-xs text-slate-500">Saved report schedules are checked by the worker every minute.</p>
                                            </div>
                                        </div>
                                        <div className="flex items-start gap-3 rounded-xl border border-white/70 bg-white/75 p-3">
                                            <div className="mt-0.5 rounded-full bg-emerald-100 p-1 text-emerald-700">
                                                <CheckCircle2 className="h-4 w-4" />
                                            </div>
                                            <div>
                                                <p className="text-sm font-medium text-slate-800">Scheduled endpoints are secured</p>
                                                <p className="text-xs text-slate-500">The backend now fails closed when scheduler auth is missing or invalid.</p>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </section>
                        )}

                        {/* Google Workspace Section */}
                        <section className="rounded-[28px] border border-slate-100/80 bg-white p-6 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]">
                            <SectionHeader
                                icon={<FileText className="w-6 h-6" />}
                                title="Google Workspace"
                                description="Create documents, spreadsheets, forms, and more with your Google account."
                            />

                            {googleWorkspace?.connected ? (
                                <div className="space-y-4">
                                    <div className="flex items-center gap-4 bg-white/80 backdrop-blur border border-blue-100 rounded-xl p-4">
                                        <div className="p-3 bg-blue-100 rounded-lg">
                                            <CheckCircle2 className="w-6 h-6 text-blue-600" />
                                        </div>
                                        <div className="flex-1">
                                            <div className="flex items-center gap-2">
                                                <h3 className="font-semibold text-slate-800">Connected</h3>
                                                <span className="text-xs font-medium text-blue-600 bg-blue-100 px-2 py-0.5 rounded-full">
                                                    Active
                                                </span>
                                            </div>
                                            <p className="text-sm text-slate-600 mt-0.5">{googleWorkspace.email}</p>
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                        {googleWorkspace.features.map((feature, index) => (
                                            <div
                                                key={index}
                                                className="flex items-center gap-2 text-sm text-slate-600 bg-white/60 rounded-lg p-3 border border-blue-100"
                                            >
                                                <CheckCircle2 className="w-4 h-4 text-blue-500 flex-shrink-0" />
                                                <span>{feature}</span>
                                            </div>
                                        ))}
                                    </div>

                                    <div className="p-3 bg-blue-100/50 rounded-lg">
                                        <p className="text-sm text-blue-800">
                                            <strong>How to use:</strong> Simply ask the AI to create a document, spreadsheet, or form. 
                                            For example: &quot;Create a project proposal document&quot; or &quot;Make a budget spreadsheet&quot;.
                                        </p>
                                    </div>
                                </div>
                            ) : (
                                <div className="text-center py-8">
                                    <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
                                        <FileText className="w-8 h-8 text-slate-400" />
                                    </div>
                                    <h3 className="font-medium text-slate-700 mb-2">Google Workspace Not Available</h3>
                                    <p className="text-sm text-slate-500 max-w-md mx-auto">
                                        {googleWorkspace?.message || 'Sign in with your Google account to enable Google Workspace features like creating documents, spreadsheets, and forms.'}
                                    </p>
                                    <p className="text-xs text-slate-400 mt-4">
                                        To use this feature, sign out and sign back in using &quot;Continue with Google&quot;.
                                    </p>
                                </div>
                            )}
                        </section>

                        {/* Analytics — Database Connections */}
                        <section className="rounded-[28px] border border-slate-100/80 bg-white p-6 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]">
                            <SectionHeader
                                icon={<Database className="w-6 h-6" />}
                                title="Analytics"
                                description="Connect external databases so the AI can query them with natural language."
                            />
                            <DBConnectionsSection />
                        </section>

                        {/* Continuous Intelligence — Monitoring Jobs */}
                        <section className="rounded-[28px] border border-slate-100/80 bg-white p-6 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]">
                            <SectionHeader
                                icon={<Radar className="w-6 h-6" />}
                                title="Continuous Intelligence"
                                description="Monitor competitors, markets, and topics automatically. Get alerted when significant changes are detected."
                            />
                            <MonitoringJobsSection />
                        </section>

                        {/* Outbound Webhooks */}
                        <section className="rounded-[28px] border border-slate-100/80 bg-white p-6 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]">
                            <SectionHeader
                                icon={<Zap className="w-6 h-6" />}
                                title="Outbound Webhooks"
                                description="Send real-time events to external services like Zapier, Make, or your own server when things happen in Pikar."
                            />
                            <WebhooksSection />
                        </section>

                        {/* MCP Tools Section */}
                        <section className="rounded-[28px] border border-slate-100/80 bg-white p-6 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]">
                            <SectionHeader
                                icon={<Settings className="w-6 h-6" />}
                                title="Optional Tools"
                                description="Enhance your AI assistant with additional capabilities. Click 'Set Up' to configure each tool."
                            />

                            <div className="space-y-4">
                                {mcpTools.length > 0 ? (
                                    mcpTools.map((tool) => (
                                        <MCPToolCard
                                            key={tool.id}
                                            tool={tool}
                                            onSetup={handleOpenSetupWizard}
                                        />
                                    ))
                                ) : (
                                    <div className="text-center py-8 text-slate-400">
                                        <Settings className="w-12 h-12 mx-auto mb-3 opacity-50" />
                                        <p>No MCP tools available</p>
                                    </div>
                                )}
                            </div>

                            <div className="mt-6 p-4 bg-teal-50 rounded-2xl border border-teal-100">
                                <div className="flex items-start gap-3">
                                    <HelpCircle className="w-5 h-5 text-teal-600 mt-0.5" />
                                    <div className="text-sm text-teal-800">
                                        <p className="font-medium">Not sure which tools you need?</p>
                                        <p className="mt-1 text-teal-700">
                                            Click &quot;Ask AI for Help&quot; above and describe what you want to accomplish. 
                                            I&apos;ll recommend the right tools and guide you through setup step by step.
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </section>

                        {/* Social Media Accounts Section */}
                        <section className="rounded-[28px] border border-slate-100/80 bg-white p-6 shadow-[0_18px_60px_-30px_rgba(15,23,42,0.35)]">
                            <SectionHeader
                                icon={<Link2 className="w-6 h-6" />}
                                title="Social Media Accounts"
                                description="Connect your social media accounts for AI-powered publishing and analytics."
                            />

                            <div className="space-y-4">
                                {socialPlatforms.length > 0 ? (
                                    socialPlatforms.map((platform) => (
                                        <SocialPlatformCard
                                            key={platform.platform}
                                            platform={platform}
                                            onConnect={handleConnectSocial}
                                            onDisconnect={handleDisconnectSocial}
                                            isLoading={connectingPlatform === platform.platform}
                                        />
                                    ))
                                ) : (
                                    <div className="text-center py-8 text-slate-400">
                                        <Link2 className="w-12 h-12 mx-auto mb-3 opacity-50" />
                                        <p>No social platforms available</p>
                                    </div>
                                )}
                            </div>

                            <div className="mt-6 p-4 bg-amber-50 rounded-2xl border border-amber-200">
                                <div className="flex items-start gap-3">
                                    <AlertCircle className="w-5 h-5 text-amber-600 mt-0.5" />
                                    <div className="text-sm text-amber-800">
                                        <p className="font-medium">OAuth Setup Required</p>
                                        <p className="mt-1 text-amber-700">
                                            To connect social accounts, you need to configure OAuth credentials for each platform.
                                            Ask AI for help if you need guidance on how to set this up.
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </section>
                    </>
                )}
            </motion.div>

            {/* Setup Wizard Modal */}
            <AnimatePresence>
                {showWizard && (
                    <SetupWizardModal
                        tool={wizardTool}
                        isOpen={showWizard}
                        onClose={() => {
                            setShowWizard(false);
                            setWizardTool(null);
                        }}
                        onSave={handleSaveApiKey}
                    />
                )}
            </AnimatePresence>
        </PremiumShell>
        </DashboardErrorBoundary>
    );
}
