import { useState, useCallback } from 'react';
import { createClient } from '@/lib/supabase/client';

interface UploadResult {
    filename: string;
    content: string;
    summary_prompt: string;
}

export function useFileUpload() {
    const [isUploading, setIsUploading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const uploadFile = useCallback(async (file: File): Promise<UploadResult | null> => {
        setIsUploading(true);
        setError(null);

        try {
            const formData = new FormData();
            formData.append('file', file);

            const supabase = createClient();
            const { data: { session } } = await supabase.auth.getSession();
            const token = session?.access_token;

            const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

            const response = await fetch(`${API_URL}/upload`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                },
                body: formData,
            });

            if (!response.ok) {
                throw new Error(`Upload failed: ${response.statusText}`);
            }

            const data = await response.json();
            return data as UploadResult;

        } catch (err) {
            console.error('File upload error:', err);
            setError(err instanceof Error ? err.message : 'Unknown upload error');
            return null;
        } finally {
            setIsUploading(false);
        }
    }, []);

    return { uploadFile, isUploading, uploadError: error };
}
