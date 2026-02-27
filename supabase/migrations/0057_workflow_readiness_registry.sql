-- Migration: 0057_workflow_readiness_registry.sql
-- Description: Add workflow readiness registry for start-time execution gating.

BEGIN;

CREATE TABLE IF NOT EXISTS public.workflow_readiness (
  template_id UUID PRIMARY KEY REFERENCES public.workflow_templates(id) ON DELETE CASCADE,
  template_name TEXT NOT NULL,
  template_version INTEGER,
  status TEXT NOT NULL DEFAULT 'ready'
    CHECK (status IN ('ready', 'blocked', 'needs_review', 'draft')),
  required_integrations JSONB NOT NULL DEFAULT '[]'::jsonb,
  requires_human_gate BOOLEAN NOT NULL DEFAULT false,
  readiness_owner TEXT,
  reason_codes JSONB NOT NULL DEFAULT '[]'::jsonb,
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_workflow_readiness_status
  ON public.workflow_readiness(status);

CREATE INDEX IF NOT EXISTS idx_workflow_readiness_template_name
  ON public.workflow_readiness(template_name);

ALTER TABLE public.workflow_readiness ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  CREATE POLICY "Service Role manages workflow_readiness"
    ON public.workflow_readiness
    USING (true)
    WITH CHECK (true);
EXCEPTION
  WHEN duplicate_object THEN NULL;
END $$;

CREATE OR REPLACE FUNCTION public._compute_requires_human_gate(phases_json JSONB)
RETURNS BOOLEAN
LANGUAGE sql
AS $$
  SELECT EXISTS (
    SELECT 1
    FROM jsonb_array_elements(COALESCE(phases_json, '[]'::jsonb)) AS p
    CROSS JOIN LATERAL jsonb_array_elements(COALESCE(p->'steps', '[]'::jsonb)) AS s
    WHERE COALESCE((s->>'required_approval')::boolean, false)
  );
$$;

CREATE OR REPLACE FUNCTION public.sync_workflow_readiness_from_template()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
  computed_status TEXT;
  computed_requires_human_gate BOOLEAN;
BEGIN
  computed_status := CASE
    WHEN NEW.lifecycle_status = 'archived' THEN 'blocked'
    WHEN NEW.lifecycle_status = 'draft' THEN 'draft'
    ELSE 'ready'
  END;

  computed_requires_human_gate := public._compute_requires_human_gate(NEW.phases);

  INSERT INTO public.workflow_readiness (
    template_id,
    template_name,
    template_version,
    status,
    requires_human_gate
  )
  VALUES (
    NEW.id,
    NEW.name,
    NEW.version,
    computed_status,
    computed_requires_human_gate
  )
  ON CONFLICT (template_id) DO UPDATE
  SET
    template_name = EXCLUDED.template_name,
    template_version = EXCLUDED.template_version,
    requires_human_gate = EXCLUDED.requires_human_gate,
    status = CASE
      WHEN NEW.lifecycle_status = 'archived' THEN 'blocked'
      WHEN NEW.lifecycle_status = 'draft' AND workflow_readiness.status = 'ready' THEN 'draft'
      ELSE workflow_readiness.status
    END,
    updated_at = now();

  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_sync_workflow_readiness_from_template
  ON public.workflow_templates;

CREATE TRIGGER trg_sync_workflow_readiness_from_template
AFTER INSERT OR UPDATE OF name, version, lifecycle_status, phases
ON public.workflow_templates
FOR EACH ROW
EXECUTE FUNCTION public.sync_workflow_readiness_from_template();

INSERT INTO public.workflow_readiness (
  template_id,
  template_name,
  template_version,
  status,
  requires_human_gate
)
SELECT
  wt.id,
  wt.name,
  wt.version,
  CASE
    WHEN wt.lifecycle_status = 'archived' THEN 'blocked'
    WHEN wt.lifecycle_status = 'draft' THEN 'draft'
    ELSE 'ready'
  END AS status,
  public._compute_requires_human_gate(wt.phases) AS requires_human_gate
FROM public.workflow_templates wt
ON CONFLICT (template_id) DO UPDATE
SET
  template_name = EXCLUDED.template_name,
  template_version = EXCLUDED.template_version,
  requires_human_gate = EXCLUDED.requires_human_gate,
  status = CASE
    WHEN EXCLUDED.status = 'blocked' THEN 'blocked'
    WHEN EXCLUDED.status = 'draft' AND workflow_readiness.status = 'ready' THEN 'draft'
    ELSE workflow_readiness.status
  END,
  updated_at = now();

COMMIT;

