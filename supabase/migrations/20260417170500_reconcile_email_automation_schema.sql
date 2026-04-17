-- Reconcile the live email automation schema before Cloudflare-native
-- /email-sequences migration work continues.
--
-- The live production project is missing the canonical CRM/email automation
-- tables from 20260404800000_crm_email_automation.sql. This migration
-- re-applies that schema in a drift-tolerant way and also widens the
-- email_tracking_events event_type constraint to accept the values the
-- current backend service actually writes (`bounced`, `unsubscribed`).

ALTER TABLE public.contacts
    ADD COLUMN IF NOT EXISTS hubspot_contact_id TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_contacts_hubspot_id
    ON public.contacts (user_id, hubspot_contact_id)
    WHERE hubspot_contact_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS public.hubspot_deals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users ON DELETE CASCADE,
    hubspot_deal_id TEXT NOT NULL,
    deal_name TEXT NOT NULL,
    pipeline TEXT,
    stage TEXT,
    amount NUMERIC(14,2),
    close_date DATE,
    associated_contacts UUID[] DEFAULT '{}',
    properties JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, hubspot_deal_id)
);

ALTER TABLE public.hubspot_deals ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'hubspot_deals'
          AND policyname = 'hubspot_deals_select_own'
    ) THEN
        CREATE POLICY "hubspot_deals_select_own"
            ON public.hubspot_deals FOR SELECT
            USING (auth.uid() = user_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'hubspot_deals'
          AND policyname = 'hubspot_deals_insert_own'
    ) THEN
        CREATE POLICY "hubspot_deals_insert_own"
            ON public.hubspot_deals FOR INSERT
            WITH CHECK (auth.uid() = user_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'hubspot_deals'
          AND policyname = 'hubspot_deals_update_own'
    ) THEN
        CREATE POLICY "hubspot_deals_update_own"
            ON public.hubspot_deals FOR UPDATE
            USING (auth.uid() = user_id)
            WITH CHECK (auth.uid() = user_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'hubspot_deals'
          AND policyname = 'hubspot_deals_delete_own'
    ) THEN
        CREATE POLICY "hubspot_deals_delete_own"
            ON public.hubspot_deals FOR DELETE
            USING (auth.uid() = user_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'hubspot_deals'
          AND policyname = 'hubspot_deals_service_role'
    ) THEN
        CREATE POLICY "hubspot_deals_service_role"
            ON public.hubspot_deals FOR ALL
            USING (auth.role() = 'service_role')
            WITH CHECK (auth.role() = 'service_role');
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS idx_hubspot_deals_user
    ON public.hubspot_deals (user_id);

CREATE INDEX IF NOT EXISTS idx_hubspot_deals_pipeline_stage
    ON public.hubspot_deals (user_id, pipeline, stage);

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_proc
        WHERE proname = 'update_updated_at_column'
    ) AND NOT EXISTS (
        SELECT 1
        FROM pg_trigger
        WHERE tgname = 'set_hubspot_deals_updated_at'
    ) THEN
        CREATE TRIGGER set_hubspot_deals_updated_at
            BEFORE UPDATE ON public.hubspot_deals
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END
$$;

CREATE TABLE IF NOT EXISTS public.email_sequences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users ON DELETE CASCADE,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'active', 'paused', 'completed')),
    campaign_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.email_sequences ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'email_sequences'
          AND policyname = 'email_sequences_select_own'
    ) THEN
        CREATE POLICY "email_sequences_select_own"
            ON public.email_sequences FOR SELECT
            USING (auth.uid() = user_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'email_sequences'
          AND policyname = 'email_sequences_insert_own'
    ) THEN
        CREATE POLICY "email_sequences_insert_own"
            ON public.email_sequences FOR INSERT
            WITH CHECK (auth.uid() = user_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'email_sequences'
          AND policyname = 'email_sequences_update_own'
    ) THEN
        CREATE POLICY "email_sequences_update_own"
            ON public.email_sequences FOR UPDATE
            USING (auth.uid() = user_id)
            WITH CHECK (auth.uid() = user_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'email_sequences'
          AND policyname = 'email_sequences_delete_own'
    ) THEN
        CREATE POLICY "email_sequences_delete_own"
            ON public.email_sequences FOR DELETE
            USING (auth.uid() = user_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'email_sequences'
          AND policyname = 'email_sequences_service_role'
    ) THEN
        CREATE POLICY "email_sequences_service_role"
            ON public.email_sequences FOR ALL
            USING (auth.role() = 'service_role')
            WITH CHECK (auth.role() = 'service_role');
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS idx_email_sequences_user
    ON public.email_sequences (user_id);

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_proc
        WHERE proname = 'update_updated_at_column'
    ) AND NOT EXISTS (
        SELECT 1
        FROM pg_trigger
        WHERE tgname = 'set_email_sequences_updated_at'
    ) THEN
        CREATE TRIGGER set_email_sequences_updated_at
            BEFORE UPDATE ON public.email_sequences
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END
$$;

