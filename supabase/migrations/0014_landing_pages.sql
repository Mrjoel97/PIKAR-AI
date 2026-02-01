-- Create landing_pages table
CREATE TABLE IF NOT EXISTS public.landing_pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    title TEXT NOT NULL,
    html_content TEXT,
    react_content TEXT,
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    campaign_id UUID, -- For future linking
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Enable RLS
ALTER TABLE public.landing_pages ENABLE ROW LEVEL SECURITY;

-- Policy: Public read (so public can view pages)
CREATE POLICY "Public read access for landing_pages"
ON public.landing_pages
FOR SELECT
USING (true);

-- Policy: Authenticated users can create/update
CREATE POLICY "Authenticated users can insert landing_pages"
ON public.landing_pages
FOR INSERT
WITH CHECK (auth.role() = 'authenticated');

CREATE POLICY "Authenticated users can update their own landing_pages"
ON public.landing_pages
FOR UPDATE
USING (auth.uid() = user_id);
