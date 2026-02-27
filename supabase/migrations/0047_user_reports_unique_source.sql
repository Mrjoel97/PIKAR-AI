-- One report per (user_id, source_type, source_id) for upsert on initiative updates
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_reports_user_source
  ON user_reports (user_id, source_type, source_id)
  WHERE source_id IS NOT NULL;
