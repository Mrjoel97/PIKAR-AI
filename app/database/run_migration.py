"""Direct SQL migration using psycopg2.

Run with: 
    uv pip install psycopg2-binary
    python app/database/run_migration.py
"""

import os
import sys

# Try to import psycopg2
try:
    import psycopg2
except ImportError:
    print("psycopg2 not installed. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary"])
    import psycopg2


MIGRATION_SQL = """
-- User Profile
CREATE TABLE IF NOT EXISTS users_profile (
    user_id VARCHAR(255) PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    business_context TEXT,
    persona VARCHAR(50) DEFAULT 'solopreneur',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User Executive Agent
CREATE TABLE IF NOT EXISTS user_executive_agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    agent_name VARCHAR(255) DEFAULT 'Executive Agent',
    configuration JSONB,
    onboarding_completed BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id)
);

-- Sessions
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    app_name VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    session_id VARCHAR(255) NOT NULL,
    state JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_sessions_app_user ON sessions(app_name, user_id);
CREATE INDEX IF NOT EXISTS ix_sessions_session_id ON sessions(session_id);

-- Session Events
CREATE TABLE IF NOT EXISTS session_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    event_index INTEGER NOT NULL,
    event_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_session_events_session ON session_events(session_id, event_index);

-- Session Version History
CREATE TABLE IF NOT EXISTS session_version_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    state_diff JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_version_history_session ON session_version_history(session_id, version);

-- Initiative Templates
CREATE TABLE IF NOT EXISTS initiative_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    phases JSONB,
    default_priority VARCHAR(20) DEFAULT 'medium',
    persona VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Initiatives
CREATE TABLE IF NOT EXISTS initiatives (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    priority VARCHAR(20) DEFAULT 'medium',
    status VARCHAR(50) DEFAULT 'active',
    phase VARCHAR(50) DEFAULT 'ideation',
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_initiatives_user ON initiatives(user_id);

-- User Journeys
CREATE TABLE IF NOT EXISTS user_journeys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    stages JSONB,
    kpis JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_user_journeys_user ON user_journeys(user_id);

-- Workflow Templates
CREATE TABLE IF NOT EXISTS workflow_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    phases JSONB,
    steps JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(name)
);

-- Workflow Executions
CREATE TABLE IF NOT EXISTS workflow_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id UUID REFERENCES workflow_templates(id) ON DELETE SET NULL,
    user_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    current_phase VARCHAR(100),
    context JSONB,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_workflow_executions_user ON workflow_executions(user_id);
CREATE INDEX IF NOT EXISTS ix_workflow_executions_template ON workflow_executions(template_id);

-- Workflow Steps
CREATE TABLE IF NOT EXISTS workflow_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id UUID NOT NULL REFERENCES workflow_executions(id) ON DELETE CASCADE,
    step_name VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    result JSONB,
    error TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_workflow_steps_execution ON workflow_steps(execution_id);

-- Approval Requests
CREATE TABLE IF NOT EXISTS approval_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    action_type VARCHAR(100) NOT NULL,
    description TEXT,
    token VARCHAR(255) NOT NULL UNIQUE,
    status VARCHAR(20) DEFAULT 'PENDING',
    metadata JSONB,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_approval_requests_user ON approval_requests(user_id);
CREATE INDEX IF NOT EXISTS ix_approval_requests_token ON approval_requests(token);

-- Vault Documents
CREATE TABLE IF NOT EXISTS vault_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    title VARCHAR(500) NOT NULL,
    content TEXT,
    source_type VARCHAR(50),
    source_url VARCHAR(1000),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_vault_documents_user ON vault_documents(user_id);

-- Embeddings
CREATE TABLE IF NOT EXISTS embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES vault_documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding JSONB NOT NULL,
    model VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_embeddings_document ON embeddings(document_id);

-- Agent Google Docs
CREATE TABLE IF NOT EXISTS agent_google_docs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    google_doc_id VARCHAR(255) NOT NULL,
    title VARCHAR(500),
    document_url VARCHAR(1000),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_agent_google_docs_user ON agent_google_docs(user_id);

-- Media Assets
CREATE TABLE IF NOT EXISTS media_assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    filename VARCHAR(500) NOT NULL,
    file_type VARCHAR(50),
    storage_path VARCHAR(1000),
    public_url VARCHAR(1000),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_media_assets_user ON media_assets(user_id);

-- Landing Pages
CREATE TABLE IF NOT EXISTS landing_pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    title VARCHAR(255) NOT NULL,
    html_content TEXT,
    react_content TEXT,
    config JSONB DEFAULT '{}',
    status VARCHAR(20) DEFAULT 'draft',
    published_url VARCHAR(1000),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_landing_pages_user ON landing_pages(user_id);
CREATE INDEX IF NOT EXISTS ix_landing_pages_status ON landing_pages(status);

-- Landing Forms
CREATE TABLE IF NOT EXISTS landing_forms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    page_id UUID NOT NULL REFERENCES landing_pages(id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    fields JSONB,
    config JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_landing_forms_page ON landing_forms(page_id);

-- Form Submissions
CREATE TABLE IF NOT EXISTS form_submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    form_id UUID NOT NULL REFERENCES landing_forms(id) ON DELETE CASCADE,
    user_id VARCHAR(255),
    data JSONB DEFAULT '{}',
    email_sent BOOLEAN DEFAULT false,
    crm_synced BOOLEAN DEFAULT false,
    crm_contact_id VARCHAR(255),
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_form_submissions_form ON form_submissions(form_id);
CREATE INDEX IF NOT EXISTS ix_form_submissions_user ON form_submissions(user_id);

-- Departments
CREATE TABLE IF NOT EXISTS departments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'IDLE',
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_departments_user ON departments(user_id);

-- Products
CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50),
    description TEXT,
    price FLOAT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_products_user ON products(user_id);

-- Inventory
CREATE TABLE IF NOT EXISTS inventory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    quantity INTEGER DEFAULT 0,
    location VARCHAR(255),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_inventory_product ON inventory(product_id);

-- Orders
CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    customer_email VARCHAR(255),
    total_amount FLOAT DEFAULT 0,
    status VARCHAR(50) DEFAULT 'pending',
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_orders_user ON orders(user_id);

-- Order Items
CREATE TABLE IF NOT EXISTS order_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    quantity INTEGER DEFAULT 1,
    unit_price FLOAT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_order_items_order ON order_items(order_id);

-- Invoices
CREATE TABLE IF NOT EXISTS invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    invoice_number VARCHAR(50) NOT NULL UNIQUE,
    amount FLOAT NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    due_date TIMESTAMP WITH TIME ZONE,
    paid_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_invoices_order ON invoices(order_id);

-- Connected Accounts
CREATE TABLE IF NOT EXISTS connected_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    provider VARCHAR(50) NOT NULL,
    provider_account_id VARCHAR(255) NOT NULL,
    access_token TEXT,
    refresh_token TEXT,
    expires_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(provider, provider_account_id)
);

CREATE INDEX IF NOT EXISTS ix_connected_accounts_user ON connected_accounts(user_id);

-- Agents
CREATE TABLE IF NOT EXISTS agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    agent_type VARCHAR(50) NOT NULL,
    configuration JSONB,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_agents_user ON agents(user_id);

-- Skills
CREATE TABLE IF NOT EXISTS skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    knowledge TEXT,
    is_global BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(name, user_id)
);

CREATE INDEX IF NOT EXISTS ix_skills_user ON skills(user_id);

-- User Configurations
CREATE TABLE IF NOT EXISTS user_configurations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    key VARCHAR(100) NOT NULL,
    value JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, key)
);

CREATE INDEX IF NOT EXISTS ix_user_configurations_user ON user_configurations(user_id);

-- User Reports
CREATE TABLE IF NOT EXISTS user_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    title VARCHAR(500) NOT NULL,
    report_type VARCHAR(100),
    content TEXT,
    file_path VARCHAR(1000),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_user_reports_user ON user_reports(user_id);

-- MCP Audit Logs
CREATE TABLE IF NOT EXISTS mcp_audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    tool_name VARCHAR(255) NOT NULL,
    agent_name VARCHAR(255),
    user_id VARCHAR(255),
    session_id VARCHAR(255),
    query_sanitized TEXT NOT NULL,
    success BOOLEAN NOT NULL,
    response_status VARCHAR(50) NOT NULL,
    error_message TEXT,
    duration_ms INTEGER,
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS ix_mcp_audit_logs_user ON mcp_audit_logs(user_id);
CREATE INDEX IF NOT EXISTS ix_mcp_audit_logs_tool ON mcp_audit_logs(tool_name);
CREATE INDEX IF NOT EXISTS ix_mcp_audit_logs_timestamp ON mcp_audit_logs(timestamp);

-- Agent Knowledge
CREATE TABLE IF NOT EXISTS agent_knowledge (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    knowledge_type VARCHAR(50) NOT NULL,
    title VARCHAR(500) NOT NULL,
    content TEXT,
    source VARCHAR(255),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_agent_knowledge_user ON agent_knowledge(user_id);
CREATE INDEX IF NOT EXISTS ix_agent_knowledge_type ON agent_knowledge(knowledge_type);

-- AI Jobs
CREATE TABLE IF NOT EXISTS ai_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR(255) NOT NULL,
    job_type VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    input_data JSONB,
    result JSONB,
    error TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_ai_jobs_user ON ai_jobs(user_id);
CREATE INDEX IF NOT EXISTS ix_ai_jobs_status ON ai_jobs(status);
"""


