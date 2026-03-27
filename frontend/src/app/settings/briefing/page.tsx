'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import { useState, useEffect } from 'react';
import {
  getBriefingPreferences,
  updateBriefingPreferences,
  type BriefingPreferences,
} from '@/services/briefing';
import {
  Clock,
  Mail,
  Zap,
  Users,
  EyeOff,
  Save,
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  X,
} from 'lucide-react';

const TIMEZONES = [
  'UTC',
  'America/New_York',
  'America/Chicago',
  'America/Denver',
  'America/Los_Angeles',
  'America/Anchorage',
  'America/Honolulu',
  'Europe/London',
  'Europe/Paris',
  'Europe/Berlin',
  'Europe/Moscow',
  'Asia/Dubai',
  'Asia/Kolkata',
  'Asia/Bangkok',
  'Asia/Singapore',
  'Asia/Tokyo',
  'Asia/Shanghai',
  'Australia/Sydney',
  'Pacific/Auckland',
];

const DEFAULT_PREFS: BriefingPreferences = {
  briefing_time: '08:00',
  timezone: 'UTC',
  email_digest_enabled: false,
  email_digest_frequency: 'daily',
  auto_act_enabled: false,
  auto_act_daily_cap: 10,
  auto_act_categories: [],
  vip_senders: [],
  ignored_senders: [],
};

function SectionCard({
  title,
  icon: Icon,
  children,
}: {
  title: string;
  icon: React.ElementType;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-slate-700 bg-slate-800 p-5">
      <div className="flex items-center gap-3 mb-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-slate-700">
          <Icon className="h-4 w-4 text-teal-400" />
        </div>
        <h2 className="text-base font-semibold text-white">{title}</h2>
      </div>
      {children}
    </div>
  );
}

