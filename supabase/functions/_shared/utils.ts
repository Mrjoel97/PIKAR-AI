import { createSupabaseAnonClient } from './supabase.ts';

export const corsHeaders = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type, x-cron-secret, x-pikar-persona, x-user-id, user-id, accept, cache-control',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
};

const UUID_REGEX =
    /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export function handleError(error: any) {
    console.error(error);
    return new Response(JSON.stringify({ error: error.message || 'Unknown error' }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 400,
    });
}

export async function validateRequest(
    req: Request,
    requiredFields: string[] = [],
    options: { allowedMethods?: string[] } = {}
) {
    const allowedMethods = options.allowedMethods || ['POST'];
    if (!allowedMethods.includes(req.method)) {
        throw new Error('Method not allowed');
    }

    const body = await parseJson(req);
    const missingFields = requiredFields.filter(field => !body[field]);

    if (missingFields.length > 0) {
        throw new Error(`Missing required fields: ${missingFields.join(', ')}`);
    }

    return body;
}

export function assertUuid(value: string, fieldName: string) {
    if (!UUID_REGEX.test(value)) {
        throw new Error(`Invalid ${fieldName}`);
    }
}

export async function parseJson(req: Request) {
    try {
        return await req.json();
    } catch {
        throw new Error('Invalid JSON body');
    }
}

function getBearerToken(req: Request) {
    const header = req.headers.get('authorization') || req.headers.get('Authorization');
    if (!header) return null;
    const [type, token] = header.split(' ');
    if (!token || type.toLowerCase() !== 'bearer') return null;
    return token;
}

export async function requireAuth(req: Request) {
    const token = getBearerToken(req);
    if (!token) {
        throw new Error('Missing authorization token');
    }

    const serviceRoleKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY');
    if (serviceRoleKey && token === serviceRoleKey) {
        return { isServiceRole: true, user: null };
    }

    const supabase = createSupabaseAnonClient();
    const { data, error } = await supabase.auth.getUser(token);
    if (error || !data?.user) {
        throw new Error('Invalid or expired token');
    }

    return { isServiceRole: false, user: data.user };
}

export function requireServiceRole(req: Request) {
    const token = getBearerToken(req);
    const serviceRoleKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY');
    if (!token || !serviceRoleKey || token !== serviceRoleKey) {
        throw new Error('Unauthorized');
    }
    return true;
}

export function requireCronSecret(req: Request) {
    const expected = Deno.env.get('CRON_SECRET');
    if (!expected) {
        throw new Error('CRON_SECRET not configured');
    }

    const headerValue = req.headers.get('x-cron-secret');
    const urlValue = new URL(req.url).searchParams.get('cron_secret');
    const provided = headerValue || urlValue;

    if (!provided || provided !== expected) {
        throw new Error('Unauthorized');
    }

    return true;
}

export function logInfo(functionName: string, message: string, data?: any) {
    console.log(JSON.stringify({
        level: 'info',
        timestamp: new Date().toISOString(),
        function: functionName,
        message,
        data
    }));
}

export function logError(functionName: string, error: any) {
    console.error(JSON.stringify({
        level: 'error',
        timestamp: new Date().toISOString(),
        function: functionName,
        message: error.message || 'Unknown error',
        stack: error.stack
    }));
}

