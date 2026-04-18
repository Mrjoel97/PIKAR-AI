// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';
import { rateLimiters, getClientIp } from '@/lib/rate-limit';

type ChecklistItem = {
  id: string;
  completed?: boolean;
  [key: string]: unknown;
};

type SessionEventRow = {
  event_data?: Record<string, unknown> | null;
};

const CHECKLIST_ACTIVITY_PATTERNS: Record<string, string[]> = {
  revenue_strategy: ['revenue strategy', 'income opportunities', 'revenue model', 'pricing strategy'],
  brain_dump: ['brain dump', 'brainstorm session', 'brainstorming session'],
  weekly_plan: ['plan my week', 'weekly plan', '7-day action plan'],
  sales_pipeline: ['sales pipeline', 'track deals', 'manage my funnel'],
  content_piece: ['content piece', 'blog post', 'social update', 'content calendar'],
  growth_experiment: ['growth experiment', 'test a hypothesis', 'accelerate growth'],
  pitch_review: ['work on my pitch', 'value proposition', 'investors and customers'],
  burn_rate: ['burn rate', 'runway', 'financial health'],
  team_update: ['team update', 'weekly team update'],
  dept_health: ['department health check', 'each team is performing'],
  process_audit: ['audit our key business processes', 'find bottlenecks', 'process audit'],
  compliance_review: ['compliance review', 'regulatory requirements'],
  kpi_dashboard: ['kpi tracking', 'key metrics', 'reporting cadence'],
  stakeholder_briefing: ['stakeholder briefing', 'leadership team'],
  risk_assessment: ['risk assessment', 'prioritize risks'],
  portfolio_review: ['initiative portfolio', 'portfolio health', 'resources are allocated'],
  approval_workflow: ['approval workflow', 'governance controls'],
};

function extractUserEventText(eventData: Record<string, unknown> | null | undefined): string {
  if (!eventData) {
    return '';
  }

  const source = eventData.source;
  const author = eventData.author;
  const role = eventData.role;
  const isUserEvent =
    source === 'user' ||
    source === 'human' ||
    author === 'user' ||
    role === 'user';

  if (!isUserEvent) {
    return '';
  }

  const content = eventData.content;
  if (typeof content === 'string') {
    return content;
  }

  if (content && typeof content === 'object' && 'parts' in content) {
    const parts = (content as { parts?: Array<{ text?: unknown }> }).parts;
    if (Array.isArray(parts)) {
      return parts
        .map((part) => (typeof part?.text === 'string' ? part.text : ''))
        .join(' ')
        .trim();
    }
  }

  if (typeof eventData.text === 'string') {
    return eventData.text;
  }

  return '';
}

function matchesChecklistSignal(text: string, patterns: string[]): boolean {
  const normalized = text.toLowerCase();
  return patterns.some((pattern) => normalized.includes(pattern));
}

function deriveCompletedChecklistItems(args: {
  items: ChecklistItem[];
  sessionTexts: string[];
  workflowCount: number;
  vaultCategories: string[];
}): Set<string> {
  const completed = new Set<string>();

  if (args.workflowCount > 0) {
    completed.add('first_workflow');
  }

  if (args.vaultCategories.some((category) => category.includes('brain'))) {
    completed.add('brain_dump');
  }

  if (
    args.vaultCategories.some((category) =>
      ['content', 'marketing', 'social', 'image', 'video'].some((hint) => category.includes(hint)),
    )
  ) {
    completed.add('content_piece');
  }

  for (const item of args.items) {
    const patterns = CHECKLIST_ACTIVITY_PATTERNS[item.id];
    if (!patterns) {
      continue;
    }

    if (args.sessionTexts.some((text) => matchesChecklistSignal(text, patterns))) {
      completed.add(item.id);
    }
  }

  return completed;
}

function mergeChecklistCompletion(items: ChecklistItem[], completedIds: Set<string>) {
  let changed = false;
  const nextItems = items.map((item) => {
    const shouldBeCompleted = item.completed === true || completedIds.has(item.id);
    if (item.completed !== shouldBeCompleted) {
      changed = true;
      return { ...item, completed: shouldBeCompleted };
    }

    return item;
  });

  return { nextItems, changed };
}

/**
 * GET /api/onboarding-checklist
 * Returns the user's in-app onboarding checklist (items + dismissed status).
 */
