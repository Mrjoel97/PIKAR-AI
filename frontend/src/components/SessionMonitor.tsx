'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import { useSessionMonitor } from '@/hooks/useSessionMonitor';

/**
 * Invisible component that monitors session health.
 * Mount once in the root layout — it handles idle timeout
 * and expired session detection, forcing re-login when needed.
 */
export default function SessionMonitor() {
  useSessionMonitor();
  return null;
}
