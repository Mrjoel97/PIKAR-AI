// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { useState, useCallback } from 'react';
import { createClient } from '@/lib/supabase/client';

interface UploadResult {
    filename: string;
    content: string;
    summary_prompt: string;
}

interface VaultUploadResult {
    success: boolean;
    document_id?: string | null;
    filename: string;
    file_path: string;
    processed: boolean;
    embedding_count: number;
    message: string;
}

// Upload paths can take a while for larger documents (PDF/DOCX text
// extraction on the backend). Browser fetch has no default timeout, so
// without our own controller the request can hang or be cancelled by the
// browser/proxy with the opaque "signal is aborted without reason"
// message. 90s is generous but still surfaces a real timeout instead of
// hanging indefinitely.
const UPLOAD_TIMEOUT_MS = 90_000;
const UPLOAD_MAX_ATTEMPTS = 4;
const UPLOAD_RETRY_BACKOFF_MS = [0, 1500, 3500, 7000]; // wait before attempts 1..4

/**
 * Route uploads through the Next.js server (Vercel function) by default
 * instead of browser → Cloud Run direct. The Next.js proxy lives in
 * /api/upload/* and forwards the multipart body to BACKEND_URL using the
 * caller's bearer token. This removes the direct browser-to-Cloud-Run
 * fetch that has been getting cancelled by some upstream layer (CDN,
 * proxy, browser navigation cleanup) with the opaque "signal is aborted
 * without reason" message. The proxy runs server-side on Vercel where
 * those cancellations don't apply.
 *
 * Set NEXT_PUBLIC_DIRECT_UPLOAD=true to force the legacy direct path
 * (e.g., for local development against an http://localhost:8000 backend
 * that doesn't have a Vercel deploy in front of it).
 */
function getUploadBaseUrl(): string {
    const useDirect = process.env.NEXT_PUBLIC_DIRECT_UPLOAD === 'true';
    if (useDirect) {
        return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    }
    // Same-origin proxy — relative URL means the request goes to the
    // Next.js server that served this page, no CORS preflight, no
    // browser-direct Cloud Run path.
    return '';
}

interface UploadOutcome<T> {
    result: T | null;
    error: string | null;
}

function classifyUploadError(err: unknown, kind: 'file' | 'vault' | 'smart'): string {
    if (err instanceof DOMException && err.name === 'AbortError') {
        return `${kind === 'vault' ? 'Vault upload' : kind === 'smart' ? 'Smart upload' : 'Upload'} was cancelled (likely a network/proxy timeout or page navigation). Try again, and if it keeps happening reduce the file size or check your network.`;
    }
    if (err instanceof TypeError && err.message.includes('Failed to fetch')) {
        return `${kind === 'vault' ? 'Vault upload' : kind === 'smart' ? 'Smart upload' : 'Upload'} failed: backend not reachable. Check NEXT_PUBLIC_API_URL and that the backend is running.`;
    }
    if (err instanceof Error) {
        return err.message;
    }
    return `Unknown ${kind} upload error`;
}

/**
 * Detect aborts that did NOT originate from our own timeout. When several
 * in-flight fetches all abort with "signal is aborted without reason" at
 * the same time, the trigger is upstream (route change, React tree
 * unmount, auth-failure forced navigation, browser tab suspend). We retry
 * once because our local fetch was perfectly healthy and a one-off
 * external cancel shouldn't fail the user's upload.
 */
function isExternalAbort(err: unknown, ourTimeoutReason: string): boolean {
    if (!(err instanceof DOMException) || err.name !== 'AbortError') return false;
    // If our setTimeout fired, the controller was aborted with our reason.
    // If the abort came from somewhere else, the reason is undefined or a
    // different string.
    const reason = (err as DOMException & { reason?: unknown }).reason;
    if (typeof reason === 'string' && reason === ourTimeoutReason) return false;
    return true;
}

