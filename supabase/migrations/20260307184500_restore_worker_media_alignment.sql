-- Restore backend/Supabase alignment for worker RPCs, semantic search, and generated media buckets.

-- ---------------------------------------------------------------------------
-- ai_jobs schema alignment
-- ---------------------------------------------------------------------------
ALTER TABLE public.ai_jobs
    ALTER COLUMN id SET DEFAULT gen_random_uuid();

ALTER TABLE public.ai_jobs
    ADD COLUMN IF NOT EXISTS priority INTEGER DEFAULT 5,
    ADD COLUMN IF NOT EXISTS locked_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS locked_by TEXT,
    ADD COLUMN IF NOT EXISTS attempt_count INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS max_attempts INTEGER DEFAULT 3,
    ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now();

UPDATE public.ai_jobs
SET
    priority = COALESCE(priority, 5),
    attempt_count = COALESCE(attempt_count, 0),
    max_attempts = COALESCE(max_attempts, 3),
    updated_at = COALESCE(updated_at, created_at, now())
WHERE
    priority IS NULL
    OR attempt_count IS NULL
    OR max_attempts IS NULL
    OR updated_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_ai_jobs_claim_queue
    ON public.ai_jobs(status, priority DESC, created_at ASC);

CREATE INDEX IF NOT EXISTS idx_ai_jobs_locked_at
    ON public.ai_jobs(locked_at)
    WHERE status = 'processing';

CREATE OR REPLACE FUNCTION public.update_ai_jobs_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path = public
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_ai_jobs_updated_at ON public.ai_jobs;
CREATE TRIGGER trg_ai_jobs_updated_at
    BEFORE UPDATE ON public.ai_jobs
    FOR EACH ROW
    EXECUTE FUNCTION public.update_ai_jobs_updated_at();

-- ---------------------------------------------------------------------------
-- ai_jobs worker RPCs
-- ---------------------------------------------------------------------------
DROP FUNCTION IF EXISTS public.claim_next_ai_job(TEXT);
DROP FUNCTION IF EXISTS public.complete_ai_job(UUID, JSONB);
DROP FUNCTION IF EXISTS public.fail_ai_job(UUID, TEXT);

CREATE FUNCTION public.claim_next_ai_job(p_worker_id TEXT)
RETURNS TABLE(id UUID, job_type TEXT, input_data JSONB, user_id UUID)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_job public.ai_jobs%ROWTYPE;
BEGIN
    SELECT *
    INTO v_job
    FROM public.ai_jobs
    WHERE status = 'pending'
      AND COALESCE(attempt_count, 0) < COALESCE(max_attempts, 3)
    ORDER BY COALESCE(priority, 0) DESC, created_at ASC
    FOR UPDATE SKIP LOCKED
    LIMIT 1;

    IF NOT FOUND THEN
        RETURN;
    END IF;

    UPDATE public.ai_jobs
    SET
        status = 'processing',
        locked_by = p_worker_id,
        locked_at = now(),
        started_at = COALESCE(started_at, now()),
        attempt_count = COALESCE(attempt_count, 0) + 1,
        updated_at = now()
    WHERE public.ai_jobs.id = v_job.id
    RETURNING public.ai_jobs.* INTO v_job;

    RETURN QUERY
    SELECT v_job.id, v_job.job_type, v_job.input_data, v_job.user_id;
END;
$$;

CREATE FUNCTION public.complete_ai_job(
    p_job_id UUID,
    p_output_data JSONB
)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    UPDATE public.ai_jobs
    SET
        status = 'completed',
        output_data = COALESCE(p_output_data, '{}'::jsonb),
        error_message = NULL,
        completed_at = now(),
        locked_at = NULL,
        locked_by = NULL,
        updated_at = now()
    WHERE id = p_job_id;
END;
$$;

CREATE FUNCTION public.fail_ai_job(
    p_job_id UUID,
    p_error_message TEXT
)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    UPDATE public.ai_jobs
    SET
        status = 'failed',
        error_message = p_error_message,
        completed_at = now(),
        locked_at = NULL,
        locked_by = NULL,
        updated_at = now()
    WHERE id = p_job_id;
END;
$$;

REVOKE ALL ON FUNCTION public.claim_next_ai_job(TEXT) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.complete_ai_job(UUID, JSONB) FROM PUBLIC;
REVOKE ALL ON FUNCTION public.fail_ai_job(UUID, TEXT) FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.claim_next_ai_job(TEXT) TO service_role;
GRANT EXECUTE ON FUNCTION public.complete_ai_job(UUID, JSONB) TO service_role;
GRANT EXECUTE ON FUNCTION public.fail_ai_job(UUID, TEXT) TO service_role;

-- ---------------------------------------------------------------------------
-- Session version pruning for superseded history rows
-- ---------------------------------------------------------------------------
DROP FUNCTION IF EXISTS public.prune_session_versions(INTEGER);

