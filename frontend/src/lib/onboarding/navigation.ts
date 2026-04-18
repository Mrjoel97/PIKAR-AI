// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import type { PersonaType } from '@/services/onboarding'

type SearchParamsLike = Pick<URLSearchParams, 'get' | 'toString'>

const DASHBOARD_LAUNCH_PARAM_KEYS = [
  'initialPrompt',
  'context',
  'initiativeId',
  'title',
  'fromJourney',
  'outcomesPrompt',
  'braindump_id',
] as const

export interface DashboardLaunchRequest {
  key: string
  prompt: string
}

function normalizePrompt(value: string | null | undefined): string | null {
  const trimmed = value?.trim()
  return trimmed ? trimmed : null
}

export function getPersonaChatRoute(persona: PersonaType): string {
  return `/${persona}`
}

export function getPostOnboardingRoute(persona?: PersonaType | null): string {
  return persona ? getPersonaChatRoute(persona) : '/dashboard/workspace'
}

export function buildChatLaunchUrl(
  persona: PersonaType,
  prompt?: string | null,
): string {
  const route = getPersonaChatRoute(persona)
  const normalizedPrompt = normalizePrompt(prompt)
  if (!normalizedPrompt) {
    return route
  }

  const params = new URLSearchParams({ initialPrompt: normalizedPrompt })
  return `${route}?${params.toString()}`
}

export function extractDashboardLaunchRequest(
  searchParams: SearchParamsLike,
): DashboardLaunchRequest | null {
  const initialPrompt = normalizePrompt(searchParams.get('initialPrompt'))
  if (initialPrompt) {
    return {
      key: `initialPrompt:${initialPrompt}`,
      prompt: initialPrompt,
    }
  }

  const braindumpId = normalizePrompt(searchParams.get('braindump_id'))
  if (braindumpId) {
    return {
      key: `braindump:${braindumpId}`,
      prompt: `I want to continue working on my brain dump. The brain dump ID is ${braindumpId}. Please use the get_braindump_document tool to retrieve the exact document by ID, then help me continue validation and research based on its contents.`,
    }
  }

  const context = searchParams.get('context')
  const initiativeId = normalizePrompt(searchParams.get('initiativeId'))
  if (context === 'initiative' && initiativeId) {
    const safeTitle = normalizePrompt(searchParams.get('title')) ?? 'this initiative'
    const fromJourney = searchParams.get('fromJourney') === '1'
    const outcomesPrompt = normalizePrompt(searchParams.get('outcomesPrompt'))

    if (fromJourney) {
      let prompt = `I started this initiative from a User Journey: "${safeTitle}" (initiative ID: ${initiativeId}). Please call start_journey_workflow first. If requirements are missing, ask me only for the missing inputs, save them with update_initiative, then retry start_journey_workflow.`
      if (outcomesPrompt) {
        prompt += ` When asking for outcomes, you can use: "${outcomesPrompt}"`
      }

      return {
        key: `initiative-journey:${initiativeId}`,
        prompt,
      }
    }

    return {
      key: `initiative:${initiativeId}`,
      prompt: `I want to discuss this initiative with you: "${safeTitle}" (ID: ${initiativeId}). Please help me with next steps, phase progress, or any questions about it.`,
    }
  }

  return null
}

export function buildUrlWithoutDashboardLaunchParams(
  pathname: string,
  searchParams: SearchParamsLike,
  extraKeysToDelete: string[] = [],
): string {
  const nextParams = new URLSearchParams(searchParams.toString())
  for (const key of DASHBOARD_LAUNCH_PARAM_KEYS) {
    nextParams.delete(key)
  }
  for (const key of extraKeysToDelete) {
    nextParams.delete(key)
  }

  const nextQuery = nextParams.toString()
  return nextQuery ? `${pathname}?${nextQuery}` : pathname
}
