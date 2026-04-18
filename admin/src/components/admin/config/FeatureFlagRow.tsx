'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import { useState } from 'react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/** Props for FeatureFlagRow */
export interface FeatureFlagRowProps {
  /** The flag key identifier (e.g. "workflow_kill_switch") */
  flagKey: string;
  /** Current enabled state of the flag */
  isEnabled: boolean;
  /** Human-readable description from the API (may be null) */
  description: string | null;
  /** Supabase access_token for Authorization header */
  token: string;
  /** Called with the flag key and new enabled state after a successful toggle */
  onToggle: (key: string, enabled: boolean) => void;
}

/**
 * Converts a snake_case flag key into a human-readable label.
 * E.g. "workflow_kill_switch" → "Workflow Kill Switch"
 */
function formatFlagKey(key: string): string {
  return key
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

/**
 * FeatureFlagRow renders a single row for a feature flag with a toggle switch.
 *
 * Toggle sends PUT /admin/config/flags/{flagKey} and calls onToggle on success.
 * Shows a brief note that changes take effect within 60 seconds.
 */
export function FeatureFlagRow({
  flagKey,
  isEnabled,
  description,
  token,
  onToggle,
}: FeatureFlagRowProps) {
  const [isToggling, setIsToggling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleToggle = async () => {
    const newValue = !isEnabled;
    setIsToggling(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/admin/config/flags/${flagKey}`, {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ is_enabled: newValue }),
      });

      if (!res.ok) {
        setError(`Toggle failed (${res.status})`);
        return;
      }

      onToggle(flagKey, newValue);
    } catch {
      setError('Toggle failed. Check that the backend is running.');
    } finally {
      setIsToggling(false);
    }
  };

  const displayName = formatFlagKey(flagKey);

  return (
    <div className="flex items-start justify-between gap-4 py-4 border-b border-gray-700 last:border-b-0">
      {/* Flag info */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-100">{displayName}</p>
        {description && (
          <p className="text-xs text-gray-400 mt-0.5">{description}</p>
        )}
        <p className="text-xs text-gray-600 mt-1">
          Changes take effect within 60 seconds
        </p>
        {error && (
          <p className="text-xs text-red-400 mt-1">{error}</p>
        )}
      </div>

      {/* Toggle switch */}
      <button
        type="button"
        role="switch"
        aria-checked={isEnabled}
        aria-label={`Toggle ${displayName}`}
        onClick={handleToggle}
        disabled={isToggling}
        className={`relative shrink-0 inline-flex h-6 w-11 items-center rounded-full border-2 border-transparent transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:ring-offset-gray-800 disabled:opacity-60 disabled:cursor-not-allowed ${
          isEnabled ? 'bg-green-500' : 'bg-gray-600'
        }`}
      >
        <span
          className={`inline-block h-4 w-4 rounded-full bg-white shadow transition-transform duration-200 ${
            isEnabled ? 'translate-x-5' : 'translate-x-1'
          }`}
          aria-hidden="true"
        />
      </button>
    </div>
  );
}