CREATE FUNCTION public.prune_session_versions(p_keep_count INTEGER DEFAULT 50)
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_deleted_count INTEGER := 0;
BEGIN
    IF COALESCE(p_keep_count, 0) < 1 THEN
        RETURN 0;
    END IF;

    WITH ranked_versions AS (
        SELECT
            app_name,
            user_id,
            session_id,
            version,
            ROW_NUMBER() OVER (
                PARTITION BY app_name, user_id, session_id
                ORDER BY version DESC
            ) AS version_rank
        FROM (
            SELECT DISTINCT app_name, user_id, session_id, version
            FROM public.session_events
        ) versions
    ),
    purgeable AS (
        SELECT se.id
        FROM public.session_events se
        JOIN ranked_versions rv
          ON rv.app_name = se.app_name
         AND rv.user_id = se.user_id
         AND rv.session_id = se.session_id
         AND rv.version = se.version
        WHERE rv.version_rank > p_keep_count
          AND se.superseded_by IS NOT NULL
    ),
    deleted AS (
        DELETE FROM public.session_events
        WHERE id IN (SELECT id FROM purgeable)
        RETURNING 1
    )
    SELECT COUNT(*) INTO v_deleted_count FROM deleted;

    RETURN COALESCE(v_deleted_count, 0);
END;
$$;

REVOKE ALL ON FUNCTION public.prune_session_versions(INTEGER) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.prune_session_versions(INTEGER) TO service_role;

-- ---------------------------------------------------------------------------
-- Knowledge vault semantic search RPC
-- ---------------------------------------------------------------------------
DROP FUNCTION IF EXISTS public.match_embeddings(vector, integer, double precision, uuid, text);
DROP FUNCTION IF EXISTS public.match_embeddings(vector, double precision, integer, uuid, uuid);

CREATE FUNCTION public.match_embeddings(
    query_embedding vector(768),
    match_count INTEGER DEFAULT 5,
    match_threshold DOUBLE PRECISION DEFAULT 0.5,
    filter_user_id UUID DEFAULT NULL,
    filter_agent_id TEXT DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    source_type TEXT,
    source_id UUID,
    agent_id UUID,
    metadata JSONB,
    similarity DOUBLE PRECISION
)
LANGUAGE sql
STABLE
SECURITY INVOKER
SET search_path = public, extensions
AS $$
    SELECT
        e.id,
        e.content,
        e.source_type,
        e.source_id,
        e.agent_id,
        COALESCE(e.metadata, '{}'::jsonb) AS metadata,
        1 - (e.embedding <=> query_embedding) AS similarity
    FROM public.embeddings e
    WHERE e.embedding IS NOT NULL
      AND (filter_user_id IS NULL OR e.user_id = filter_user_id)
      AND (filter_agent_id IS NULL OR e.agent_id::text = filter_agent_id)
      AND (1 - (e.embedding <=> query_embedding)) >= match_threshold
    ORDER BY e.embedding <=> query_embedding
    LIMIT GREATEST(COALESCE(match_count, 5), 1);
$$;

REVOKE ALL ON FUNCTION public.match_embeddings(vector, integer, double precision, uuid, text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.match_embeddings(vector, integer, double precision, uuid, text) TO authenticated;
GRANT EXECUTE ON FUNCTION public.match_embeddings(vector, integer, double precision, uuid, text) TO service_role;

-- ---------------------------------------------------------------------------
-- Generated media buckets used by DirectorService / media tooling
-- ---------------------------------------------------------------------------
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES
    ('generated-assets', 'generated-assets', true, 104857600, '{image/*,video/*,audio/*,application/json}'),
    ('generated-videos', 'generated-videos', true, 524288000, '{video/*,audio/*,application/json}')
ON CONFLICT (id) DO UPDATE SET
    public = EXCLUDED.public,
    file_size_limit = EXCLUDED.file_size_limit,
    allowed_mime_types = EXCLUDED.allowed_mime_types;

DROP POLICY IF EXISTS "Users can access their own files in generated-assets" ON storage.objects;
CREATE POLICY "Users can access their own files in generated-assets" ON storage.objects
    FOR ALL
    TO authenticated
    USING (
        bucket_id = 'generated-assets'
        AND split_part(name, '/', 1) = auth.uid()::text
    )
    WITH CHECK (
        bucket_id = 'generated-assets'
        AND split_part(name, '/', 1) = auth.uid()::text
    );

DROP POLICY IF EXISTS "Users can access their own files in generated-videos" ON storage.objects;
CREATE POLICY "Users can access their own files in generated-videos" ON storage.objects
    FOR ALL
    TO authenticated
    USING (
        bucket_id = 'generated-videos'
        AND split_part(name, '/', 1) = auth.uid()::text
    )
    WITH CHECK (
        bucket_id = 'generated-videos'
        AND split_part(name, '/', 1) = auth.uid()::text
    );



