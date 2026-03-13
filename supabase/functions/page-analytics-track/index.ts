import { createSupabaseClient } from '../_shared/supabase.ts';
import { corsHeaders, handleError, logError, logInfo, parseJson } from '../_shared/utils.ts';

const trackingCorsHeaders = {
    ...corsHeaders,
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
};

const transparentGif = new Uint8Array([
    0x47, 0x49, 0x46, 0x38, 0x39, 0x61, 0x01, 0x00, 0x01, 0x00,
    0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0xff, 0xff, 0xff, 0x21,
    0xf9, 0x04, 0x01, 0x00, 0x00, 0x00, 0x00, 0x2c, 0x00, 0x00,
    0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0x02, 0x02, 0x44,
    0x01, 0x00, 0x3b,
]);

const uuidRegex =
    /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function truncate(value: unknown, maxLength: number): string | null {
    if (value == null) return null;
    const text = String(value).trim();
    if (!text) return null;
    return text.slice(0, maxLength);
}

function normalizePageId(value: unknown): string | null {
    const text = truncate(value, 64);
    return text && uuidRegex.test(text) ? text : null;
}

function createPixelResponse(): Response {
    return new Response(transparentGif, {
        status: 200,
        headers: {
            ...trackingCorsHeaders,
            'Content-Type': 'image/gif',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            Pragma: 'no-cache',
            Expires: '0',
        },
    });
}

function createJsonResponse(payload: Record<string, unknown>, status = 200): Response {
    return new Response(JSON.stringify(payload), {
        status,
        headers: {
            ...trackingCorsHeaders,
            'Content-Type': 'application/json',
        },
    });
}

function buildTrackingRecord(
    source: Record<string, unknown>,
    fallbackUserAgent: string | null,
): Record<string, unknown> {
    return {
        user_id: truncate(source.uid, 255),
        page_id: normalizePageId(source.pid),
        page_url: truncate(source.url, 500),
        event_type: truncate(source.ev, 100) || 'pageview',
        event_label: truncate(source.label, 255),
        visitor_id: truncate(source.vid, 255) || crypto.randomUUID(),
        session_id: truncate(source.sid, 255) || crypto.randomUUID(),
        referrer: truncate(source.ref, 500),
        utm_source: truncate(source.utm_source, 100),
        utm_medium: truncate(source.utm_medium, 100),
        utm_campaign: truncate(source.utm_campaign, 100),
        user_agent: truncate(source.ua, 500) || fallbackUserAgent,
        device_type: truncate(source.dt, 50),
    };
}

async function insertTrackingRecord(record: Record<string, unknown>) {
    const supabase = createSupabaseClient();
    const { error } = await supabase.from('page_analytics').insert(record);
    if (error) {
        throw new Error(error.message);
    }
}

Deno.serve(async (req) => {
    if (req.method === 'OPTIONS') {
        return new Response('ok', { headers: trackingCorsHeaders });
    }

    if (req.method === 'GET') {
        try {
            const params = Object.fromEntries(new URL(req.url).searchParams.entries());
            const uid = truncate(params.uid, 255);
            const pageUrl = truncate(params.url, 500);

            if (!uid || !pageUrl) {
                return createPixelResponse();
            }

            const record = buildTrackingRecord(
                params,
                truncate(req.headers.get('user-agent'), 500),
            );
            await insertTrackingRecord(record);
            logInfo('page-analytics-track', 'Tracked analytics pixel event', {
                user_id: record.user_id,
                page_id: record.page_id,
                event_type: record.event_type,
            });
        } catch (error) {
            logError('page-analytics-track', error);
        }

        return createPixelResponse();
    }

    if (req.method === 'POST') {
        try {
            const body = await parseJson(req);
            const uid = truncate(body.uid, 255);
            if (!uid) {
                throw new Error('Missing uid');
            }

            const record = buildTrackingRecord(
                body,
                truncate(req.headers.get('user-agent'), 500),
            );
            await insertTrackingRecord(record);
            logInfo('page-analytics-track', 'Tracked analytics event', {
                user_id: record.user_id,
                page_id: record.page_id,
                event_type: record.event_type,
            });

            return createJsonResponse({
                success: true,
                event_type: record.event_type,
            });
        } catch (error) {
            logError('page-analytics-track', error);
            return handleError(error);
        }
    }

    return createJsonResponse({ error: 'Method not allowed' }, 405);
});