'use client';

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
