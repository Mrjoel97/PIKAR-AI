-- Self-Improvement System Tables
-- Inspired by Karpathy's autoresearch: autonomous iteration with metric-driven keep/discard

-- ============================================================================
-- 1. Interaction Logs - Captures every agent interaction for signal collection
-- ============================================================================
CREATE TABLE IF NOT EXISTS interaction_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    session_id TEXT,

    -- Agent & Skill context
    agent_id TEXT NOT NULL,               -- e.g. 'FIN', 'MKT', 'EXEC'
    skill_used TEXT,                       -- skill name if a skill was invoked
    skill_category TEXT,

    -- Interaction details
    user_query TEXT NOT NULL,              -- what the user asked
    agent_response_summary TEXT,           -- truncated response (first 500 chars)
    response_tokens INTEGER,              -- response size signal

    -- Quality signals
    user_feedback TEXT CHECK (user_feedback IN ('positive', 'negative', 'neutral', NULL)),
    was_escalated BOOLEAN DEFAULT FALSE,  -- did user escalate to another agent?
    had_followup BOOLEAN DEFAULT FALSE,   -- did user immediately re-ask (retry signal)?
    task_completed BOOLEAN,               -- did the task resolve?
    response_time_ms INTEGER,             -- latency

    -- Metadata
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- Indexes for the evaluation engine's queries
CREATE INDEX idx_interaction_logs_user ON interaction_logs(user_id, created_at DESC);
CREATE INDEX idx_interaction_logs_agent ON interaction_logs(agent_id, created_at DESC);
CREATE INDEX idx_interaction_logs_skill ON interaction_logs(skill_used) WHERE skill_used IS NOT NULL;
CREATE INDEX idx_interaction_logs_feedback ON interaction_logs(user_feedback) WHERE user_feedback IS NOT NULL;
CREATE INDEX idx_interaction_logs_created ON interaction_logs(created_at DESC);

-- RLS
ALTER TABLE interaction_logs ENABLE ROW LEVEL SECURITY;
CREATE POLICY interaction_logs_user_access ON interaction_logs
    FOR ALL USING (auth.uid() = user_id);
CREATE POLICY interaction_logs_service_access ON interaction_logs
    FOR ALL USING (auth.role() = 'service_role');


-- ============================================================================
-- 2. Skill Performance Scores - Periodic evaluation snapshots
-- ============================================================================
CREATE TABLE IF NOT EXISTS skill_scores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    skill_name TEXT NOT NULL,
    evaluation_period TEXT NOT NULL,        -- e.g. '2026-03-18_daily', '2026-W12_weekly'

    -- Usage metrics
    total_uses INTEGER DEFAULT 0,
    unique_users INTEGER DEFAULT 0,

    -- Quality metrics (0.0 to 1.0)
    positive_rate REAL DEFAULT 0.0,        -- positive feedback / total feedback
    completion_rate REAL DEFAULT 0.0,      -- tasks completed / total uses
    escalation_rate REAL DEFAULT 0.0,      -- escalations / total uses
    retry_rate REAL DEFAULT 0.0,           -- followups / total uses

    -- Composite score (weighted average of quality metrics)
    effectiveness_score REAL DEFAULT 0.0,  -- the "val_bpb" equivalent

    -- Trend
    score_delta REAL DEFAULT 0.0,          -- change from previous period
    trend TEXT CHECK (trend IN ('improving', 'stable', 'declining', 'new')),

    -- Metadata
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,

    UNIQUE (skill_name, evaluation_period)
);

CREATE INDEX idx_skill_scores_name ON skill_scores(skill_name, created_at DESC);
CREATE INDEX idx_skill_scores_effectiveness ON skill_scores(effectiveness_score DESC);

-- RLS - scores are system-level, read by all authenticated users
ALTER TABLE skill_scores ENABLE ROW LEVEL SECURITY;
CREATE POLICY skill_scores_read_access ON skill_scores
    FOR SELECT USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');
CREATE POLICY skill_scores_write_access ON skill_scores
    FOR INSERT WITH CHECK (auth.role() = 'service_role');
CREATE POLICY skill_scores_update_access ON skill_scores
    FOR UPDATE USING (auth.role() = 'service_role');


-- ============================================================================
-- 3. Improvement Actions - Log of what the engine changed (audit trail)
-- ============================================================================
CREATE TABLE IF NOT EXISTS improvement_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- What was done
    action_type TEXT NOT NULL CHECK (action_type IN (
        'skill_created',       -- new skill generated from patterns
        'skill_refined',       -- existing skill knowledge improved
        'skill_promoted',      -- candidate → active
        'skill_demoted',       -- active → candidate/inactive
        'skill_merged',        -- redundant skills combined
        'gap_identified',      -- coverage gap found
        'instruction_updated'  -- agent instruction improved
    )),

    -- Context
    skill_name TEXT,
    agent_id TEXT,
    trigger_reason TEXT NOT NULL,          -- what triggered this action
    details JSONB DEFAULT '{}',            -- action-specific details

    -- Result tracking (the keep/discard mechanism)
    status TEXT DEFAULT 'pending' CHECK (status IN (
        'pending',    -- action proposed
        'applied',    -- action executed
        'validated',  -- confirmed improvement (kept)
        'reverted'    -- no improvement (discarded)
    )),
    effectiveness_before REAL,             -- score before change
    effectiveness_after REAL,              -- score after change (filled on validation)

    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    validated_at TIMESTAMPTZ
);

CREATE INDEX idx_improvement_actions_type ON improvement_actions(action_type, created_at DESC);
CREATE INDEX idx_improvement_actions_skill ON improvement_actions(skill_name) WHERE skill_name IS NOT NULL;
CREATE INDEX idx_improvement_actions_status ON improvement_actions(status);

-- RLS
ALTER TABLE improvement_actions ENABLE ROW LEVEL SECURITY;
CREATE POLICY improvement_actions_read_access ON improvement_actions
    FOR SELECT USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');
CREATE POLICY improvement_actions_write_access ON improvement_actions
    FOR ALL USING (auth.role() = 'service_role');


-- ============================================================================
-- 4. Coverage Gaps - Queries that no skill could handle
-- ============================================================================
CREATE TABLE IF NOT EXISTS coverage_gaps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,

    user_query TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    matched_skills TEXT[],                 -- skills that partially matched
    confidence_score REAL DEFAULT 0.0,     -- how well the best match scored

    -- Resolution tracking
    resolved BOOLEAN DEFAULT FALSE,
    resolved_by_skill TEXT,                -- skill that was created/improved to fill gap
    resolved_at TIMESTAMPTZ,

    occurrence_count INTEGER DEFAULT 1,    -- how many times similar gap appeared
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX idx_coverage_gaps_unresolved ON coverage_gaps(resolved, created_at DESC) WHERE NOT resolved;
CREATE INDEX idx_coverage_gaps_agent ON coverage_gaps(agent_id);

-- RLS
ALTER TABLE coverage_gaps ENABLE ROW LEVEL SECURITY;
CREATE POLICY coverage_gaps_user_access ON coverage_gaps
    FOR ALL USING (auth.uid() = user_id);
CREATE POLICY coverage_gaps_service_access ON coverage_gaps
    FOR ALL USING (auth.role() = 'service_role');
