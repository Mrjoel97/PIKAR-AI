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

    const uploadFile = useCallback(async (file: File): Promise<UploadResult | null> => {
        setIsUploading(true);
        setError(null);

        try {
            const formData = new FormData();
            formData.append('file', file);

            const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

            const headers = await getAuthHeaders();

            const response = await fetch(`${API_URL}/upload`, {
                method: 'POST',
                headers,
                body: formData,
            });

            if (!response.ok) {
                throw new Error(`Upload failed: ${response.statusText}`);
            }

            const data = await response.json();
            return data as UploadResult;

        } catch (err) {
            console.error('File upload error:', err);
            if (err instanceof TypeError && err.message.includes('Failed to fetch')) {
                setError('Upload failed: backend not reachable. Check NEXT_PUBLIC_API_URL and that the backend is running.');
            } else {
                setError(err instanceof Error ? err.message : 'Unknown upload error');
            }
            return null;
        } finally {
            setIsUploading(false);
        }
    }, [getAuthHeaders]);

    const uploadFileToVault = useCallback(async (file: File): Promise<VaultUploadResult | null> => {
        setIsUploading(true);
        setError(null);

        try {
            const formData = new FormData();
            formData.append('file', file);

            const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
            const headers = await getAuthHeaders();

            const response = await fetch(`${API_URL}/upload/to-vault`, {
                method: 'POST',
                headers,
                body: formData,
            });

            if (!response.ok) {
                const detail = await response.text().catch(() => '');
                throw new Error(detail || `Vault upload failed: ${response.statusText}`);
            }

            const data = await response.json();
            return data as VaultUploadResult;
        } catch (err) {
            console.error('Vault upload error:', err);
            if (err instanceof TypeError && err.message.includes('Failed to fetch')) {
                setError('Vault upload failed: backend not reachable. Check NEXT_PUBLIC_API_URL and that the backend is running.');
            } else {
                setError(err instanceof Error ? err.message : 'Unknown vault upload error');
            }
            return null;
        } finally {
            setIsUploading(false);
        }
    }, [getAuthHeaders]);

    return { uploadFile, uploadFileToVault, isUploading, uploadError: error };
}
