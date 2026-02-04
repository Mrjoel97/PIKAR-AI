-- Seed remaining departments ensuring no duplicates by checking type
-- We already have SALES from 0013_departments.sql

-- 2. Marketing
INSERT INTO public.departments (name, type, status, config)
SELECT 'Marketing Command', 'MARKETING', 'PAUSED', '{"check_interval_mins": 60, "focus": "campaign_optimization"}'::jsonb
WHERE NOT EXISTS (SELECT 1 FROM public.departments WHERE type = 'MARKETING');

-- 3. Content
INSERT INTO public.departments (name, type, status, config)
SELECT 'Content Studio', 'CONTENT', 'PAUSED', '{"check_interval_mins": 120, "focus": "trend_monitoring"}'::jsonb
WHERE NOT EXISTS (SELECT 1 FROM public.departments WHERE type = 'CONTENT');

-- 4. Strategic Planning
INSERT INTO public.departments (name, type, status, config)
SELECT 'Strategy Office', 'STRATEGIC', 'PAUSED', '{"check_interval_mins": 240, "focus": "okr_tracking"}'::jsonb
WHERE NOT EXISTS (SELECT 1 FROM public.departments WHERE type = 'STRATEGIC');

-- 5. Data Analysis
INSERT INTO public.departments (name, type, status, config)
SELECT 'Data Intelligence', 'DATA', 'PAUSED', '{"check_interval_mins": 60, "focus": "anomaly_detection"}'::jsonb
WHERE NOT EXISTS (SELECT 1 FROM public.departments WHERE type = 'DATA');

-- 6. Financial
INSERT INTO public.departments (name, type, status, config)
SELECT 'Finance & Treasury', 'FINANCIAL', 'PAUSED', '{"check_interval_mins": 360, "focus": "cash_flow"}'::jsonb
WHERE NOT EXISTS (SELECT 1 FROM public.departments WHERE type = 'FINANCIAL');

-- 7. Customer Support
INSERT INTO public.departments (name, type, status, config)
SELECT 'Customer Experience', 'SUPPORT', 'PAUSED', '{"check_interval_mins": 30, "focus": "ticket_triage"}'::jsonb
WHERE NOT EXISTS (SELECT 1 FROM public.departments WHERE type = 'SUPPORT');

-- 8. HR & Recruitment
INSERT INTO public.departments (name, type, status, config)
SELECT 'People & Talent', 'HR', 'PAUSED', '{"check_interval_mins": 1440, "focus": "employee_sentiment"}'::jsonb
WHERE NOT EXISTS (SELECT 1 FROM public.departments WHERE type = 'HR');

-- 9. Compliance
INSERT INTO public.departments (name, type, status, config)
SELECT 'Risk & Compliance', 'COMPLIANCE', 'PAUSED', '{"check_interval_mins": 1440, "focus": "regulatory_check"}'::jsonb
WHERE NOT EXISTS (SELECT 1 FROM public.departments WHERE type = 'COMPLIANCE');

-- 10. Operations
INSERT INTO public.departments (name, type, status, config)
SELECT 'Operations Control', 'OPERATIONS', 'PAUSED', '{"check_interval_mins": 120, "focus": "efficiency_metrics"}'::jsonb
WHERE NOT EXISTS (SELECT 1 FROM public.departments WHERE type = 'OPERATIONS');