CREATE TABLE IF NOT EXISTS public.email_sequence_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sequence_id UUID NOT NULL REFERENCES public.email_sequences ON DELETE CASCADE,
    step_number INT NOT NULL,
    subject_template TEXT NOT NULL,
    body_template TEXT NOT NULL,
    delay_hours INT NOT NULL DEFAULT 24,
    delay_type TEXT NOT NULL DEFAULT 'after_previous'
        CHECK (delay_type IN ('after_previous', 'at_time')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE (sequence_id, step_number)
);

ALTER TABLE public.email_sequence_steps
    ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE public.email_sequence_steps ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'email_sequence_steps'
          AND policyname = 'email_sequence_steps_select_own'
    ) THEN
        CREATE POLICY "email_sequence_steps_select_own"
            ON public.email_sequence_steps FOR SELECT
            USING (EXISTS (
                SELECT 1
                FROM public.email_sequences s
                WHERE s.id = email_sequence_steps.sequence_id
                  AND s.user_id = auth.uid()
            ));
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'email_sequence_steps'
          AND policyname = 'email_sequence_steps_insert_own'
    ) THEN
        CREATE POLICY "email_sequence_steps_insert_own"
            ON public.email_sequence_steps FOR INSERT
            WITH CHECK (EXISTS (
                SELECT 1
                FROM public.email_sequences s
                WHERE s.id = email_sequence_steps.sequence_id
                  AND s.user_id = auth.uid()
            ));
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'email_sequence_steps'
          AND policyname = 'email_sequence_steps_update_own'
    ) THEN
        CREATE POLICY "email_sequence_steps_update_own"
            ON public.email_sequence_steps FOR UPDATE
            USING (EXISTS (
                SELECT 1
                FROM public.email_sequences s
                WHERE s.id = email_sequence_steps.sequence_id
                  AND s.user_id = auth.uid()
            ))
            WITH CHECK (EXISTS (
                SELECT 1
                FROM public.email_sequences s
                WHERE s.id = email_sequence_steps.sequence_id
                  AND s.user_id = auth.uid()
            ));
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'email_sequence_steps'
          AND policyname = 'email_sequence_steps_delete_own'
    ) THEN
        CREATE POLICY "email_sequence_steps_delete_own"
            ON public.email_sequence_steps FOR DELETE
            USING (EXISTS (
                SELECT 1
                FROM public.email_sequences s
                WHERE s.id = email_sequence_steps.sequence_id
                  AND s.user_id = auth.uid()
            ));
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'email_sequence_steps'
          AND policyname = 'email_sequence_steps_service_role'
    ) THEN
        CREATE POLICY "email_sequence_steps_service_role"
            ON public.email_sequence_steps FOR ALL
            USING (auth.role() = 'service_role')
            WITH CHECK (auth.role() = 'service_role');
    END IF;
END
$$;

CREATE TABLE IF NOT EXISTS public.email_sequence_enrollments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sequence_id UUID NOT NULL REFERENCES public.email_sequences ON DELETE CASCADE,
    contact_id UUID NOT NULL REFERENCES public.contacts ON DELETE CASCADE,
    current_step INT NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'completed', 'bounced', 'unsubscribed', 'paused')),
    enrolled_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    next_send_at TIMESTAMPTZ,
    timezone TEXT DEFAULT 'UTC',
    UNIQUE (sequence_id, contact_id)
);

