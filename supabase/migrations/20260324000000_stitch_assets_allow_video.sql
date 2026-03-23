-- Add video/mp4 to stitch-assets bucket allowed MIME types.
-- Required for Remotion walkthrough video uploads (Phase 22, OUTP-04).
UPDATE storage.buckets
SET allowed_mime_types = array_cat(
    allowed_mime_types,
    ARRAY['video/mp4']::text[]
)
WHERE id = 'stitch-assets'
  AND NOT ('video/mp4' = ANY(allowed_mime_types));
