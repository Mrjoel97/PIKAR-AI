-- User MCP Integrations Schema
-- Extensible system for any app integration (not limited to templates)

-- =============================================================================
-- Integration Templates Table
-- Pre-configured templates for common integrations (Supabase, Resend, etc.)
-- =============================================================================
CREATE TABLE IF NOT EXISTS mcp_integration_templates (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    icon_url TEXT,
    category TEXT DEFAULT 'other',
    required_fields JSONB NOT NULL DEFAULT '[]',
    optional_fields JSONB DEFAULT '[]',
    test_endpoint TEXT,
    docs_url TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default templates
INSERT INTO mcp_integration_templates (id, name, description, category, required_fields, optional_fields, docs_url) VALUES
('supabase', 'Supabase', 'Database, Auth, and Storage', 'database', 
 '[{"key": "url", "label": "Project URL", "type": "url", "placeholder": "https://xxx.supabase.co"},
   {"key": "anon_key", "label": "Anon/Public Key", "type": "secret", "placeholder": "eyJ..."},
   {"key": "service_role_key", "label": "Service Role Key", "type": "secret", "placeholder": "eyJ..."}]',
 '[]', 'https://supabase.com/docs'),

('resend', 'Resend', 'Email API for developers', 'email',
 '[{"key": "api_key", "label": "API Key", "type": "secret", "placeholder": "re_..."}]',
 '[{"key": "from_email", "label": "Default From Email", "type": "email", "placeholder": "hello@yourdomain.com"}]',
 'https://resend.com/docs'),

('slack', 'Slack', 'Team messaging and notifications', 'communication',
 '[{"key": "webhook_url", "label": "Webhook URL", "type": "url", "placeholder": "https://hooks.slack.com/..."}]',
 '[{"key": "bot_token", "label": "Bot Token (optional)", "type": "secret", "placeholder": "xoxb-..."}]',
 'https://api.slack.com/docs'),

('notion', 'Notion', 'Workspace and documentation', 'productivity',
 '[{"key": "api_key", "label": "Integration Token", "type": "secret", "placeholder": "secret_..."}]',
 '[]', 'https://developers.notion.com'),

('airtable', 'Airtable', 'Spreadsheet database', 'database',
 '[{"key": "api_key", "label": "API Key", "type": "secret", "placeholder": "pat..."},
   {"key": "base_id", "label": "Base ID", "type": "text", "placeholder": "app..."}]',
 '[]', 'https://airtable.com/developers/web/api'),

('hubspot', 'HubSpot', 'CRM and marketing', 'crm',
 '[{"key": "api_key", "label": "Private App Token", "type": "secret", "placeholder": "pat-..."}]',
 '[]', 'https://developers.hubspot.com'),

('stripe', 'Stripe', 'Payments and billing', 'payments',
 '[{"key": "secret_key", "label": "Secret Key", "type": "secret", "placeholder": "sk_..."}]',
 '[{"key": "webhook_secret", "label": "Webhook Secret", "type": "secret", "placeholder": "whsec_..."}]',
 'https://stripe.com/docs/api'),

('openai', 'OpenAI', 'AI models and APIs', 'ai',
 '[{"key": "api_key", "label": "API Key", "type": "secret", "placeholder": "sk-..."}]',
 '[{"key": "org_id", "label": "Organization ID", "type": "text", "placeholder": "org-..."}]',
 'https://platform.openai.com/docs'),

('custom', 'Custom Integration', 'Configure any API manually', 'other',
 '[{"key": "base_url", "label": "Base URL", "type": "url", "placeholder": "https://api.example.com"}]',
 '[{"key": "api_key", "label": "API Key", "type": "secret"},
   {"key": "headers", "label": "Custom Headers (JSON)", "type": "json"}]',
 NULL)
ON CONFLICT (id) DO NOTHING;

-- =============================================================================
-- User MCP Integrations Table
-- Per-user integration configurations (encrypted)
-- =============================================================================
CREATE TABLE IF NOT EXISTS user_mcp_integrations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id TEXT NOT NULL,
    integration_type TEXT NOT NULL,
    display_name TEXT,
    config_encrypted TEXT NOT NULL,  -- AES-256 encrypted JSON
    is_active BOOLEAN DEFAULT FALSE,
    last_tested_at TIMESTAMPTZ,
    test_status TEXT CHECK (test_status IN ('success', 'failed', 'pending', NULL)),
    test_error TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, integration_type, display_name)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_user_mcp_integrations_user_id ON user_mcp_integrations(user_id);
CREATE INDEX IF NOT EXISTS idx_user_mcp_integrations_type ON user_mcp_integrations(integration_type);
CREATE INDEX IF NOT EXISTS idx_user_mcp_integrations_active ON user_mcp_integrations(is_active) WHERE is_active = TRUE;

-- RLS Policy
ALTER TABLE user_mcp_integrations ENABLE ROW LEVEL SECURITY;

CREATE POLICY user_mcp_integrations_policy ON user_mcp_integrations
    FOR ALL
    USING (auth.uid()::text = user_id);

-- Trigger for updated_at
DROP TRIGGER IF EXISTS update_user_mcp_integrations_updated_at ON user_mcp_integrations;
CREATE TRIGGER update_user_mcp_integrations_updated_at
    BEFORE UPDATE ON user_mcp_integrations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Comments
COMMENT ON TABLE mcp_integration_templates IS 'Pre-configured templates for common integrations';
COMMENT ON TABLE user_mcp_integrations IS 'Per-user encrypted MCP integration configurations';
