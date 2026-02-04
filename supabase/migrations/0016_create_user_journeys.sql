-- Migration: 0016_create_user_journeys.sql
-- Description: Create table for User Journeys (templates) mapped to personas.

CREATE TABLE user_journeys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    persona TEXT NOT NULL, -- 'solopreneur', 'startup', 'sme', 'enterprise'
    title TEXT NOT NULL,
    description TEXT,
    stages JSONB NOT NULL DEFAULT '[]', -- Array of steps/stages in the journey
    kpis JSONB DEFAULT '[]', -- Key Performance Indicators
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for performance
CREATE INDEX idx_user_journeys_persona ON user_journeys(persona);

-- RLS Policies
ALTER TABLE user_journeys ENABLE ROW LEVEL SECURITY;

-- Allow read access to all authenticated users (so they can see available journeys for their persona)
CREATE POLICY "Authenticated users can view all user journeys" ON user_journeys
    FOR SELECT
    TO authenticated
    USING (true);

-- Only allow service role (admin) to insert/update/delete (typically seeded data)
-- Policies are restrictive by default, so omitting INSERT/UPDATE/DELETE policies for 'authenticated' role prevents users from modifying these templates.
