-- Reconcile workflow readiness required_integrations metadata so the
-- readiness registry derives its integration list from workflow phases.

BEGIN;

CREATE OR REPLACE FUNCTION public._workflow_tool_required_integrations(tool_name TEXT)
RETURNS JSONB
LANGUAGE sql
IMMUTABLE
AS $$
  SELECT CASE lower(COALESCE(tool_name, ''))
    WHEN 'mcp_web_search' THEN '["tavily"]'::jsonb
    WHEN 'quick_research' THEN '["tavily"]'::jsonb
    WHEN 'deep_research' THEN '["tavily"]'::jsonb
    WHEN 'market_research' THEN '["tavily"]'::jsonb
    WHEN 'competitor_research' THEN '["tavily"]'::jsonb
    WHEN 'monitor_brand' THEN '["tavily"]'::jsonb
    WHEN 'compare_share_of_voice' THEN '["tavily"]'::jsonb
    WHEN 'mcp_web_scrape' THEN '["firecrawl"]'::jsonb
    WHEN 'crawl_website' THEN '["firecrawl"]'::jsonb
    WHEN 'map_website' THEN '["firecrawl"]'::jsonb
    WHEN 'mcp_generate_landing_page' THEN '["stitch"]'::jsonb
    WHEN 'mcp_stitch_landing_page' THEN '["stitch"]'::jsonb
    WHEN 'generate_image' THEN '["google_ai"]'::jsonb
    WHEN 'ocr_document' THEN '["google_ai"]'::jsonb
    WHEN 'record_video' THEN '["google_ai"]'::jsonb
    WHEN 'get_seo_performance' THEN '["google_seo"]'::jsonb
    WHEN 'get_top_search_queries' THEN '["google_seo"]'::jsonb
    WHEN 'get_top_pages' THEN '["google_seo"]'::jsonb
    WHEN 'get_indexing_status' THEN '["google_seo"]'::jsonb
    WHEN 'get_website_traffic' THEN '["google_analytics"]'::jsonb
    WHEN 'get_social_analytics' THEN '["social_oauth"]'::jsonb
    WHEN 'get_all_platform_analytics' THEN '["social_oauth"]'::jsonb
    WHEN 'send_message' THEN '["email"]'::jsonb
    WHEN 'start_call' THEN '["email"]'::jsonb
    WHEN 'create_crm_contact' THEN '["crm"]'::jsonb
    WHEN 'create_connection' THEN '["supabase"]'::jsonb
    WHEN 'upload_file' THEN '["supabase"]'::jsonb
    WHEN 'approve_request' THEN '["supabase"]'::jsonb
    WHEN 'process_payment' THEN '["supabase"]'::jsonb
    WHEN 'send_payment' THEN '["supabase"]'::jsonb
    WHEN 'verify_po' THEN '["supabase"]'::jsonb
    WHEN 'process_data' THEN '["supabase"]'::jsonb
    WHEN 'train_model' THEN '["supabase"]'::jsonb
    WHEN 'deploy_service' THEN '["supabase"]'::jsonb
    WHEN 'update_hris' THEN '["supabase"]'::jsonb
    WHEN 'create_checklist' THEN '["supabase"]'::jsonb
    WHEN 'record_notes' THEN '["supabase"]'::jsonb
    WHEN 'listen_call' THEN '["supabase"]'::jsonb
    WHEN 'process_expense' THEN '["supabase"]'::jsonb
    WHEN 'book_travel' THEN '["supabase"]'::jsonb
    ELSE '[]'::jsonb
  END;
$$;

CREATE OR REPLACE FUNCTION public._compute_workflow_required_integrations(phases_json JSONB)
RETURNS JSONB
LANGUAGE sql
IMMUTABLE
AS $$
  WITH step_rows AS (
    SELECT step.step
    FROM jsonb_array_elements(COALESCE(phases_json, '[]'::jsonb)) AS phase(phase)
    CROSS JOIN LATERAL jsonb_array_elements(COALESCE(phase.phase->'steps', '[]'::jsonb)) AS step(step)
  ),
  expanded AS (
    SELECT jsonb_array_elements_text(
      CASE
        WHEN jsonb_typeof(step->'required_integrations') = 'array'
          AND jsonb_array_length(step->'required_integrations') > 0
        THEN step->'required_integrations'
        ELSE public._workflow_tool_required_integrations(
          COALESCE(step->>'tool', step->>'action_type')
        )
      END
    ) AS integration
    FROM step_rows
  )
  SELECT COALESCE(
    jsonb_agg(integration ORDER BY integration),
    '[]'::jsonb
  )
  FROM (
    SELECT DISTINCT btrim(integration) AS integration
    FROM expanded
    WHERE btrim(integration) <> ''
  ) dedup;
$$;

CREATE OR REPLACE FUNCTION public.sync_workflow_readiness_from_template()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
  computed_status TEXT;
  computed_requires_human_gate BOOLEAN;
  computed_required_integrations JSONB;
BEGIN
  computed_status := CASE
    WHEN NEW.lifecycle_status = 'archived' THEN 'blocked'
    WHEN NEW.lifecycle_status = 'draft' THEN 'draft'
    ELSE 'ready'
  END;

  computed_requires_human_gate := public._compute_requires_human_gate(NEW.phases);
  computed_required_integrations := public._compute_workflow_required_integrations(NEW.phases);

  INSERT INTO public.workflow_readiness (
    template_id,
    template_name,
    template_version,
    status,
    required_integrations,
    requires_human_gate
  )
  VALUES (
    NEW.id,
    NEW.name,
    NEW.version,
    computed_status,
    computed_required_integrations,
    computed_requires_human_gate
  )
  ON CONFLICT (template_id) DO UPDATE
  SET
    template_name = EXCLUDED.template_name,
    template_version = EXCLUDED.template_version,
    required_integrations = EXCLUDED.required_integrations,
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

UPDATE public.workflow_readiness AS wr
SET
  template_name = wt.name,
  template_version = wt.version,
  required_integrations = public._compute_workflow_required_integrations(wt.phases),
  requires_human_gate = public._compute_requires_human_gate(wt.phases),
  updated_at = now()
FROM public.workflow_templates AS wt
WHERE wt.id = wr.template_id;

COMMIT;
