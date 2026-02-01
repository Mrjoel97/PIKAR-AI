import { createClient } from '@/lib/supabase/client';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

type FetchOptions = RequestInit & {
  // Add any custom options here if needed
};

export async function fetchWithAuth(endpoint: string, options: FetchOptions = {}): Promise<Response> {
  const supabase = createClient();
  const { data: { session } } = await supabase.auth.getSession();

  const headers = new Headers(options.headers);

  if (session?.access_token) {
    headers.set('Authorization', `Bearer ${session.access_token}`);
  }

  // Ensure JSON content type if body is present and not FormData
  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const url = `${API_BASE_URL}${endpoint.startsWith('/') ? endpoint : `/${endpoint}`}`;

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (!response.ok) {
        // Attempt to parse error message from JSON, fallback to status text
        let errorMessage = response.statusText || 'API Request Failed';
        try {
            const errorData = await response.json();
            if (errorData && typeof errorData === 'object' && 'detail' in errorData) {
                 errorMessage = JSON.stringify(errorData.detail);
            } else if (errorData && typeof errorData === 'object' && 'message' in errorData) {
                errorMessage = errorData.message;
            }
        } catch (e) {
            // response was not JSON
        }
        
        throw new Error(`API Error ${response.status}: ${errorMessage}`);
    }

    return response;
  } catch (error) {
    console.error('Fetch error:', error);
    throw error;
  }
}
