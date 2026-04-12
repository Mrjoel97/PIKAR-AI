-- Phase 75-01: Scheduled Improvement Cycle
-- Adds self_improvement_settings table, expands improvement_actions constraints,
-- and adds approval tracking columns.

-- ============================================================================
-- 1. self_improvement_settings - Admin-configurable settings for the engine
-- ============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'self_improvement_settings'
    ) THEN
        CREATE TABLE self_improvement_settings (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            key TEXT UNIQUE NOT NULL,
            value JSONB NOT NULL,
            updated_at TIMESTAMPTZ DEFAULT now(),
            updated_by TEXT
        );

        -- Seed default rows
        INSERT INTO self_improvement_settings (key, value) VALUES
            ('auto_execute_enabled', 'false'::jsonb),
            ('auto_execute_risk_tiers', '["skill_demoted","pattern_extract"]'::jsonb);

        -- RLS: service_role only
        ALTER TABLE self_improvement_settings ENABLE ROW LEVEL SECURITY;
        CREATE POLICY self_improvement_settings_service_access
            ON self_improvement_settings
            FOR ALL USING (auth.role() = 'service_role');
    END IF;
END $$;


-- ============================================================================
-- 2. Expand improvement_actions.action_type CHECK constraint
--    Add 'pattern_extract' and 'investigate' to allowed values
-- ============================================================================

DO $$
BEGIN
    -- Drop the existing action_type check constraint
    ALTER TABLE improvement_actions
        DROP CONSTRAINT IF EXISTS improvement_actions_action_type_check;

    -- Re-create with expanded values
    ALTER TABLE improvement_actions
        ADD CONSTRAINT improvement_actions_action_type_check
        CHECK (action_type IN (
            'skill_created',
            'skill_refined',
            'skill_promoted',
            'skill_demoted',
            'skill_merged',
            'gap_identified',
            'instruction_updated',
            'pattern_extract',
            'investigate'
        ));
END $$;


-- ============================================================================
-- 3. Expand improvement_actions.status CHECK constraint
--    Add 'pending_approval' and 'declined' to allowed values
-- ============================================================================

DO $$
BEGIN
    -- Drop the existing status check constraint
    ALTER TABLE improvement_actions
        DROP CONSTRAINT IF EXISTS improvement_actions_status_check;

    -- Re-create with expanded values
    ALTER TABLE improvement_actions
        ADD CONSTRAINT improvement_actions_status_check
        CHECK (status IN (
            'pending',
            'applied',
            'validated',
            'reverted',
            'pending_approval',
            'declined'
        ));
END $$;


-- ============================================================================
-- 4. Add approval tracking columns to improvement_actions
-- ============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'improvement_actions' AND column_name = 'approved_by'
    ) THEN
        ALTER TABLE improvement_actions ADD COLUMN approved_by UUID;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'improvement_actions' AND column_name = 'approved_at'
    ) THEN
        ALTER TABLE improvement_actions ADD COLUMN approved_at TIMESTAMPTZ;
    END IF;
END $$;
