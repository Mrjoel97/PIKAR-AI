-- Team Organization Structure
-- Stores human team members with reporting relationships for org chart visualization.
-- Separate from the AI agent org chart (app/routers/org.py) which shows agent hierarchy.

CREATE TABLE team_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    name TEXT NOT NULL,
    email TEXT,
    position TEXT NOT NULL,
    department TEXT,
    reports_to UUID REFERENCES team_members(id),
    hire_date DATE DEFAULT CURRENT_DATE,
    status TEXT DEFAULT 'active',
    candidate_id UUID REFERENCES recruitment_candidates(id),
    job_id UUID REFERENCES recruitment_jobs(id),
    created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE team_members ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can CRUD their own team members" ON team_members
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE INDEX idx_team_members_user_id ON team_members(user_id);
CREATE INDEX idx_team_members_reports_to ON team_members(reports_to);
CREATE INDEX idx_team_members_department ON team_members(department);
