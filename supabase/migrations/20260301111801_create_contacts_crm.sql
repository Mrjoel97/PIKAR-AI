-- ============================================================
-- Lightweight CRM: contacts table with lifecycle tracking
-- Run this migration in Supabase SQL Editor
-- ============================================================

-- Lifecycle stages for the sales pipeline
CREATE TYPE public.contact_lifecycle_stage AS ENUM (
    'lead',
    'qualified',
    'opportunity',
    'customer',
    'churned',
    'inactive'
);

-- Source tracking for how contacts were acquired
CREATE TYPE public.contact_source AS ENUM (
    'form_submission',
    'stripe_payment',
    'manual',
    'import',
    'referral',
    'social',
    'other'
);

CREATE TABLE public.contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Basic info
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    company TEXT,
    
    -- Pipeline
    lifecycle_stage public.contact_lifecycle_stage NOT NULL DEFAULT 'lead',
    source public.contact_source NOT NULL DEFAULT 'manual',
    source_detail TEXT,  -- e.g. form ID, campaign name
    
    -- Value
    estimated_value NUMERIC(12,2) DEFAULT 0,
    currency TEXT DEFAULT 'USD',
    
    -- Notes & metadata
    notes TEXT,
    tags TEXT[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_contacted_at TIMESTAMPTZ,
    converted_at TIMESTAMPTZ  -- when moved to 'customer'
);

-- Indexes
CREATE INDEX idx_contacts_user_id ON public.contacts(user_id);
CREATE INDEX idx_contacts_email ON public.contacts(email);
CREATE INDEX idx_contacts_lifecycle ON public.contacts(user_id, lifecycle_stage);
CREATE INDEX idx_contacts_source ON public.contacts(user_id, source);
CREATE INDEX idx_contacts_created ON public.contacts(user_id, created_at DESC);

-- RLS
ALTER TABLE public.contacts ENABLE ROW LEVEL SECURITY;

CREATE POLICY contacts_select ON public.contacts
    FOR SELECT TO authenticated
    USING (user_id = (SELECT auth.uid()));

CREATE POLICY contacts_insert ON public.contacts
    FOR INSERT TO authenticated
    WITH CHECK (user_id = (SELECT auth.uid()));

CREATE POLICY contacts_update ON public.contacts
    FOR UPDATE TO authenticated
    USING (user_id = (SELECT auth.uid()))
    WITH CHECK (user_id = (SELECT auth.uid()));

CREATE POLICY contacts_delete ON public.contacts
    FOR DELETE TO authenticated
    USING (user_id = (SELECT auth.uid()));

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION public.update_contacts_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_contacts_updated_at
    BEFORE UPDATE ON public.contacts
    FOR EACH ROW
    EXECUTE FUNCTION public.update_contacts_updated_at();

-- Contact activity log for tracking interactions
CREATE TABLE public.contact_activities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id UUID NOT NULL REFERENCES public.contacts(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    activity_type TEXT NOT NULL,  -- 'email_sent', 'call', 'meeting', 'note', 'stage_change'
    description TEXT,
    metadata JSONB DEFAULT '{}',
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_contact_activities_contact ON public.contact_activities(contact_id, created_at DESC);
CREATE INDEX idx_contact_activities_user ON public.contact_activities(user_id);

ALTER TABLE public.contact_activities ENABLE ROW LEVEL SECURITY;

CREATE POLICY contact_activities_select ON public.contact_activities
    FOR SELECT TO authenticated
    USING (user_id = (SELECT auth.uid()));

CREATE POLICY contact_activities_insert ON public.contact_activities
    FOR INSERT TO authenticated
    WITH CHECK (user_id = (SELECT auth.uid()));
