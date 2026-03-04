-- Migration: 0054_workflow_template_marketplace_versions.sql
-- Description: Persist shared version history for workflow marketplace listings.

CREATE TABLE IF NOT EXISTS workflow_template_marketplace_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  listing_id UUID NOT NULL REFERENCES workflow_template_marketplace(id) ON DELETE CASCADE,
  template_id UUID NOT NULL REFERENCES workflow_templates(id) ON DELETE CASCADE,
  template_version INTEGER NOT NULL DEFAULT 1,
  template_name TEXT NOT NULL,
  template_description TEXT DEFAULT '' NOT NULL,
  category TEXT NOT NULL,
  personas_allowed JSONB DEFAULT '[]'::jsonb NOT NULL,
  summary TEXT DEFAULT '' NOT NULL,
  tags JSONB DEFAULT '[]'::jsonb NOT NULL,
  use_cases JSONB DEFAULT '[]'::jsonb NOT NULL,
  template_snapshot JSONB DEFAULT '{}'::jsonb NOT NULL,
  shared_at TIMESTAMPTZ DEFAULT now() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'workflow_template_marketplace_versions_listing_template_key'
      AND conrelid = 'workflow_template_marketplace_versions'::regclass
  ) THEN
    ALTER TABLE workflow_template_marketplace_versions
      ADD CONSTRAINT workflow_template_marketplace_versions_listing_template_key
      UNIQUE (listing_id, template_id);
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_workflow_template_marketplace_versions_listing_id
  ON workflow_template_marketplace_versions(listing_id);
CREATE INDEX IF NOT EXISTS idx_workflow_template_marketplace_versions_template_version
  ON workflow_template_marketplace_versions(listing_id, template_version DESC);
CREATE INDEX IF NOT EXISTS idx_workflow_template_marketplace_versions_shared_at
  ON workflow_template_marketplace_versions(shared_at DESC);

INSERT INTO workflow_template_marketplace_versions (
  listing_id,
  template_id,
  template_version,
  template_name,
  template_description,
  category,
  personas_allowed,
  summary,
  tags,
  use_cases,
  template_snapshot,
  shared_at,
  updated_at
)
SELECT
  listing.id,
  listing.template_id,
  listing.template_version,
  listing.template_name,
  COALESCE(listing.template_description, ''),
  listing.category,
  COALESCE(listing.personas_allowed, '[]'::jsonb),
  COALESCE(listing.summary, ''),
  COALESCE(listing.tags, '[]'::jsonb),
  COALESCE(listing.use_cases, '[]'::jsonb),
  COALESCE(listing.template_snapshot, '{}'::jsonb),
  COALESCE(listing.created_at, now()),
  COALESCE(listing.updated_at, now())
FROM workflow_template_marketplace listing
WHERE NOT EXISTS (
  SELECT 1
  FROM workflow_template_marketplace_versions version_row
  WHERE version_row.listing_id = listing.id
    AND version_row.template_id = listing.template_id
);

ALTER TABLE workflow_template_marketplace_versions ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = 'workflow_template_marketplace_versions'
      AND policyname = 'Users can view active workflow marketplace listing versions'
  ) THEN
    CREATE POLICY "Users can view active workflow marketplace listing versions"
      ON workflow_template_marketplace_versions
      FOR SELECT
      USING (
        EXISTS (
          SELECT 1
          FROM workflow_template_marketplace listing
          WHERE listing.id = listing_id
            AND listing.is_active = true
        )
      );
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = 'workflow_template_marketplace_versions'
      AND policyname = 'Users can manage their own workflow marketplace listing versions'
  ) THEN
    CREATE POLICY "Users can manage their own workflow marketplace listing versions"
      ON workflow_template_marketplace_versions
      FOR ALL
      USING (
        EXISTS (
          SELECT 1
          FROM workflow_template_marketplace listing
          WHERE listing.id = listing_id
            AND listing.owner_user_id = (SELECT auth.uid())
        )
      )
      WITH CHECK (
        EXISTS (
          SELECT 1
          FROM workflow_template_marketplace listing
          WHERE listing.id = listing_id
            AND listing.owner_user_id = (SELECT auth.uid())
        )
      );
  END IF;
END $$;
