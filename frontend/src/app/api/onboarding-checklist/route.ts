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

const DEFAULT_CHECKLIST_ITEMS: Record<string, ChecklistItem[]> = {
  solopreneur: [
    { id: 'revenue_strategy', icon: '💰', title: 'Map your revenue strategy', description: 'Identify your best income opportunities', completed: false },
    { id: 'brain_dump', icon: '🧠', title: 'Do a brain dump', description: 'Get all your ideas organized', completed: false },
    { id: 'weekly_plan', icon: '📋', title: 'Plan your week', description: 'Create a focused 7-day action plan', completed: false },
    { id: 'first_workflow', icon: '⚡', title: 'Run your first workflow', description: 'Automate a repetitive task', completed: false },
    { id: 'content_piece', icon: '✍️', title: 'Create your first content piece', description: 'Generate a blog post or social update', completed: false },
  ],
  startup: [
    { id: 'growth_experiment', icon: '🚀', title: 'Design a growth experiment', description: 'Test a hypothesis to accelerate growth', completed: false },
    { id: 'pitch_review', icon: '🎯', title: 'Review your pitch', description: 'Sharpen your value proposition', completed: false },
    { id: 'burn_rate', icon: '📊', title: 'Check your burn rate', description: 'Understand your runway', completed: false },
    { id: 'team_update', icon: '👥', title: 'Write a team update', description: 'Align your team on priorities', completed: false },
    { id: 'first_workflow', icon: '⚡', title: 'Run your first workflow', description: 'Automate a repeatable process', completed: false },
  ],
  sme: [
    { id: 'dept_health', icon: '🏥', title: 'Run a department health check', description: 'See how each team is performing', completed: false },
    { id: 'process_audit', icon: '⚙️', title: 'Audit your processes', description: 'Find bottlenecks and optimize', completed: false },
    { id: 'compliance_review', icon: '🛡️', title: 'Run a compliance review', description: 'Ensure nothing falls through cracks', completed: false },
    { id: 'kpi_dashboard', icon: '📊', title: 'Set up KPI tracking', description: 'Define and monitor key metrics', completed: false },
    { id: 'first_workflow', icon: '⚡', title: 'Run your first workflow', description: 'Automate a department process', completed: false },
  ],
  enterprise: [
    { id: 'stakeholder_briefing', icon: '📋', title: 'Prepare a stakeholder briefing', description: 'Strategic update for leadership', completed: false },
    { id: 'risk_assessment', icon: '⚠️', title: 'Run a risk assessment', description: 'Identify and prioritize risks', completed: false },
    { id: 'portfolio_review', icon: '📈', title: 'Review initiative portfolio', description: 'Evaluate portfolio health', completed: false },
    { id: 'approval_workflow', icon: '✅', title: 'Set up an approval workflow', description: 'Configure governance controls', completed: false },
    { id: 'first_workflow', icon: '⚡', title: 'Run your first workflow', description: 'Automate an enterprise process', completed: false },
  ],
};

function getDefaultChecklistItems(persona: string | null | undefined): ChecklistItem[] {
  const resolvedPersona = typeof persona === 'string' ? persona.toLowerCase() : '';
  const template = DEFAULT_CHECKLIST_ITEMS[resolvedPersona] ?? DEFAULT_CHECKLIST_ITEMS.startup;
  return template.map((item) => ({ ...item }));
}

function hasStrongVaultSignal(vaultCategories: string[], keywords: string[]): boolean {
  return vaultCategories.some((category) =>
    keywords.some((keyword) => category.includes(keyword)),
  );
}

function deriveCompletedChecklistItems(args: {
  workflowCount: number;
  vaultCategories: string[];
}): Set<string> {
  const completed = new Set<string>();

  if (args.workflowCount > 0) {
    completed.add('first_workflow');
  }

  if (hasStrongVaultSignal(args.vaultCategories, ['brain dump', 'brainstorm', 'validation plan'])) {
    completed.add('brain_dump');
  }

  if (hasStrongVaultSignal(args.vaultCategories, ['content piece', 'generated content', 'content asset'])) {
    completed.add('content_piece');
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
    const { data: profileData, error: profileError } = await supabase
      .from('users_profile')
      .select('persona')
      .eq('user_id', user.id)
      .maybeSingle();

    if (profileError) {
      console.error('Checklist persona fetch error:', profileError);
      return NextResponse.json({ error: 'Failed to fetch checklist persona' }, { status: 500 });
    }

    const seededItems = getDefaultChecklistItems(profileData?.persona);
    const seededPersona =
      typeof profileData?.persona === 'string' && profileData.persona.trim()
        ? profileData.persona.trim().toLowerCase()
        : 'startup';

    const { error: insertError } = await supabase
      .from('onboarding_checklist')
      .upsert({
        user_id: user.id,
        persona: seededPersona,
        items: seededItems,
        updated_at: new Date().toISOString(),
      }, {
        onConflict: 'user_id',
        ignoreDuplicates: true,
      });

    if (insertError) {
      console.error('Checklist bootstrap error:', insertError);
    }

    return NextResponse.json({
      items: seededItems,
      dismissed: false,
    });
  }

  const checklistItems = (data.items ?? []) as ChecklistItem[];

  const [workflowExecutionsResult, vaultDocumentsResult] = await Promise.allSettled([
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
