import { createClient } from '@/lib/supabase/client';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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
    communication_style?: string;
    notification_frequency?: string;
}

export interface OnboardingStatus {
    is_completed: boolean;
    current_step: number;
    business_context_completed: boolean;
    preferences_completed: boolean;
    agent_setup_completed: boolean;
    persona?: string | null;
}

const getHeaders = async () => {
    const supabase = createClient();
    const { data: { session } } = await supabase.auth.getSession();
    const token = session?.access_token;

    return {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : '',
    };
};

export const getOnboardingStatus = async (): Promise<OnboardingStatus> => {
    const headers = await getHeaders();
    const response = await fetch(`${API_BASE_URL}/onboarding/status`, {
        method: 'GET',
        headers,
    });

    if (!response.ok) {
        throw new Error('Failed to fetch onboarding status');
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
        throw new Error('Failed to submit business context');
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
        throw new Error('Failed to submit preferences');
    }
};

export const completeOnboarding = async (): Promise<{ status: string; persona: string }> => {
    const headers = await getHeaders();
    const response = await fetch(`${API_BASE_URL}/onboarding/complete`, {
        method: 'POST',
        headers,
    });

    if (!response.ok) {
        throw new Error('Failed to complete onboarding');
    }

    return response.json();
};
