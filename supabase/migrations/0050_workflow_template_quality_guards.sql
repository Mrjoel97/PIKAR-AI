-- Migration: 0050_workflow_template_quality_guards.sql
-- Description: Fix known template tool typos and enforce workflow step tool quality.

BEGIN;

-- 1) Typo fix in existing workflow template JSON.
UPDATE workflow_templates
SET phases = REPLACE(phases::text, '"sent_contract"', '"send_contract"')::jsonb
WHERE phases::text LIKE '%"sent_contract"%';

-- 2) Validate that every step contains a non-empty tool value.
CREATE OR REPLACE FUNCTION workflow_phases_have_tools(p_phases jsonb)
RETURNS boolean
LANGUAGE plpgsql
AS $$
DECLARE
  ph jsonb;
  st jsonb;
  tool_text text;
BEGIN
  IF p_phases IS NULL OR jsonb_typeof(p_phases) <> 'array' THEN
    RETURN false;
  END IF;

  FOR ph IN SELECT * FROM jsonb_array_elements(p_phases)
  LOOP
    IF jsonb_typeof(ph->'steps') <> 'array' THEN
      RETURN false;
    END IF;

    FOR st IN SELECT * FROM jsonb_array_elements(ph->'steps')
    LOOP
      tool_text := COALESCE(st->>'tool', '');
      IF btrim(tool_text) = '' THEN
        RETURN false;
      END IF;
    END LOOP;
  END LOOP;

  RETURN true;
END;
$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'workflow_templates_phases_have_tools_chk'
      AND conrelid = 'workflow_templates'::regclass
  ) THEN
    ALTER TABLE workflow_templates
      ADD CONSTRAINT workflow_templates_phases_have_tools_chk
      CHECK (workflow_phases_have_tools(phases));
  END IF;
END $$;

COMMIT;