def main():
    import socket
    
    supabase_url = os.getenv("SUPABASE_URL")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not supabase_url or not service_key:
        print("Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
        sys.exit(1)
    
    project_ref = supabase_url.split("://")[1].split(".supabase")[0]
    
    # Try different connection methods - direct (5432) and pooler (6543)
    hosts_to_try = [
        (f"db.{project_ref}.supabase.co", 5432),
        (f"db.{project_ref}.supabase.co", 6543),
        ("db.rbdowedrdhtlbngapexj.supabase.co", 5432),
    ]
    
    conn = None
    for host, port in hosts_to_try:
        try:
            print(f"Trying connection to {host}:{port}...")
            # For direct mode, use just "postgres" as user, for pooler use "postgres.project_ref"
            conn_string = f"postgresql://postgres:{service_key}@{host}:{port}/postgres"
            conn = psycopg2.connect(conn_string)
            print(f"Connected to {host}:{port}!")
            break
        except Exception as e:
            print(f"  Failed: {e}")
            continue
    
    if conn is None:
        print("\nCould not connect to Supabase. Please run SQL manually in Supabase SQL Editor:")
        print("1. Go to Supabase Dashboard > SQL Editor")
        print("2. Copy the SQL from app/database/run_migration.py")
        sys.exit(1)
    
    cursor = conn.cursor()
    print("Executing migration SQL...")
    cursor.execute(MIGRATION_SQL)
    conn.commit()
    cursor.close()
    conn.close()
    
    print("Migration completed successfully!")


if __name__ == "__main__":
    main()
