// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.
'use client';

import { useEffect } from 'react';

import { isAbortLikeError } from '@/lib/abort';

export default function AbortErrorSilencer() {
  useEffect(() => {
    const handler = (event: PromiseRejectionEvent) => {
      if (isAbortLikeError(event.reason)) {
        event.preventDefault();
      }
    };
    window.addEventListener('unhandledrejection', handler);
    return () => window.removeEventListener('unhandledrejection', handler);
  }, []);

  return null;
}
