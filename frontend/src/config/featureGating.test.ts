import { afterEach, describe, expect, it, vi } from 'vitest';

afterEach(() => {
  vi.unstubAllEnvs();
});

describe('feature gate override', () => {
  it('unlocks gated features when the testing override is enabled', async () => {
    vi.stubEnv('NEXT_PUBLIC_ALLOW_ALL_FEATURES_FOR_TESTING', 'true');
    const { isFeatureAllowed } = await import('./featureGating');

    expect(isFeatureAllowed('teams', 'solopreneur')).toBe(true);
    expect(isFeatureAllowed('governance', 'solopreneur')).toBe(true);
  });
});
