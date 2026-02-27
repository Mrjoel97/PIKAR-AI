-- Migration: 0055_optimize_workflow_queries.sql
-- Description: Add indexes to workflow_templates to prevent timeouts on listing.

BEGIN;

-- 1. Index on category (used for filtering)
CREATE INDEX IF NOT EXISTS idx_workflow_templates_category ON public.workflow_templates(category);

-- 2. GIN Index on personas_allowed (used for JSONB containment filtering)
CREATE INDEX IF NOT EXISTS idx_workflow_templates_personas_allowed ON public.workflow_templates USING gin (personas_allowed);

COMMIT;
