
import React from 'react';
import { Check } from 'lucide-react';

const PricingSection = () => {
    return (
        <section id="pricing" className="relative flex flex-col items-center justify-start pt-16 pb-32 px-4 sm:px-8 lg:px-12 overflow-hidden bg-[var(--muted)]">
            {/* Background Grid Pattern */}
            <div className="absolute inset-0 z-0 bg-grid-pattern-pricing opacity-40 pointer-events-none"></div>

            <div className="relative z-10 max-w-4xl w-full text-center mb-20">
                <h2 className="text-[#111718] font-display tracking-tight text-3xl md:text-4xl lg:text-[45px] font-bold leading-[1.1] mb-6">
                    Choose your intelligence tier.
                </h2>
                <p className="text-[#111718]/70 text-base md:text-lg font-normal max-w-2xl mx-auto font-sans">
                    All plans include access to all 11 autonomous agents, seamless integration, and 24/7 reliability.
                </p>
            </div>

            <div className="relative z-10 w-full max-w-[1400px] grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 items-start">

                {/* Solopreneur Card */}
                <div className="clay-card-subtle flex flex-col h-full p-8 relative group border-white/10" style={{ backgroundImage: 'linear-gradient(to bottom, #0a2e2e, var(--teal-900), #061a1a)' }}>
                    <div className="mb-6">
                        <h3 className="text-white font-display text-xl font-bold mb-2">Solopreneur</h3>
                        <p className="text-sm text-teal-100/70 font-medium font-sans">The One-Person Army</p>
                    </div>
                    <div className="mb-8 flex items-baseline">
                        <span className="text-[26px] font-display font-bold text-white tracking-tight">$99</span>
                        <span className="text-sm text-teal-100/70 ml-1 font-sans">/mo</span>
                    </div>
                    <div className="flex-grow space-y-4 mb-8">
                        <div className="flex items-start gap-3">
                            <Check className="text-[var(--teal-300)] h-5 w-5 font-bold shrink-0" strokeWidth={3} />
                            <span className="text-sm text-teal-50/90 font-sans">All 11 AI Agents</span>
                        </div>
                        <div className="flex items-start gap-3">
                            <Check className="text-[var(--teal-300)] h-5 w-5 font-bold shrink-0" strokeWidth={3} />
                            <span className="text-sm text-teal-50/90 font-sans">Brain Dump &rarr; Action Plans</span>
                        </div>
                        <div className="flex items-start gap-3">
                            <Check className="text-[var(--teal-300)] h-5 w-5 font-bold shrink-0" strokeWidth={3} />
                            <span className="text-sm text-teal-50/90 font-sans">Invoice Generation & Tracking</span>
                        </div>
                        <div className="flex items-start gap-3">
                            <Check className="text-[var(--teal-300)] h-5 w-5 font-bold shrink-0" strokeWidth={3} />
                            <span className="text-sm text-teal-50/90 font-sans">Social Media Publishing (6 platforms)</span>
                        </div>
                        <div className="flex items-start gap-3">
                            <Check className="text-[var(--teal-300)] h-5 w-5 font-bold shrink-0" strokeWidth={3} />
                            <span className="text-sm text-teal-50/90 font-sans">Content Creation Engine</span>
                        </div>
                        <div className="flex items-start gap-3">
                            <Check className="text-[var(--teal-300)] h-5 w-5 font-bold shrink-0" strokeWidth={3} />
                            <span className="text-sm text-teal-50/90 font-sans">Knowledge Vault & Research</span>
                        </div>
                    </div>
                    <button className="w-full py-2 rounded-full bg-white text-[var(--teal-900)] font-bold hover:bg-gray-100 transition-all cursor-pointer">
                        Get Started
                    </button>
                </div>

                {/* Startup Card (Most Popular) */}
                <div className="clay-card-prominent flex flex-col h-full p-8 relative lg:-mt-6 lg:mb-6 z-10">
                    <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-[var(--teal-700)] text-white text-xs font-bold uppercase tracking-wider py-1.5 px-4 rounded-full shadow-lg font-sans">
                        Most Popular
                    </div>
                    <div className="mb-6">
                        <h3 className="text-[#111718] font-display text-2xl font-bold mb-2">Startup</h3>
                        <p className="text-sm text-[#111718]/60 font-medium font-sans">Growth Engine</p>
                    </div>
                    <div className="mb-8 flex items-baseline">
                        <span className="text-[32px] font-display font-bold text-[#111718] tracking-tight">$297</span>
                        <span className="text-sm text-[#111718]/60 ml-1 font-sans">/mo</span>
                    </div>
                    <div className="flex-grow space-y-4 mb-8">
                        <div className="flex items-start gap-3">
                            <div className="bg-[var(--teal-700)]/10 rounded-full p-0.5">
                                <Check className="text-[var(--teal-700)] h-5 w-5 font-bold shrink-0" strokeWidth={3} />
                            </div>
                            <span className="text-sm text-[#111718]/80 font-medium font-sans">Everything in Solopreneur</span>
                        </div>
                        <div className="flex items-start gap-3">
                            <div className="bg-[var(--teal-700)]/10 rounded-full p-0.5">
                                <Check className="text-[var(--teal-700)] h-5 w-5 font-bold shrink-0" strokeWidth={3} />
                            </div>
                            <span className="text-sm text-[#111718]/80 font-medium font-sans">Workflow Automation Engine</span>
                        </div>
                        <div className="flex items-start gap-3">
                            <div className="bg-[var(--teal-700)]/10 rounded-full p-0.5">
                                <Check className="text-[var(--teal-700)] h-5 w-5 font-bold shrink-0" strokeWidth={3} />
                            </div>
                            <span className="text-sm text-[#111718]/80 font-medium font-sans">Sales Pipeline & CRM</span>
                        </div>
                        <div className="flex items-start gap-3">
                            <div className="bg-[var(--teal-700)]/10 rounded-full p-0.5">
                                <Check className="text-[var(--teal-700)] h-5 w-5 font-bold shrink-0" strokeWidth={3} />
                            </div>
                            <span className="text-sm text-[#111718]/80 font-medium font-sans">Campaign Management</span>
                        </div>
                        <div className="flex items-start gap-3">
                            <div className="bg-[var(--teal-700)]/10 rounded-full p-0.5">
                                <Check className="text-[var(--teal-700)] h-5 w-5 font-bold shrink-0" strokeWidth={3} />
                            </div>
                            <span className="text-sm text-[#111718]/80 font-medium font-sans">Advanced Analytics & Approvals</span>
                        </div>
                    </div>
                    <button className="w-full py-3 rounded-full bg-[var(--teal-700)] text-white font-extrabold shadow-xl shadow-[var(--teal-700)]/20 hover:bg-[#1d6b62] transition-all transform hover:scale-[1.02] cursor-pointer">
                        Get Started Now
                    </button>
                </div>

                {/* SME Card */}
                <div className="clay-card-subtle flex flex-col h-full p-8 relative group border-white/10" style={{ backgroundImage: 'linear-gradient(to bottom, #0a2e2e, var(--teal-900), #061a1a)' }}>
                    <div className="mb-6">
                        <h3 className="text-white font-display text-xl font-bold mb-2">SME</h3>
                        <p className="text-sm text-teal-100/70 font-medium font-sans">Efficiency at Scale</p>
                    </div>
                    <div className="mb-8 flex items-baseline">
                        <span className="text-[26px] font-display font-bold text-white tracking-tight">$597</span>
                        <span className="text-sm text-teal-100/70 ml-1 font-sans">/mo</span>
                    </div>
                    <div className="flex-grow space-y-4 mb-8">
                        <div className="flex items-start gap-3">
                            <Check className="text-[var(--teal-300)] h-5 w-5 font-bold shrink-0" strokeWidth={3} />
                            <span className="text-sm text-teal-50/90 font-sans">Everything in Startup</span>
                        </div>
                        <div className="flex items-start gap-3">
                            <Check className="text-[var(--teal-300)] h-5 w-5 font-bold shrink-0" strokeWidth={3} />
                            <span className="text-sm text-teal-50/90 font-sans">Compliance & Risk Management</span>
                        </div>
                        <div className="flex items-start gap-3">
                            <Check className="text-[var(--teal-300)] h-5 w-5 font-bold shrink-0" strokeWidth={3} />
                            <span className="text-sm text-teal-50/90 font-sans">Financial Forecasting</span>
                        </div>
                        <div className="flex items-start gap-3">
                            <Check className="text-[var(--teal-300)] h-5 w-5 font-bold shrink-0" strokeWidth={3} />
                            <span className="text-sm text-teal-50/90 font-sans">Deep Research & Market Analysis</span>
                        </div>
                        <div className="flex items-start gap-3">
                            <Check className="text-[var(--teal-300)] h-5 w-5 font-bold shrink-0" strokeWidth={3} />
                            <span className="text-sm text-teal-50/90 font-sans">Department-Level Operations</span>
                        </div>
                        <div className="flex items-start gap-3">
                            <Check className="text-[var(--teal-300)] h-5 w-5 font-bold shrink-0" strokeWidth={3} />
                            <span className="text-sm text-teal-50/90 font-sans">Priority Support & Onboarding</span>
                        </div>
                    </div>
                    <button className="w-full py-2 rounded-full bg-white text-[var(--teal-900)] font-bold hover:bg-gray-100 transition-all cursor-pointer">
                        Get Started
                    </button>
                </div>

                {/* Enterprise Card */}
                <div className="clay-card-subtle flex flex-col h-full p-8 relative group">
                    <div className="mb-6">
                        <h3 className="text-[#111718] font-display text-xl font-bold mb-2">Enterprise</h3>
                        <p className="text-sm text-[#111718]/60 font-medium font-sans">Cognitive Infrastructure</p>
                    </div>
                    <div className="mb-8 flex items-baseline">
                        <span className="text-[26px] font-display font-bold text-[#111718] tracking-tight">Custom</span>
                    </div>
                    <div className="flex-grow space-y-4 mb-8">
                        <div className="flex items-start gap-3">
                            <Check className="text-[var(--teal-700)] h-5 w-5 font-bold shrink-0" strokeWidth={3} />
                            <span className="text-sm text-[#111718]/80 font-sans">Everything in SME</span>
                        </div>
                        <div className="flex items-start gap-3">
                            <Check className="text-[var(--teal-700)] h-5 w-5 font-bold shrink-0" strokeWidth={3} />
                            <span className="text-sm text-[#111718]/80 font-sans">Full Audit Trail & Governance</span>
                        </div>
                        <div className="flex items-start gap-3">
                            <Check className="text-[var(--teal-700)] h-5 w-5 font-bold shrink-0" strokeWidth={3} />
                            <span className="text-sm text-[#111718]/80 font-sans">Custom Workflow Templates</span>
                        </div>
                        <div className="flex items-start gap-3">
                            <Check className="text-[var(--teal-700)] h-5 w-5 font-bold shrink-0" strokeWidth={3} />
                            <span className="text-sm text-[#111718]/80 font-sans">SSO & Advanced Security</span>
                        </div>
                        <div className="flex items-start gap-3">
                            <Check className="text-[var(--teal-700)] h-5 w-5 font-bold shrink-0" strokeWidth={3} />
                            <span className="text-sm text-[#111718]/80 font-sans">Dedicated Account Management</span>
                        </div>
                        <div className="flex items-start gap-3">
                            <Check className="text-[var(--teal-700)] h-5 w-5 font-bold shrink-0" strokeWidth={3} />
                            <span className="text-sm text-[#111718]/80 font-sans">SLA Guarantee</span>
                        </div>
                    </div>
                    <button className="w-full py-2 rounded-full bg-[#111718] text-white font-bold hover:bg-[#1a2325] transition-colors shadow-lg shadow-[#111718]/10 cursor-pointer">
                        Talk to Sales
                    </button>
                </div>

            </div>
        </section>
    );
};

export default PricingSection;
