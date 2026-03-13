-- Migration: 20260312183000_phase2_database_alignment.sql
-- Description: Align skills/custom skills schema and add audit fields to content bundle tables.

-- -----------------------------------------------------------------------------
-- skills.agent_ids normalization
-- -----------------------------------------------------------------------------
DO $$
DECLARE
  agent_ids_type text;
BEGIN
  SELECT pg_catalog.format_type(a.atttypid, a.atttypmod)
  INTO agent_ids_type
  FROM pg_attribute a
  JOIN pg_class c ON a.attrelid = c.oid
  JOIN pg_namespace n ON c.relnamespace = n.oid
  WHERE n.nspname = 'public'
    AND c.relname = 'skills'
    AND a.attname = 'agent_ids'
    AND NOT a.attisdropped;

  IF agent_ids_type IS NULL THEN
    ALTER TABLE public.skills
      ADD COLUMN agent_ids JSONB DEFAULT '[]'::jsonb;
  ELSIF agent_ids_type = 'text[]' THEN
    ALTER TABLE public.skills
      ADD COLUMN agent_ids_jsonb JSONB DEFAULT '[]'::jsonb;

    UPDATE public.skills
    SET agent_ids_jsonb = COALESCE(to_jsonb(agent_ids), '[]'::jsonb);

    ALTER TABLE public.skills DROP COLUMN agent_ids;
    ALTER TABLE public.skills RENAME COLUMN agent_ids_jsonb TO agent_ids;
  ELSIF agent_ids_type = 'json' THEN
    ALTER TABLE public.skills
      ALTER COLUMN agent_ids TYPE JSONB USING COALESCE(agent_ids::jsonb, '[]'::jsonb);
  ELSIF agent_ids_type <> 'jsonb' THEN
    ALTER TABLE public.skills
      ADD COLUMN agent_ids_jsonb JSONB DEFAULT '[]'::jsonb;

    EXECUTE $sql$
      UPDATE public.skills
      SET agent_ids_jsonb = CASE
        WHEN agent_ids IS NULL THEN '[]'::jsonb
        ELSE to_jsonb(ARRAY[agent_ids::text])
      END
    $sql$;

    ALTER TABLE public.skills DROP COLUMN agent_ids;
    ALTER TABLE public.skills RENAME COLUMN agent_ids_jsonb TO agent_ids;
  END IF;
END $$;

UPDATE public.skills
SET agent_ids = '[]'::jsonb
WHERE agent_ids IS NULL;

ALTER TABLE public.skills
  ALTER COLUMN agent_ids SET DEFAULT '[]'::jsonb,
  ALTER COLUMN agent_ids SET NOT NULL;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'skills_agent_ids_is_array'
      AND conrelid = 'public.skills'::regclass
  ) THEN
    ALTER TABLE public.skills
      ADD CONSTRAINT skills_agent_ids_is_array
      CHECK (jsonb_typeof(agent_ids) = 'array');
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_skills_agent_ids ON public.skills USING GIN (agent_ids);

