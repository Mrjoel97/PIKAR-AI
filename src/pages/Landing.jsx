import React from 'react'
import { Link } from 'react-router-dom'

export default function Landing() {
  return (
    <div className="min-h-screen bg-white">
      <header className="max-w-7xl mx-auto px-4 py-6 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <img src="/assets/logo.svg" alt="PIKAR AI" className="w-8 h-8" />
          <span className="font-bold text-xl">PIKAR AI</span>
        </div>
        <nav className="hidden md:flex items-center gap-6 text-sm text-gray-700">
          <a href="#features">Features</a>
          <a href="#solutions">Solutions</a>
          <a href="#pricing">Pricing</a>
          <a href="#faq">FAQ</a>
          <Link to="/login" className="px-3 py-1.5 rounded-md border">Sign in</Link>
          <Link to="/register" className="px-3 py-1.5 rounded-md bg-emerald-600 text-white">Start free</Link>
        </nav>
      </header>

      <main>
        <section className="max-w-7xl mx-auto px-4 py-16 grid md:grid-cols-2 gap-8 items-center">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200 text-sm">AI Marketing • Automations • Insights</div>
            <h1 className="mt-4 text-5xl font-bold leading-tight">Launch and grow with AI-powered marketing and operations</h1>
            <p className="mt-4 text-lg text-gray-700">PIKAR AI helps startups and SMEs plan, publish, and optimize campaigns across every channel, while automating workflows and surfacing insights that move the needle.</p>
            <div className="mt-6 flex gap-3">
              <Link to="/SocialMediaMarketing" className="px-5 py-3 rounded-md bg-emerald-600 text-white">Try the Marketing Suite</Link>
              <Link to="/MarketingAnalytics" className="px-5 py-3 rounded-md border">View Analytics</Link>
            </div>
            <div className="mt-4 text-sm text-gray-600">7‑day free trial • No credit card required • Cancel anytime</div>
          </div>
          <div>
            <img src="/assets/landing-hero.png" className="w-full rounded-xl border" alt="PIKAR AI dashboard" />
          </div>
        </section>

        <section id="features" className="bg-gray-50 border-y">
          <div className="max-w-7xl mx-auto px-4 py-16 grid md:grid-cols-3 gap-6">
            {[
              { title: 'AI Campaign Orchestrator', desc: 'Generate high-performing ad variants and organic content in minutes.' },
              { title: 'Cross-platform Publishing', desc: 'Post everywhere with one click and schedule across timezones.' },
              { title: 'Unified Analytics', desc: 'Track KPIs across Meta, X, LinkedIn, YouTube, and TikTok.' },
              { title: 'A/B Testing', desc: 'Run experiments, find winners, and scale what works.' },
              { title: 'Workflow Automation', desc: 'Automate repetitive tasks and handoffs across your stack.' },
              { title: 'Secure & Compliant', desc: 'RLS, audit logs, and enterprise-grade controls out of the box.' },
            ].map((f, i) => (
              <div key={i} className="p-6 bg-white rounded-xl border">
                <div className="font-semibold">{f.title}</div>
                <div className="text-gray-600 mt-2 text-sm">{f.desc}</div>
              </div>
            ))}
          </div>
        </section>

        <section id="solutions" className="max-w-7xl mx-auto px-4 py-16">
          <h2 className="text-3xl font-bold">Built for Solopreneurs, Startups, and SMEs</h2>
          <div className="grid md:grid-cols-3 gap-6 mt-6">
            {[
              { title: 'Solopreneurs', bullets: ['1‑click Content', 'Autopilot Scheduling', 'Lead Capture'] },
              { title: 'Startups', bullets: ['A/B testing', 'Attribution', 'Sales Integrations'] },
              { title: 'SMEs', bullets: ['Team Roles', 'Approvals', 'Advanced Analytics'] },
            ].map((s, i) => (
              <div key={i} className="p-6 bg-white rounded-xl border">
                <div className="font-semibold">{s.title}</div>
                <ul className="list-disc ml-6 text-sm text-gray-700 mt-2">
                  {s.bullets.map((b, j) => <li key={j}>{b}</li>)}
                </ul>
              </div>
            ))}
          </div>
        </section>

        <section id="pricing" className="bg-gray-50 border-y">
          <div className="max-w-7xl mx-auto px-4 py-16">
            <h2 className="text-3xl font-bold text-center">Simple, transparent pricing</h2>
            <div className="grid md:grid-cols-3 gap-6 mt-8">
              {[{name:'Solo',price:'$19/mo',features:['All core tools','1 brand','Community support']},{name:'Startup',price:'$49/mo',features:['A/B testing','3 brands','Priority support']},{name:'SME',price:'$99/mo',features:['Advanced analytics','10 brands','SLA support']}].map((p,i)=> (
                <div key={i} className="p-6 bg-white rounded-xl border text-center">
                  <div className="text-xl font-semibold">{p.name}</div>
                  <div className="text-3xl font-bold mt-2">{p.price}</div>
                  <ul className="text-sm text-gray-700 mt-3">
                    {p.features.map((f,j)=>(<li key={j}>{f}</li>))}
                  </ul>
                  <Link to="/register" className="inline-block mt-4 px-4 py-2 rounded-md bg-emerald-600 text-white">Start free</Link>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="faq" className="max-w-5xl mx-auto px-4 py-16">
          <h2 className="text-3xl font-bold text-center">Frequently asked questions</h2>
          <div className="grid md:grid-cols-2 gap-6 mt-8 text-sm text-gray-700">
            {[
              {q:'Can I connect my social accounts?',a:'Yes—connect Meta, X/Twitter, LinkedIn, YouTube, and TikTok from Integrations.'},
              {q:'Do you support A/B testing?',a:'Absolutely. Create variants and track winners across platforms.'},
              {q:'Is my data secure?',a:'We use Supabase with RLS and follow best practices for security and privacy.'},
              {q:'Can I cancel anytime?',a:'Yes—no questions asked.'}
            ].map((f,i)=> (
              <div key={i} className="p-4 rounded-lg bg-gray-50 border">
                <div className="font-medium">{f.q}</div>
                <div className="text-gray-600 mt-1">{f.a}</div>
              </div>
            ))}
          </div>
        </section>

        <footer className="max-w-7xl mx-auto px-4 py-10 text-sm text-gray-600">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div>© {new Date().getFullYear()} PIKAR AI. All rights reserved.</div>
            <div className="flex items-center gap-4">
              <Link to="/PrivacyPolicy">Privacy</Link>
              <Link to="/Terms">Terms</Link>
              <a href="mailto:support@pikar-ai.com">Contact</a>
            </div>
          </div>
        </footer>
      </main>
    </div>
  )
}