ALTER TABLE public.email_sequence_enrollments ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'email_sequence_enrollments'
          AND policyname = 'email_sequence_enrollments_select_own'
    ) THEN
        CREATE POLICY "email_sequence_enrollments_select_own"
            ON public.email_sequence_enrollments FOR SELECT
            USING (EXISTS (
                SELECT 1
                FROM public.email_sequences s
                WHERE s.id = email_sequence_enrollments.sequence_id
                  AND s.user_id = auth.uid()
            ));
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'email_sequence_enrollments'
          AND policyname = 'email_sequence_enrollments_insert_own'
    ) THEN
        CREATE POLICY "email_sequence_enrollments_insert_own"
            ON public.email_sequence_enrollments FOR INSERT
            WITH CHECK (EXISTS (
                SELECT 1
                FROM public.email_sequences s
                WHERE s.id = email_sequence_enrollments.sequence_id
                  AND s.user_id = auth.uid()
            ));
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'email_sequence_enrollments'
          AND policyname = 'email_sequence_enrollments_update_own'
    ) THEN
        CREATE POLICY "email_sequence_enrollments_update_own"
            ON public.email_sequence_enrollments FOR UPDATE
            USING (EXISTS (
                SELECT 1
                FROM public.email_sequences s
                WHERE s.id = email_sequence_enrollments.sequence_id
                  AND s.user_id = auth.uid()
            ))
            WITH CHECK (EXISTS (
                SELECT 1
                FROM public.email_sequences s
                WHERE s.id = email_sequence_enrollments.sequence_id
                  AND s.user_id = auth.uid()
            ));
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'email_sequence_enrollments'
          AND policyname = 'email_sequence_enrollments_delete_own'
    ) THEN
        CREATE POLICY "email_sequence_enrollments_delete_own"
            ON public.email_sequence_enrollments FOR DELETE
            USING (EXISTS (
                SELECT 1
                FROM public.email_sequences s
                WHERE s.id = email_sequence_enrollments.sequence_id
                  AND s.user_id = auth.uid()
            ));
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'email_sequence_enrollments'
          AND policyname = 'email_sequence_enrollments_service_role'
    ) THEN
        CREATE POLICY "email_sequence_enrollments_service_role"
            ON public.email_sequence_enrollments FOR ALL
            USING (auth.role() = 'service_role')
            WITH CHECK (auth.role() = 'service_role');
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS idx_enrollments_next_send
    ON public.email_sequence_enrollments (next_send_at)
    WHERE status = 'active' AND next_send_at IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_enrollments_sequence_contact
    ON public.email_sequence_enrollments (sequence_id, contact_id);

CREATE TABLE IF NOT EXISTS public.email_tracking_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    enrollment_id UUID NOT NULL REFERENCES public.email_sequence_enrollments ON DELETE CASCADE,
    step_number INT NOT NULL,
    event_type TEXT NOT NULL
        CHECK (event_type IN (
            'open',
            'click',
            'bounce',
            'bounced',
            'unsubscribe',
            'unsubscribed',
            'delivered'
        )),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.email_tracking_events ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.email_tracking_events
    DROP CONSTRAINT IF EXISTS email_tracking_events_event_type_check;

ALTER TABLE public.email_tracking_events
    ADD CONSTRAINT email_tracking_events_event_type_check
    CHECK (event_type IN (
        'open',
        'click',
        'bounce',
        'bounced',
        'unsubscribe',
        'unsubscribed',
        'delivered'
    ));

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'email_tracking_events'
          AND policyname = 'email_tracking_events_select_own'
    ) THEN
        CREATE POLICY "email_tracking_events_select_own"
            ON public.email_tracking_events FOR SELECT
            USING (EXISTS (
                SELECT 1
                FROM public.email_sequence_enrollments e
                JOIN public.email_sequences s ON s.id = e.sequence_id
                WHERE e.id = email_tracking_events.enrollment_id
                  AND s.user_id = auth.uid()
            ));
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'email_tracking_events'
          AND policyname = 'email_tracking_events_insert_own'
    ) THEN
        CREATE POLICY "email_tracking_events_insert_own"
            ON public.email_tracking_events FOR INSERT
            WITH CHECK (EXISTS (
                SELECT 1
                FROM public.email_sequence_enrollments e
                JOIN public.email_sequences s ON s.id = e.sequence_id
                WHERE e.id = email_tracking_events.enrollment_id
                  AND s.user_id = auth.uid()
            ));
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'email_tracking_events'
          AND policyname = 'email_tracking_events_delete_own'
    ) THEN
        CREATE POLICY "email_tracking_events_delete_own"
            ON public.email_tracking_events FOR DELETE
            USING (EXISTS (
                SELECT 1
                FROM public.email_sequence_enrollments e
                JOIN public.email_sequences s ON s.id = e.sequence_id
                WHERE e.id = email_tracking_events.enrollment_id
                  AND s.user_id = auth.uid()
            ));
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'email_tracking_events'
          AND policyname = 'email_tracking_events_service_role'
    ) THEN
        CREATE POLICY "email_tracking_events_service_role"
            ON public.email_tracking_events FOR ALL
            USING (auth.role() = 'service_role')
            WITH CHECK (auth.role() = 'service_role');
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS idx_tracking_events_enrollment_type
    ON public.email_tracking_events (enrollment_id, event_type);
