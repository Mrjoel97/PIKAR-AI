-- Migration: 0029_consolidate_landing_pages_policies.sql
-- Description: Consolidates landing_pages policies to avoid multiple permissive policies
--              for the same role/action combination.
--
-- Problem: The table has:
--   1. "Public read access for landing_pages" - SELECT for public (anyone)
--   2. "landing_pages_user_policy" - ALL for authenticated (including SELECT)
--
-- This means authenticated users have TWO policies evaluated for SELECT.
-- Solution: Split the user policy into INSERT, UPDATE, DELETE only.

-- Drop the existing ALL policy
DROP POLICY IF EXISTS "landing_pages_user_policy" ON public.landing_pages;

-- Create separate policies for INSERT, UPDATE, DELETE (not SELECT)
CREATE POLICY "Users can insert their own landing_pages" ON public.landing_pages
    FOR INSERT TO authenticated
    WITH CHECK (user_id = (SELECT auth.uid()));

CREATE POLICY "Users can update their own landing_pages" ON public.landing_pages
    FOR UPDATE TO authenticated
    USING (user_id = (SELECT auth.uid()))
    WITH CHECK (user_id = (SELECT auth.uid()));

CREATE POLICY "Users can delete their own landing_pages" ON public.landing_pages
    FOR DELETE TO authenticated
    USING (user_id = (SELECT auth.uid()));

-- The public SELECT policy remains unchanged - it allows anyone to read all landing pages
