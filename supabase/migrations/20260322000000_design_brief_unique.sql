-- =============================================================================
-- Phase 18: Design Brief Research — UNIQUE constraint on design_systems
--
-- Enables the upsert pattern in design_brief_service.py:
--   supabase.table("design_systems").upsert(..., on_conflict="project_id")
-- =============================================================================

ALTER TABLE design_systems
    ADD CONSTRAINT design_systems_project_id_unique UNIQUE (project_id);
