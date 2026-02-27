-- Migration: 0056_initiative_checklists.sql
-- Description: Persisted initiative checklist items with audit trail.

CREATE TABLE IF NOT EXISTS initiative_checklist_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  initiative_id UUID NOT NULL REFERENCES initiatives(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id),
  phase TEXT NOT NULL CHECK (phase IN ('ideation', 'validation', 'prototype', 'build', 'scale')),
  title TEXT NOT NULL,
  description TEXT,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'blocked', 'skipped')),
  owner_user_id UUID REFERENCES auth.users(id),
  owner_label TEXT,
  due_at TIMESTAMPTZ,
  evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
  sort_order INTEGER NOT NULL DEFAULT 0,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  is_deleted BOOLEAN NOT NULL DEFAULT false,
  deleted_at TIMESTAMPTZ,
  created_by UUID,
  updated_by UUID,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_initiative_checklist_items_initiative
  ON initiative_checklist_items(initiative_id, phase, is_deleted);
CREATE INDEX IF NOT EXISTS idx_initiative_checklist_items_user
  ON initiative_checklist_items(user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_initiative_checklist_items_status
  ON initiative_checklist_items(status);
CREATE INDEX IF NOT EXISTS idx_initiative_checklist_items_due_at
  ON initiative_checklist_items(due_at);

CREATE OR REPLACE FUNCTION update_initiative_checklist_items_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_initiative_checklist_items_updated_at ON initiative_checklist_items;
CREATE TRIGGER trigger_initiative_checklist_items_updated_at
  BEFORE UPDATE ON initiative_checklist_items
  FOR EACH ROW
  EXECUTE FUNCTION update_initiative_checklist_items_updated_at();

ALTER TABLE initiative_checklist_items ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can CRUD their own initiative checklist items" ON initiative_checklist_items;
CREATE POLICY "Users can CRUD their own initiative checklist items"
  ON initiative_checklist_items
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE TABLE IF NOT EXISTS initiative_checklist_item_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  item_id UUID REFERENCES initiative_checklist_items(id) ON DELETE CASCADE,
  initiative_id UUID NOT NULL REFERENCES initiatives(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id),
  event_type TEXT NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  actor_user_id UUID,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_initiative_checklist_events_item
  ON initiative_checklist_item_events(item_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_initiative_checklist_events_initiative
  ON initiative_checklist_item_events(initiative_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_initiative_checklist_events_user
  ON initiative_checklist_item_events(user_id, created_at DESC);

ALTER TABLE initiative_checklist_item_events ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can read their own initiative checklist events" ON initiative_checklist_item_events;
CREATE POLICY "Users can read their own initiative checklist events"
  ON initiative_checklist_item_events
  FOR SELECT
  USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert their own initiative checklist events" ON initiative_checklist_item_events;
CREATE POLICY "Users can insert their own initiative checklist events"
  ON initiative_checklist_item_events
  FOR INSERT
  WITH CHECK (auth.uid() = user_id);
