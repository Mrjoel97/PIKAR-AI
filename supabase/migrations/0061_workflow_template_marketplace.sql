-- Migration: 0053_workflow_template_marketplace.sql
-- Description: Add workflow template marketplace listings and reviews.

CREATE TABLE IF NOT EXISTS workflow_template_marketplace (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  template_id UUID NOT NULL REFERENCES workflow_templates(id) ON DELETE CASCADE,
  owner_user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  template_name TEXT NOT NULL,
  template_description TEXT DEFAULT '',
  category TEXT NOT NULL,
  template_key TEXT,
  template_version INTEGER NOT NULL DEFAULT 1,
  personas_allowed JSONB DEFAULT '[]'::jsonb NOT NULL,
  author_name TEXT,
  author_persona TEXT,
  summary TEXT DEFAULT '' NOT NULL,
  tags JSONB DEFAULT '[]'::jsonb NOT NULL,
  use_cases JSONB DEFAULT '[]'::jsonb NOT NULL,
  template_snapshot JSONB DEFAULT '{}'::jsonb NOT NULL,
  average_rating NUMERIC(3, 2) DEFAULT 0 NOT NULL,
  rating_count INTEGER DEFAULT 0 NOT NULL,
  clone_count INTEGER DEFAULT 0 NOT NULL,
  featured BOOLEAN DEFAULT false NOT NULL,
  is_active BOOLEAN DEFAULT true NOT NULL,
  last_cloned_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_workflow_template_marketplace_owner_template_key
  ON workflow_template_marketplace(owner_user_id, template_key)
  WHERE template_key IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_workflow_template_marketplace_template_id
  ON workflow_template_marketplace(template_id);
CREATE INDEX IF NOT EXISTS idx_workflow_template_marketplace_category
  ON workflow_template_marketplace(category);
CREATE INDEX IF NOT EXISTS idx_workflow_template_marketplace_active
  ON workflow_template_marketplace(is_active);
CREATE INDEX IF NOT EXISTS idx_workflow_template_marketplace_featured
  ON workflow_template_marketplace(featured);
CREATE INDEX IF NOT EXISTS idx_workflow_template_marketplace_rating
  ON workflow_template_marketplace(average_rating DESC, rating_count DESC);

ALTER TABLE workflow_template_marketplace ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = 'workflow_template_marketplace'
      AND policyname = 'Users can view active workflow marketplace listings'
  ) THEN
    CREATE POLICY "Users can view active workflow marketplace listings"
      ON workflow_template_marketplace
      FOR SELECT
      USING (is_active = true);
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = 'workflow_template_marketplace'
      AND policyname = 'Users can manage their own workflow marketplace listings'
  ) THEN
    CREATE POLICY "Users can manage their own workflow marketplace listings"
      ON workflow_template_marketplace
      FOR ALL
      USING ((SELECT auth.uid()) = owner_user_id)
      WITH CHECK ((SELECT auth.uid()) = owner_user_id);
  END IF;
END $$;

CREATE TABLE IF NOT EXISTS workflow_template_marketplace_reviews (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  listing_id UUID NOT NULL REFERENCES workflow_template_marketplace(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  rating INTEGER NOT NULL,
  review_text TEXT,
  created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'workflow_template_marketplace_reviews_rating_chk'
      AND conrelid = 'workflow_template_marketplace_reviews'::regclass
  ) THEN
    ALTER TABLE workflow_template_marketplace_reviews
      ADD CONSTRAINT workflow_template_marketplace_reviews_rating_chk
      CHECK (rating BETWEEN 1 AND 5);
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'workflow_template_marketplace_reviews_listing_user_key'
      AND conrelid = 'workflow_template_marketplace_reviews'::regclass
  ) THEN
    ALTER TABLE workflow_template_marketplace_reviews
      ADD CONSTRAINT workflow_template_marketplace_reviews_listing_user_key
      UNIQUE (listing_id, user_id);
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_workflow_template_marketplace_reviews_listing_id
  ON workflow_template_marketplace_reviews(listing_id);
CREATE INDEX IF NOT EXISTS idx_workflow_template_marketplace_reviews_user_id
  ON workflow_template_marketplace_reviews(user_id);

ALTER TABLE workflow_template_marketplace_reviews ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = 'workflow_template_marketplace_reviews'
      AND policyname = 'Users can view workflow marketplace reviews'
  ) THEN
    CREATE POLICY "Users can view workflow marketplace reviews"
      ON workflow_template_marketplace_reviews
      FOR SELECT
      USING (true);
  END IF;
END $$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = 'workflow_template_marketplace_reviews'
      AND policyname = 'Users can manage their own workflow marketplace reviews'
  ) THEN
    CREATE POLICY "Users can manage their own workflow marketplace reviews"
      ON workflow_template_marketplace_reviews
      FOR ALL
      USING ((SELECT auth.uid()) = user_id)
      WITH CHECK ((SELECT auth.uid()) = user_id);
  END IF;
END $$;
