'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.

import { useCallback, useEffect, useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/** Autonomy level values */
type AutonomyLevel = 'auto' | 'confirm' | 'blocked';

/** Shape of a single permission from GET /admin/config/permissions */
interface Permission {
  action_name: string;
  action_category: string;
  autonomy_level: AutonomyLevel;
  risk_level: string;
  description: string | null;
}

/** Props for AutonomyTierTab */
export interface AutonomyTierTabProps {
  /** Supabase access_token for Authorization header */
  token: string;
}

/** Map known action name prefixes/substrings to domain labels */
const DOMAIN_MAP: Record<string, string> = {
  check_system_health: 'System',
  get_api_health: 'Monitoring',
  get_active_incidents: 'Monitoring',
  get_incident: 'Monitoring',
  run_diagnostic: 'Monitoring',
  check_error: 'Monitoring',
  check_rate: 'Monitoring',
  get_usage: 'Analytics',
  get_agent_effectiveness: 'Analytics',
  get_engagement: 'Analytics',
  generate_report: 'Analytics',
  sentry_: 'Integrations',
  posthog_: 'Integrations',
  github_: 'Integrations',
  get_agent_config: 'Config',
  update_agent: 'Config',
  get_config: 'Config',
  rollback: 'Config',
  get_feature: 'Config',
  toggle: 'Config',
  get_autonomy: 'Config',
  update_autonomy: 'Config',
  assess_config: 'Config',
  recommend_config: 'Config',
  upload_knowledge: 'Knowledge',
  list_knowledge: 'Knowledge',
  search_knowledge: 'Knowledge',
  delete_knowledge: 'Knowledge',
  get_knowledge: 'Knowledge',
  check_knowledge: 'Knowledge',
  validate_knowledge: 'Knowledge',
  recommend_chunking: 'Knowledge',
  list_users: 'Users',
  get_user: 'Users',
  suspend: 'Users',
  unsuspend: 'Users',
  change_user: 'Users',
  impersonate: 'Users',
  get_at_risk: 'Users',
  get_user_support: 'Users',
  get_billing: 'Billing',
  get_plan_dist: 'Billing',
  issue_refund: 'Billing',
  detect_analytics: 'Billing',
  generate_executive: 'Billing',
  forecast: 'Billing',
  assess_refund: 'Billing',
  recommend_autonomy: 'Governance',
  generate_compliance: 'Governance',
  suggest_role: 'Governance',
  generate_daily: 'Governance',
  classify_and: 'Governance',
  list_all_approvals: 'Governance',
  override_approval: 'Governance',
  manage_admin: 'Governance',
};

/** Determine the domain label for an action name */
function getDomain(actionName: string): string {
  for (const [prefix, domain] of Object.entries(DOMAIN_MAP)) {
    if (actionName.startsWith(prefix) || actionName.includes(prefix)) {
      return domain;
    }
  }
  return 'Other';
}

/** Color classes for tier select */
const TIER_BG: Record<AutonomyLevel, string> = {
  auto: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400',
  confirm: 'bg-amber-500/10 border-amber-500/30 text-amber-400',
  blocked: 'bg-rose-500/10 border-rose-500/30 text-rose-400',
};

/**
 * AutonomyTierTab renders all 58+ admin tool permissions grouped by domain.
 *
 * Each row has a tier dropdown (auto / confirm / blocked) that sends a
 * PUT /admin/config/permissions/{action_name} request with optimistic update.
 * Domains are collapsible to reduce visual noise.
 */
export function AutonomyTierTab({ token }: AutonomyTierTabProps) {
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [savingAction, setSavingAction] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  /** Track which domain sections are expanded */
  const [expandedDomains, setExpandedDomains] = useState<Set<string>>(new Set());

  // ─── Fetch permissions ────────────────────────────────────────────────────

  const fetchPermissions = useCallback(async () => {
    setIsLoading(true);
    setFetchError(null);
    try {
      const res = await fetch(`${API_URL}/admin/config/permissions`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        setFetchError(`Failed to load permissions (${res.status})`);
        return;
      }
      const data = (await res.json()) as Permission[];
      setPermissions(data);
      // Expand all domains by default on first load
      const domains = new Set(data.map((p) => getDomain(p.action_name)));
      setExpandedDomains(domains);
    } catch {
      setFetchError('Failed to load permissions. Check that the backend is running.');
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchPermissions();
  }, [fetchPermissions]);

  // ─── handleTierChange ─────────────────────────────────────────────────────

  const handleTierChange = useCallback(
    async (actionName: string, newLevel: AutonomyLevel) => {
      setSavingAction(actionName);
      setSaveError(null);
      // Optimistic update
      setPermissions((prev) =>
        prev.map((p) =>
          p.action_name === actionName ? { ...p, autonomy_level: newLevel } : p,
        ),
      );
      try {
        const res = await fetch(`${API_URL}/admin/config/permissions/${actionName}`, {
          method: 'PUT',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ autonomy_level: newLevel }),
        });
        if (!res.ok) {
          setSaveError(`Save failed (${res.status})`);
          // Revert on error
          fetchPermissions();
        }
      } catch {
        setSaveError('Save failed. Check that the backend is running.');
        fetchPermissions();
      } finally {
        setSavingAction(null);
      }
    },
    [token, fetchPermissions],
  );

  // ─── Domain toggle ────────────────────────────────────────────────────────

  const toggleDomain = useCallback((domain: string) => {
    setExpandedDomains((prev) => {
      const next = new Set(prev);
      if (next.has(domain)) {
        next.delete(domain);
      } else {
        next.add(domain);
      }
      return next;
    });
  }, []);

  // ─── Group by domain ─────────────────────────────────────────────────────

  const grouped = permissions.reduce<Record<string, Permission[]>>((acc, p) => {
    const domain = getDomain(p.action_name);
    if (!acc[domain]) acc[domain] = [];
    acc[domain].push(p);
    return acc;
  }, {});

  const domains = Object.keys(grouped).sort();

  // ─── Loading state ────────────────────────────────────────────────────────

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="bg-gray-800 rounded-lg border border-gray-700 h-10 animate-pulse" />
        ))}
      </div>
    );
  }

  if (fetchError) {
    return (
      <div className="flex flex-col items-center justify-center py-12 gap-4">
        <p className="text-red-400 text-sm">{fetchError}</p>
        <button
          type="button"
          onClick={fetchPermissions}
          className="px-4 py-2 bg-gray-800 text-gray-200 rounded-lg border border-gray-600 hover:bg-gray-700 text-sm transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header count */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-400">
          <span className="text-gray-200 font-semibold">{permissions.length}</span> tool permissions
          across {domains.length} domains
        </p>
      </div>

      {/* Save error banner */}
      {saveError && (
        <div className="flex items-center gap-3 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
          <span className="flex-1">{saveError}</span>
          <button
            type="button"
            onClick={() => setSaveError(null)}
            className="opacity-60 hover:opacity-100"
            aria-label="Dismiss error"
          >
            ✕
          </button>
        </div>
      )}

      {/* Domain sections */}
      {domains.map((domain) => {
        const isExpanded = expandedDomains.has(domain);
        const domainPerms = grouped[domain];
        return (
          <div key={domain} className="bg-gray-800 border border-gray-700 rounded-lg overflow-hidden">
            {/* Domain header (clickable toggle) */}
            <button
              type="button"
              onClick={() => toggleDomain(domain)}
              className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-gray-750 transition-colors"
            >
              <div className="flex items-center gap-3">
                {isExpanded ? (
                  <ChevronDown size={14} className="text-gray-400 flex-shrink-0" />
                ) : (
                  <ChevronRight size={14} className="text-gray-400 flex-shrink-0" />
                )}
                <span className="text-sm font-semibold text-gray-200">{domain}</span>
                <span className="text-xs text-gray-500">
                  {domainPerms.length} action{domainPerms.length !== 1 ? 's' : ''}
                </span>
              </div>
            </button>

            {/* Permissions table */}
            {isExpanded && (
              <table className="w-full text-sm border-t border-gray-700">
                <tbody className="divide-y divide-gray-700">
                  {domainPerms.map((perm) => {
                    const tier = perm.autonomy_level;
                    return (
                      <tr key={perm.action_name} className="hover:bg-gray-750">
                        <td className="px-4 py-2.5 text-gray-300 font-mono text-xs">
                          {perm.action_name}
                        </td>
                        <td className="px-4 py-2.5 w-32">
                          <select
                            value={tier}
                            onChange={(e) =>
                              handleTierChange(perm.action_name, e.target.value as AutonomyLevel)
                            }
                            disabled={savingAction === perm.action_name}
                            className={`text-xs font-medium rounded-lg px-2.5 py-1 border focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:opacity-60 disabled:cursor-not-allowed bg-transparent cursor-pointer transition-colors ${TIER_BG[tier]}`}
                            aria-label={`Autonomy tier for ${perm.action_name}`}
                          >
                            <option value="auto">auto</option>
                            <option value="confirm">confirm</option>
                            <option value="blocked">blocked</option>
                          </select>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        );
      })}

      {permissions.length === 0 && (
        <div className="text-center py-12 text-gray-500 text-sm">
          No permissions configured.
        </div>
      )}
    </div>
  );
}
