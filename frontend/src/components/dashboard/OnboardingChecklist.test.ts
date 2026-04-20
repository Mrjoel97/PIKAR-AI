import { describe, expect, it } from 'vitest';

import {
  enrichChecklistItems,
  getRecommendedChecklistItem,
} from './OnboardingChecklist';

describe('OnboardingChecklist helpers', () => {
  it('hydrates backend checklist items with matching frontend prompts', () => {
    const enriched = enrichChecklistItems('solopreneur', [
      {
        id: 'brain_dump',
        title: 'Do a brain dump',
        description: 'Get all your ideas organized',
        completed: false,
      },
    ]);

    expect(enriched[0]?.prompt).toContain('onboarding');
    expect(enriched[0]?.prompt).toContain('knowledge vault');
    expect(enriched[0]?.icon).toBe('🧠');
  });

  it('falls back to a generic guided prompt for unknown checklist ids', () => {
    const enriched = enrichChecklistItems('startup', [
      {
        id: 'custom_step',
        title: 'Custom step',
        description: 'A custom onboarding action',
        completed: false,
      },
    ]);

    expect(enriched[0]?.prompt).toContain('saved onboarding brief');
    expect(enriched[0]?.prompt).toContain('Custom step');
  });

  it('returns the first incomplete item as the recommended next step', () => {
    const recommended = getRecommendedChecklistItem([
      {
        id: 'first_workflow',
        icon: '⚡',
        title: 'Run your first workflow',
        description: 'Automate a repetitive task',
        prompt: 'Prompt A',
        completed: true,
      },
      {
        id: 'brain_dump',
        icon: '🧠',
        title: 'Do a brain dump',
        description: 'Get all your ideas organized',
        prompt: 'Prompt B',
        completed: false,
      },
    ]);

    expect(recommended?.id).toBe('brain_dump');
  });
});
