import { createClient } from '@/lib/supabase/client';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// ============================================================================
// Types
// ============================================================================

export interface BusinessContextInput {
    company_name: string;
    industry: string;
    description: string;
    goals: string[];
    team_size?: string;
    role?: string;
    website?: string;
}

export interface UserPreferencesInput {
    tone: string;
    verbosity: string;
    communication_style: string;
    notification_frequency: string;
}

export interface AgentSetupInput {
    agent_name: string;
    focus_areas?: string[];
}

export interface OnboardingStatus {
    is_completed: boolean;
    current_step: number;
    total_steps?: number;
    business_context_completed: boolean;
    preferences_completed: boolean;
    agent_setup_completed: boolean;
    persona?: string | null;
    agent_name?: string | null;
}

export type PersonaType = 'solopreneur' | 'startup' | 'sme' | 'enterprise';

export interface PersonaInfo {
    id: PersonaType;
    title: string;
    description: string;
    icon: string;
    color: string;
}

export const PERSONA_INFO: Record<PersonaType, PersonaInfo> = {
    solopreneur: {
        id: 'solopreneur',
        title: 'Solopreneur',
        description: 'Efficiency-focused, low-overhead solutions for solo operators',
        icon: '🚀',
        color: 'from-orange-500 to-amber-500'
    },
    startup: {
        id: 'startup',
        title: 'Startup',
        description: 'Growth-focused, metrics-driven assistance for fast-moving teams',
        icon: '⚡',
        color: 'from-violet-500 to-purple-500'
    },
    sme: {
        id: 'sme',
        title: 'SME',
        description: 'Optimization-focused, compliance-oriented support for established businesses',
        icon: '📊',
        color: 'from-blue-500 to-cyan-500'
    },
    enterprise: {
        id: 'enterprise',
        title: 'Enterprise',
        description: 'Strategy-focused, security-conscious guidance for large organizations',
        icon: '🏢',
        color: 'from-slate-600 to-slate-800'
    }
};

// ============================================================================
// API Helpers
// ============================================================================

const getHeaders = async (): Promise<Record<string, string>> => {
    const supabase = createClient();
    const { data: { session } } = await supabase.auth.getSession();
    const token = session?.access_token;

    return {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : '',
    };
};

// ============================================================================
// Persona Determination (Client-side preview)
// ============================================================================

export const determinePersonaPreview = (context: BusinessContextInput): PersonaType => {
    const size = (context.team_size || '').toLowerCase();
    const role = (context.role || '').toLowerCase();
    const industry = (context.industry || '').toLowerCase();

    // Enterprise Rules
    if (size.includes('200+') || size.includes('enterprise') || size.includes('500+')) {
        return 'enterprise';
    }
    if (industry.includes('corporate') && (role.includes('vp') || role.includes('chief') || role.includes('head'))) {
        return 'enterprise';
    }

    // SME Rules
    if (size.includes('51-200')) {
        return 'sme';
    }
    if (size.includes('11-50') && industry.includes('manufacturing')) {
        return 'sme';
    }

    // Solopreneur Rules
    if (size.includes('just me') || size.includes('solopreneur') || size === '1') {
        return 'solopreneur';
    }
    if (role.includes('freelance') || role.includes('consultant')) {
        return 'solopreneur';
    }

    // Default to Startup
    return 'startup';
};

// ============================================================================
// API Functions
// ============================================================================

export const getOnboardingStatus = async (): Promise<OnboardingStatus> => {
    const headers = await getHeaders();
    const response = await fetch(`${API_BASE_URL}/onboarding/status`, {
        method: 'GET',
        headers,
    });

    if (!response.ok) {
        const error = await response.text().catch(() => 'Unknown error');
        throw new Error(`Failed to fetch onboarding status: ${error}`);
    }

    return response.json();
};

export const submitBusinessContext = async (data: BusinessContextInput): Promise<void> => {
    const headers = await getHeaders();
    const response = await fetch(`${API_BASE_URL}/onboarding/business-context`, {
        method: 'POST',
        headers,
        body: JSON.stringify(data),
    });

    if (!response.ok) {
        const error = await response.text().catch(() => 'Unknown error');
        throw new Error(`Failed to submit business context: ${error}`);
    }
};

