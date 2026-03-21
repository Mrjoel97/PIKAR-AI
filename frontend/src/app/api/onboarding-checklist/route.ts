import { NextRequest, NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';

/**
 * GET /api/onboarding-checklist
 * Returns the user's in-app onboarding checklist (items + dismissed status).
 */
export async function GET() {
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

  return NextResponse.json({
    items: data.items ?? [],
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