export async function GET(request: NextRequest) {
  const rl = rateLimiters.authenticated.check(getClientIp(request));
  if (!rl.success) {
    return NextResponse.json(
      { error: 'Too many requests' },
      { status: 429, headers: { 'Retry-After': String(rl.retryAfter) } }
    );
  }

  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  if (!user) {
    return NextResponse.json({ error: 'Not authenticated' }, { status: 401 });
  }

  const { data, error } = await supabase
    .from('onboarding_checklist')
    .select('items, dismissed_at')
    .eq('user_id', user.id)
    .maybeSingle();

  if (error) {
    console.error('Checklist fetch error:', error);
    return NextResponse.json({ error: 'Failed to fetch checklist' }, { status: 500 });
  }

  if (!data) {
    return NextResponse.json({ error: 'No checklist found' }, { status: 404 });
  }

  const checklistItems = (data.items ?? []) as ChecklistItem[];

  const [sessionEventsResult, workflowExecutionsResult, vaultDocumentsResult] = await Promise.allSettled([
    supabase
      .from('session_events')
      .select('event_data')
      .eq('user_id', user.id)
      .eq('app_name', 'agents')
      .is('superseded_by', null)
      .order('created_at', { ascending: false })
      .limit(400),
    supabase
      .from('workflow_executions')
      .select('id', { count: 'exact', head: true })
      .eq('user_id', user.id),
    supabase
      .from('vault_documents')
      .select('category')
      .eq('user_id', user.id)
      .order('created_at', { ascending: false })
      .limit(100),
  ]);

  const sessionTexts =
    sessionEventsResult.status === 'fulfilled'
      ? ((sessionEventsResult.value.data ?? []) as SessionEventRow[])
          .map((row) => extractUserEventText(row.event_data))
          .filter((text): text is string => Boolean(text))
      : [];
  const workflowCount =
    workflowExecutionsResult.status === 'fulfilled'
      ? workflowExecutionsResult.value.count ?? 0
      : 0;
  const vaultCategories =
    vaultDocumentsResult.status === 'fulfilled'
      ? ((vaultDocumentsResult.value.data ?? []) as Array<{ category?: string | null }>)
          .map((row) => (row.category ?? '').toLowerCase())
          .filter(Boolean)
      : [];

  const autoCompletedIds = deriveCompletedChecklistItems({
    items: checklistItems,
    sessionTexts,
    workflowCount,
    vaultCategories,
  });
  const { nextItems, changed } = mergeChecklistCompletion(checklistItems, autoCompletedIds);

  if (changed) {
    const { error: updateError } = await supabase
      .from('onboarding_checklist')
      .update({ items: nextItems, updated_at: new Date().toISOString() })
      .eq('user_id', user.id);

    if (updateError) {
      console.error('Checklist reconcile error:', updateError);
    }
  }

  return NextResponse.json({
    items: nextItems,
    dismissed: !!data.dismissed_at,
  });
}

/**
 * PATCH /api/onboarding-checklist
 * Update checklist: complete an item or dismiss the whole checklist.
 *
 * Body options:
 *   { itemId: string, completed: boolean }  — mark item complete
 *   { dismiss: true }                       — dismiss the checklist
 */
export async function PATCH(request: NextRequest) {
  const rl = rateLimiters.authenticated.check(getClientIp(request));
  if (!rl.success) {
    return NextResponse.json(
      { error: 'Too many requests' },
      { status: 429, headers: { 'Retry-After': String(rl.retryAfter) } }
    );
  }

  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();

  if (!user) {
    return NextResponse.json({ error: 'Not authenticated' }, { status: 401 });
  }

  const body = await request.json() as {
    itemId?: string;
    completed?: boolean;
    dismiss?: boolean;
  };

  // Dismiss the entire checklist
  if (body.dismiss) {
    const { error } = await supabase
      .from('onboarding_checklist')
      .update({ dismissed_at: new Date().toISOString(), updated_at: new Date().toISOString() })
      .eq('user_id', user.id);

    if (error) {
      console.error('Checklist dismiss error:', error);
      return NextResponse.json({ error: 'Failed to dismiss' }, { status: 500 });
    }
    return NextResponse.json({ success: true });
  }

  // Complete a specific item
  if (body.itemId) {
    // Fetch current items
    const { data, error: fetchError } = await supabase
      .from('onboarding_checklist')
      .select('items')
      .eq('user_id', user.id)
      .single();

    if (fetchError || !data) {
      return NextResponse.json({ error: 'Checklist not found' }, { status: 404 });
    }

    const items = (data.items ?? []) as { id: string; completed: boolean }[];
    const updated = items.map(item =>
      item.id === body.itemId ? { ...item, completed: body.completed ?? true } : item
    );

    const { error: updateError } = await supabase
      .from('onboarding_checklist')
      .update({ items: updated, updated_at: new Date().toISOString() })
      .eq('user_id', user.id);

    if (updateError) {
      console.error('Checklist update error:', updateError);
      return NextResponse.json({ error: 'Failed to update' }, { status: 500 });
    }

    return NextResponse.json({ success: true, items: updated });
  }

  return NextResponse.json({ error: 'Invalid request body' }, { status: 400 });
}
