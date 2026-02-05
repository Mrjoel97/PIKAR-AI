export const corsHeaders = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
};

export function handleError(error: any) {
    console.error(error);
    return new Response(JSON.stringify({ error: error.message || 'Unknown error' }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 400,
    });
}

export async function validateRequest(req: Request, requiredFields: string[] = []) {
    if (req.method !== 'POST') {
        throw new Error('Method not allowed');
    }

    const body = await req.json();
    const missingFields = requiredFields.filter(field => !body[field]);

    if (missingFields.length > 0) {
        throw new Error(`Missing required fields: ${missingFields.join(', ')}`);
    }

    return body;
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
