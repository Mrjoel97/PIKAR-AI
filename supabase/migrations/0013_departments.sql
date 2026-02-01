-- Create departments table
CREATE TABLE IF NOT EXISTS public.departments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    type TEXT NOT NULL, -- 'SALES', 'HR', etc.
    status TEXT NOT NULL DEFAULT 'PAUSED' CHECK (status IN ('RUNNING', 'PAUSED', 'ERROR')),
    state JSONB NOT NULL DEFAULT '{}'::jsonb, -- Internal memory of the department
    config JSONB NOT NULL DEFAULT '{}'::jsonb, -- User settings (goals, targets)
    last_heartbeat TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Enable RLS
ALTER TABLE public.departments ENABLE ROW LEVEL SECURITY;

-- Policy: Public read (for Org Chart etc)
CREATE POLICY "Public read access for departments"
ON public.departments
FOR SELECT
USING (true);

-- Policy: Service role full access
-- (implicit)

-- Seed Data: Create a Sales Department
INSERT INTO public.departments (name, type, status, config)
VALUES (
    'Sales Force Alpha', 
    'SALES', 
    'PAUSED', 
    '{"target_industry": "Tech", "email_template": "intro_v1"}'::jsonb
) ON CONFLICT DO NOTHING;
