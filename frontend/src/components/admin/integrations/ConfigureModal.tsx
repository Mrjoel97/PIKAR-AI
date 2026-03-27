'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import { useEffect, useState } from 'react';

/**
 * Provider-specific extra config fields rendered in the modal form.
 * Each field maps to a key in the `config` object sent to the API.
 */
const PROVIDER_FIELDS: Record<
  string,
  Array<{ key: string; label: string; placeholder: string }>
> = {
  sentry: [
    { key: 'org_slug', label: 'Organization Slug', placeholder: 'my-org' },
    { key: 'project_slug', label: 'Project Slug', placeholder: 'my-project' },
  ],
  posthog: [{ key: 'project_id', label: 'Project ID', placeholder: '12345' }],
  github: [
    { key: 'owner', label: 'Owner', placeholder: 'my-org' },
    { key: 'repo', label: 'Repository', placeholder: 'my-repo' },
  ],
  stripe: [],
};

/** Props for ConfigureModal */
export interface ConfigureModalProps {
  /** null means the modal is closed */
  provider: string | null;
  /** Existing config values to pre-fill provider-specific fields */
  currentConfig: Record<string, string>;
  onClose: () => void;
  /** Called with the payload to PUT to the API */
  onSave: (data: {
    api_key?: string;
    base_url?: string;
    config: Record<string, string>;
  }) => void;
  isSaving: boolean;
}

/**
 * ConfigureModal renders a dark overlay modal for setting up an integration provider.
 *
 * Security: the API key field is password-type and never pre-filled. Only the last-4
 * characters are ever shown (by the ProviderCard). The base_url field is shown only
 * for PostHog.
 */
export function ConfigureModal({
  provider,
  currentConfig,
  onClose,
  onSave,
  isSaving,
}: ConfigureModalProps) {
  const [apiKey, setApiKey] = useState('');
  const [baseUrl, setBaseUrl] = useState('');
  const [configFields, setConfigFields] = useState<Record<string, string>>({});

  // Reset form state whenever the modal opens for a new provider
  useEffect(() => {
    if (!provider) return;
    setApiKey('');
    setBaseUrl('');
    // Pre-fill provider-specific config fields with existing values
    const fields = PROVIDER_FIELDS[provider] ?? [];
    const initial: Record<string, string> = {};
    for (const field of fields) {
      initial[field.key] = currentConfig[field.key] ?? '';
    }
    setConfigFields(initial);
  }, [provider, currentConfig]);

  if (!provider) return null;

  const displayName = provider.charAt(0).toUpperCase() + provider.slice(1);
  const extraFields = PROVIDER_FIELDS[provider] ?? [];
  const showBaseUrl = provider === 'posthog';

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const payload: {
      api_key?: string;
      base_url?: string;
      config: Record<string, string>;
    } = { config: configFields };

    // Only include api_key if the user actually entered something
    if (apiKey.trim() !== '') {
      payload.api_key = apiKey.trim();
    }
    if (showBaseUrl && baseUrl.trim() !== '') {
      payload.base_url = baseUrl.trim();
    }

    onSave(payload);
  }

  function handleConfigFieldChange(key: string, value: string) {
    setConfigFields((prev) => ({ ...prev, [key]: value }));
  }

  return (
    /* Backdrop */
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={`Configure ${displayName}`}
    >
      {/* Modal panel — stop propagation so clicks inside don't close */}
      <div
        className="bg-gray-800 border border-gray-700 rounded-xl shadow-2xl w-full max-w-md mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-700">
          <h2 className="text-gray-100 font-semibold text-base">
            Configure {displayName}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-400 hover:text-gray-200 transition-colors"
            aria-label="Close modal"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit}>
          <div className="px-6 py-5 space-y-4">
            {/* API Key field */}
            <div>
              <label
                htmlFor="integration-api-key"
                className="block text-sm font-medium text-gray-300 mb-1.5"
              >
                API Key
              </label>
              <input
                id="integration-api-key"
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="Enter API key"
                autoComplete="new-password"
                className="w-full bg-gray-900 border border-gray-600 text-gray-100 rounded-lg px-3 py-2 text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              />
              <p className="mt-1.5 text-xs text-gray-500">
                Key will be encrypted. Only the last 4 characters will be visible after saving.
              </p>
            </div>

            {/* Base URL — PostHog only */}
            {showBaseUrl && (
              <div>
                <label
                  htmlFor="integration-base-url"
                  className="block text-sm font-medium text-gray-300 mb-1.5"
                >
                  Base URL
                </label>
                <input
                  id="integration-base-url"
                  type="text"
                  value={baseUrl}
                  onChange={(e) => setBaseUrl(e.target.value)}
                  placeholder="https://us.posthog.com"
                  className="w-full bg-gray-900 border border-gray-600 text-gray-100 rounded-lg px-3 py-2 text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                />
              </div>
            )}

            {/* Provider-specific config fields */}
            {extraFields.map((field) => (
              <div key={field.key}>
                <label
                  htmlFor={`config-${field.key}`}
                  className="block text-sm font-medium text-gray-300 mb-1.5"
                >
                  {field.label}
                </label>
                <input
                  id={`config-${field.key}`}
                  type="text"
                  value={configFields[field.key] ?? ''}
                  onChange={(e) => handleConfigFieldChange(field.key, e.target.value)}
                  placeholder={field.placeholder}
                  className="w-full bg-gray-900 border border-gray-600 text-gray-100 rounded-lg px-3 py-2 text-sm placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                />
              </div>
            ))}
          </div>

          {/* Footer buttons */}
          <div className="flex justify-end gap-3 px-6 py-4 border-t border-gray-700">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm bg-gray-700 hover:bg-gray-600 text-gray-200 rounded-lg border border-gray-600 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSaving}
              className="px-4 py-2 text-sm bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 disabled:cursor-not-allowed text-white rounded-lg transition-colors flex items-center gap-1.5"
            >
              {isSaving ? (
                <>
                  <svg
                    className="w-3.5 h-3.5 animate-spin"
                    fill="none"
                    viewBox="0 0 24 24"
                    aria-hidden="true"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                    />
                  </svg>
                  Saving…
                </>
              ) : (
                'Save'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
