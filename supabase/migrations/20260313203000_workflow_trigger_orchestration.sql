-- Migration: workflow trigger orchestration
-- Description: Adds durable workflow triggers and event logs for recurring/event-driven workflow execution.

CREATE TABLE IF NOT EXISTS public.workflow_triggers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    template_id UUID NOT NULL REFERENCES public.workflow_templates(id) ON DELETE CASCADE,
    trigger_name TEXT NOT NULL,
    trigger_type TEXT NOT NULL,
    schedule_frequency TEXT,
    event_name TEXT,
    context JSONB NOT NULL DEFAULT '{}'::jsonb,
    enabled BOOLEAN NOT NULL DEFAULT true,
    run_source TEXT NOT NULL DEFAULT 'agent_ui',
    next_run_at TIMESTAMPTZ,
    last_run_at TIMESTAMPTZ,
    last_event_at TIMESTAMPTZ,
    queue_mode TEXT NOT NULL DEFAULT 'followup',
    lane TEXT NOT NULL DEFAULT 'automation',
    persona TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.workflow_triggers
    ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS template_id UUID REFERENCES public.workflow_templates(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS trigger_name TEXT,
    ADD COLUMN IF NOT EXISTS trigger_type TEXT,
    ADD COLUMN IF NOT EXISTS schedule_frequency TEXT,
    ADD COLUMN IF NOT EXISTS event_name TEXT,
    ADD COLUMN IF NOT EXISTS context JSONB DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS enabled BOOLEAN DEFAULT true,
    ADD COLUMN IF NOT EXISTS run_source TEXT DEFAULT 'agent_ui',
    ADD COLUMN IF NOT EXISTS next_run_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS last_run_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS last_event_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS queue_mode TEXT DEFAULT 'followup',
    ADD COLUMN IF NOT EXISTS lane TEXT DEFAULT 'automation',
    ADD COLUMN IF NOT EXISTS persona TEXT,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now(),
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now();

UPDATE public.workflow_triggers
SET
    context = COALESCE(context, '{}'::jsonb),
    enabled = COALESCE(enabled, true),
    run_source = COALESCE(run_source, 'agent_ui'),
    queue_mode = COALESCE(queue_mode, 'followup'),
    lane = COALESCE(lane, 'automation'),
    created_at = COALESCE(created_at, now()),
    updated_at = COALESCE(updated_at, now())
WHERE context IS NULL
   OR enabled IS NULL
   OR run_source IS NULL
   OR queue_mode IS NULL
   OR lane IS NULL
   OR created_at IS NULL
   OR updated_at IS NULL;

ALTER TABLE public.workflow_triggers
    ALTER COLUMN user_id SET NOT NULL,
    ALTER COLUMN template_id SET NOT NULL,
    ALTER COLUMN trigger_name SET NOT NULL,
    ALTER COLUMN trigger_type SET NOT NULL,
    ALTER COLUMN context SET DEFAULT '{}'::jsonb,
    ALTER COLUMN context SET NOT NULL,
    ALTER COLUMN enabled SET DEFAULT true,
    ALTER COLUMN enabled SET NOT NULL,
    ALTER COLUMN run_source SET DEFAULT 'agent_ui',
    ALTER COLUMN run_source SET NOT NULL,
    ALTER COLUMN queue_mode SET DEFAULT 'followup',
    ALTER COLUMN queue_mode SET NOT NULL,
    ALTER COLUMN lane SET DEFAULT 'automation',
    ALTER COLUMN lane SET NOT NULL,
    ALTER COLUMN created_at SET DEFAULT now(),
    ALTER COLUMN created_at SET NOT NULL,
    ALTER COLUMN updated_at SET DEFAULT now(),
    ALTER COLUMN updated_at SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'workflow_triggers_trigger_type_check'
          AND conrelid = 'public.workflow_triggers'::regclass
    ) THEN
        ALTER TABLE public.workflow_triggers
            ADD CONSTRAINT workflow_triggers_trigger_type_check
            CHECK (trigger_type IN ('schedule', 'event'));
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'workflow_triggers_schedule_frequency_check'
          AND conrelid = 'public.workflow_triggers'::regclass
    ) THEN
        ALTER TABLE public.workflow_triggers
            ADD CONSTRAINT workflow_triggers_schedule_frequency_check
            CHECK (
                schedule_frequency IS NULL
                OR schedule_frequency IN ('hourly', 'daily', 'weekly', 'monthly', 'quarterly', 'yearly')
            );
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'workflow_triggers_shape_check'
          AND conrelid = 'public.workflow_triggers'::regclass
    ) THEN
        ALTER TABLE public.workflow_triggers
            ADD CONSTRAINT workflow_triggers_shape_check
            CHECK (
                (trigger_type = 'schedule' AND schedule_frequency IS NOT NULL AND event_name IS NULL)
                OR (trigger_type = 'event' AND event_name IS NOT NULL AND schedule_frequency IS NULL)
            );
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_workflow_triggers_user_id
    ON public.workflow_triggers(user_id);
