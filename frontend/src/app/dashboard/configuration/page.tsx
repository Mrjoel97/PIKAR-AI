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
} from 'lucide-react';
import {
    fetchProviders,
    fetchIntegrationStatus,
    disconnectProvider as disconnectIntegration,
    type IntegrationProvider,
    type IntegrationStatus,
} from '@/services/integrations';
import { API_BASE_URL } from '@/services/api';

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
}: {
    provider: IntegrationProvider;
    status: IntegrationStatus | undefined;
    expanded: boolean;
    onToggleExpand: () => void;
    onConnect: (key: string) => void;
    onDisconnect: (key: string) => void;
    isDisconnecting: boolean;
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
                            <button
                                onClick={() => onConnect(provider.key)}
                                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-teal-600 hover:bg-teal-700 rounded-2xl transition-colors"
                            >
                                <Link2 className="w-4 h-4" />
                                Connect
                            </button>
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
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.div>
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

    // Integration connect via OAuth popup
    const handleConnectIntegration = useCallback((providerKey: string) => {
        const popupUrl = `${API_BASE_URL}/integrations/${providerKey}/authorize`;
        window.open(popupUrl, 'oauth-popup', 'width=600,height=700,scrollbars=yes');
    }, []);

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
