-- Brand DNA System: brand_profiles table for persistent creative identity
-- Each user/workspace gets a brand profile that all creative agents read before generating content.

CREATE TABLE IF NOT EXISTS brand_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    workspace_id UUID,

    -- Brand identity
    brand_name TEXT NOT NULL DEFAULT '',
    tagline TEXT DEFAULT '',
    brand_description TEXT DEFAULT '',

    -- Voice & tone
    voice_tone TEXT DEFAULT 'professional',
    voice_personality TEXT[] DEFAULT '{}',
    voice_examples TEXT DEFAULT '',

    -- Visual identity (flexible JSONB for color palettes, fonts, moods, etc.)
    visual_style JSONB DEFAULT '{
        "color_palette": [],
        "mood": "",
        "lighting_style": "",
        "composition_rules": "",
        "typography": "",
        "reference_styles": []
    }'::jsonb,

    -- Target audience
    audience_description TEXT DEFAULT '',
    audience_demographics TEXT DEFAULT '',
    audience_psychographics TEXT DEFAULT '',

    -- Platform-specific rules (e.g., {"instagram": {"tone": "casual", "max_hashtags": 15}})
    platform_rules JSONB DEFAULT '{}'::jsonb,

    -- Content guardrails
    content_rules TEXT[] DEFAULT '{}',
    forbidden_terms TEXT[] DEFAULT '{}',
    required_disclosures TEXT[] DEFAULT '{}',

    -- Preferred tools/styles for generation
    preferred_image_style TEXT DEFAULT 'vibrant',
    preferred_video_style TEXT DEFAULT '',
    preferred_aspect_ratios JSONB DEFAULT '{}'::jsonb,

    -- Metadata
    is_default BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_brand_profiles_user_id ON brand_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_brand_profiles_workspace_id ON brand_profiles(workspace_id) WHERE workspace_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_brand_profiles_user_default ON brand_profiles(user_id) WHERE is_default = true;

-- Updated_at trigger
CREATE OR REPLACE FUNCTION update_brand_profiles_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_brand_profiles_updated_at ON brand_profiles;
CREATE TRIGGER trg_brand_profiles_updated_at
    BEFORE UPDATE ON brand_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_brand_profiles_updated_at();

-- RLS policies
ALTER TABLE brand_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own brand profiles"
    ON brand_profiles FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own brand profiles"
    ON brand_profiles FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own brand profiles"
    ON brand_profiles FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own brand profiles"
    ON brand_profiles FOR DELETE
    USING (auth.uid() = user_id);

-- Service role bypass for backend agents
CREATE POLICY "Service role full access to brand_profiles"
    ON brand_profiles FOR ALL
    USING (auth.role() = 'service_role');
