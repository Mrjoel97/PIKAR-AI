
import { createClient } from 'supabase';

function buildClient(supabaseUrl: string, apiKey: string) {
    return createClient(supabaseUrl, apiKey, {
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

export function createSupabaseAdminClient() {
    const supabaseUrl = Deno.env.get('SUPABASE_URL');
    const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY');

    if (!supabaseUrl || !supabaseServiceKey) {
        throw new Error('Missing Supabase environment variables');
    }

    return buildClient(supabaseUrl, supabaseServiceKey);
}

export function createSupabaseAnonClient() {
    const supabaseUrl = Deno.env.get('SUPABASE_URL');
    const supabaseAnonKey = Deno.env.get('SUPABASE_ANON_KEY');

    if (!supabaseUrl || !supabaseAnonKey) {
        throw new Error('Missing Supabase environment variables');
    }

    return buildClient(supabaseUrl, supabaseAnonKey);
}

// Backwards compatibility
export function createSupabaseClient() {
    return createSupabaseAdminClient();
}
