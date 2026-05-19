-- Copyright (c) 2024-2026 Pikar AI. All rights reserved.
-- Migration: restore department_health_summary view
--
-- Background:
--   20260403400000_department_tasks.sql originally created the
--   ``department_health_summary`` view. That migration was recorded as
--   applied in ``supabase_migrations.schema_migrations`` but the objects
--   never materialised on remote (per the 2026-04-27 b484 →
--   pikar-ai-project Cloud Run move — see project_cloud_run_migration.md).
--
--   20260511120050_restore_department_tasks.sql brought back the
--   ``department_tasks`` table, indexes, and RLS policies but explicitly
--   deferred the view, citing an assumed dependency on
--   ``_governance_set_updated_at``. The view does NOT depend on that
--   function — only the (also-deferred) ``dept_tasks_set_updated_at``
--   trigger does. Meanwhile ``/departments/health`` (app/routers/
--   departments.py) queries this view and returns 500 without it,
--   bricking the /dashboard/departments page.
--
-- This migration restores the view independently of the trigger.
-- Idempotent: CREATE OR REPLACE VIEW. Safe to re-run, and safe to
-- coexist with a future re-application of the original 20260403400000
-- migration (which uses the same CREATE OR REPLACE shape).

CREATE OR REPLACE VIEW public.department_health_summary AS
SELECT
    d.id                AS department_id,
    d.name              AS department_name,
    d.type              AS department_type,
    d.status            AS department_status,
    COUNT(dt.id) FILTER (
        WHERE dt.status IN ('pending', 'in_progress')
    )                   AS active_tasks,
    COUNT(dt.id) FILTER (
        WHERE dt.status = 'completed'
          AND dt.completed_at >= now() - INTERVAL '30 days'
    )                   AS completed_30d,
    COUNT(dt.id) FILTER (
        WHERE dt.status IN ('pending', 'in_progress', 'completed')
          AND dt.created_at >= now() - INTERVAL '30 days'
    )                   AS total_30d,
    CASE
        WHEN COUNT(dt.id) FILTER (
                 WHERE dt.created_at >= now() - INTERVAL '30 days'
             ) = 0
            THEN 'green'
        WHEN (
            COUNT(dt.id) FILTER (
                WHERE dt.status = 'completed'
                  AND dt.completed_at >= now() - INTERVAL '30 days'
            )::FLOAT
            / NULLIF(COUNT(dt.id) FILTER (
                WHERE dt.status IN ('pending', 'in_progress', 'completed')
                  AND dt.created_at >= now() - INTERVAL '30 days'
            ), 0)
        ) > 0.8
            THEN 'green'
        WHEN (
            COUNT(dt.id) FILTER (
                WHERE dt.status = 'completed'
                  AND dt.completed_at >= now() - INTERVAL '30 days'
            )::FLOAT
            / NULLIF(COUNT(dt.id) FILTER (
                WHERE dt.status IN ('pending', 'in_progress', 'completed')
                  AND dt.created_at >= now() - INTERVAL '30 days'
            ), 0)
        ) > 0.5
            THEN 'yellow'
        ELSE 'red'
    END                 AS health_status
FROM public.departments d
LEFT JOIN public.department_tasks dt ON dt.to_department_id = d.id
GROUP BY d.id, d.name, d.type, d.status;
