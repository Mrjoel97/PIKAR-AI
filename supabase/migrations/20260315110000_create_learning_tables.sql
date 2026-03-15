-- Learning Courses table
CREATE TABLE IF NOT EXISTS learning_courses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  description TEXT,
  category TEXT NOT NULL DEFAULT 'general',
  difficulty TEXT NOT NULL DEFAULT 'beginner' CHECK (difficulty IN ('beginner', 'intermediate', 'advanced')),
  duration_minutes INTEGER NOT NULL DEFAULT 30,
  lessons_count INTEGER NOT NULL DEFAULT 1,
  thumbnail_gradient TEXT,
  is_recommended BOOLEAN NOT NULL DEFAULT false,
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Learning Progress table
CREATE TABLE IF NOT EXISTS learning_progress (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  course_id UUID NOT NULL REFERENCES learning_courses(id) ON DELETE CASCADE,
  progress_percent NUMERIC(5,2) NOT NULL DEFAULT 0 CHECK (progress_percent >= 0 AND progress_percent <= 100),
  status TEXT NOT NULL DEFAULT 'not_started' CHECK (status IN ('not_started', 'in_progress', 'completed')),
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(user_id, course_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_learning_progress_user_id ON learning_progress(user_id);
CREATE INDEX IF NOT EXISTS idx_learning_courses_category ON learning_courses(category);

-- RLS for learning_courses (readable by all authenticated users)
ALTER TABLE learning_courses ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Authenticated users can view courses"
  ON learning_courses FOR SELECT
  USING (auth.role() = 'authenticated');

-- RLS for learning_progress
ALTER TABLE learning_progress ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own progress"
  ON learning_progress FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can create own progress"
  ON learning_progress FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own progress"
  ON learning_progress FOR UPDATE
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- Auto-update updated_at for learning_progress
CREATE OR REPLACE FUNCTION update_learning_progress_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_learning_progress_updated_at
  BEFORE UPDATE ON learning_progress
  FOR EACH ROW EXECUTE FUNCTION update_learning_progress_updated_at();

-- Seed initial learning courses
INSERT INTO learning_courses (title, description, category, difficulty, duration_minutes, lessons_count, thumbnail_gradient, is_recommended, sort_order) VALUES
  ('Getting Started with Pikar-AI', 'Learn the basics of your AI executive system', 'onboarding', 'beginner', 15, 3, 'from-teal-400 to-emerald-500', true, 1),
  ('Mastering Brain Dumps', 'Turn chaotic thoughts into actionable plans', 'productivity', 'beginner', 20, 4, 'from-violet-400 to-purple-500', true, 2),
  ('Financial Dashboard Deep Dive', 'Understand invoices, revenue tracking, and forecasting', 'finance', 'intermediate', 30, 5, 'from-blue-400 to-indigo-500', false, 3),
  ('Sales Pipeline Optimization', 'Maximize your CRM and lead scoring', 'sales', 'intermediate', 25, 4, 'from-amber-400 to-orange-500', false, 4),
  ('Content Creation Workflows', 'Automate content across all platforms', 'content', 'beginner', 20, 3, 'from-pink-400 to-rose-500', true, 5),
  ('Advanced Workflow Automation', 'Build custom multi-step workflows', 'automation', 'advanced', 45, 8, 'from-slate-400 to-zinc-500', false, 6),
  ('Compliance & Risk Management', 'Keep your business compliant and secure', 'compliance', 'advanced', 35, 6, 'from-red-400 to-rose-500', false, 7);
