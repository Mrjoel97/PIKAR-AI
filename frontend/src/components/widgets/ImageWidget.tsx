'use client';

import React, { useState, useEffect } from 'react';
import { WidgetProps } from './WidgetRegistry';
import { createClient } from '@/lib/supabase/client';

const PLACEHOLDER_URL = '[stored in knowledge vault]';

function isValidImageUrl(url: string): boolean {
  return typeof url === 'string' && url.length > 0 && url !== PLACEHOLDER_URL && (url.startsWith('http') || url.startsWith('data:'));
}

export interface ImageWidgetData {
  imageUrl: string;
  prompt?: string;
  asset_id?: string;
  caption?: string;
}

export default function ImageWidget({ definition }: WidgetProps) {
  const data = (definition.data as unknown) as ImageWidgetData;
  const originalUrl = data?.imageUrl;
  const caption = data?.caption || data?.prompt || 'Generated image';

  const [currentUrl, setCurrentUrl] = useState(originalUrl);
  const [loadError, setLoadError] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Sync state when prop changes
  useEffect(() => {
    setCurrentUrl(originalUrl);
    setLoadError(false);
  }, [originalUrl, data?.asset_id]);

  // Effect to refresh URL if it's a placeholder or if it failed to load
  useEffect(() => {
    // If the URL is explicitly the placeholder, or if we hit a load error, we try to refresh.
    // We only try if we have an asset_id.
    const needsRefresh = (currentUrl === PLACEHOLDER_URL || loadError) && !isRefreshing && data?.asset_id;

    if (needsRefresh) {
      const refreshUrl = async () => {
        setIsRefreshing(true);
        try {
          const supabase = createClient();

          // 1. Get the latest file_path from media_assets table
          //    The URL might be expired, but the path in DB is source of truth.
          const { data: assetData, error: assetError } = await supabase
            .from('media_assets')
            .select('file_path')
            .eq('id', data.asset_id)
            .single();

          if (assetError || !assetData?.file_path) {
            console.error('Failed to find media asset:', assetError);
            return;
          }

          // 2. Generate a new signed URL
          const { data: signData, error: signError } = await supabase
            .storage
            .from('knowledge-vault')
            .createSignedUrl(assetData.file_path, 3600); // 1 hour validity

          if (signError || !signData?.signedUrl) {
            console.error('Failed to sign URL:', signError);
            return;
          }

          // 3. Update state
          setCurrentUrl(signData.signedUrl);
          setLoadError(false); // Reset error state since we have a new URL to try
        } catch (err) {
          console.error('Error refreshing image URL:', err);
        } finally {
          setIsRefreshing(false);
        }
      };

      refreshUrl();
    }
  }, [currentUrl, loadError, data?.asset_id, isRefreshing]);

  // If we are actively refreshing, show a loading state
  if (isRefreshing) {
    return (
      <div className="p-4 text-sm text-blue-600 dark:text-blue-400 rounded-lg bg-blue-50 dark:bg-blue-900/20 animate-pulse">
        Refreshing secure image link...
      </div>
    );
  }

  if (!currentUrl || !isValidImageUrl(currentUrl)) {
    return (
      <div className="p-4 text-sm text-amber-600 dark:text-amber-400 rounded-lg bg-amber-50 dark:bg-amber-900/20">
        Image is loading or unavailable. If you just refreshed, it may appear shortly.
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="p-4 text-sm text-amber-600 dark:text-amber-400 rounded-lg bg-amber-50 dark:bg-amber-900/20">
        Image could not be loaded. It may have expired or was removed.
      </div>
    );
  }

  return (
    <div className="p-4">
      <div className="relative rounded-lg overflow-hidden bg-slate-100 dark:bg-slate-900">
        <img
          src={currentUrl}
          alt={caption}
          className="w-full h-auto max-h-[70vh] object-contain"
          crossOrigin={currentUrl.startsWith('data:') ? undefined : 'anonymous'}
          onError={() => setLoadError(true)}
        />
      </div>
      {caption && (
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-400 line-clamp-2">
          {caption}
        </p>
      )}
    </div>
  );
}
