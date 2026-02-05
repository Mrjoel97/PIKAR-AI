-- Migration: 0024_edge_function_webhooks.sql
-- Description: Configure database webhooks to trigger Edge Functions on data changes
-- Uses pg_net extension for HTTP requests from Postgres

-- ============================================================================
-- ENABLE REQUIRED EXTENSIONS
-- ============================================================================

-- pg_net allows Postgres to make HTTP requests
CREATE EXTENSION IF NOT EXISTS pg_net WITH SCHEMA extensions;

-- ============================================================================
-- EDGE FUNCTION WEBHOOK CONFIGURATION
-- ============================================================================

-- Create a table to store webhook configuration (makes it easy to update URLs)
CREATE TABLE IF NOT EXISTS _edge_function_config (
    function_name TEXT PRIMARY KEY,
    base_url TEXT NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    service_role_key TEXT, -- Store auth key here (avoids ALTER DATABASE permission issues)
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Insert default configuration
-- The base_url will be: https://<project-ref>.supabase.co/functions/v1/<function-name>
-- We use a placeholder that should be updated after deployment
INSERT INTO _edge_function_config (function_name, base_url) VALUES
    ('send-notification', 'https://YOUR_PROJECT_REF.supabase.co/functions/v1/send-notification'),
    ('execute-workflow', 'https://YOUR_PROJECT_REF.supabase.co/functions/v1/execute-workflow')
ON CONFLICT (function_name) DO NOTHING;

-- ============================================================================
-- HELPER FUNCTION: Call Edge Function via HTTP
-- ============================================================================

CREATE OR REPLACE FUNCTION call_edge_function(
    p_function_name TEXT,
    p_payload JSONB,
    p_service_role_key TEXT DEFAULT NULL
)
RETURNS BIGINT
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_url TEXT;
    v_enabled BOOLEAN;
    v_stored_key TEXT;
    v_request_id BIGINT;
    v_headers JSONB;
    v_auth_key TEXT;
BEGIN
    -- Get function URL, status, and stored key
    SELECT base_url, enabled, service_role_key INTO v_url, v_enabled, v_stored_key
    FROM _edge_function_config
    WHERE function_name = p_function_name;
    
    -- Skip if function not configured or disabled
    IF v_url IS NULL OR NOT v_enabled THEN
        RAISE NOTICE 'Edge function % not configured or disabled', p_function_name;
        RETURN NULL;
    END IF;
    
    -- Skip if URL contains placeholder (not yet configured)
    IF v_url LIKE '%YOUR_PROJECT_REF%' THEN
        RAISE NOTICE 'Edge function % URL not configured (contains placeholder)', p_function_name;
        RETURN NULL;
    END IF;
    
    -- Use provided key, or stored key, or try database setting
    v_auth_key := COALESCE(p_service_role_key, v_stored_key, current_setting('app.settings.service_role_key', true));
    
    IF v_auth_key IS NULL OR v_auth_key = '' THEN
        RAISE NOTICE 'Edge function % has no authentication key configured', p_function_name;
        RETURN NULL;
    END IF;
    
    -- Build headers with service role key for authentication
    v_headers := jsonb_build_object(
        'Content-Type', 'application/json',
        'Authorization', 'Bearer ' || v_auth_key
    );
    
    -- Make async HTTP POST request using pg_net
    SELECT net.http_post(
        url := v_url,
        headers := v_headers,
        body := p_payload
    ) INTO v_request_id;
    
    RAISE NOTICE 'Edge function % called with request_id %', p_function_name, v_request_id;
    RETURN v_request_id;
END;
$$;

-- ============================================================================
-- TRIGGER FUNCTION: Send Notification Webhook
-- ============================================================================

CREATE OR REPLACE FUNCTION trigger_send_notification()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_payload JSONB;
    v_should_send BOOLEAN := FALSE;
BEGIN
    -- Only trigger for new notifications or status changes to 'pending'
    -- Also check metadata for 'send_immediately' flag
    IF TG_OP = 'INSERT' THEN
        -- Check if send_immediately is set in metadata
        v_should_send := COALESCE((NEW.metadata->>'send_immediately')::BOOLEAN, FALSE);
    ELSIF TG_OP = 'UPDATE' THEN
        -- Trigger if metadata.send_immediately was just set to true
        v_should_send := COALESCE((NEW.metadata->>'send_immediately')::BOOLEAN, FALSE) 
                         AND NOT COALESCE((OLD.metadata->>'send_immediately')::BOOLEAN, FALSE);
    END IF;
    
    IF v_should_send THEN
        v_payload := jsonb_build_object('notification_id', NEW.id::TEXT);
        PERFORM call_edge_function('send-notification', v_payload);
    END IF;
    
    RETURN NEW;
END;
$$;

-- Create trigger on notifications table
DROP TRIGGER IF EXISTS on_notification_send ON notifications;
CREATE TRIGGER on_notification_send
    AFTER INSERT OR UPDATE ON notifications
    FOR EACH ROW
    EXECUTE FUNCTION trigger_send_notification();

-- ============================================================================
-- TRIGGER FUNCTION: Execute Workflow Webhook
-- ============================================================================

CREATE OR REPLACE FUNCTION trigger_execute_workflow()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_payload JSONB;
BEGIN
    -- Trigger when a new execution is created with status 'pending' or 'running'
    IF TG_OP = 'INSERT' THEN
        IF NEW.status IN ('pending', 'running') THEN
            v_payload := jsonb_build_object(
                'execution_id', NEW.id::TEXT,
                'step_action', 'start'
            );
            PERFORM call_edge_function('execute-workflow', v_payload);
        END IF;
    ELSIF TG_OP = 'UPDATE' THEN
        -- Trigger when status changes from 'pending' to 'running'
        IF OLD.status = 'pending' AND NEW.status = 'running' THEN
            v_payload := jsonb_build_object(
                'execution_id', NEW.id::TEXT,
                'step_action', 'start'
            );
            PERFORM call_edge_function('execute-workflow', v_payload);
        -- Trigger when step index advances (workflow progression)
        ELSIF NEW.current_step_index > OLD.current_step_index 
              OR NEW.current_phase_index > OLD.current_phase_index THEN
            v_payload := jsonb_build_object(
                'execution_id', NEW.id::TEXT,
                'step_action', 'advance'
            );
            PERFORM call_edge_function('execute-workflow', v_payload);
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$;

-- Create trigger on workflow_executions table
DROP TRIGGER IF EXISTS on_workflow_execution_change ON workflow_executions;
CREATE TRIGGER on_workflow_execution_change
    AFTER INSERT OR UPDATE ON workflow_executions
    FOR EACH ROW
    EXECUTE FUNCTION trigger_execute_workflow();

-- ============================================================================
-- CONVENIENCE FUNCTIONS
-- ============================================================================

-- Function to update Edge Function URLs (call after deployment)
CREATE OR REPLACE FUNCTION update_edge_function_url(
    p_function_name TEXT,
    p_new_url TEXT
)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    UPDATE _edge_function_config
    SET base_url = p_new_url
    WHERE function_name = p_function_name;
    
    IF NOT FOUND THEN
        INSERT INTO _edge_function_config (function_name, base_url)
        VALUES (p_function_name, p_new_url);
    END IF;
END;
$$;

-- Function to enable/disable a webhook
CREATE OR REPLACE FUNCTION toggle_edge_function_webhook(
    p_function_name TEXT,
    p_enabled BOOLEAN
)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    UPDATE _edge_function_config
    SET enabled = p_enabled
    WHERE function_name = p_function_name;
END;
$$;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE _edge_function_config IS 'Configuration for Edge Function webhook URLs';
COMMENT ON FUNCTION call_edge_function IS 'Makes async HTTP POST to Edge Function via pg_net';
COMMENT ON FUNCTION trigger_send_notification IS 'Triggers send-notification Edge Function on notification insert/update';
COMMENT ON FUNCTION trigger_execute_workflow IS 'Triggers execute-workflow Edge Function on workflow execution changes';
COMMENT ON FUNCTION update_edge_function_url IS 'Updates the URL for an Edge Function webhook';
COMMENT ON FUNCTION toggle_edge_function_webhook IS 'Enables or disables a webhook trigger';

-- ============================================================================
-- INSTRUCTIONS
-- ============================================================================
-- After deploying Edge Functions, update URLs with:
--
-- SELECT update_edge_function_url('send-notification', 'https://<project-ref>.supabase.co/functions/v1/send-notification');
-- SELECT update_edge_function_url('execute-workflow', 'https://<project-ref>.supabase.co/functions/v1/execute-workflow');
--
-- To disable a webhook temporarily:
-- SELECT toggle_edge_function_webhook('send-notification', FALSE);
--
-- To re-enable:
-- SELECT toggle_edge_function_webhook('send-notification', TRUE);
