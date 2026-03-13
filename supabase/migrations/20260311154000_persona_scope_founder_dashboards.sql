ALTER TABLE public.user_workflows
  ADD COLUMN IF NOT EXISTS persona_scope TEXT NOT NULL DEFAULT 'all';

UPDATE public.user_workflows
SET persona_scope = 'all'
WHERE persona_scope IS NULL OR btrim(persona_scope) = '';

ALTER TABLE public.user_workflows
  DROP CONSTRAINT IF EXISTS user_workflows_persona_scope_check;

ALTER TABLE public.user_workflows
  ADD CONSTRAINT user_workflows_persona_scope_check
  CHECK (persona_scope IN ('all', 'solopreneur', 'startup', 'sme', 'enterprise'));

ALTER TABLE public.user_workflows
  DROP CONSTRAINT IF EXISTS user_workflows_user_id_workflow_name_key;

ALTER TABLE public.user_workflows
  ADD CONSTRAINT user_workflows_user_id_workflow_name_persona_scope_key
  UNIQUE (user_id, workflow_name, persona_scope);

CREATE INDEX IF NOT EXISTS idx_user_workflows_user_persona_usage
  ON public.user_workflows(user_id, persona_scope, usage_count DESC);

UPDATE public.workflow_templates
SET personas_allowed = '["solopreneur", "startup"]'::jsonb
WHERE COALESCE(personas_allowed, '[]'::jsonb) = '[]'::jsonb
  AND name IN ('Idea-to-Venture', 'Landing Page to Launch');

UPDATE public.workflow_templates
SET personas_allowed = '["solopreneur", "startup", "sme"]'::jsonb
WHERE COALESCE(personas_allowed, '[]'::jsonb) = '[]'::jsonb
  AND name IN (
    'Lead Generation Workflow',
    'Content Creation Workflow',
    'Social Media Campaign Workflow',
    'Email Sequence Workflow'
  );

UPDATE public.workflow_templates
SET personas_allowed = '["startup", "sme"]'::jsonb
WHERE COALESCE(personas_allowed, '[]'::jsonb) = '[]'::jsonb
  AND name IN (
    'A/B Testing Workflow',
    'Product Launch Workflow',
    'Competitor Analysis Workflow'
  );

UPDATE public.workflow_templates
SET personas_allowed = '["all"]'::jsonb
WHERE COALESCE(personas_allowed, '[]'::jsonb) = '[]'::jsonb
  AND name = 'Initiative Framework';
