-- Composite index for VaultInterface image/video tabs.
-- Without this, queries of the shape
--   SELECT * FROM media_assets
--   WHERE user_id = $1 AND file_type LIKE 'image/%'
--   ORDER BY created_at DESC
-- could only use idx_media_assets_user (created in 0036), then filtered
-- file_type and sorted in memory — slow for users with large libraries
-- and the cause of the Knowledge Vault refresh hang reported 2026-05-06.
--
-- The composite index lets Postgres satisfy the WHERE + ORDER BY directly.

CREATE INDEX IF NOT EXISTS idx_media_assets_user_filetype_created
    ON media_assets (user_id, file_type, created_at DESC);
