-- Migration: 0058_journey_readiness_view.sql
-- Description: Add journey readiness view joined to workflow readiness registry.

BEGIN;

CREATE OR REPLACE VIEW public.journey_readiness AS
WITH ranked_readiness AS (
  SELECT
    wr.*,
    ROW_NUMBER() OVER (
      PARTITION BY wr.template_name
      ORDER BY wr.updated_at DESC NULLS LAST, wr.template_version DESC NULLS LAST
    ) AS readiness_rank
  FROM public.workflow_readiness wr
)
SELECT
  uj.id AS journey_id,
  uj.persona,
  uj.title,
  uj.primary_workflow_template_name AS template_name,
  COALESCE(rr.status, 'missing') AS readiness_status,
  COALESCE(rr.reason_codes, '[]'::jsonb) AS reason_codes,
  CASE
    WHEN uj.primary_workflow_template_name IS NULL THEN '["primary_template_missing"]'::jsonb
    WHEN rr.template_name IS NULL THEN '["readiness_record_missing"]'::jsonb
    ELSE COALESCE(rr.reason_codes, '[]'::jsonb)
  END AS blockers,
  COALESCE(rr.required_integrations, '[]'::jsonb) AS required_integrations,
  COALESCE(rr.requires_human_gate, false) AS requires_human_gate,
  rr.readiness_owner,
  rr.notes,
  rr.updated_at AS readiness_updated_at
FROM public.user_journeys uj
LEFT JOIN ranked_readiness rr
  ON uj.primary_workflow_template_name = rr.template_name
 AND rr.readiness_rank = 1;

COMMENT ON VIEW public.journey_readiness IS
  'Journey readiness joined to workflow_readiness by primary workflow template name.';

COMMIT;
