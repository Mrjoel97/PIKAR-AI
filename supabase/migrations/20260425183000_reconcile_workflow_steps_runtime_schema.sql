-- Reconcile workflow_steps schema with the runtime expectations used by
-- execute-workflow and workflow status/history readers.

ALTER TABLE public.workflow_steps
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now(),
    ADD COLUMN IF NOT EXISTS phase_key TEXT;

UPDATE public.workflow_steps
SET
    created_at = COALESCE(created_at, started_at, completed_at, now()),
    phase_key = COALESCE(
        NULLIF(phase_key, ''),
        NULLIF(regexp_replace(lower(COALESCE(phase_name, '')), '\s+', '_', 'g'), '')
    )
WHERE created_at IS NULL
   OR phase_key IS NULL
   OR phase_key = '';

ALTER TABLE public.workflow_steps
    ALTER COLUMN created_at SET DEFAULT now();

CREATE INDEX IF NOT EXISTS idx_workflow_steps_execution_created_at
    ON public.workflow_steps (execution_id, created_at DESC);
