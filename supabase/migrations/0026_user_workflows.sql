-- Create user_workflows table
CREATE TABLE IF NOT EXISTS public.user_workflows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    workflow_name TEXT NOT NULL,
    workflow_pattern TEXT NOT NULL CHECK (workflow_pattern IN ('sequential', 'parallel', 'loop')),
    agent_ids TEXT[],
    request_pattern TEXT,
    workflow_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    usage_count INTEGER NOT NULL DEFAULT 0,
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Enforce unique workflow names per user
    UNIQUE(user_id, workflow_name)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_workflows_user_id ON public.user_workflows(user_id);
CREATE INDEX IF NOT EXISTS idx_user_workflows_pattern ON public.user_workflows(workflow_pattern);
CREATE INDEX IF NOT EXISTS idx_user_workflows_usage ON public.user_workflows(usage_count DESC);

-- Enable Row Level Security
ALTER TABLE public.user_workflows ENABLE ROW LEVEL SECURITY;

-- Create RLS policies
CREATE POLICY "Users can view their own workflows"
    ON public.user_workflows
    FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own workflows"
    ON public.user_workflows
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own workflows"
    ON public.user_workflows
    FOR UPDATE
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own workflows"
    ON public.user_workflows
    FOR DELETE
    USING (auth.uid() = user_id);

-- Create trigger for updated_at
CREATE TRIGGER update_user_workflows_updated_at
    BEFORE UPDATE ON public.user_workflows
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
