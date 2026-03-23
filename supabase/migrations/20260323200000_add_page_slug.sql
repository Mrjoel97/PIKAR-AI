-- =============================================================================
-- Phase 21: Multi-Page Builder
-- Adds page_slug column to app_screens for multi-page baton loop tracking.
-- =============================================================================

ALTER TABLE app_screens ADD COLUMN IF NOT EXISTS page_slug TEXT;
