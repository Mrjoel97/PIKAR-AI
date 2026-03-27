// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

/**
 * In-memory sliding window rate limiter for Next.js API routes.
 *
 * Each limiter instance tracks requests per IP using a sliding window.
 * Designed for single-instance deployments; for multi-instance, swap to
 * @upstash/ratelimit with Redis.
 */

interface RateLimitEntry {
  timestamps: number[];
}

interface RateLimiterOptions {
  /** Maximum requests allowed within the window. */
  limit: number;
  /** Time window in seconds. */
  windowSeconds: number;
}

const store = new Map<string, RateLimitEntry>();

// Periodic cleanup every 5 minutes to prevent memory leaks
const CLEANUP_INTERVAL_MS = 5 * 60 * 1000;
let cleanupTimer: ReturnType<typeof setInterval> | null = null;

function ensureCleanupTimer(windowSeconds: number) {
  if (cleanupTimer) return;
  cleanupTimer = setInterval(() => {
    const now = Date.now();
    const maxAge = windowSeconds * 1000;
    for (const [key, entry] of store) {
      entry.timestamps = entry.timestamps.filter((t) => now - t < maxAge);
      if (entry.timestamps.length === 0) {
        store.delete(key);
      }
    }
  }, CLEANUP_INTERVAL_MS);
  // Allow the process to exit even if the timer is running
  if (typeof cleanupTimer === 'object' && 'unref' in cleanupTimer) {
    cleanupTimer.unref();
  }
}

export function rateLimit(options: RateLimiterOptions) {
  const { limit, windowSeconds } = options;

  ensureCleanupTimer(windowSeconds);

  return {
    /**
     * Check if the request should be allowed.
     * Returns { success: true } if under the limit, or
     * { success: false, retryAfter } if rate limited.
     */
    check(ip: string): { success: boolean; remaining: number; retryAfter?: number } {
      const now = Date.now();
      const windowMs = windowSeconds * 1000;

      let entry = store.get(ip);
      if (!entry) {
        entry = { timestamps: [] };
        store.set(ip, entry);
      }

      // Remove expired timestamps
      entry.timestamps = entry.timestamps.filter((t) => now - t < windowMs);

      if (entry.timestamps.length >= limit) {
        const oldest = entry.timestamps[0];
        const retryAfter = Math.ceil((oldest + windowMs - now) / 1000);
        return { success: false, remaining: 0, retryAfter };
      }

      entry.timestamps.push(now);
      return { success: true, remaining: limit - entry.timestamps.length };
    },
  };
}

/**
 * Pre-configured rate limiters for different route categories.
 */
export const rateLimiters = {
  /** Public endpoints (waitlist, etc.) — strict: 5 req/min per IP. */
  public: rateLimit({ limit: 5, windowSeconds: 60 }),

  /** Authenticated API routes — moderate: 30 req/min per IP. */
  authenticated: rateLimit({ limit: 30, windowSeconds: 60 }),

  /** Sensitive operations (API key saves, OAuth) — tight: 10 req/min per IP. */
  sensitive: rateLimit({ limit: 10, windowSeconds: 60 }),

  /** Cron endpoints — very strict: 2 req/min per IP. */
  cron: rateLimit({ limit: 2, windowSeconds: 60 }),

  /** Webhook endpoints — moderate: 20 req/min per IP. */
  webhook: rateLimit({ limit: 20, windowSeconds: 60 }),
};

/**
 * Extract client IP from a Next.js request.
 */
export function getClientIp(request: Request): string {
  const forwarded = request.headers.get('x-forwarded-for');
  if (forwarded) {
    return forwarded.split(',')[0].trim();
  }
  const realIp = request.headers.get('x-real-ip');
  if (realIp) {
    return realIp.trim();
  }
  return '127.0.0.1';
}