-- -----------------------------------------------------------------------------
-- custom_skills backing table for active runtime code
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.custom_skills (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT NOT NULL,
  category TEXT NOT NULL,
  agent_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
  knowledge TEXT,
  based_on_skill TEXT,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  is_active BOOLEAN NOT NULL DEFAULT true,
  created_by UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.custom_skills
  ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  ADD COLUMN IF NOT EXISTS name TEXT,
  ADD COLUMN IF NOT EXISTS description TEXT,
  ADD COLUMN IF NOT EXISTS category TEXT,
  ADD COLUMN IF NOT EXISTS knowledge TEXT,
  ADD COLUMN IF NOT EXISTS based_on_skill TEXT,
  ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT true,
  ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now(),
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now();

DO $$
DECLARE
  custom_agent_ids_type text;
BEGIN
  SELECT pg_catalog.format_type(a.atttypid, a.atttypmod)
  INTO custom_agent_ids_type
  FROM pg_attribute a
  JOIN pg_class c ON a.attrelid = c.oid
  JOIN pg_namespace n ON c.relnamespace = n.oid
  WHERE n.nspname = 'public'
    AND c.relname = 'custom_skills'
    AND a.attname = 'agent_ids'
    AND NOT a.attisdropped;

  IF custom_agent_ids_type IS NULL THEN
    ALTER TABLE public.custom_skills
      ADD COLUMN agent_ids JSONB DEFAULT '[]'::jsonb;
  ELSIF custom_agent_ids_type = 'text[]' THEN
    ALTER TABLE public.custom_skills
      ADD COLUMN agent_ids_jsonb JSONB DEFAULT '[]'::jsonb;

    UPDATE public.custom_skills
    SET agent_ids_jsonb = COALESCE(to_jsonb(agent_ids), '[]'::jsonb);

    ALTER TABLE public.custom_skills DROP COLUMN agent_ids;
    ALTER TABLE public.custom_skills RENAME COLUMN agent_ids_jsonb TO agent_ids;
  ELSIF custom_agent_ids_type = 'json' THEN
    ALTER TABLE public.custom_skills
      ALTER COLUMN agent_ids TYPE JSONB USING COALESCE(agent_ids::jsonb, '[]'::jsonb);
  ELSIF custom_agent_ids_type <> 'jsonb' THEN
    ALTER TABLE public.custom_skills
      ADD COLUMN agent_ids_jsonb JSONB DEFAULT '[]'::jsonb;

    EXECUTE $sql$
      UPDATE public.custom_skills
      SET agent_ids_jsonb = CASE
        WHEN agent_ids IS NULL THEN '[]'::jsonb
        ELSE to_jsonb(ARRAY[agent_ids::text])
      END
    $sql$;

    ALTER TABLE public.custom_skills DROP COLUMN agent_ids;
    ALTER TABLE public.custom_skills RENAME COLUMN agent_ids_jsonb TO agent_ids;
  END IF;
END $$;

UPDATE public.custom_skills
SET
  metadata = COALESCE(metadata, '{}'::jsonb),
  agent_ids = COALESCE(agent_ids, '[]'::jsonb),
  is_active = COALESCE(is_active, true),
  created_by = COALESCE(created_by, user_id)
WHERE metadata IS NULL
   OR agent_ids IS NULL
   OR is_active IS NULL
   OR created_by IS NULL;

ALTER TABLE public.custom_skills
  ALTER COLUMN user_id SET NOT NULL,
  ALTER COLUMN name SET NOT NULL,
  ALTER COLUMN description SET NOT NULL,
  ALTER COLUMN category SET NOT NULL,
  ALTER COLUMN metadata SET DEFAULT '{}'::jsonb,
  ALTER COLUMN metadata SET NOT NULL,
  ALTER COLUMN agent_ids SET DEFAULT '[]'::jsonb,
  ALTER COLUMN agent_ids SET NOT NULL,
  ALTER COLUMN is_active SET DEFAULT true,
  ALTER COLUMN is_active SET NOT NULL,
  ALTER COLUMN created_at SET DEFAULT now(),
  ALTER COLUMN created_at SET NOT NULL,
  ALTER COLUMN updated_at SET DEFAULT now(),
  ALTER COLUMN updated_at SET NOT NULL;

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'custom_skills'
      AND column_name = 'created_by'
  ) AND EXISTS (
    SELECT 1 FROM public.custom_skills WHERE created_by IS NULL
  ) THEN
    RAISE EXCEPTION 'custom_skills.created_by contains NULL values after backfill';
  END IF;
END $$;

