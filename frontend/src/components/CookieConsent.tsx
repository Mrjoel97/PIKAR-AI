'use client';

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Cookie, X } from 'lucide-react';

const CONSENT_KEY = 'pikar_cookie_consent';

export default function CookieConsent() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    // Only show banner if user hasn't decided yet
    const stored = localStorage.getItem(CONSENT_KEY);
    if (!stored) setVisible(true);
  }, []);

  if (!visible) return null;

  const save = (value: 'accepted' | 'rejected') => {
    localStorage.setItem(CONSENT_KEY, value);
    setVisible(false);
    // Dispatch event so analytics code can conditionally activate
    window.dispatchEvent(new CustomEvent('cookieConsentChange', { detail: value }));
  };

  return (
    <div
      role="dialog"
      aria-modal="false"
      aria-label="Cookie consent"
      className="fixed bottom-0 left-0 right-0 z-[9999] p-3 md:p-5 pointer-events-none"
    >
      <div className="max-w-4xl mx-auto pointer-events-auto bg-slate-900/95 backdrop-blur-md border border-slate-700/60 rounded-2xl shadow-2xl p-4 md:p-5">
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
          {/* Icon + text */}
          <div className="flex items-start gap-3 flex-1 min-w-0">
            <div className="p-2 rounded-lg bg-[#1a8a6e]/20 text-[#56ab91] shrink-0 mt-0.5">
              <Cookie className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <p className="text-white text-sm font-semibold mb-0.5">
                We use cookies
              </p>
              <p className="text-slate-400 text-xs leading-relaxed">
                We use essential cookies to keep the site working. With your consent, we also use analytics cookies to understand how you use our site. Your choice is stored locally and you can change it at any time.{' '}
                <Link
                  href="/privacy#cookie-policy"
                  className="text-[#56ab91] hover:underline whitespace-nowrap"
                >
                  Privacy Policy
                </Link>
              </p>
            </div>
          </div>

          {/* Buttons */}
          <div className="flex items-center gap-2 shrink-0 w-full sm:w-auto">
            <button
              onClick={() => save('rejected')}
              className="flex-1 sm:flex-none px-4 py-2 text-xs font-semibold text-slate-300 border border-slate-700 rounded-lg hover:bg-slate-800 transition-colors"
            >
              Reject Non-Essential
            </button>
            <button
              onClick={() => save('accepted')}
              className="flex-1 sm:flex-none px-4 py-2 text-xs font-semibold text-white bg-[#1a8a6e] rounded-lg hover:bg-[#0d6b4f] transition-colors"
            >
              Accept All
            </button>
            <button
              onClick={() => save('rejected')}
              aria-label="Dismiss and reject non-essential cookies"
              className="p-2 text-slate-500 hover:text-slate-300 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