CREATE INDEX IF NOT EXISTS idx_workflow_triggers_template_id
    ON public.workflow_triggers(template_id);
CREATE INDEX IF NOT EXISTS idx_workflow_triggers_event_name
    ON public.workflow_triggers(event_name)
    WHERE trigger_type = 'event' AND enabled = true;
CREATE INDEX IF NOT EXISTS idx_workflow_triggers_next_run
    ON public.workflow_triggers(next_run_at)
    WHERE trigger_type = 'schedule' AND enabled = true;

ALTER TABLE public.workflow_triggers ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view their own workflow triggers" ON public.workflow_triggers;
CREATE POLICY "Users can view their own workflow triggers"
    ON public.workflow_triggers
    FOR SELECT TO authenticated
    USING (user_id = auth.uid());

DROP POLICY IF EXISTS "Users can insert their own workflow triggers" ON public.workflow_triggers;
CREATE POLICY "Users can insert their own workflow triggers"
    ON public.workflow_triggers
    FOR INSERT TO authenticated
    WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "Users can update their own workflow triggers" ON public.workflow_triggers;
CREATE POLICY "Users can update their own workflow triggers"
    ON public.workflow_triggers
    FOR UPDATE TO authenticated
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "Users can delete their own workflow triggers" ON public.workflow_triggers;
CREATE POLICY "Users can delete their own workflow triggers"
    ON public.workflow_triggers
    FOR DELETE TO authenticated
    USING (user_id = auth.uid());

DROP POLICY IF EXISTS "Service role manages workflow triggers" ON public.workflow_triggers;
CREATE POLICY "Service role manages workflow triggers"
    ON public.workflow_triggers
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);

DROP TRIGGER IF EXISTS update_workflow_triggers_updated_at ON public.workflow_triggers;
CREATE TRIGGER update_workflow_triggers_updated_at
    BEFORE UPDATE ON public.workflow_triggers
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TABLE IF NOT EXISTS public.workflow_trigger_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    event_name TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    source TEXT NOT NULL DEFAULT 'system',
    handled_trigger_count INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'queued',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.workflow_trigger_events
    ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    ADD COLUMN IF NOT EXISTS event_name TEXT,
    ADD COLUMN IF NOT EXISTS payload JSONB DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'system',
    ADD COLUMN IF NOT EXISTS handled_trigger_count INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'queued',
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now();

UPDATE public.workflow_trigger_events
SET
    payload = COALESCE(payload, '{}'::jsonb),
    source = COALESCE(source, 'system'),
    handled_trigger_count = COALESCE(handled_trigger_count, 0),
    status = COALESCE(status, 'queued'),
    created_at = COALESCE(created_at, now())
WHERE payload IS NULL
   OR source IS NULL
   OR handled_trigger_count IS NULL
   OR status IS NULL
   OR created_at IS NULL;

ALTER TABLE public.workflow_trigger_events
    ALTER COLUMN user_id SET NOT NULL,
    ALTER COLUMN event_name SET NOT NULL,
    ALTER COLUMN payload SET DEFAULT '{}'::jsonb,
    ALTER COLUMN payload SET NOT NULL,
    ALTER COLUMN source SET DEFAULT 'system',
    ALTER COLUMN source SET NOT NULL,
    ALTER COLUMN handled_trigger_count SET DEFAULT 0,
    ALTER COLUMN handled_trigger_count SET NOT NULL,
    ALTER COLUMN status SET DEFAULT 'queued',
    ALTER COLUMN status SET NOT NULL,
    ALTER COLUMN created_at SET DEFAULT now(),
    ALTER COLUMN created_at SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_workflow_trigger_events_user_id
    ON public.workflow_trigger_events(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_workflow_trigger_events_event_name
    ON public.workflow_trigger_events(event_name, created_at DESC);

ALTER TABLE public.workflow_trigger_events ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view their own workflow trigger events" ON public.workflow_trigger_events;
CREATE POLICY "Users can view their own workflow trigger events"
    ON public.workflow_trigger_events
    FOR SELECT TO authenticated
    USING (user_id = auth.uid());

DROP POLICY IF EXISTS "Service role manages workflow trigger events" ON public.workflow_trigger_events;
CREATE POLICY "Service role manages workflow trigger events"
    ON public.workflow_trigger_events
    FOR ALL TO service_role
    USING (true)
    WITH CHECK (true);
