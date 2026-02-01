-- MCP Connector Database Schema for Pikar AI
-- This creates the required tables for the MCP connector module

-- =============================================================================
-- Audit Logs Table
-- Tracks all MCP tool invocations for compliance and debugging
-- =============================================================================
CREATE TABLE IF NOT EXISTS mcp_audit_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    tool_name TEXT NOT NULL,
    agent_name TEXT,
    user_id UUID REFERENCES auth.users(id),
    session_id TEXT,
    query_sanitized TEXT NOT NULL,
    success BOOLEAN NOT NULL,
    response_status TEXT NOT NULL,
    error_message TEXT,
    duration_ms INTEGER,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for querying by user
CREATE INDEX IF NOT EXISTS idx_mcp_audit_logs_user_id ON mcp_audit_logs(user_id);
-- Index for querying by tool
CREATE INDEX IF NOT EXISTS idx_mcp_audit_logs_tool_name ON mcp_audit_logs(tool_name);
-- Index for time-based queries
CREATE INDEX IF NOT EXISTS idx_mcp_audit_logs_timestamp ON mcp_audit_logs(timestamp DESC);

-- =============================================================================
-- Landing Pages Table
-- Stores generated landing page configurations and content
-- =============================================================================
CREATE TABLE IF NOT EXISTS landing_pages (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) NOT NULL,
    title TEXT NOT NULL,
    html_content TEXT NOT NULL,
    react_content TEXT,
    config JSONB NOT NULL DEFAULT '{}',
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'archived')),
    published_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for user's landing pages
CREATE INDEX IF NOT EXISTS idx_landing_pages_user_id ON landing_pages(user_id);
-- Index for status filtering
CREATE INDEX IF NOT EXISTS idx_landing_pages_status ON landing_pages(status);

-- RLS Policy for landing pages
ALTER TABLE landing_pages ENABLE ROW LEVEL SECURITY;

CREATE POLICY landing_pages_user_policy ON landing_pages
    FOR ALL
    USING (auth.uid() = user_id);

-- =============================================================================
-- Form Submissions Table
-- Stores form submission data from landing pages
-- =============================================================================
CREATE TABLE IF NOT EXISTS form_submissions (
    id UUID PRIMARY KEY,
    form_id TEXT NOT NULL,
    user_id UUID REFERENCES auth.users(id),
    data JSONB NOT NULL DEFAULT '{}',
    submitted_at TIMESTAMPTZ DEFAULT NOW(),
    email_sent BOOLEAN DEFAULT FALSE,
    crm_synced BOOLEAN DEFAULT FALSE,
    crm_contact_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for form queries
CREATE INDEX IF NOT EXISTS idx_form_submissions_form_id ON form_submissions(form_id);
-- Index for user queries
CREATE INDEX IF NOT EXISTS idx_form_submissions_user_id ON form_submissions(user_id);
-- Index for time-based queries
CREATE INDEX IF NOT EXISTS idx_form_submissions_submitted_at ON form_submissions(submitted_at DESC);

-- RLS Policy for form submissions (user can see submissions to their forms)
ALTER TABLE form_submissions ENABLE ROW LEVEL SECURITY;

CREATE POLICY form_submissions_user_policy ON form_submissions
    FOR ALL
    USING (
        auth.uid() = user_id 
        OR 
        form_id IN (SELECT id::text FROM landing_pages WHERE user_id = auth.uid())
    );

-- =============================================================================
-- Functions
-- =============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for landing_pages
DROP TRIGGER IF EXISTS update_landing_pages_updated_at ON landing_pages;
CREATE TRIGGER update_landing_pages_updated_at
    BEFORE UPDATE ON landing_pages
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- Comments
-- =============================================================================
COMMENT ON TABLE mcp_audit_logs IS 'Audit logs for all MCP tool invocations';
COMMENT ON TABLE landing_pages IS 'Generated landing pages with HTML and React components';
COMMENT ON TABLE form_submissions IS 'Form submissions from landing pages';

