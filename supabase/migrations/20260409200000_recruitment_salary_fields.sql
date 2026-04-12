-- HR-01: Add salary and seniority fields to recruitment_jobs
-- Supports job description generation with compensation benchmarking.

ALTER TABLE recruitment_jobs ADD COLUMN salary_min INTEGER;
ALTER TABLE recruitment_jobs ADD COLUMN salary_max INTEGER;
ALTER TABLE recruitment_jobs ADD COLUMN seniority_level TEXT;
ALTER TABLE recruitment_jobs ADD COLUMN responsibilities TEXT;

COMMENT ON COLUMN recruitment_jobs.salary_min IS 'Minimum salary range from compensation benchmarking';
COMMENT ON COLUMN recruitment_jobs.salary_max IS 'Maximum salary range from compensation benchmarking';
COMMENT ON COLUMN recruitment_jobs.seniority_level IS 'Job seniority: junior, mid, senior, lead, executive';
COMMENT ON COLUMN recruitment_jobs.responsibilities IS 'Structured responsibilities section of the job description';
