
import { createSupabaseClient } from '../_shared/supabase.ts';
import { handleError, logInfo, logError, corsHeaders } from '../_shared/utils.ts';

Deno.serve(async (req) => {
    // Allow manual invocation via GET or POST
    if (req.method === 'OPTIONS') {
        return new Response('ok', { headers: corsHeaders });
    }

    try {
        const supabase = createSupabaseClient();
        logInfo('cleanup-sessions', 'Starting session cleanup');

        // 30 days ago
        const cutoffDate = new Date();
        cutoffDate.setDate(cutoffDate.getDate() - 30);
        const cutoffIso = cutoffDate.toISOString();

        // Find old sessions
        const { data: sessions, error: fetchError } = await supabase
            .from('sessions')
            .select('session_id')
            .lt('updated_at', cutoffIso)
            .limit(100);

        if (fetchError) throw fetchError;

        if (!sessions || sessions.length === 0) {
            logInfo('cleanup-sessions', 'No sessions needed cleanup');
            return new Response(JSON.stringify({ message: 'No sessions found to cleanup', count: 0 }), {
                headers: { ...corsHeaders, 'Content-Type': 'application/json' },
                status: 200,
            });
        }

        const sessionIds = sessions.map(s => s.session_id);

        // Delete them (cascade should handle related data if configured, otherwise we delete related first)
        // Assuming cascade delete is set up in DB schema for session_events
        const { error: deleteError } = await supabase
            .from('sessions')
            .delete()
            .in('session_id', sessionIds);

        if (deleteError) throw deleteError;

        logInfo('cleanup-sessions', `Deleted ${sessions.length} sessions`);

        return new Response(JSON.stringify({
            success: true,
            message: `Cleanup complete`,
            sessions_deleted: sessions.length
        }), {
            headers: { ...corsHeaders, 'Content-Type': 'application/json' },
            status: 200,
        });

    } catch (error) {
        logError('cleanup-sessions', error);
        return handleError(error);
    }
});
