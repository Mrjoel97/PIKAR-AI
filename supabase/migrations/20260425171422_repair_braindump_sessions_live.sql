-- Reconcile live schema drift where braindump_sessions was missing in production.
-- The original table migration exists in-repo, but this repair migration keeps
-- existing environments idempotent and records the out-of-band production fix.

CREATE TABLE IF NOT EXISTS public.braindump_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    session_type TEXT DEFAULT 'voice' CHECK (session_type IN ('voice')),
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'completed', 'timed_out', 'abandoned')),
    started_at TIMESTAMPTZ DEFAULT now(),
    ended_at TIMESTAMPTZ,
    duration_seconds INTEGER,
    turn_count INTEGER DEFAULT 0,
    transcript_doc_id UUID REFERENCES public.vault_documents(id) ON DELETE SET NULL,
    analysis_doc_id UUID REFERENCES public.vault_documents(id) ON DELETE SET NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE public.braindump_sessions
    ADD COLUMN IF NOT EXISTS session_type TEXT DEFAULT 'voice',
    ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'active',
    ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ DEFAULT now(),
    ADD COLUMN IF NOT EXISTS ended_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS duration_seconds INTEGER,
    ADD COLUMN IF NOT EXISTS turn_count INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS transcript_doc_id UUID REFERENCES public.vault_documents(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS analysis_doc_id UUID REFERENCES public.vault_documents(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now(),
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now();

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'braindump_sessions_session_type_check'
    ) THEN
        ALTER TABLE public.braindump_sessions
            ADD CONSTRAINT braindump_sessions_session_type_check
            CHECK (session_type IN ('voice'));
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'braindump_sessions_status_check'
    ) THEN
        ALTER TABLE public.braindump_sessions
            ADD CONSTRAINT braindump_sessions_status_check
            CHECK (status IN ('active', 'completed', 'timed_out', 'abandoned'));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_braindump_sessions_user_id
    ON public.braindump_sessions(user_id);

CREATE INDEX IF NOT EXISTS idx_braindump_sessions_status
    ON public.braindump_sessions(status);

ALTER TABLE public.braindump_sessions ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'braindump_sessions'
          AND policyname = 'service_role_full_access_braindump'
    ) THEN
        CREATE POLICY "service_role_full_access_braindump"
            ON public.braindump_sessions
            FOR ALL
            USING (auth.role() = 'service_role');
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'braindump_sessions'
          AND policyname = 'users_access_own_braindumps'
    ) THEN
        CREATE POLICY "users_access_own_braindumps"
            ON public.braindump_sessions
            FOR SELECT
            USING (auth.uid() = user_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'braindump_sessions'
          AND policyname = 'users_create_own_braindumps'
    ) THEN
        CREATE POLICY "users_create_own_braindumps"
            ON public.braindump_sessions
            FOR INSERT
            WITH CHECK (auth.uid() = user_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'braindump_sessions'
          AND policyname = 'users_delete_own_braindumps'
    ) THEN
        CREATE POLICY "users_delete_own_braindumps"
            ON public.braindump_sessions
            FOR DELETE
            USING (auth.uid() = user_id);
    END IF;
END $$;

CREATE OR REPLACE FUNCTION public.update_braindump_sessions_updated_at()
RETURNS trigger AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_trigger
        WHERE tgname = 'braindump_sessions_updated_at'
          AND tgrelid = 'public.braindump_sessions'::regclass
    ) THEN
        CREATE TRIGGER braindump_sessions_updated_at
            BEFORE UPDATE ON public.braindump_sessions
            FOR EACH ROW
            EXECUTE FUNCTION public.update_braindump_sessions_updated_at();
    END IF;
END $$;
