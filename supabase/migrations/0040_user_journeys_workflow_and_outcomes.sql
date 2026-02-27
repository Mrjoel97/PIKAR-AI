-- Migration: 0040_user_journeys_workflow_and_outcomes.sql
-- Description: Add workflow linkage and outcomes prompt to user_journeys for agent-driven execution.

ALTER TABLE user_journeys
  ADD COLUMN IF NOT EXISTS primary_workflow_template_name TEXT,
  ADD COLUMN IF NOT EXISTS suggested_workflows JSONB DEFAULT '[]',
  ADD COLUMN IF NOT EXISTS outcomes_prompt TEXT,
  ADD COLUMN IF NOT EXISTS category TEXT;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'fk_user_journeys_primary_workflow_template_name'
      AND conrelid = 'user_journeys'::regclass
  ) THEN
    ALTER TABLE user_journeys
      ADD CONSTRAINT fk_user_journeys_primary_workflow_template_name
      FOREIGN KEY (primary_workflow_template_name)
      REFERENCES workflow_templates(name)
      ON UPDATE CASCADE
      ON DELETE SET NULL;
  END IF;
END $$;

CREATE OR REPLACE FUNCTION validate_user_journey_workflow_references()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
  workflow_name TEXT;
BEGIN
  IF NEW.suggested_workflows IS NULL THEN
    NEW.suggested_workflows := '[]'::jsonb;
  END IF;

  IF jsonb_typeof(NEW.suggested_workflows) <> 'array' THEN
    RAISE EXCEPTION 'suggested_workflows must be a JSON array'
      USING ERRCODE = '22023';
  END IF;

  FOR workflow_name IN
    SELECT value
    FROM jsonb_array_elements_text(NEW.suggested_workflows)
  LOOP
    IF NOT EXISTS (
      SELECT 1
      FROM workflow_templates wt
      WHERE wt.name = workflow_name
    ) THEN
      RAISE EXCEPTION 'Invalid workflow template name in suggested_workflows: %', workflow_name
        USING ERRCODE = '23503';
    END IF;
  END LOOP;

  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_validate_user_journey_workflow_references ON user_journeys;

CREATE TRIGGER trg_validate_user_journey_workflow_references
BEFORE INSERT OR UPDATE OF primary_workflow_template_name, suggested_workflows
ON user_journeys
FOR EACH ROW
EXECUTE FUNCTION validate_user_journey_workflow_references();

CREATE OR REPLACE FUNCTION sync_user_journeys_suggested_workflows_on_template_rename()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  UPDATE user_journeys uj
  SET suggested_workflows = (
    SELECT COALESCE(
      jsonb_agg(
        CASE
          WHEN workflow_name = OLD.name THEN to_jsonb(NEW.name)
          ELSE to_jsonb(workflow_name)
        END
      ),
      '[]'::jsonb
    )
    FROM jsonb_array_elements_text(COALESCE(uj.suggested_workflows, '[]'::jsonb)) AS workflow_name
  )
  WHERE OLD.name IS DISTINCT FROM NEW.name
    AND uj.suggested_workflows @> jsonb_build_array(OLD.name);

  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_sync_user_journeys_suggested_workflows_on_template_rename ON workflow_templates;

CREATE TRIGGER trg_sync_user_journeys_suggested_workflows_on_template_rename
AFTER UPDATE OF name ON workflow_templates
FOR EACH ROW
WHEN (OLD.name IS DISTINCT FROM NEW.name)
EXECUTE FUNCTION sync_user_journeys_suggested_workflows_on_template_rename();

COMMENT ON COLUMN user_journeys.primary_workflow_template_name IS 'Workflow template name (workflow_templates.name) to run when user starts this journey as initiative';
COMMENT ON COLUMN user_journeys.suggested_workflows IS 'Array of workflow template names for alternative or supporting workflows';
COMMENT ON COLUMN user_journeys.outcomes_prompt IS 'Prompt text for agent to ask user: e.g. What does success look like? Timeline?';
COMMENT ON COLUMN user_journeys.category IS 'Category for filtering: marketing, operations, content, sales, finance, etc.';

CREATE INDEX IF NOT EXISTS idx_user_journeys_primary_workflow ON user_journeys(primary_workflow_template_name) WHERE primary_workflow_template_name IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_user_journeys_category ON user_journeys(category) WHERE category IS NOT NULL;
