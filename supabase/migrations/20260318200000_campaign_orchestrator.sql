-- Campaign Orchestrator: Phase 3
-- Marketing audiences, buyer personas, campaign phases, UTM tracking

-- =============================================================================
-- 1. Marketing Audiences (reusable audience segments)
-- =============================================================================
CREATE TABLE IF NOT EXISTS marketing_audiences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    demographics JSONB NOT NULL DEFAULT '{}'::jsonb,
    -- demographics: { age_range, gender, location, income_bracket, education, job_title }
    psychographics JSONB NOT NULL DEFAULT '{}'::jsonb,
    -- psychographics: { interests[], values[], pain_points[], motivations[], lifestyle }
    behavioral JSONB NOT NULL DEFAULT '{}'::jsonb,
    -- behavioral: { purchase_frequency, brand_loyalty, channel_preferences[], device_usage }
    estimated_size INTEGER,
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_marketing_audiences_user ON marketing_audiences(user_id);

ALTER TABLE marketing_audiences ENABLE ROW LEVEL SECURITY;

CREATE POLICY "marketing_audiences_select_own" ON marketing_audiences
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "marketing_audiences_insert_own" ON marketing_audiences
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "marketing_audiences_update_own" ON marketing_audiences
    FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "marketing_audiences_delete_own" ON marketing_audiences
    FOR DELETE USING (auth.uid() = user_id);
CREATE POLICY "marketing_audiences_service_role" ON marketing_audiences
    FOR ALL USING (auth.role() = 'service_role');

CREATE TRIGGER marketing_audiences_updated_at
    BEFORE UPDATE ON marketing_audiences
    FOR EACH ROW EXECUTE FUNCTION moddatetime(updated_at);


-- =============================================================================
-- 2. Marketing Personas (buyer personas)
-- =============================================================================
CREATE TABLE IF NOT EXISTS marketing_personas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    -- e.g., "Startup Sarah", "Enterprise Eric"
    role_title TEXT,
    company_type TEXT,
    bio TEXT,
    goals TEXT[] DEFAULT '{}',
    pain_points TEXT[] DEFAULT '{}',
    objections TEXT[] DEFAULT '{}',
    preferred_channels TEXT[] DEFAULT '{}',
    -- preferred_channels: ['email', 'linkedin', 'twitter', 'blog']
    content_preferences JSONB NOT NULL DEFAULT '{}'::jsonb,
    -- content_preferences: { formats[], tone, length, frequency }
    buying_journey_stage TEXT DEFAULT 'awareness',
    -- awareness, consideration, decision, retention
    audience_id UUID REFERENCES marketing_audiences(id) ON DELETE SET NULL,
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_marketing_personas_user ON marketing_personas(user_id);
CREATE INDEX IF NOT EXISTS idx_marketing_personas_audience ON marketing_personas(audience_id) WHERE audience_id IS NOT NULL;

ALTER TABLE marketing_personas ENABLE ROW LEVEL SECURITY;

CREATE POLICY "marketing_personas_select_own" ON marketing_personas
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "marketing_personas_insert_own" ON marketing_personas
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "marketing_personas_update_own" ON marketing_personas
    FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "marketing_personas_delete_own" ON marketing_personas
    FOR DELETE USING (auth.uid() = user_id);
CREATE POLICY "marketing_personas_service_role" ON marketing_personas
    FOR ALL USING (auth.role() = 'service_role');

CREATE TRIGGER marketing_personas_updated_at
    BEFORE UPDATE ON marketing_personas
    FOR EACH ROW EXECUTE FUNCTION moddatetime(updated_at);


-- =============================================================================
-- 3. Campaign Phases (orchestrator state tracking)
-- =============================================================================
CREATE TABLE IF NOT EXISTS campaign_phases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    phase TEXT NOT NULL CHECK (phase IN ('draft', 'review', 'approved', 'active', 'completed', 'paused')),
    entered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    exited_at TIMESTAMPTZ,
    approval_request_id UUID REFERENCES approval_requests(id) ON DELETE SET NULL,
    notes TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
    -- metadata: { triggered_by, reason, checklist_status, performance_snapshot }
);

CREATE INDEX IF NOT EXISTS idx_campaign_phases_campaign ON campaign_phases(campaign_id);
CREATE INDEX IF NOT EXISTS idx_campaign_phases_user ON campaign_phases(user_id);

ALTER TABLE campaign_phases ENABLE ROW LEVEL SECURITY;

CREATE POLICY "campaign_phases_select_own" ON campaign_phases
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "campaign_phases_insert_own" ON campaign_phases
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "campaign_phases_update_own" ON campaign_phases
    FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "campaign_phases_service_role" ON campaign_phases
    FOR ALL USING (auth.role() = 'service_role');


-- =============================================================================
-- 4. Add structured fields to campaigns table
-- =============================================================================
ALTER TABLE campaigns
    ADD COLUMN IF NOT EXISTS current_phase TEXT DEFAULT 'draft',
    ADD COLUMN IF NOT EXISTS audience_id UUID REFERENCES marketing_audiences(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS persona_id UUID REFERENCES marketing_personas(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS utm_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    -- utm_config: { source, medium, campaign_name, term, content }
    ADD COLUMN IF NOT EXISTS channels TEXT[] DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS budget JSONB NOT NULL DEFAULT '{}'::jsonb,
    -- budget: { total, daily_cap, currency, allocated_channels: { social: 500, email: 200 } }
    ADD COLUMN IF NOT EXISTS schedule_end TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS goals JSONB NOT NULL DEFAULT '{}'::jsonb;
    -- goals: { primary_kpi, target_value, secondary_kpis: [] }

CREATE INDEX IF NOT EXISTS idx_campaigns_phase ON campaigns(user_id, current_phase);
CREATE INDEX IF NOT EXISTS idx_campaigns_audience ON campaigns(audience_id) WHERE audience_id IS NOT NULL;
