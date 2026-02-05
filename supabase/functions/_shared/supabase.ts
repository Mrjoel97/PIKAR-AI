
import { createClient } from 'supabase';

export function createSupabaseClient() {
    const supabaseUrl = Deno.env.get('SUPABASE_URL');
    const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY');

    if (!supabaseUrl || !supabaseServiceKey) {
        throw new Error('Missing Supabase environment variables');
    }

    return createClient(supabaseUrl, supabaseServiceKey, {
        auth: {
            persistSession: false,
        },
        global: {
            headers: {
                'X-Client-Info': 'supabase-edge-functions',
            },
            fetch: (input, init) => {
                // Add timeout to fetch
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 60000); // 60s timeout

                return fetch(input, {
                    ...init,
                    signal: controller.signal,
                }).finally(() => clearTimeout(timeoutId));
            }
        },
    });
}
