CREATE TABLE agents (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id),
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    description TEXT,
    avatar TEXT,
    is_system BOOLEAN DEFAULT false,
    tier_required TEXT DEFAULT 'solopreneur',
    base_model TEXT DEFAULT 'gemini-1.5-pro',
    temperature DECIMAL(3,2) DEFAULT 0.7,
    system_prompt TEXT,
    enabled_tools TEXT[],
    status TEXT DEFAULT 'active',
    tasks_completed INTEGER DEFAULT 0,
    success_rate DECIMAL(5,2) DEFAULT 100.0,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE agent_knowledge (
    id UUID PRIMARY KEY,
    agent_id UUID REFERENCES agents(id),
    user_id UUID REFERENCES auth.users(id),
    source_type TEXT NOT NULL, -- 'document', 'url', 'text', 'example'
    title TEXT,
    content TEXT,
    file_path TEXT,
    is_processed BOOLEAN DEFAULT false,
    chunk_count INTEGER,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE embeddings (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id),
    source_type TEXT NOT NULL, -- 'brain_dump', 'content', 'task', 'document'
    source_id UUID NOT NULL,
    agent_id UUID REFERENCES agents(id), -- Optional, for agent-specific
    content TEXT NOT NULL,
    embedding vector(768),
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX ON embeddings USING ivfflat (embedding vector_cosine_ops);

CREATE TABLE ai_jobs (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id),
    agent_id UUID REFERENCES agents(id),
    job_type TEXT NOT NULL,
    status TEXT DEFAULT 'pending', -- pending, running, completed, failed
    input_data JSONB,
    output_data JSONB,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ
);
