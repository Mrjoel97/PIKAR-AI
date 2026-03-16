"use client";

import React, { useEffect, useState } from 'react';
import { ArrowRight, AtSign, BriefcaseBusiness, CheckCircle, LoaderCircle, Rocket, Sparkles, User, Users } from 'lucide-react';
import { motion } from 'framer-motion';

type WaitlistForm = {
    fullName: string;
    email: string;
    companyOrRole: string;
    biggestBottleneck: string;
    website: string;
};

type Attribution = {
    pagePath: string;
    referrer: string;
    utmSource: string;
    utmMedium: string;
    utmCampaign: string;
    utmContent: string;
    utmTerm: string;
};

const INITIAL_FORM: WaitlistForm = {
    fullName: '',
    email: '',
    companyOrRole: '',
    biggestBottleneck: '',
    website: '',
};

const INITIAL_ATTRIBUTION: Attribution = {
    pagePath: '/',
    referrer: '',
    utmSource: '',
    utmMedium: '',
    utmCampaign: '',
    utmContent: '',
    utmTerm: '',
};

export default function ContactSection() {
    const [form, setForm] = useState<WaitlistForm>(INITIAL_FORM);
    const [attribution, setAttribution] = useState<Attribution>(INITIAL_ATTRIBUTION);
    const [isSubmitted, setIsSubmitted] = useState(false);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (typeof window === 'undefined') {
            return;
        }

        const params = new URLSearchParams(window.location.search);
        setAttribution({
            pagePath: window.location.pathname,
            referrer: document.referrer,
            utmSource: params.get('utm_source') ?? '',
            utmMedium: params.get('utm_medium') ?? '',
            utmCampaign: params.get('utm_campaign') ?? '',
            utmContent: params.get('utm_content') ?? '',
            utmTerm: params.get('utm_term') ?? '',
        });
    }, []);

    const handleChange = (field: keyof WaitlistForm) => (
        event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
    ) => {
        const value = event.target.value;
        setForm((current) => ({ ...current, [field]: value }));
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setIsSubmitting(true);

        try {
            const response = await fetch('/api/waitlist', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    fullName: form.fullName,
                    email: form.email,
                    companyOrRole: form.companyOrRole,
                    biggestBottleneck: form.biggestBottleneck,
                    source: 'landing_page_waitlist',
                    pagePath: attribution.pagePath,
                    referrer: attribution.referrer,
                    utmSource: attribution.utmSource,
                    utmMedium: attribution.utmMedium,
                    utmCampaign: attribution.utmCampaign,
                    utmContent: attribution.utmContent,
                    utmTerm: attribution.utmTerm,
                    website: form.website,
                }),
            });

            const result = await response.json().catch(() => ({}));

            if (!response.ok) {
                setError(result.error || 'Unable to join the waitlist right now.');
                return;
            }

            setIsSubmitted(true);
            setForm(INITIAL_FORM);
        } catch (submitError) {
            console.error('Waitlist submit error:', submitError);
            setError('Unable to join the waitlist right now.');
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <section id="waitlist" className="font-display bg-[#f6f8f8] text-[#0d1b19] flex flex-col lg:flex-row antialiased h-auto scroll-mt-28">
            {/* Left Column: Content */}
            <div className="relative w-full lg:w-5/12 flex flex-col justify-center p-6 lg:p-8 xl:p-12 bg-[#f6f8f8] bg-[radial-gradient(#cbd5e1_1.5px,transparent_1.5px)] bg-[length:16px_16px]">
                <div className="max-w-sm mx-auto lg:mx-0 flex flex-col h-full justify-center">
                    {/* Branding */}
                    <div className="mb-4">
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-[#0fbd9a]/10 text-[#0fbd9a] text-xs font-bold tracking-wide uppercase">
                            Join the Founding Waitlist
                        </span>
                    </div>
                    {/* Headline */}
                    <h1 className="text-2xl lg:text-3xl font-extrabold tracking-tight text-[#0d1b19] leading-[1.1] mb-3">
                        Get early access to your <span className="text-[#0fbd9a]">AI executive team</span>
                    </h1>
                    {/* Subheadline */}
                    <p className="text-sm text-gray-600 font-medium leading-relaxed mb-6">
                        Join the founders and operators who want first access to Pikar-AI. We will roll out beta workflows in waves and share launch updates with this list first.
                    </p>

                    {/* Waitlist Benefits */}
                    <div className="space-y-3">
                        <div className="bg-white shadow-[4px_4px_8px_#d1d5db,-4px_-4px_8px_#ffffff] hover:shadow-[6px_6px_10px_#d1d5db,-6px_-6px_10px_#ffffff] hover:-translate-y-0.5 transition-all duration-200 flex items-center gap-3 p-3 rounded-xl group">
                            <div className="flex items-center justify-center shrink-0 w-8 h-8 rounded-full bg-[#0fbd9a]/10 text-[#0fbd9a] transition-colors group-hover:bg-[#0fbd9a] group-hover:text-white">
                                <Rocket className="w-4 h-4" />
                            </div>
                            <div className="flex flex-col">
                                <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Early Access</span>
                                <span className="text-sm font-bold text-[#0d1b19]">See the first live workflows before public launch.</span>
                            </div>
                            <div className="ml-auto text-gray-300 group-hover:text-[#0fbd9a] transition-colors">
                                <ArrowRight className="w-4 h-4" />
                            </div>
                        </div>

                        <div className="bg-white shadow-[4px_4px_8px_#d1d5db,-4px_-4px_8px_#ffffff] hover:shadow-[6px_6px_10px_#d1d5db,-6px_-6px_10px_#ffffff] hover:-translate-y-0.5 transition-all duration-200 flex items-center gap-3 p-3 rounded-xl group">
                            <div className="flex items-center justify-center shrink-0 w-8 h-8 rounded-full bg-[#0fbd9a]/10 text-[#0fbd9a] transition-colors group-hover:bg-[#0fbd9a] group-hover:text-white">
                                <Users className="w-4 h-4" />
                            </div>
                            <div className="flex flex-col">
                                <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Founder Cohort</span>
                                <span className="text-sm font-bold text-[#0d1b19]">Help shape the first workflows we release.</span>
                            </div>
                            <div className="ml-auto text-gray-300 group-hover:text-[#0fbd9a] transition-colors">
                                <ArrowRight className="w-4 h-4" />
                            </div>
                        </div>

                        <div className="bg-white shadow-[4px_4px_8px_#d1d5db,-4px_-4px_8px_#ffffff] hover:shadow-[6px_6px_10px_#d1d5db,-6px_-6px_10px_#ffffff] hover:-translate-y-0.5 transition-all duration-200 flex items-center gap-3 p-3 rounded-xl group">
                            <div className="flex items-center justify-center shrink-0 w-8 h-8 rounded-full bg-[#0fbd9a]/10 text-[#0fbd9a] transition-colors group-hover:bg-[#0fbd9a] group-hover:text-white">
                                <Sparkles className="w-4 h-4" />
                            </div>
                            <div className="flex flex-col">
                                <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Launch Updates</span>
                                <span className="text-sm font-bold text-[#0d1b19]">Get product drops and launch signals without the noise.</span>
                            </div>
                            <div className="ml-auto text-gray-300 group-hover:text-[#0fbd9a] transition-colors">
                                <ArrowRight className="w-4 h-4" />
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Right Column: Form */}
            <div className="relative w-full lg:w-7/12 min-h-[400px] lg:h-auto bg-[#f6f8f8] bg-[radial-gradient(#cbd5e1_1.5px,transparent_1.5px)] bg-[length:16px_16px] flex items-center justify-center p-4 lg:p-8">
                {/* Claymorphic Container */}
                <div className="w-full max-w-md p-6 lg:p-8 rounded-[1.5rem] relative overflow-hidden bg-[linear-gradient(145deg,#0e302e,#091e1d)]">
                    {/* Decorative glow */}
                    <div className="absolute top-[-20%] right-[-10%] w-[150px] h-[150px] bg-[#0fbd9a]/20 rounded-full blur-[50px] pointer-events-none"></div>
                    <div className="absolute bottom-[-10%] left-[-10%] w-[100px] h-[100px] bg-teal-500/10 rounded-full blur-[40px] pointer-events-none"></div>

                    <div className="relative z-10 flex flex-col h-full min-h-[300px] justify-center">
                        {isSubmitted ? (
                            <motion.div
                                initial={{ opacity: 0, scale: 0.8 }}
                                animate={{ opacity: 1, scale: 1 }}
                                className="flex flex-col items-center justify-center h-full text-center space-y-4"
                            >
                                <div className="w-16 h-16 bg-[#0fbd9a] rounded-full flex items-center justify-center shadow-[6px_6px_12px_rgba(0,0,0,0.3),-4px_-4px_12px_rgba(255,255,255,0.1),inset_0px_-2px_0px_rgba(0,0,0,0.1)]">
                                    <CheckCircle className="w-8 h-8 text-[#0d2d2d]" strokeWidth={3} />
                                </div>
                                <div className="space-y-1.5">
                                    <h3 className="text-xl font-bold text-white mb-1">You’re on the waitlist.</h3>
                                    <p className="text-white/60 text-xs max-w-xs mx-auto">We will send early-access invites, launch updates, and first access to beta workflows from this list.</p>
                                </div>
                                <button onClick={() => setIsSubmitted(false)} className="text-[#0fbd9a] hover:text-white transition-colors font-bold text-[10px] uppercase tracking-wider flex items-center gap-1.5 mt-2 cursor-pointer">
                                    Add another founder
                                </button>
                            </motion.div>
                        ) : (
                            <>
                                <div className="mb-6">
                                    <h2 className="text-xl font-bold text-white mb-1">Join the waitlist</h2>
                                    <p className="text-white/60 text-xs">Tell us who you are and what you want automated first. This helps us shape the first beta wave.</p>
                                </div>

                                <form className="space-y-4 flex-1 flex flex-col justify-center" onSubmit={handleSubmit}>
                                    <div className="space-y-1">
                                        <label className="block text-xs font-medium text-[#0fbd9a] ml-3" htmlFor="name">Full Name</label>
                                        <div className="relative">
                                            <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-[#0fbd9a]/50">
                                                <User className="w-3.5 h-3.5" />
                                            </div>
                                            <input
                                                className="w-full rounded-full py-2.5 pl-10 pr-4 text-sm text-white placeholder:text-white/30 bg-[rgba(15,189,154,0.05)] backdrop-blur-md border border-[rgba(15,189,154,0.2)] shadow-[inset_1px_1px_3px_rgba(0,0,0,0.2),inset_-1px_-1px_3px_rgba(255,255,255,0.05)] focus:bg-[rgba(15,189,154,0.1)] focus:border-[rgba(15,189,154,0.6)] focus:outline-none focus:shadow-[inset_1px_1px_3px_rgba(0,0,0,0.3),0_0_10px_rgba(15,189,154,0.2)] transition-all duration-300"
                                                id="name"
                                                placeholder="Jane Founder"
                                                type="text"
                                                value={form.fullName}
                                                onChange={handleChange('fullName')}
                                                required
                                            />
                                        </div>
                                    </div>

                                    <div className="space-y-1">
                                        <label className="block text-xs font-medium text-[#0fbd9a] ml-3" htmlFor="email">Work Email</label>
                                        <div className="relative">
                                            <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-[#0fbd9a]/50">
                                                <AtSign className="w-3.5 h-3.5" />
                                            </div>
                                            <input
                                                className="w-full rounded-full py-2.5 pl-10 pr-4 text-sm text-white placeholder:text-white/30 bg-[rgba(15,189,154,0.05)] backdrop-blur-md border border-[rgba(15,189,154,0.2)] shadow-[inset_1px_1px_3px_rgba(0,0,0,0.2),inset_-1px_-1px_3px_rgba(255,255,255,0.05)] focus:bg-[rgba(15,189,154,0.1)] focus:border-[rgba(15,189,154,0.6)] focus:outline-none focus:shadow-[inset_1px_1px_3px_rgba(0,0,0,0.3),0_0_10px_rgba(15,189,154,0.2)] transition-all duration-300"
                                                id="email"
                                                placeholder="john@company.com"
                                                type="email"
                                                value={form.email}
                                                onChange={handleChange('email')}
                                                required
                                            />
                                        </div>
                                    </div>

                                    <div className="space-y-1">
                                        <label className="block text-xs font-medium text-[#0fbd9a] ml-3" htmlFor="companyOrRole">Company or Role</label>
                                        <div className="relative">
                                            <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-[#0fbd9a]/50">
                                                <BriefcaseBusiness className="w-3.5 h-3.5" />
                                            </div>
                                            <input
                                                className="w-full rounded-full py-2.5 pl-10 pr-4 text-sm text-white placeholder:text-white/30 bg-[rgba(15,189,154,0.05)] backdrop-blur-md border border-[rgba(15,189,154,0.2)] shadow-[inset_1px_1px_3px_rgba(0,0,0,0.2),inset_-1px_-1px_3px_rgba(255,255,255,0.05)] focus:bg-[rgba(15,189,154,0.1)] focus:border-[rgba(15,189,154,0.6)] focus:outline-none focus:shadow-[inset_1px_1px_3px_rgba(0,0,0,0.3),0_0_10px_rgba(15,189,154,0.2)] transition-all duration-300"
                                                id="companyOrRole"
                                                placeholder="Founder, COO, or your company"
                                                type="text"
                                                value={form.companyOrRole}
                                                onChange={handleChange('companyOrRole')}
                                            />
                                        </div>
                                    </div>

                                    <div className="space-y-1">
                                        <label className="block text-xs font-medium text-[#0fbd9a] ml-3" htmlFor="message">Biggest Bottleneck</label>
                                        <div className="relative">
                                            <textarea
                                                className="w-full rounded-[1.5rem] py-2.5 px-4 text-sm text-white placeholder:text-white/30 bg-[rgba(15,189,154,0.05)] backdrop-blur-md border border-[rgba(15,189,154,0.2)] shadow-[inset_1px_1px_3px_rgba(0,0,0,0.2),inset_-1px_-1px_3px_rgba(255,255,255,0.05)] focus:bg-[rgba(15,189,154,0.1)] focus:border-[rgba(15,189,154,0.6)] focus:outline-none focus:shadow-[inset_1px_1px_3px_rgba(0,0,0,0.3),0_0_10px_rgba(15,189,154,0.2)] transition-all duration-300 resize-none"
                                                id="message"
                                                placeholder="What do you want an AI executive team to take off your plate first?"
                                                rows={3}
                                                value={form.biggestBottleneck}
                                                onChange={handleChange('biggestBottleneck')}
                                            ></textarea>
                                        </div>
                                    </div>

                                    <input
                                        className="hidden"
                                        type="text"
                                        name="website"
                                        autoComplete="off"
                                        tabIndex={-1}
                                        value={form.website}
                                        onChange={handleChange('website')}
                                    />

                                    {error ? (
                                        <p className="text-xs text-[#f8b4b4] px-2">
                                            {error}
                                        </p>
                                    ) : null}

                                    <div className="pt-2">
                                        <button
                                            className="w-full cursor-pointer py-3 rounded-full text-sm font-bold flex items-center justify-center gap-2 group bg-white text-[#0d2d2d] shadow-[4px_4px_8px_rgba(0,0,0,0.3),-2px_-2px_8px_rgba(255,255,255,0.1),inset_0px_-2px_0px_rgba(0,0,0,0.1)] active:translate-y-[1px] active:shadow-[1px_1px_3px_rgba(0,0,0,0.3),-1px_-1px_3px_rgba(255,255,255,0.1),inset_0px_-1px_0px_rgba(0,0,0,0.1)] transition-all duration-200 disabled:cursor-not-allowed disabled:opacity-70"
                                            type="submit"
                                            disabled={isSubmitting}
                                        >
                                            {isSubmitting ? 'Joining Waitlist...' : 'Join Waitlist'}
                                            {isSubmitting ? (
                                                <LoaderCircle className="w-3.5 h-3.5 animate-spin" />
                                            ) : (
                                                <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
                                            )}
                                        </button>
                                    </div>
                                </form>
                            </>
                        )}
                    </div>
                </div>
            </div>
        </section>
    );
}