export const submitPreferences = async (data: UserPreferencesInput): Promise<void> => {
    const headers = await getHeaders();
    const response = await fetch(`${API_BASE_URL}/onboarding/preferences`, {
        method: 'POST',
        headers,
        body: JSON.stringify(data),
    });

    if (!response.ok) {
        const error = await response.text().catch(() => 'Unknown error');
        throw new Error(`Failed to submit preferences: ${error}`);
    }
};

export const submitAgentSetup = async (data: AgentSetupInput): Promise<void> => {
    const headers = await getHeaders();
    const response = await fetch(`${API_BASE_URL}/onboarding/agent-setup`, {
        method: 'POST',
        headers,
        body: JSON.stringify(data),
    });

    if (!response.ok) {
        const error = await response.text().catch(() => 'Unknown error');
        throw new Error(`Failed to submit agent setup: ${error}`);
    }
};

export const completeOnboarding = async (): Promise<{ status: string; persona: string }> => {
    const headers = await getHeaders();
    const response = await fetch(`${API_BASE_URL}/onboarding/complete`, {
        method: 'POST',
        headers,
    });

    if (!response.ok) {
        const error = await response.text().catch(() => 'Unknown error');
        throw new Error(`Failed to complete onboarding: ${error}`);
    }

    return response.json();
};

// ============================================================================
// Constants
// ============================================================================

export const GOALS_OPTIONS = [
    { id: 'growth', label: 'Revenue Growth', icon: '📈' },
    { id: 'efficiency', label: 'Operational Efficiency', icon: '⚡' },
    { id: 'automation', label: 'Process Automation', icon: '🤖' },
    { id: 'cost_reduction', label: 'Cost Reduction', icon: '💰' },
    { id: 'innovation', label: 'Innovation & R&D', icon: '💡' },
    { id: 'risk', label: 'Risk Management', icon: '🛡️' },
    { id: 'customer', label: 'Customer Experience', icon: '❤️' },
    { id: 'talent', label: 'Talent & Culture', icon: '👥' },
];

export const TEAM_SIZES = [
    { id: 'solo', label: 'Just Me (Solopreneur)', description: 'Solo operator or freelancer' },
    { id: 'startup', label: '1-10 (Startup)', description: 'Small founding team' },
    { id: 'sme-small', label: '11-50 (Growing SME)', description: 'Established small business' },
    { id: 'sme-large', label: '51-200 (Scaling SME)', description: 'Scaling organization' },
    { id: 'enterprise', label: '200+ (Enterprise)', description: 'Large organization' },
];

export const INDUSTRIES = [
    'Technology / SaaS',
    'E-commerce / Retail',
    'Financial Services / Fintech',
    'Healthcare / MedTech',
    'Manufacturing',
    'Professional Services',
    'Education / EdTech',
    'Real Estate',
    'Media / Entertainment',
    'Hospitality / Travel',
    'Logistics / Supply Chain',
    'Energy / CleanTech',
    'Other',
];

export const TONE_OPTIONS = [
    { id: 'professional', label: 'Professional', description: 'Formal and precise communication', icon: '👔' },
    { id: 'casual', label: 'Casual', description: 'Relaxed and conversational', icon: '😊' },
    { id: 'enthusiastic', label: 'Enthusiastic', description: 'Energetic and motivating', icon: '🔥' },
];

export const VERBOSITY_OPTIONS = [
    { id: 'concise', label: 'Concise', description: 'Brief, to-the-point responses', icon: '📝' },
    { id: 'balanced', label: 'Balanced', description: 'Clear explanations with context', icon: '⚖️' },
    { id: 'detailed', label: 'Detailed', description: 'Thorough analysis and explanations', icon: '📚' },
];

export const COMMUNICATION_STYLE_OPTIONS = [
    { id: 'direct', label: 'Direct', description: 'Straightforward and action-oriented' },
    { id: 'supportive', label: 'Supportive', description: 'Encouraging with guidance' },
    { id: 'analytical', label: 'Analytical', description: 'Data-driven with insights' },
];

export const NOTIFICATION_FREQUENCY_OPTIONS = [
    { id: 'realtime', label: 'Real-time', description: 'Instant notifications' },
    { id: 'daily', label: 'Daily Digest', description: 'Summary once per day' },
    { id: 'weekly', label: 'Weekly Summary', description: 'Overview each week' },
];
