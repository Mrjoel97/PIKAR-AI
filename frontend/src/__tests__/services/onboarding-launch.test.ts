import { describe, expect, it } from 'vitest'

import {
  buildChatLaunchUrl,
  buildUrlWithoutDashboardLaunchParams,
  extractDashboardLaunchRequest,
  getPostOnboardingRoute,
} from '@/lib/onboarding/navigation'

describe('onboarding launch helpers', () => {
  it('builds a persona chat launch URL with a sanitized prompt', () => {
    const url = buildChatLaunchUrl('startup', '  Help me plan our next experiment  ')
    const parsed = new URL(url, 'https://example.com')

    expect(parsed.pathname).toBe('/startup')
    expect(parsed.searchParams.get('initialPrompt')).toBe('Help me plan our next experiment')
  })

  it('falls back to the base persona route when the prompt is empty', () => {
    expect(buildChatLaunchUrl('enterprise', '   ')).toBe('/enterprise')
  })

  it('extracts a direct initialPrompt launch request', () => {
    const request = extractDashboardLaunchRequest(
      new URLSearchParams('initialPrompt=Launch+my+first+workflow'),
    )

    expect(request).toEqual({
      key: 'initialPrompt:Launch my first workflow',
      prompt: 'Launch my first workflow',
    })
  })

  it('extracts initiative journey launch requests with optional outcomes context', () => {
    const request = extractDashboardLaunchRequest(
      new URLSearchParams(
        'context=initiative&initiativeId=init-42&title=North+Star+Launch&fromJourney=1&outcomesPrompt=Define+activation+targets',
      ),
    )

    expect(request?.key).toBe('initiative-journey:init-42')
    expect(request?.prompt).toContain('North Star Launch')
    expect(request?.prompt).toContain('start_journey_workflow')
    expect(request?.prompt).toContain('Define activation targets')
  })

  it('extracts brain dump launch requests', () => {
    const request = extractDashboardLaunchRequest(
      new URLSearchParams('braindump_id=brain-123'),
    )

    expect(request?.key).toBe('braindump:brain-123')
    expect(request?.prompt).toContain('brain-123')
    expect(request?.prompt).toContain('get_braindump_document')
  })

  it('removes launch params while preserving unrelated query state', () => {
    const cleaned = buildUrlWithoutDashboardLaunchParams(
      '/startup',
      new URLSearchParams('initialPrompt=Hello&notice=ok&session=session-1'),
      ['session'],
    )

    expect(cleaned).toBe('/startup?notice=ok')
  })

  it('returns a chat-enabled post-onboarding fallback route', () => {
    expect(getPostOnboardingRoute('sme')).toBe('/sme')
    expect(getPostOnboardingRoute(null)).toBe('/dashboard/workspace')
  })
})
