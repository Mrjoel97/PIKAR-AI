-- Migration: 20260303164156_add_workflow_template_designer_state.sql
-- Description: Add optional visual editor metadata to workflow templates.

BEGIN;

ALTER TABLE public.workflow_templates
  ADD COLUMN IF NOT EXISTS designer_state JSONB NOT NULL DEFAULT '{}'::jsonb;

COMMENT ON COLUMN public.workflow_templates.designer_state IS
  'Visual editor metadata (versioned node/edge canvas state). Runtime execution remains phase/step-driven.';

UPDATE public.workflow_templates
SET designer_state = '{}'::jsonb
WHERE designer_state IS NULL;

COMMIT;
