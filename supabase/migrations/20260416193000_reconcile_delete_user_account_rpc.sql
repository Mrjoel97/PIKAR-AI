-- Migration: 20260416193000_reconcile_delete_user_account_rpc.sql
-- Description: Reconcile the live delete_user_account() RPC with production drift.
--
-- The earlier GDPR hardening migration assumes a large set of historical tables
-- exists in every environment. Production drift broke that assumption, which
-- left the delete_user_account() RPC missing entirely on the live project.
--
-- This version rebuilds the function so it is resilient to missing tables:
--   1. Preserve deletion audit rows in data_deletion_requests.
--   2. Preserve governance audit history by anonymizing the actor.
--   3. Delete all public base-table rows with a user_id column except the
--      explicitly preserved audit tables.
--   4. Clean up the small set of legacy tables that use non-standard owner
--      columns but still contain user-linked data.

CREATE OR REPLACE FUNCTION delete_user_account(p_user_id UUID)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, auth
AS $$
DECLARE
    _sentinel_uuid UUID := '00000000-0000-0000-0000-000000000000';
    _column RECORD;
BEGIN
    -- Preserve governance history, but anonymize the actor identity.
    IF to_regclass('public.governance_audit_log') IS NOT NULL THEN
        UPDATE public.governance_audit_log
           SET user_id = _sentinel_uuid,
               ip_address = NULL
         WHERE user_id = p_user_id;
    END IF;

    -- Approval chains do not need to survive account deletion.
    IF to_regclass('public.approval_chains') IS NOT NULL THEN
        DELETE FROM public.approval_chains WHERE user_id = p_user_id;
    END IF;

    -- Delete from every user-scoped public table that exposes a user_id column,
    -- while preserving the deletion audit trail and anonymized governance log.
    FOR _column IN
        SELECT c.table_name, c.udt_name, c.data_type
        FROM information_schema.columns AS c
        JOIN information_schema.tables AS t
          ON t.table_schema = c.table_schema
         AND t.table_name = c.table_name
        WHERE c.table_schema = 'public'
          AND c.column_name = 'user_id'
          AND t.table_type = 'BASE TABLE'
          AND c.table_name NOT IN ('data_deletion_requests', 'governance_audit_log')
    LOOP
        IF _column.udt_name = 'uuid' THEN
            EXECUTE format('DELETE FROM public.%I WHERE user_id = $1', _column.table_name)
            USING p_user_id;
        ELSIF _column.data_type IN ('text', 'character varying') THEN
            EXECUTE format('DELETE FROM public.%I WHERE user_id = $1', _column.table_name)
            USING p_user_id::text;
        END IF;
    END LOOP;

    -- Clean up the small set of user-linked tables that do not use `user_id`.
    IF to_regclass('public.initiative_checklist_items') IS NOT NULL THEN
        DELETE FROM public.initiative_checklist_items WHERE owner_user_id = p_user_id;
    END IF;

    IF to_regclass('public.admin_chat_sessions') IS NOT NULL THEN
        DELETE FROM public.admin_chat_sessions WHERE admin_user_id = p_user_id;
    END IF;

    -- Preserve the audit row itself, but close any pending deletion requests.
    IF to_regclass('public.data_deletion_requests') IS NOT NULL THEN
        UPDATE public.data_deletion_requests
           SET status = 'completed',
               completed_at = now()
         WHERE user_id = p_user_id
           AND status = 'pending';
    END IF;

    DELETE FROM auth.users WHERE id = p_user_id;
END;
$$;

REVOKE ALL ON FUNCTION delete_user_account(UUID) FROM PUBLIC;
REVOKE ALL ON FUNCTION delete_user_account(UUID) FROM authenticated;
REVOKE ALL ON FUNCTION delete_user_account(UUID) FROM anon;
GRANT EXECUTE ON FUNCTION delete_user_account(UUID) TO service_role;
