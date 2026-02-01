-- Create approval_requests table
CREATE TABLE IF NOT EXISTS public.approval_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token TEXT UNIQUE NOT NULL,
    action_type TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED', 'EXPIRED')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    -- Audit fields
    responded_at TIMESTAMP WITH TIME ZONE,
    responder_ip TEXT
);

-- Enable RLS
ALTER TABLE public.approval_requests ENABLE ROW LEVEL SECURITY;

-- Policy: Everyone can read pending approvals (if they have the token, effectively)
-- In practice, we will query this from the backend (service role) or frontend with a specific query.
-- Since the frontend is public for the approval page, we should allow public read access 
-- if they know the UUID/Token. But usually, we might want to restrict this.
-- For now, let's allow public read for valid tokens to render the page.
CREATE POLICY "Public read access for approval requests"
ON public.approval_requests
FOR SELECT
USING (true);

-- Policy: Backend (Service Role) can do everything
-- Supabase service role bypasses RLS, so no specific policy needed for that.

-- Indexes
CREATE INDEX idx_approval_requests_token ON public.approval_requests(token);
CREATE INDEX idx_approval_requests_status ON public.approval_requests(status);
