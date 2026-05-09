-- Phase 104 (POST-06): Twitter OAuth2 scope expanded to include media.write.
-- Existing tokens were issued without that scope and cannot upload media via
-- the v2 /2/media/upload endpoint (v1.1 upload.twitter.com was sunset
-- 2025-06-09). Mark all existing twitter rows for re-authorization. The
-- frontend already treats non-active status as "Click to connect" /
-- "Reconnect", so no UI change is required for this hop.
--
-- Idempotent: only flips rows currently active. Does NOT touch rows that
-- the user has already manually revoked.
UPDATE connected_accounts
SET status = 'reconnect_required'
WHERE platform = 'twitter'
  AND status = 'active';

COMMENT ON COLUMN connected_accounts.status IS
  'One of: active, revoked, reconnect_required. Phase 104 added '
  'reconnect_required to flag accounts whose token scope is stale.';
