
import React from 'react';
import { ArrowRight, User, Users, Building2, Building } from 'lucide-react';

const PERSONA_ICONS = [
    { icon: User, emoji: '🚀', gradient: 'from-teal-400 to-emerald-500' },
    { icon: Users, emoji: '💡', gradient: 'from-cyan-400 to-teal-500' },
    { icon: Building2, emoji: '🏢', gradient: 'from-emerald-400 to-green-500' },
    { icon: Building, emoji: '🏛️', gradient: 'from-teal-500 to-cyan-600' },
];

const BuiltForGrowthSection = () => {
    return (
        <section id="solutions" className="relative overflow-hidden pt-24 pb-16 bg-[var(--muted)]">
            {/* Background Effects - Confined to this section */}
            <div className="absolute inset-0 z-0 pointer-events-none">
                <div className="absolute inset-0 bg-dot-pattern opacity-60"></div>
                <div className="absolute top-0 left-0 w-96 h-96 bg-[#0F766E]/20 rounded-full mix-blend-multiply filter blur-3xl opacity-40 animate-blob"></div>
                <div className="absolute top-0 right-0 w-96 h-96 bg-teal-400/20 rounded-full mix-blend-multiply filter blur-3xl opacity-40 animate-blob animation-delay-2000"></div>
                <div className="absolute -bottom-32 left-20 w-80 h-80 bg-emerald-300/30 rounded-full mix-blend-multiply filter blur-3xl opacity-40 animate-blob animation-delay-4000"></div>
            </div>

            <div className="relative z-10 container mx-auto px-4 flex flex-col items-center justify-center">
                <div className="text-center max-w-3xl mx-auto mb-32">
                    <h2 className="text-3xl md:text-4xl lg:text-5xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-teal-800 to-emerald-600 mb-6 drop-shadow-sm tracking-tight font-display">
                        Built for every stage of growth
                    </h2>
                    <p className="text-base md:text-lg text-slate-600 max-w-2xl mx-auto leading-relaxed font-sans">
                        Select your role to see how Pikar AI transforms your workflow with intelligent automation and insights.
                    </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-x-8 gap-y-16 sm:gap-y-24 w-full max-w-7xl mx-auto px-4">

                    {/* Solopreneur Card */}
                    <div className="group relative pt-16">
                        <div className="absolute -top-16 sm:-top-20 left-1/2 transform -translate-x-1/2 z-20 w-24 h-36 sm:w-32 sm:h-44 transition-transform duration-500 group-hover:scale-110 group-hover:-translate-y-4 flex items-center justify-center">
                            <div className={`w-20 h-20 sm:w-24 sm:h-24 rounded-full bg-gradient-to-br ${PERSONA_ICONS[0].gradient} flex items-center justify-center shadow-[0_20px_20px_rgba(0,0,0,0.3)]`}>
                                <span className="text-3xl sm:text-4xl">{PERSONA_ICONS[0].emoji}</span>
                            </div>
                        </div>
                        <div className="relative rounded-[2.5rem] shadow-clay-persona p-2 overflow-visible transition-all duration-300 hover:shadow-2xl" style={{ backgroundImage: 'linear-gradient(to bottom, #0a2e2e, var(--teal-900), #061a1a)' }}>
                            <div className="absolute inset-0 rounded-[2.5rem] bg-gradient-to-b from-white/10 to-transparent pointer-events-none"></div>
                            <div className="bg-teal-900/40 backdrop-blur-sm rounded-[2rem] p-5 pt-16 sm:pt-20 h-full border border-white/10 shadow-clay-inset-persona flex flex-col items-center text-center relative overflow-hidden">
                                <div className="absolute top-0 left-1/2 -translate-x-1/2 w-32 h-1 bg-teal-300/50 blur-md rounded-full"></div>
                                <h3 className="text-xl font-bold text-white mb-2 tracking-wide drop-shadow-md font-display">Solopreneur</h3>
                                <p className="text-teal-100/80 text-xs mb-6 leading-relaxed font-sans">
                                    Maximize efficiency and speed for one.
                                </p>
                                <div className="flex flex-wrap justify-center gap-2 mb-8 w-full">
                                    <span className="px-3 py-1 rounded-full text-[10px] font-semibold text-teal-50 bg-white/10 backdrop-blur-md border border-white/20 shadow-pills">
                                        Efficiency
                                    </span>
                                    <span className="px-3 py-1 rounded-full text-[10px] font-semibold text-teal-50 bg-white/10 backdrop-blur-md border border-white/20 shadow-pills">
                                        Speed
                                    </span>
                                </div>
                                <a href="/auth/signup" className="mt-auto w-full group/btn relative overflow-hidden rounded-xl bg-gradient-to-r from-teal-500/20 to-teal-600/20 border border-white/10 p-0.5 transition-all hover:scale-[1.02] cursor-pointer block">
                                    <div className="relative rounded-[10px] bg-gradient-to-b from-teal-600/50 to-teal-800/50 px-6 py-3 shadow-[inset_0_1px_1px_rgba(255,255,255,0.3)] transition-colors group-hover/btn:from-teal-500/60 group-hover/btn:to-teal-700/60">
                                        <span className="flex items-center justify-center text-sm font-bold text-white tracking-wider font-sans">
                                            Explore <ArrowRight className="w-4 h-4 ml-1 transform group-hover/btn:translate-x-1 transition-transform" />
                                        </span>
                                    </div>
                                </a>
                            </div>
                        </div>
                    </div>

                    {/* Founder Card */}
                    <div className="group relative pt-16">
                        <div className="absolute -top-16 sm:-top-20 left-1/2 transform -translate-x-1/2 z-20 w-24 h-36 sm:w-32 sm:h-44 transition-transform duration-500 group-hover:scale-110 group-hover:-translate-y-4 flex items-center justify-center">
                            <div className={`w-20 h-20 sm:w-24 sm:h-24 rounded-full bg-gradient-to-br ${PERSONA_ICONS[1].gradient} flex items-center justify-center shadow-[0_20px_20px_rgba(0,0,0,0.3)]`}>
                                <span className="text-3xl sm:text-4xl">{PERSONA_ICONS[1].emoji}</span>
                            </div>
                        </div>
                        <div className="relative rounded-[2.5rem] shadow-clay-persona p-2 overflow-visible transition-all duration-300 hover:shadow-2xl" style={{ backgroundImage: 'linear-gradient(to bottom, #0a2e2e, var(--teal-900), #061a1a)' }}>
                            <div className="absolute inset-0 rounded-[2.5rem] bg-gradient-to-b from-white/10 to-transparent pointer-events-none"></div>
                            <div className="bg-teal-900/40 backdrop-blur-sm rounded-[2rem] p-5 pt-16 sm:pt-20 h-full border border-white/10 shadow-clay-inset-persona flex flex-col items-center text-center relative overflow-hidden">
                                <div className="absolute top-0 left-1/2 -translate-x-1/2 w-32 h-1 bg-teal-300/50 blur-md rounded-full"></div>
                                <h3 className="text-xl font-bold text-white mb-2 tracking-wide drop-shadow-md font-display">Founder</h3>
                                <p className="text-teal-100/80 text-xs mb-6 leading-relaxed font-sans">
                                    Scale your vision from MVP to IPO.
                                </p>
                                <div className="flex flex-wrap justify-center gap-2 mb-8 w-full">
                                    <span className="px-3 py-1 rounded-full text-[10px] font-semibold text-teal-50 bg-white/10 backdrop-blur-md border border-white/20 shadow-pills">
                                        Fundraising
                                    </span>
                                    <span className="px-3 py-1 rounded-full text-[10px] font-semibold text-teal-50 bg-white/10 backdrop-blur-md border border-white/20 shadow-pills">
                                        MVP
                                    </span>
                                </div>
                                <a href="/auth/signup" className="mt-auto w-full group/btn relative overflow-hidden rounded-xl bg-gradient-to-r from-teal-500/20 to-teal-600/20 border border-white/10 p-0.5 transition-all hover:scale-[1.02] cursor-pointer block">
                                    <div className="relative rounded-[10px] bg-gradient-to-b from-teal-600/50 to-teal-800/50 px-6 py-3 shadow-[inset_0_1px_1px_rgba(255,255,255,0.3)] transition-colors group-hover/btn:from-teal-500/60 group-hover/btn:to-teal-700/60">
                                        <span className="flex items-center justify-center text-sm font-bold text-white tracking-wider font-sans">
                                            Explore <ArrowRight className="w-4 h-4 ml-1 transform group-hover/btn:translate-x-1 transition-transform" />
                                        </span>
                                    </div>
                                </a>
                            </div>
                        </div>
                    </div>

                    {/* Owner Card */}
                    <div className="group relative pt-16">
                        <div className="absolute -top-16 sm:-top-20 left-1/2 transform -translate-x-1/2 z-20 w-24 h-36 sm:w-32 sm:h-44 transition-transform duration-500 group-hover:scale-110 group-hover:-translate-y-4 flex items-center justify-center">
                            <div className={`w-20 h-20 sm:w-24 sm:h-24 rounded-full bg-gradient-to-br ${PERSONA_ICONS[2].gradient} flex items-center justify-center shadow-[0_20px_20px_rgba(0,0,0,0.3)]`}>
                                <span className="text-3xl sm:text-4xl">{PERSONA_ICONS[2].emoji}</span>
                            </div>
                        </div>
                        <div className="relative rounded-[2.5rem] shadow-clay-persona p-2 overflow-visible transition-all duration-300 hover:shadow-2xl" style={{ backgroundImage: 'linear-gradient(to bottom, #0a2e2e, var(--teal-900), #061a1a)' }}>
                            <div className="absolute inset-0 rounded-[2.5rem] bg-gradient-to-b from-white/10 to-transparent pointer-events-none"></div>
                            <div className="bg-teal-900/40 backdrop-blur-sm rounded-[2rem] p-5 pt-16 sm:pt-20 h-full border border-white/10 shadow-clay-inset-persona flex flex-col items-center text-center relative overflow-hidden">
                                <div className="absolute top-0 left-1/2 -translate-x-1/2 w-32 h-1 bg-teal-300/50 blur-md rounded-full"></div>
                                <h3 className="text-xl font-bold text-white mb-2 tracking-wide drop-shadow-md font-display">Owner</h3>
                                <p className="text-teal-100/80 text-xs mb-6 leading-relaxed font-sans">
                                    Operational stability you can trust.
                                </p>
                                <div className="flex flex-wrap justify-center gap-2 mb-8 w-full">
                                    <span className="px-3 py-1 rounded-full text-[10px] font-semibold text-teal-50 bg-white/10 backdrop-blur-md border border-white/20 shadow-pills">
                                        Operations
                                    </span>
                                    <span className="px-3 py-1 rounded-full text-[10px] font-semibold text-teal-50 bg-white/10 backdrop-blur-md border border-white/20 shadow-pills">
                                        Stability
                                    </span>
                                </div>
                                <a href="/auth/signup" className="mt-auto w-full group/btn relative overflow-hidden rounded-xl bg-gradient-to-r from-teal-500/20 to-teal-600/20 border border-white/10 p-0.5 transition-all hover:scale-[1.02] cursor-pointer block">
                                    <div className="relative rounded-[10px] bg-gradient-to-b from-teal-600/50 to-teal-800/50 px-6 py-3 shadow-[inset_0_1px_1px_rgba(255,255,255,0.3)] transition-colors group-hover/btn:from-teal-500/60 group-hover/btn:to-teal-700/60">
                                        <span className="flex items-center justify-center text-sm font-bold text-white tracking-wider font-sans">
                                            Explore <ArrowRight className="w-4 h-4 ml-1 transform group-hover/btn:translate-x-1 transition-transform" />
                                        </span>
                                    </div>
                                </a>
                            </div>
                        </div>
                    </div>

                    {/* Executive Card */}
                    <div className="group relative pt-16">
                        <div className="absolute -top-16 sm:-top-20 left-1/2 transform -translate-x-1/2 z-20 w-24 h-36 sm:w-32 sm:h-44 transition-transform duration-500 group-hover:scale-110 group-hover:-translate-y-4 flex items-center justify-center">
                            <div className={`w-20 h-20 sm:w-24 sm:h-24 rounded-full bg-gradient-to-br ${PERSONA_ICONS[3].gradient} flex items-center justify-center shadow-[0_20px_20px_rgba(0,0,0,0.3)]`}>
                                <span className="text-3xl sm:text-4xl">{PERSONA_ICONS[3].emoji}</span>
                            </div>
                        </div>
                        <div className="relative rounded-[2.5rem] shadow-clay-persona p-2 overflow-visible transition-all duration-300 hover:shadow-2xl" style={{ backgroundImage: 'linear-gradient(to bottom, #0a2e2e, var(--teal-900), #061a1a)' }}>
                            <div className="absolute inset-0 rounded-[2.5rem] bg-gradient-to-b from-white/10 to-transparent pointer-events-none"></div>
                            <div className="bg-teal-900/40 backdrop-blur-sm rounded-[2rem] p-5 pt-16 sm:pt-20 h-full border border-white/10 shadow-clay-inset-persona flex flex-col items-center text-center relative overflow-hidden">
                                <div className="absolute top-0 left-1/2 -translate-x-1/2 w-32 h-1 bg-teal-300/50 blur-md rounded-full"></div>
                                <h3 className="text-xl font-bold text-white mb-2 tracking-wide drop-shadow-md font-display">Executive</h3>
                                <p className="text-teal-100/80 text-xs mb-6 leading-relaxed font-sans">
                                    Enterprise-grade security &amp; control.
                                </p>
                                <div className="flex flex-wrap justify-center gap-2 mb-8 w-full">
                                    <span className="px-3 py-1 rounded-full text-[10px] font-semibold text-teal-50 bg-white/10 backdrop-blur-md border border-white/20 shadow-pills">
                                        Enterprise
                                    </span>
                                    <span className="px-3 py-1 rounded-full text-[10px] font-semibold text-teal-50 bg-white/10 backdrop-blur-md border border-white/20 shadow-pills">
                                        Security
                                    </span>
                                </div>
                                <a href="/auth/signup" className="mt-auto w-full group/btn relative overflow-hidden rounded-xl bg-gradient-to-r from-teal-500/20 to-teal-600/20 border border-white/10 p-0.5 transition-all hover:scale-[1.02] cursor-pointer block">
                                    <div className="relative rounded-[10px] bg-gradient-to-b from-teal-600/50 to-teal-800/50 px-6 py-3 shadow-[inset_0_1px_1px_rgba(255,255,255,0.3)] transition-colors group-hover/btn:from-teal-500/60 group-hover/btn:to-teal-700/60">
                                        <span className="flex items-center justify-center text-sm font-bold text-white tracking-wider font-sans">
                                            Explore <ArrowRight className="w-4 h-4 ml-1 transform group-hover/btn:translate-x-1 transition-transform" />
                                        </span>
                                    </div>
                                </a>
                            </div>
                        </div>
                    </div>

                </div>
            </div>
        </section>
    );
};

export default BuiltForGrowthSection;
