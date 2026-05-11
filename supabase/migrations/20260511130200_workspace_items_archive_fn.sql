-- Archive workspace_items for completed/cancelled workflow runs older than 48h.

CREATE OR REPLACE FUNCTION archive_stale_workflow_items()
RETURNS TABLE (archived INT)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    n INT;
BEGIN
    WITH stale AS (
        SELECT wi.id
        FROM workspace_items wi
        JOIN workflow_executions we ON we.id = wi.workflow_execution_id
        WHERE wi.widget_type = 'workflow_timeline'
          AND wi.archived_at IS NULL
          AND we.status IN ('completed', 'cancelled')
          AND we.completed_at IS NOT NULL
          AND we.completed_at < NOW() - INTERVAL '48 hours'
    ),
    upd AS (
        UPDATE workspace_items
           SET archived_at = NOW()
         WHERE id IN (SELECT id FROM stale)
         RETURNING 1
    )
    SELECT COUNT(*) INTO n FROM upd;
    RETURN QUERY SELECT n;
END;
$$;
