import { describe, expect, it } from 'vitest';

import {
    BUILT_IN_RESEARCH_PROVIDER_FALLBACKS,
    normalizeBuiltInResearchProviders,
} from './builtInResearchProviders';

describe('builtInResearchProviders', () => {
    it('falls back to Tavily and Firecrawl when the API payload is missing', () => {
        expect(normalizeBuiltInResearchProviders()).toEqual(
            BUILT_IN_RESEARCH_PROVIDER_FALLBACKS,
        );
    });

    it('keeps platform-managed providers active even if the API reports them inactive', () => {
        const normalized = normalizeBuiltInResearchProviders([
            {
                id: 'tavily',
                configured: false,
                status: 'Unconfigured',
                operator_configured: false,
                operator_status: 'Server API key missing',
            },
        ]);

        const tavily = normalized.find((provider) => provider.id === 'tavily');
        expect(tavily).toMatchObject({
            configured: true,
            status: 'Active for all users',
            platform_managed: true,
            availability_scope: 'all_users',
            operator_configured: false,
            operator_status: 'Server API key missing',
        });
    });
});
