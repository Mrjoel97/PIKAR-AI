-- Allow authenticated users to update their own session state (title, lastMessage)
-- so chat history can display meaningful headlines instead of only date/time.
CREATE POLICY "Users can update their own sessions"
ON public.sessions
FOR UPDATE TO authenticated
USING (user_id = (SELECT auth.uid()))
WITH CHECK (user_id = (SELECT auth.uid()));
