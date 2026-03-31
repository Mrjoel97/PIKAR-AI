-- Optimize users_profile RLS policies to use subquery form of auth.uid().
-- The (SELECT auth.uid()) pattern is evaluated once per statement instead of
-- once per row, which is the Supabase-recommended approach for high-traffic tables.

DROP POLICY IF EXISTS "Users can view their own profile" ON users_profile;
DROP POLICY IF EXISTS "Users can update their own profile" ON users_profile;
DROP POLICY IF EXISTS "Users can insert their own profile" ON users_profile;

CREATE POLICY "Users can view their own profile" ON users_profile
    FOR SELECT
    USING ((SELECT auth.uid()) = user_id);

CREATE POLICY "Users can update their own profile" ON users_profile
    FOR UPDATE
    USING ((SELECT auth.uid()) = user_id)
    WITH CHECK ((SELECT auth.uid()) = user_id);

CREATE POLICY "Users can insert their own profile" ON users_profile
    FOR INSERT
    WITH CHECK ((SELECT auth.uid()) = user_id);
