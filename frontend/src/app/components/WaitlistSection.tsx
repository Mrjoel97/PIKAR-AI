'use client';

import { useState, useEffect } from 'react';
import { ArrowRight, CheckCircle2, Zap, Users, Lock, Star, Loader2 } from 'lucide-react';

const BENEFITS = [
  { Icon: Zap,   text: 'Early access before the public launch' },
  { Icon: Users, text: 'Founding member pricing — 20% off your first two months' },
  { Icon: Star,  text: 'Priority onboarding & dedicated support' },
  { Icon: Lock,  text: 'Direct feedback channel to shape the product' },
] as const;

export default function WaitlistSection() {
  const [step, setStep]       = useState<'form' | 'success'>('form');
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState<string | null>(null);
  const [utmParams, setUtmParams] = useState<Record<string, string>>({});

  useEffect(() => {
    const p = new URLSearchParams(window.location.search);
    const obj: Record<string, string> = {};
    ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term'].forEach((k) => {
      const v = p.get(k);
      if (v) obj[k.replace('utm_', 'utm').replace(/_([a-z])/g, (_, c) => c.toUpperCase())] = v;
    });
    setUtmParams(obj);
  }, []);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const form = e.currentTarget;
    const data = new FormData(form);

    const body = {
      fullName:          data.get('fullName'),
      email:             data.get('email'),
      companyOrRole:     data.get('companyOrRole'),
      category:          data.get('category'),
      biggestBottleneck: data.get('biggestBottleneck'),
      website:           data.get('website'), // honeypot
      source:            'landing_page_waitlist',
      pagePath:          window.location.pathname,
      referrer:          document.referrer || undefined,
      ...utmParams,
    };

    try {
      const res  = await fetch('/api/waitlist', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(body),
      });
      const json = await res.json() as { error?: string };

      if (!res.ok) {
        setError(json.error ?? 'Something went wrong. Please try again.');
        return;
      }
      setStep('success');
    } catch {
      setError('Network error — please check your connection and try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <section
      id="waitlist"
      className="relative bg-gradient-to-b from-[#f6f8f8] to-white py-20 md:py-28 px-6 overflow-hidden"
    >
      {/* Dot-grid background */}
      <div className="absolute inset-0 bg-[radial-gradient(#cbd5e1_1.5px,transparent_1.5px)] bg-[length:24px_24px] opacity-40 pointer-events-none" />
      {/* Top glow */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[700px] h-[350px] bg-[#1a8a6e]/6 rounded-full blur-[90px] pointer-events-none" />

      <div className="relative max-w-6xl mx-auto">
        {/* Section header */}
        <div className="text-center mb-14">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#1a8a6e]/10 text-[#1a8a6e] text-xs font-bold uppercase tracking-wide border border-[#1a8a6e]/20 mb-5">
            <span className="w-1.5 h-1.5 rounded-full bg-[#1a8a6e] animate-pulse" />
            Early Access · Limited Spots
          </div>
          <h2 className="text-4xl md:text-5xl font-black tracking-tight text-slate-900 leading-[1.05] mb-4">
            Be First. Be Ahead.<br />
            <span className="text-[#1a8a6e]">Join the Waitlist.</span>
          </h2>
          <p className="text-slate-500 text-lg max-w-xl mx-auto leading-relaxed">
            Get exclusive early access, founding member pricing, and a direct line to the team building the future of business AI.
          </p>
        </div>

        <div className="grid lg:grid-cols-5 gap-10 items-start">
          {/* Left: Benefits + social proof */}
          <div className="lg:col-span-2 space-y-4">
            <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-5">
              What you get
            </p>

            {BENEFITS.map(({ Icon, text }) => (
              <div key={text} className="flex items-start gap-3">
                <div className="w-9 h-9 rounded-xl bg-[#1a8a6e]/10 flex items-center justify-center shrink-0">
                  <Icon className="w-4 h-4 text-[#1a8a6e]" />
                </div>
                <p className="text-slate-700 font-medium text-sm leading-relaxed pt-2">{text}</p>
              </div>
            ))}

            {/* Founding offer card */}
            <div className="mt-8 p-5 rounded-2xl bg-slate-900 text-white relative overflow-hidden">
              <div className="absolute -top-8 -right-8 w-28 h-28 bg-[#1a8a6e]/20 rounded-full blur-2xl" />
              <p className="text-xs text-slate-400 uppercase tracking-wider font-bold mb-1 relative">
                Founding Member Offer
              </p>
              <p className="text-3xl font-black text-[#56ab91] mb-1 relative">20% off</p>
              <p className="text-xs text-slate-400 relative">
                For your first two months · First 500 signups only
              </p>
            </div>
          </div>

          {/* Right: Form */}
          <div className="lg:col-span-3">
            {step === 'success' ? (
              <div className="bg-white rounded-3xl p-10 border border-slate-100 shadow-sm text-center">
                <div className="w-16 h-16 rounded-full bg-[#1a8a6e]/10 flex items-center justify-center mx-auto mb-5">
                  <CheckCircle2 className="w-8 h-8 text-[#1a8a6e]" />
                </div>
                <h3 className="text-2xl font-black text-slate-900 mb-2">You&apos;re on the list!</h3>
                <p className="text-slate-500 text-sm max-w-sm mx-auto leading-relaxed">
                  We&apos;ll send your early-access invitation to the email you provided. Watch your inbox — and get ready.
                </p>
              </div>
            ) : (
              <form
                onSubmit={handleSubmit}
                className="bg-white rounded-3xl p-8 md:p-10 border border-slate-100 shadow-sm space-y-5"
              >
                {/* Name + Email row */}
                <div className="grid sm:grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="wl-name" className="block text-xs font-semibold text-slate-600 mb-1.5">
                      Full Name <span className="text-red-500">*</span>
                    </label>
                    <input
                      id="wl-name"
                      name="fullName"
                      type="text"
                      required
                      placeholder="Jane Smith"
                      autoComplete="name"
                      className="w-full px-4 py-3 text-sm rounded-xl border border-slate-200 bg-slate-50 text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#1a8a6e]/30 focus:border-[#1a8a6e] transition"
                    />
                  </div>
                  <div>
                    <label htmlFor="wl-email" className="block text-xs font-semibold text-slate-600 mb-1.5">
                      Enter your email <span className="text-red-500">*</span>
                    </label>
                    <input
                      id="wl-email"
                      name="email"
                      type="email"
                      required
                      placeholder="jane@company.com"
                      autoComplete="email"
                      className="w-full px-4 py-3 text-sm rounded-xl border border-slate-200 bg-slate-50 text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#1a8a6e]/30 focus:border-[#1a8a6e] transition"
                    />
                  </div>
                </div>

                {/* Company / Role + Category row */}
                <div className="grid sm:grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="wl-company" className="block text-xs font-semibold text-slate-600 mb-1.5">
                      Company / Role
                    </label>
                    <input
                      id="wl-company"
                      name="companyOrRole"
                      type="text"
                      autoComplete="organization-title"
                      placeholder="CEO at Acme · Ops Manager"
                      className="w-full px-4 py-3 text-sm rounded-xl border border-slate-200 bg-slate-50 text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#1a8a6e]/30 focus:border-[#1a8a6e] transition"
                    />
                  </div>
                  <div>
                    <label htmlFor="wl-category" className="block text-xs font-semibold text-slate-600 mb-1.5">
                      Category <span className="text-red-500">*</span>
                    </label>
                    <select
                      id="wl-category"
                      name="category"
                      required
                      defaultValue=""
                      className="w-full px-4 py-3 text-sm rounded-xl border border-slate-200 bg-slate-50 text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#1a8a6e]/30 focus:border-[#1a8a6e] transition appearance-none bg-[url('data:image/svg+xml;utf8,<svg xmlns=%22http://www.w3.org/2000/svg%22 fill=%22none%22 viewBox=%220 0 24 24%22 stroke=%22%2364748b%22 stroke-width=%222%22><path stroke-linecap=%22round%22 stroke-linejoin=%22round%22 d=%22M19 9l-7 7-7-7%22/></svg>')] bg-no-repeat bg-[right_1rem_center] bg-[length:1rem] pr-10"
                    >
                      <option value="" disabled>
                        Select one…
                      </option>
                      <option value="solopreneur">Solopreneur</option>
                      <option value="startup">Startup</option>
                      <option value="sme">SME</option>
                      <option value="enterprise">Enterprise</option>
                    </select>
                  </div>
                </div>

                {/* Biggest bottleneck */}
                <div>
                  <label htmlFor="wl-bottleneck" className="block text-xs font-semibold text-slate-600 mb-1.5">
                    Biggest operational bottleneck?
                  </label>
                  <textarea
                    id="wl-bottleneck"
                    name="biggestBottleneck"
                    rows={3}
                    placeholder="E.g. Manual reporting, scattered marketing, slow finance approvals..."
                    className="w-full px-4 py-3 text-sm rounded-xl border border-slate-200 bg-slate-50 text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-[#1a8a6e]/30 focus:border-[#1a8a6e] transition resize-none"
                  />
                </div>

                {/* Honeypot — hidden from real users, catches bots */}
                <input name="website" type="text" className="hidden" tabIndex={-1} autoComplete="off" aria-hidden="true" />

                {/* GDPR consent — required under Art. 6(1)(a) GDPR */}
                <div className="flex items-start gap-3 pt-1">
                  <input
                    id="wl-consent"
                    name="consent"
                    type="checkbox"
                    required
                    className="mt-0.5 w-4 h-4 rounded border-slate-300 text-[#1a8a6e] focus:ring-[#1a8a6e] shrink-0 cursor-pointer"
                  />
                  <label htmlFor="wl-consent" className="text-xs text-slate-500 leading-relaxed cursor-pointer">
                    I agree to Pikar AI processing my personal data to send waitlist updates and product news. I can withdraw my consent at any time by emailing{' '}
                    <a href="mailto:privacy@pikar-ai.com" className="text-[#1a8a6e] hover:underline">
                      privacy@pikar-ai.com
                    </a>
                    . See our{' '}
                    <a href="/privacy" className="text-[#1a8a6e] hover:underline">
                      Privacy Policy
                    </a>
                    .
                  </label>
                </div>

                {/* Error */}
                {error && (
                  <p className="text-sm text-red-600 bg-red-50 border border-red-100 rounded-xl px-4 py-3">
                    {error}
                  </p>
                )}

                {/* Submit */}
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-4 rounded-xl bg-gradient-to-r from-[#1a8a6e] to-[#0d6b4f] text-white font-bold text-sm flex items-center justify-center gap-2 hover:opacity-90 active:scale-[0.99] transition-all disabled:opacity-60 disabled:cursor-not-allowed shadow-lg shadow-[#1a8a6e]/20"
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Securing your spot…
                    </>
                  ) : (
                    <>
                      Join the Waitlist
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>

                <p className="text-center text-xs text-slate-400">
                  No credit card · Free to join · Unsubscribe any time
                </p>
              </form>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