export function useFileUpload() {
    const [isUploading, setIsUploading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const getAuthHeaders = useCallback(async (): Promise<HeadersInit> => {
        const supabase = createClient();
        const { data: { session } } = await supabase.auth.getSession();
        const token = session?.access_token;

        const headers: HeadersInit = {};
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        return headers;
    }, []);

    // Return both the result and any error directly to the caller. Callers
    // that read `uploadError` from this hook's state see a STALE value
    // because React state updates aren't visible synchronously after the
    // promise resolves — that bug is what caused chat attachment failures
    // to show a generic "backend rejected the file" message instead of
    // the actual reason. Per-call return is the source of truth.
    const uploadFile = useCallback(async (file: File): Promise<UploadOutcome<UploadResult>> => {
        setIsUploading(true);
        setError(null);

        const baseUrl = getUploadBaseUrl();
        let lastError: unknown = null;

        try {
            for (let attempt = 1; attempt <= UPLOAD_MAX_ATTEMPTS; attempt++) {
                const backoffMs = UPLOAD_RETRY_BACKOFF_MS[attempt - 1] ?? 0;
                if (backoffMs > 0) {
                    await new Promise((r) => setTimeout(r, backoffMs));
                }
                const ourReason = `Upload timed out after ${UPLOAD_TIMEOUT_MS / 1000}s`;
                const controller = new AbortController();
                const timeout = setTimeout(() => controller.abort(ourReason), UPLOAD_TIMEOUT_MS);

                try {
                    const formData = new FormData();
                    formData.append('file', file);
                    const headers = await getAuthHeaders();

                    const response = await fetch(`${baseUrl}/api/upload`, {
                        method: 'POST',
                        headers,
                        body: formData,
                        signal: controller.signal,
                    });

                    if (!response.ok) {
                        const detail = await response.text().catch(() => '');
                        throw new Error(detail || `Upload failed: ${response.status} ${response.statusText}`);
                    }

                    const data = await response.json();
                    return { result: data as UploadResult, error: null };
                } catch (err) {
                    lastError = err;
                    if (attempt < UPLOAD_MAX_ATTEMPTS && isExternalAbort(err, ourReason)) {
                        console.warn(`File upload externally aborted on attempt ${attempt}/${UPLOAD_MAX_ATTEMPTS}, retrying after ${UPLOAD_RETRY_BACKOFF_MS[attempt] ?? 0}ms.`);
                        continue;
                    }
                    throw err;
                } finally {
                    clearTimeout(timeout);
                }
            }
            throw lastError ?? new Error('Upload failed');
        } catch (err) {
            console.error('File upload error:', err);
            const message = classifyUploadError(err, 'file');
            setError(message);
            return { result: null, error: message };
        } finally {
            setIsUploading(false);
        }
    }, [getAuthHeaders]);

    const uploadFileToVault = useCallback(async (file: File): Promise<UploadOutcome<VaultUploadResult>> => {
        setIsUploading(true);
        setError(null);

        const baseUrl = getUploadBaseUrl();
        let lastError: unknown = null;

        try {
            for (let attempt = 1; attempt <= UPLOAD_MAX_ATTEMPTS; attempt++) {
                const backoffMs = UPLOAD_RETRY_BACKOFF_MS[attempt - 1] ?? 0;
                if (backoffMs > 0) {
                    await new Promise((r) => setTimeout(r, backoffMs));
                }
                const ourReason = `Vault upload timed out after ${UPLOAD_TIMEOUT_MS / 1000}s`;
                const controller = new AbortController();
                const timeout = setTimeout(() => controller.abort(ourReason), UPLOAD_TIMEOUT_MS);

                try {
                    const formData = new FormData();
                    formData.append('file', file);
                    const headers = await getAuthHeaders();

                    const response = await fetch(`${baseUrl}/api/upload/to-vault`, {
                        method: 'POST',
                        headers,
                        body: formData,
                        signal: controller.signal,
                    });

                    if (!response.ok) {
                        const detail = await response.text().catch(() => '');
                        throw new Error(detail || `Vault upload failed: ${response.status} ${response.statusText}`);
                    }

                    const data = await response.json();
                    return { result: data as VaultUploadResult, error: null };
                } catch (err) {
                    lastError = err;
                    if (attempt < UPLOAD_MAX_ATTEMPTS && isExternalAbort(err, ourReason)) {
                        console.warn(`Vault upload externally aborted on attempt ${attempt}/${UPLOAD_MAX_ATTEMPTS}, retrying after ${UPLOAD_RETRY_BACKOFF_MS[attempt] ?? 0}ms.`);
                        continue;
                    }
                    throw err;
                } finally {
                    clearTimeout(timeout);
                }
            }
            throw lastError ?? new Error('Vault upload failed');
        } catch (err) {
            console.error('Vault upload error:', err);
            const message = classifyUploadError(err, 'vault');
            setError(message);
            return { result: null, error: message };
        } finally {
            setIsUploading(false);
        }
    }, [getAuthHeaders]);

    return { uploadFile, uploadFileToVault, isUploading, uploadError: error };
}