function Toggle({
  checked,
  onChange,
  label,
  description,
}: {
  checked: boolean;
  onChange: (val: boolean) => void;
  label: string;
  description?: string;
}) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div>
        <p className="text-sm font-medium text-white">{label}</p>
        {description && <p className="text-xs text-slate-400 mt-0.5">{description}</p>}
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-2 focus:ring-offset-slate-800 ${
          checked ? 'bg-teal-500' : 'bg-slate-600'
        }`}
      >
        <span
          className={`inline-block h-4 w-4 rounded-full bg-white shadow transition-transform ${
            checked ? 'translate-x-6' : 'translate-x-1'
          }`}
        />
      </button>
    </div>
  );
}

function EmailChipInput({
  label,
  values,
  onAdd,
  onRemove,
  placeholder,
}: {
  label: string;
  values: string[];
  onAdd: (email: string) => void;
  onRemove: (email: string) => void;
  placeholder?: string;
}) {
  const [inputValue, setInputValue] = useState('');

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      const trimmed = inputValue.trim().replace(/,$/, '');
      if (trimmed && !values.includes(trimmed)) {
        onAdd(trimmed);
        setInputValue('');
      }
    }
  }

  function handleBlur() {
    const trimmed = inputValue.trim();
    if (trimmed && !values.includes(trimmed)) {
      onAdd(trimmed);
      setInputValue('');
    }
  }

  return (
    <div>
      <label className="block text-sm font-medium text-slate-300 mb-2">{label}</label>
      <input
        type="email"
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={handleBlur}
        placeholder={placeholder ?? 'Press Enter to add'}
        className="w-full rounded-xl border border-slate-600 bg-slate-700 px-4 py-2.5 text-sm text-white placeholder-slate-400 focus:border-teal-500 focus:ring-1 focus:ring-teal-500 outline-none transition-all"
      />
      {values.length > 0 && (
        <div className="flex flex-wrap gap-2 mt-2">
          {values.map((email) => (
            <span
              key={email}
              className="inline-flex items-center gap-1.5 rounded-lg bg-slate-700 px-3 py-1 text-xs text-slate-200 border border-slate-600"
            >
              {email}
              <button
                type="button"
                onClick={() => onRemove(email)}
                aria-label={`Remove ${email}`}
                className="text-slate-400 hover:text-white transition-colors"
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

export default function BriefingSettingsPage() {
  const [prefs, setPrefs] = useState<BriefingPreferences>(DEFAULT_PREFS);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'success' | 'error'>('idle');

  useEffect(() => {
    async function load() {
      try {
        const data = await getBriefingPreferences();
        setPrefs(data);
      } catch {
        // Use defaults if endpoint not available
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  function update<K extends keyof BriefingPreferences>(key: K, value: BriefingPreferences[K]) {
    setPrefs((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSave() {
    setSaving(true);
    setSaveStatus('idle');
    try {
      const updated = await updateBriefingPreferences(prefs);
      setPrefs(updated);
      setSaveStatus('success');
      setTimeout(() => setSaveStatus('idle'), 3000);
    } catch {
      setSaveStatus('error');
      setTimeout(() => setSaveStatus('idle'), 3000);
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <div className="max-w-2xl mx-auto space-y-4 p-6 animate-pulse">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-40 rounded-2xl bg-slate-700/50" />
        ))}
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6 p-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Briefing Preferences</h1>
        <p className="mt-1 text-sm text-slate-400">
          Customise when and how your daily briefing is delivered.
        </p>
      </div>

      {/* Briefing Schedule */}
      <SectionCard title="Schedule" icon={Clock}>
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="briefing-time" className="block text-sm font-medium text-slate-300 mb-2">
              Briefing time
            </label>
            <input
              id="briefing-time"
              type="time"
              value={prefs.briefing_time}
              onChange={(e) => update('briefing_time', e.target.value)}
              className="w-full rounded-xl border border-slate-600 bg-slate-700 px-4 py-2.5 text-sm text-white focus:border-teal-500 focus:ring-1 focus:ring-teal-500 outline-none transition-all"
            />
          </div>
          <div>
            <label htmlFor="timezone" className="block text-sm font-medium text-slate-300 mb-2">
              Timezone
            </label>
            <select
              id="timezone"
              value={prefs.timezone}
              onChange={(e) => update('timezone', e.target.value)}
              className="w-full rounded-xl border border-slate-600 bg-slate-700 px-4 py-2.5 text-sm text-white focus:border-teal-500 focus:ring-1 focus:ring-teal-500 outline-none transition-all"
            >
              {TIMEZONES.map((tz) => (
                <option key={tz} value={tz}>
                  {tz}
                </option>
              ))}
            </select>
          </div>
        </div>
      </SectionCard>

      {/* Email Digest */}
      <SectionCard title="Email Digest" icon={Mail}>
        <div className="space-y-4">
          <Toggle
            checked={prefs.email_digest_enabled}
            onChange={(val) => update('email_digest_enabled', val)}
            label="Enable email digest"
            description="Receive a summary of your briefing by email."
          />
          {prefs.email_digest_enabled && (
            <div>
              <label htmlFor="digest-freq" className="block text-sm font-medium text-slate-300 mb-2">
                Frequency
              </label>
              <select
                id="digest-freq"
                value={prefs.email_digest_frequency}
                onChange={(e) =>
                  update('email_digest_frequency', e.target.value as BriefingPreferences['email_digest_frequency'])
                }
                className="w-full rounded-xl border border-slate-600 bg-slate-700 px-4 py-2.5 text-sm text-white focus:border-teal-500 focus:ring-1 focus:ring-teal-500 outline-none transition-all"
              >
                <option value="daily">Daily</option>
                <option value="weekdays">Weekdays only</option>
                <option value="off">Off</option>
              </select>
            </div>
          )}
        </div>
      </SectionCard>

      {/* Auto-Act */}
      <SectionCard title="Auto-Act (Shadow Mode)" icon={Zap}>
        <div className="space-y-4">
          <Toggle
            checked={prefs.auto_act_enabled}
            onChange={(val) => update('auto_act_enabled', val)}
            label="Enable auto-act"
            description="Allow the AI to take approved actions automatically."
          />
          {prefs.auto_act_enabled && (
            <>
              <div className="flex items-start gap-3 rounded-xl border border-amber-700/50 bg-amber-900/20 p-4">
                <AlertTriangle className="h-4 w-4 text-amber-400 mt-0.5 shrink-0" />
                <p className="text-xs text-amber-300">
                  Auto-act allows the AI to send emails, schedule meetings, and update records on your behalf.
                  Start with a low daily cap and review the activity log regularly.
                </p>
              </div>
              <div>
                <div className="flex justify-between items-center mb-2">
                  <label htmlFor="auto-act-cap" className="text-sm font-medium text-slate-300">
                    Daily action cap
                  </label>
                  <span className="text-sm font-bold text-teal-400">{prefs.auto_act_daily_cap}</span>
                </div>
                <input
                  id="auto-act-cap"
                  type="range"
                  min={1}
                  max={50}
                  step={1}
                  value={prefs.auto_act_daily_cap}
                  onChange={(e) => update('auto_act_daily_cap', Number(e.target.value))}
                  className="w-full accent-teal-500"
                />
                <div className="flex justify-between text-[10px] text-slate-500 mt-1">
                  <span>1</span>
                  <span>50</span>
                </div>
              </div>
            </>
          )}
        </div>
      </SectionCard>

      {/* VIP Senders */}
      <SectionCard title="VIP Senders" icon={Users}>
        <EmailChipInput
          label="Always surface emails from these addresses"
          values={prefs.vip_senders}
          onAdd={(email) => update('vip_senders', [...prefs.vip_senders, email])}
          onRemove={(email) => update('vip_senders', prefs.vip_senders.filter((s) => s !== email))}
          placeholder="ceo@company.com — press Enter to add"
        />
      </SectionCard>

      {/* Ignored Senders */}
      <SectionCard title="Ignored Senders" icon={EyeOff}>
        <EmailChipInput
          label="Never surface emails from these addresses"
          values={prefs.ignored_senders}
          onAdd={(email) => update('ignored_senders', [...prefs.ignored_senders, email])}
          onRemove={(email) => update('ignored_senders', prefs.ignored_senders.filter((s) => s !== email))}
          placeholder="noreply@newsletter.com — press Enter to add"
        />
      </SectionCard>

      {/* Save button */}
      <div className="flex items-center justify-end gap-3 pb-4">
        {saveStatus === 'error' && (
          <div className="flex items-center gap-2 text-sm text-rose-400">
            <AlertCircle className="h-4 w-4" />
            Failed to save. Please try again.
          </div>
        )}
        <button
          onClick={handleSave}
          disabled={saving}
          className={`inline-flex items-center gap-2 rounded-xl px-6 py-2.5 text-sm font-semibold text-white transition-all disabled:opacity-50 ${
            saveStatus === 'success'
              ? 'bg-emerald-600'
              : saveStatus === 'error'
              ? 'bg-rose-600'
              : 'bg-teal-600 hover:bg-teal-500'
          }`}
        >
          {saveStatus === 'success' ? (
            <>
              <CheckCircle2 className="h-4 w-4" />
              Saved
            </>
          ) : (
            <>
              <Save className="h-4 w-4" />
              {saving ? 'Saving…' : 'Save Preferences'}
            </>
          )}
        </button>
      </div>
    </div>
  );
}
