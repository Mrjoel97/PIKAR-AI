"use client";

import React from "react";
import {
    BrainCircuit,
    ClipboardCheck,
    Workflow,
    PenTool,
    Rocket,
    Zap,
    LayoutGrid,
    ShieldCheck
} from "lucide-react";

export default function ProductSystem() {
    return (
        <section className="relative w-full py-8 md:py-14 bg-white dark:bg-[#0f172a] overflow-hidden transition-colors duration-300">
            {/* Background Pattern */}
            {/* Background Pattern */}
            <div className="absolute inset-0 pointer-events-none z-0 opacity-70"
                style={{
                    backgroundImage: "linear-gradient(rgba(13, 148, 136, 0.15) 2px, transparent 2px), linear-gradient(90deg, rgba(13, 148, 136, 0.15) 2px, transparent 2px)",
                    backgroundSize: "40px 40px"
                }}>
            </div>

            <div className="relative z-10 w-full max-w-7xl mx-auto px-4 flex flex-col items-center">

                {/* Header */}
                <div className="text-center mb-8 space-y-2">
                    <div className="inline-flex items-center px-2 py-0.5 rounded-full border border-white/10" style={{ backgroundImage: 'linear-gradient(to bottom, #0a2e2e, var(--teal-900), #061a1a)' }}>
                        <span className="text-[9px] md:text-[10px] font-semibold text-white tracking-wide uppercase">Pikar AI Product Lifecycle Automation V2</span>
                    </div>
                    <h1 className="text-2xl md:text-3xl lg:text-4xl font-extrabold tracking-tight text-slate-900 dark:text-white leading-tight font-display">
                        From Insights to <span className="text-[#06b6d4]">Launch</span>:<br />
                        The Product <span className="text-[#06b6d4]">AI-System</span>
                    </h1>
                </div>

                {/* Diagram Section */}
                <div className="relative w-full grid grid-cols-1 lg:grid-cols-12 gap-5 items-center justify-items-center">

                    {/* SVG Connector Lines (Visible on Desktop) */}
                    <svg className="absolute inset-0 w-full h-full pointer-events-none hidden lg:block z-0" preserveAspectRatio="none" viewBox="0 0 1200 600">
                        <path className="opacity-40 dark:opacity-60" d="M 350 150 C 450 150, 480 250, 550 280" fill="none" stroke="#0d6b4f" strokeLinecap="round" strokeWidth="3"></path>
                        <path className="opacity-40 dark:opacity-60" d="M 350 450 C 450 450, 480 350, 550 320" fill="none" stroke="#0d6b4f" strokeLinecap="round" strokeWidth="3"></path>
                        <path className="opacity-40 dark:opacity-60" d="M 850 150 C 750 150, 720 250, 650 280" fill="none" stroke="#0d6b4f" strokeLinecap="round" strokeWidth="3"></path>
                        <path className="opacity-40 dark:opacity-60" d="M 850 450 C 750 450, 720 350, 650 320" fill="none" stroke="#0d6b4f" strokeLinecap="round" strokeWidth="3"></path>
                    </svg>

                    {/* Left Column Cards */}
                    <div className="lg:col-span-4 flex flex-col gap-5 md:gap-8 w-full max-w-sm z-10">

                        {/* Market Research Card */}
                        <div className="bg-white dark:bg-[#1e293b] rounded-xl shadow-[0_10px_30px_-5px_rgba(0,0,0,0.1),0_5px_15px_-5px_rgba(0,0,0,0.05)] dark:shadow-[0_10px_30px_-5px_rgba(0,0,0,0.3)] p-3 border-2 border-slate-100 dark:border-slate-700 relative group flex items-start gap-3 hover:-translate-y-1 transition-all duration-300">
                            <div className="w-20 h-20 shrink-0 relative rounded-lg overflow-hidden border border-slate-200 dark:border-slate-600 shadow-sm">
                                <img alt="Market analysis dashboard with charts" className="absolute inset-0 w-full h-full object-cover" src="/market_research.png" />
                                <div className="absolute inset-0 bg-[#0d6b4f]/10 group-hover:bg-transparent transition-colors duration-300"></div>
                            </div>
                            <div className="flex-1 flex flex-col">
                                <div className="flex items-center justify-between mb-1">
                                    <h3 className="text-sm font-bold text-slate-900 dark:text-white">Market Research</h3>
                                    <div className="w-6 h-6 rounded-md shadow-sm flex items-center justify-center" style={{ backgroundImage: 'linear-gradient(to bottom, #0a2e2e, var(--teal-900), #061a1a)' }}>
                                        <BrainCircuit className="text-white w-3.5 h-3.5" />
                                    </div>
                                </div>
                                <p className="text-[10px] text-slate-500 dark:text-slate-400 leading-snug mb-2">
                                    AI-powered analysis of global market trends and real-time consumer insights.
                                </p>
                                <div className="text-[9px] font-medium text-cyan-600 dark:text-cyan-400 bg-cyan-50 dark:bg-cyan-900/30 px-1.5 py-0.5 rounded w-fit">
                                    +45% Accuracy
                                </div>
                            </div>
                        </div>

                        {/* QA & Testing Card */}
                        <div className="bg-white dark:bg-[#1e293b] rounded-xl shadow-[0_10px_30px_-5px_rgba(0,0,0,0.1),0_5px_15px_-5px_rgba(0,0,0,0.05)] dark:shadow-[0_10px_30px_-5px_rgba(0,0,0,0.3)] p-3 border-2 border-slate-100 dark:border-slate-700 relative group flex items-start gap-3 hover:-translate-y-1 transition-all duration-300">
                            <div className="w-20 h-20 shrink-0 relative rounded-lg overflow-hidden border border-slate-200 dark:border-slate-600 shadow-sm">
                                <img alt="Automated QA robot arm in lab" className="absolute inset-0 w-full h-full object-cover" src="/qa_testing.png" />
                                <div className="absolute inset-0 bg-[#0d6b4f]/10 group-hover:bg-transparent transition-colors duration-300"></div>
                            </div>
                            <div className="flex-1 flex flex-col">
                                <div className="flex items-center justify-between mb-1">
                                    <h3 className="text-sm font-bold text-slate-900 dark:text-white">QA & Testing</h3>
                                    <div className="w-6 h-6 rounded-md shadow-sm flex items-center justify-center" style={{ backgroundImage: 'linear-gradient(to bottom, #0a2e2e, var(--teal-900), #061a1a)' }}>
                                        <ClipboardCheck className="text-white w-3.5 h-3.5" />
                                    </div>
                                </div>
                                <p className="text-[10px] text-slate-500 dark:text-slate-400 leading-snug mb-2">
                                    Automated testing flows ensuring zero-bug releases and robust quality assurance.
                                </p>
                                <div className="text-[9px] font-medium text-cyan-600 dark:text-cyan-400 bg-cyan-50 dark:bg-cyan-900/30 px-1.5 py-0.5 rounded w-fit">
                                    Zero Defects
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Center Hub */}
                    <div className="lg:col-span-4 flex justify-center items-center py-4 lg:py-0 z-20">
                        <div className="relative w-32 h-32 md:w-40 md:h-40 rounded-full flex items-center justify-center bg-white dark:bg-slate-900 p-1 shadow-[0_0_30px_-5px_rgba(6,182,212,0.3)] dark:shadow-[0_0_30px_-5px_rgba(6,182,212,0.15)]">
                            <div className="absolute inset-0 rounded-full border border-dashed border-cyan-200 dark:border-cyan-800 animate-[spin_20s_linear_infinite]"></div>
                            <div className="relative w-full h-full rounded-full overflow-hidden bg-slate-900 shadow-inner flex items-center justify-center border-2 border-slate-100 dark:border-slate-800">
                                <img alt="High fidelity 3D isometric circular hub with glowing teal circuits" className="object-cover w-full h-full opacity-90 hover:scale-105 transition-transform duration-700" src="https://lh3.googleusercontent.com/aida-public/AB6AXuDTqMKi1bAitjz32T5f_CnNSItG6YJ_dgVlw8bY_w_HqqBaxfImUljSM2xZ7owcFteffbZvzowZxBgx8qs_yFazI98MRLmpBbY4UGpm1yAteGQQjr-NSziRSX9Kd-V2J2q3e3pKH73C7ZBcOYHb8bgM41RlkOlQEx1HlNkjxNumRNpg-E8tJMPXY19LySQz_sVD-KdrbVlfOIPcJMx8wMRzzsCN2IIU8L94Ee0QBum7pPwhbyexfZlDTXLbWOIyJTPgaG2weXwtzKs" />
                                <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/40 backdrop-blur-[2px]">
                                    <Workflow className="text-cyan-400 w-6 h-6 mb-0.5 drop-shadow-lg" />
                                    <h2 className="text-white font-bold text-center text-[10px] md:text-xs tracking-wider drop-shadow-md">PRODUCT LAB<br />CORE V2.0</h2>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Right Column Cards */}
                    <div className="lg:col-span-4 flex flex-col gap-5 md:gap-8 w-full max-w-sm z-10">

                        {/* Prototype Design Card */}
                        <div className="bg-white dark:bg-[#1e293b] rounded-xl shadow-[0_10px_30px_-5px_rgba(0,0,0,0.1),0_5px_15px_-5px_rgba(0,0,0,0.05)] dark:shadow-[0_10px_30px_-5px_rgba(0,0,0,0.3)] p-3 border-2 border-slate-100 dark:border-slate-700 relative group flex items-start gap-3 hover:-translate-y-1 transition-all duration-300 flex-row-reverse">
                            <div className="w-20 h-20 shrink-0 relative rounded-lg overflow-hidden border border-slate-200 dark:border-slate-600 shadow-sm">
                                <img alt="Designer working on high fidelity prototype" className="absolute inset-0 w-full h-full object-cover" src="/prototype.png" />
                                <div className="absolute inset-0 bg-[#0d6b4f]/10 group-hover:bg-transparent transition-colors duration-300"></div>
                            </div>
                            <div className="flex-1 flex flex-col items-end text-right">
                                <div className="flex items-center justify-end w-full mb-1 gap-2 flex-row-reverse">
                                    <h3 className="text-sm font-bold text-slate-900 dark:text-white">Prototype Design</h3>
                                    <div className="w-6 h-6 rounded-md shadow-sm flex items-center justify-center" style={{ backgroundImage: 'linear-gradient(to bottom, #0a2e2e, var(--teal-900), #061a1a)' }}>
                                        <PenTool className="text-white w-3.5 h-3.5" />
                                    </div>
                                </div>
                                <p className="text-[10px] text-slate-500 dark:text-slate-400 leading-snug mb-2">
                                    Accelerated design iteration with generative AI tools for rapid prototyping.
                                </p>
                                <div className="text-[9px] font-medium text-cyan-600 dark:text-cyan-400 bg-cyan-50 dark:bg-cyan-900/30 px-1.5 py-0.5 rounded w-fit">
                                    10x Faster
                                </div>
                            </div>
                        </div>

                        {/* Launch Ops Card */}
                        <div className="bg-white dark:bg-[#1e293b] rounded-xl shadow-[0_10px_30px_-5px_rgba(0,0,0,0.1),0_5px_15px_-5px_rgba(0,0,0,0.05)] dark:shadow-[0_10px_30px_-5px_rgba(0,0,0,0.3)] p-3 border-2 border-slate-100 dark:border-slate-700 relative group flex items-start gap-3 hover:-translate-y-1 transition-all duration-300 flex-row-reverse">
                            <div className="w-20 h-20 shrink-0 relative rounded-lg overflow-hidden border border-slate-200 dark:border-slate-600 shadow-sm">
                                <img alt="Mission control room screens for launch operations" className="absolute inset-0 w-full h-full object-cover" src="/launch_ops.png" />
                                <div className="absolute inset-0 bg-[#0d6b4f]/10 group-hover:bg-transparent transition-colors duration-300"></div>
                            </div>
                            <div className="flex-1 flex flex-col items-end text-right">
                                <div className="flex items-center justify-end w-full mb-1 gap-2 flex-row-reverse">
                                    <h3 className="text-sm font-bold text-slate-900 dark:text-white">Launch Ops</h3>
                                    <div className="w-6 h-6 rounded-md shadow-sm flex items-center justify-center" style={{ backgroundImage: 'linear-gradient(to bottom, #0a2e2e, var(--teal-900), #061a1a)' }}>
                                        <Rocket className="text-white w-3.5 h-3.5" />
                                    </div>
                                </div>
                                <p className="text-[10px] text-slate-500 dark:text-slate-400 leading-snug mb-2">
                                    Seamless orchestration of go-to-market strategies with predictive timing.
                                </p>
                                <div className="text-[9px] font-medium text-cyan-600 dark:text-cyan-400 bg-cyan-50 dark:bg-cyan-900/30 px-1.5 py-0.5 rounded w-fit">
                                    Viral Launch
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Bottom Stats */}
                <div className="mt-10 grid grid-cols-1 md:grid-cols-3 gap-3 w-full max-w-xl z-10">
                    <div className="rounded-lg shadow-sm p-2 flex items-center gap-2 hover:-translate-y-1 transition-transform duration-300 border border-white/10" style={{ backgroundImage: 'linear-gradient(to bottom, #0a2e2e, var(--teal-900), #061a1a)' }}>
                        <div className="p-1 px-1.5 bg-white/20 rounded-md">
                            <Zap className="text-white w-4 h-4" />
                        </div>
                        <div>
                            <div className="text-sm font-bold text-white">10x</div>
                            <div className="text-[9px] font-semibold text-white/80 uppercase tracking-wider">Speed</div>
                        </div>
                    </div>

                    <div className="rounded-lg shadow-sm p-2 flex items-center gap-2 hover:-translate-y-1 transition-transform duration-300 border border-white/10" style={{ backgroundImage: 'linear-gradient(to bottom, #0a2e2e, var(--teal-900), #061a1a)' }}>
                        <div className="p-1 px-1.5 bg-white/20 rounded-md">
                            <LayoutGrid className="text-white w-4 h-4" />
                        </div>
                        <div>
                            <div className="text-sm font-bold text-white">500+</div>
                            <div className="text-[9px] font-semibold text-white/80 uppercase tracking-wider">Nodes</div>
                        </div>
                    </div>

                    <div className="rounded-lg shadow-sm p-2 flex items-center gap-2 hover:-translate-y-1 transition-transform duration-300 border border-white/10" style={{ backgroundImage: 'linear-gradient(to bottom, #0a2e2e, var(--teal-900), #061a1a)' }}>
                        <div className="p-1 px-1.5 bg-white/20 rounded-md">
                            <ShieldCheck className="text-white w-4 h-4" />
                        </div>
                        <div>
                            <div className="text-sm font-bold text-white">99.9%</div>
                            <div className="text-[9px] font-semibold text-white/80 uppercase tracking-wider">Uptime</div>
                        </div>
                    </div>
                </div>

            </div>
        </section>
    );
}
