-- =============================================================================
-- Phase 19: Screen Generation — stitch_project_id on app_projects
--
-- app_projects did not have stitch_project_id (it was on app_screens).
-- This migration adds it so a single Stitch project is reused across all
-- screens in the same app project.
--
-- Also adds page_slug to app_screens for build_plan → screen mapping.
-- =============================================================================

ALTER TABLE app_projects
    ADD COLUMN IF NOT EXISTS stitch_project_id TEXT;

ALTER TABLE app_screens
    ADD COLUMN IF NOT EXISTS page_slug TEXT;

COMMENT ON COLUMN app_projects.stitch_project_id IS
    'Stitch project ID created on first screen generation; reused for all subsequent screens in this project.';

COMMENT ON COLUMN app_screens.page_slug IS
    'URL slug matching the build_plan page entry (e.g. "home", "pricing"). Used for build plan → screen mapping.';
