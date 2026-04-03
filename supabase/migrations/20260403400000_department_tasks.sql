-- Copyright (c) 2024-2026 Pikar AI. All rights reserved.
-- Migration: department_tasks — cross-department task handoff schema
-- Purpose: USER-initiated cross-department task handoffs visible in the SME
--          department dashboard. Distinct from inter_dept_requests which is
--          for autonomous department-to-department coordination.

-- ---------------------------------------------------------------------------
-- Table
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS department_tasks (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    title               TEXT        NOT NULL,
    description         TEXT,
    from_department_id  UUID        NOT NULL REFERENCES departments(id),
    to_department_id    UUID        NOT NULL REFERENCES departments(id),
    created_by          UUID        NOT NULL,
    assigned_to         UUID,
    status              TEXT        NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'in_progress', 'completed', 'cancelled')),
    priority            TEXT        NOT NULL DEFAULT 'medium'
                        CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
    due_date            TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,
    metadata            JSONB       NOT NULL DEFAULT '{}',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Indexes
-- ---------------------------------------------------------------------------

-- Primary query path: tasks assigned to a department that are still active
CREATE INDEX IF NOT EXISTS idx_dept_tasks_to_dept_status
    ON department_tasks (to_department_id, status)
    WHERE status IN ('pending', 'in_progress');

-- For tracking outbound handoffs from a department
CREATE INDEX IF NOT EXISTS idx_dept_tasks_from_dept
    ON department_tasks (from_department_id);

-- For fetching all tasks a specific user has created
CREATE INDEX IF NOT EXISTS idx_dept_tasks_created_by
    ON department_tasks (created_by);

-- For overdue detection: active tasks with a due_date
CREATE INDEX IF NOT EXISTS idx_dept_tasks_due_date
    ON department_tasks (due_date)
    WHERE status IN ('pending', 'in_progress');

-- ---------------------------------------------------------------------------
-- Row-Level Security
-- ---------------------------------------------------------------------------

ALTER TABLE department_tasks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Authenticated users can read department tasks"
    ON department_tasks
    FOR SELECT
    USING (auth.role() = 'authenticated');

CREATE POLICY "Service role full access"
    ON department_tasks
    FOR ALL
    USING (auth.role() = 'service_role');

-- ---------------------------------------------------------------------------
-- Auto-update trigger for updated_at
-- (re-uses _governance_set_updated_at from 20260403300000_enterprise_governance.sql)
-- ---------------------------------------------------------------------------

CREATE TRIGGER dept_tasks_set_updated_at
    BEFORE UPDATE ON department_tasks
    FOR EACH ROW
    EXECUTE FUNCTION _governance_set_updated_at();

-- ---------------------------------------------------------------------------
-- View: department_health_summary
-- Computes per-department health based on 30-day task completion rate.
-- green  = no tasks in 30d, OR >80% completion rate
-- yellow = 50%–80% completion rate
-- red    = <50% completion rate
-- ---------------------------------------------------------------------------

CREATE OR REPLACE VIEW department_health_summary AS
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
FROM departments d
LEFT JOIN department_tasks dt ON dt.to_department_id = d.id
GROUP BY d.id, d.name, d.type, d.status;
