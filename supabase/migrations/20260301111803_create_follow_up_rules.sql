-- ============================================================
-- Automated Follow-Up System: rules + execution log
-- Run this migration in Supabase SQL Editor
-- ============================================================

CREATE TABLE public.follow_up_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    -- Rule definition
    name TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,

    -- Trigger
    trigger_event TEXT NOT NULL,  -- 'form_submission', 'new_contact', 'stage_change', 'payment_received'
    trigger_filter JSONB DEFAULT '{}',  -- e.g. {"form_id": "xyz"} or {"new_stage": "qualified"}

    -- Action
    action_type TEXT NOT NULL,  -- 'send_email', 'create_task', 'update_stage', 'send_notification', 'score_lead'
    action_config JSONB NOT NULL DEFAULT '{}',
    -- For send_email: {"subject": "...", "body_template": "...", "to_field": "email"}
    -- For create_task: {"description": "Follow up with {{name}}", "priority": "high", "assignee": "sales"}
    -- For update_stage: {"new_stage": "qualified"}
    -- For send_notification: {"message": "New lead: {{name}}"}
    -- For score_lead: {"add_points": 10}

    -- Timing
    delay_minutes INT NOT NULL DEFAULT 0,  -- 0 = immediate, 60 = 1 hour, 1440 = 1 day

    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_follow_up_rules_user ON public.follow_up_rules(user_id);
CREATE INDEX idx_follow_up_rules_trigger ON public.follow_up_rules(user_id, trigger_event, is_active);

ALTER TABLE public.follow_up_rules ENABLE ROW LEVEL SECURITY;

CREATE POLICY follow_up_rules_select ON public.follow_up_rules
    FOR SELECT TO authenticated USING (user_id = (SELECT auth.uid()));
CREATE POLICY follow_up_rules_insert ON public.follow_up_rules
    FOR INSERT TO authenticated WITH CHECK (user_id = (SELECT auth.uid()));
CREATE POLICY follow_up_rules_update ON public.follow_up_rules
    FOR UPDATE TO authenticated
    USING (user_id = (SELECT auth.uid())) WITH CHECK (user_id = (SELECT auth.uid()));
CREATE POLICY follow_up_rules_delete ON public.follow_up_rules
    FOR DELETE TO authenticated USING (user_id = (SELECT auth.uid()));

-- Execution log: tracks every fired follow-up action
CREATE TABLE public.follow_up_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_id UUID NOT NULL REFERENCES public.follow_up_rules(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    trigger_data JSONB DEFAULT '{}',   -- snapshot of the event payload
    action_result JSONB DEFAULT '{}',  -- result of the action
    status TEXT NOT NULL DEFAULT 'pending',  -- pending, executed, failed
    error_message TEXT,

    scheduled_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    executed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_follow_up_exec_rule ON public.follow_up_executions(rule_id, created_at DESC);
CREATE INDEX idx_follow_up_exec_user ON public.follow_up_executions(user_id, status);

ALTER TABLE public.follow_up_executions ENABLE ROW LEVEL SECURITY;

CREATE POLICY follow_up_exec_select ON public.follow_up_executions
    FOR SELECT TO authenticated USING (user_id = (SELECT auth.uid()));
CREATE POLICY follow_up_exec_insert ON public.follow_up_executions
    FOR INSERT TO authenticated WITH CHECK (user_id = (SELECT auth.uid()));

-- Auto-update trigger
CREATE OR REPLACE FUNCTION public.update_follow_up_rules_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END; $$;

CREATE TRIGGER trg_follow_up_rules_updated_at
    BEFORE UPDATE ON public.follow_up_rules
    FOR EACH ROW EXECUTE FUNCTION public.update_follow_up_rules_updated_at();