ALTER TABLE public.custom_skills
  ALTER COLUMN created_by SET NOT NULL;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'custom_skills_user_name_key'
      AND conrelid = 'public.custom_skills'::regclass
  ) THEN
    ALTER TABLE public.custom_skills
      ADD CONSTRAINT custom_skills_user_name_key UNIQUE (user_id, name);
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'custom_skills_agent_ids_is_array'
      AND conrelid = 'public.custom_skills'::regclass
  ) THEN
    ALTER TABLE public.custom_skills
      ADD CONSTRAINT custom_skills_agent_ids_is_array
      CHECK (jsonb_typeof(agent_ids) = 'array');
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'custom_skills_metadata_is_object'
      AND conrelid = 'public.custom_skills'::regclass
  ) THEN
    ALTER TABLE public.custom_skills
      ADD CONSTRAINT custom_skills_metadata_is_object
      CHECK (jsonb_typeof(metadata) = 'object');
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_custom_skills_user_active_created
  ON public.custom_skills(user_id, is_active, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_custom_skills_category
  ON public.custom_skills(category);
CREATE INDEX IF NOT EXISTS idx_custom_skills_agent_ids
  ON public.custom_skills USING GIN (agent_ids);
CREATE INDEX IF NOT EXISTS idx_custom_skills_created_by
  ON public.custom_skills(created_by);

ALTER TABLE public.custom_skills ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can manage their own custom skills" ON public.custom_skills;
CREATE POLICY "Users can manage their own custom skills" ON public.custom_skills
  FOR ALL TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Service role has full access to custom_skills" ON public.custom_skills;
CREATE POLICY "Service role has full access to custom_skills" ON public.custom_skills
  FOR ALL TO service_role
  USING (true)
  WITH CHECK (true);

DROP TRIGGER IF EXISTS update_custom_skills_updated_at ON public.custom_skills;
CREATE TRIGGER update_custom_skills_updated_at
  BEFORE UPDATE ON public.custom_skills
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- -----------------------------------------------------------------------------
-- Audit-field alignment for content bundle tables already present in the chain
-- -----------------------------------------------------------------------------
ALTER TABLE public.content_bundles
  ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES auth.users(id) ON DELETE CASCADE;
UPDATE public.content_bundles SET created_by = user_id WHERE created_by IS NULL;
ALTER TABLE public.content_bundles ALTER COLUMN created_by SET NOT NULL;
CREATE INDEX IF NOT EXISTS idx_content_bundles_created_by ON public.content_bundles(created_by);
DROP TRIGGER IF EXISTS update_content_bundles_updated_at ON public.content_bundles;
CREATE TRIGGER update_content_bundles_updated_at
  BEFORE UPDATE ON public.content_bundles
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

ALTER TABLE public.content_bundle_deliverables
  ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES auth.users(id) ON DELETE CASCADE;
UPDATE public.content_bundle_deliverables SET created_by = user_id WHERE created_by IS NULL;
ALTER TABLE public.content_bundle_deliverables ALTER COLUMN created_by SET NOT NULL;
CREATE INDEX IF NOT EXISTS idx_content_bundle_deliverables_created_by ON public.content_bundle_deliverables(created_by);
DROP TRIGGER IF EXISTS update_content_bundle_deliverables_updated_at ON public.content_bundle_deliverables;
CREATE TRIGGER update_content_bundle_deliverables_updated_at
  BEFORE UPDATE ON public.content_bundle_deliverables
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

ALTER TABLE public.workspace_items
  ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES auth.users(id) ON DELETE CASCADE;
UPDATE public.workspace_items SET created_by = user_id WHERE created_by IS NULL;
ALTER TABLE public.workspace_items ALTER COLUMN created_by SET NOT NULL;
CREATE INDEX IF NOT EXISTS idx_workspace_items_created_by ON public.workspace_items(created_by);
DROP TRIGGER IF EXISTS update_workspace_items_updated_at ON public.workspace_items;
CREATE TRIGGER update_workspace_items_updated_at
  BEFORE UPDATE ON public.workspace_items
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
