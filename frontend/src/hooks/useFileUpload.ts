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

        const controller = new AbortController();
        const timeout = setTimeout(
            () => controller.abort(`Upload timed out after ${UPLOAD_TIMEOUT_MS / 1000}s`),
            UPLOAD_TIMEOUT_MS,
        );

        try {
            const formData = new FormData();
            formData.append('file', file);

            const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

            const headers = await getAuthHeaders();

            const response = await fetch(`${API_URL}/upload`, {
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
            console.error('File upload error:', err);
            const message = classifyUploadError(err, 'file');
            setError(message);
            return { result: null, error: message };
        } finally {
            clearTimeout(timeout);
            setIsUploading(false);
        }
    }, [getAuthHeaders]);

    const uploadFileToVault = useCallback(async (file: File): Promise<UploadOutcome<VaultUploadResult>> => {
        setIsUploading(true);
        setError(null);

        const controller = new AbortController();
        const timeout = setTimeout(
            () => controller.abort(`Vault upload timed out after ${UPLOAD_TIMEOUT_MS / 1000}s`),
            UPLOAD_TIMEOUT_MS,
        );

        try {
            const formData = new FormData();
            formData.append('file', file);

            const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
            const headers = await getAuthHeaders();

            const response = await fetch(`${API_URL}/upload/to-vault`, {
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
            console.error('Vault upload error:', err);
            const message = classifyUploadError(err, 'vault');
            setError(message);
            return { result: null, error: message };
        } finally {
            clearTimeout(timeout);
            setIsUploading(false);
        }
    }, [getAuthHeaders]);

    return { uploadFile, uploadFileToVault, isUploading, uploadError: error };
}
