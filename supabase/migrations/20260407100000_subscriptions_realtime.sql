-- Migration: 20260407100000_subscriptions_realtime.sql
-- Description: Enable Supabase Realtime postgres_changes streaming for the
-- subscriptions table so the frontend SubscriptionContext can subscribe to
-- UPDATE events and reflect Stripe webhook-driven state changes in real time.
--
-- Without this, supabase.channel(...).on('postgres_changes', ...) will not
-- deliver any events for the subscriptions table even though RLS grants
-- the user SELECT on their own row.
--
-- Why the DO block: `ALTER PUBLICATION ... ADD TABLE` raises
-- `ERROR: relation "public.subscriptions" is already member of publication "supabase_realtime"`
-- when the table is already in the publication. Wrapping the ALTER in a
-- pg_publication_tables existence check makes the migration idempotent so
-- `supabase db reset --local` can be re-run without error.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_publication_tables
        WHERE pubname = 'supabase_realtime'
          AND schemaname = 'public'
          AND tablename = 'subscriptions'
    ) THEN
        ALTER PUBLICATION supabase_realtime ADD TABLE subscriptions;
    END IF;
END $$;
