-- Fix: Prevent anonymous users from spoofing user_id in page_analytics
-- The original anon insert policy used WITH CHECK (true), allowing anon users
-- to insert rows with arbitrary user_id values. This restricts anon inserts
-- to rows where user_id IS NULL.

-- Step 1: Allow NULL user_id for anonymous tracking events
ALTER TABLE public.page_analytics ALTER COLUMN user_id DROP NOT NULL;

-- Step 2: Replace the overly-permissive anon insert policy
DROP POLICY IF EXISTS "page_analytics_insert_anon" ON public.page_analytics;

CREATE POLICY "page_analytics_insert_anon"
ON public.page_analytics FOR INSERT
TO anon
WITH CHECK (user_id IS NULL);
