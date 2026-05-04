// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.
'use client';

import { useEffect } from 'react';

import { isAbortLikeError } from '@/lib/abort';

// Patterns for "Uncaught (in promise)" rejections that originate OUTSIDE our
// app code and should be silenced because they have no functional effect:
// 1. AbortError — fetch cleanups in useEffect that didn't catch
// 2. Browser extension content scripts that returned true from
//    chrome.runtime.onMessage.addListener and closed the channel before
//    responding. Common with Grammarly, LastPass, password managers,
//    MetaMask, and ad blockers. Not actionable from our code.
const EXTENSION_NOISE_PATTERNS = [
  'message channel closed before a response was received',
  'A listener indicated an asynchronous response by returning true',
  'Extension context invalidated',
];

function isBrowserExtensionNoise(reason: unknown): boolean {
  const message = reason instanceof Error
    ? reason.message
    : typeof reason === 'string'
      ? reason
      : (reason && typeof reason === 'object' && 'message' in reason
        && typeof (reason as { message?: unknown }).message === 'string')
        ? (reason as { message: string }).message
        : '';
  if (!message) return false;
  return EXTENSION_NOISE_PATTERNS.some((pattern) => message.includes(pattern));
}

export default function AbortErrorSilencer() {
  useEffect(() => {
    const handler = (event: PromiseRejectionEvent) => {
      if (isAbortLikeError(event.reason) || isBrowserExtensionNoise(event.reason)) {
        event.preventDefault();
      }
    };
    window.addEventListener('unhandledrejection', handler);
    return () => window.removeEventListener('unhandledrejection', handler);
  }, []);

  return null;
}
