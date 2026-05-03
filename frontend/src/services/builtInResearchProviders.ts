export interface BuiltInResearchProviderStatus {
    id: string;
    name: string;
    description: string;
    is_built_in: boolean;
    configured: boolean;
    status: string;
    platform_managed?: boolean;
    availability_scope?: string;
    operator_configured?: boolean;
    operator_status?: string;
}

export const BUILT_IN_RESEARCH_PROVIDER_FALLBACKS: BuiltInResearchProviderStatus[] = [
    {
        id: 'tavily',
        name: 'Web Search (Tavily)',
        description: 'AI-powered web search - automatically used for research tasks.',
        is_built_in: true,
        configured: true,
        status: 'Active for all users',
        platform_managed: true,
        availability_scope: 'all_users',
    },
    {
        id: 'firecrawl',
        name: 'Web Scraping (Firecrawl)',
        description: 'Content extraction from webpages - automatically used for deep research.',
        is_built_in: true,
        configured: true,
        status: 'Active for all users',
        platform_managed: true,
        availability_scope: 'all_users',
    },
];

const FALLBACK_BY_ID = new Map(
    BUILT_IN_RESEARCH_PROVIDER_FALLBACKS.map((provider) => [provider.id, provider]),
);

export const BUILT_IN_RESEARCH_PROVIDER_IDS = new Set(FALLBACK_BY_ID.keys());

export function normalizeBuiltInResearchProviders(
    providers?: Partial<BuiltInResearchProviderStatus>[] | null,
): BuiltInResearchProviderStatus[] {
    const normalized = new Map<string, BuiltInResearchProviderStatus>();

    for (const fallback of BUILT_IN_RESEARCH_PROVIDER_FALLBACKS) {
        normalized.set(fallback.id, { ...fallback });
    }

    for (const provider of providers ?? []) {
        if (!provider || typeof provider.id !== 'string') continue;

        const fallback = FALLBACK_BY_ID.get(provider.id);
        const merged: BuiltInResearchProviderStatus = {
            ...(fallback ?? {
                id: provider.id,
                name: provider.name ?? provider.id,
                description: provider.description ?? '',
                is_built_in: true,
                configured: Boolean(provider.configured),
                status: provider.status ?? 'Bundled in the app',
            }),
            ...provider,
        };

        if (fallback) {
            merged.configured = true;
            merged.status = 'Active for all users';
            merged.is_built_in = true;
            merged.platform_managed = true;
            merged.availability_scope = 'all_users';
        }

        normalized.set(provider.id, merged);
    }

    const ordered = BUILT_IN_RESEARCH_PROVIDER_FALLBACKS.map(
        (provider) => normalized.get(provider.id) ?? provider,
    );

    for (const [providerId, provider] of normalized.entries()) {
        if (!FALLBACK_BY_ID.has(providerId)) {
            ordered.push(provider);
        }
    }

    return ordered;
}
