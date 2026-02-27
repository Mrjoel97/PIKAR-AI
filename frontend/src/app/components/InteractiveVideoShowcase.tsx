"use client";

import React from "react";
import Image from "next/image";
import {
    Play,
    Pause,
    Settings,
    Maximize,
    Volume2,
    ArrowRight,
    Bot,
    Workflow,
    Rocket
} from "lucide-react";

export default function InteractiveVideoShowcase() {
    return (
        <section className="relative w-full py-12 px-4 sm:px-6 lg:px-8 mx-auto overflow-hidden bg-[#f5f8f8] dark:bg-[#101f22] transition-colors duration-300">
            {/* Background Grid */}
            <div className="absolute inset-0 bg-dot-grid pointer-events-none opacity-40 z-0"></div>

            <div className="relative z-10 flex-grow flex flex-col items-center justify-center w-full max-w-[1440px] mx-auto">
                <div className="w-full max-w-7xl mb-6 md:mb-10 px-4 text-center">
                    <h2 className="text-2xl md:text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white mb-4 font-display">
                        Pikar AI in Action
                    </h2>
                    <p className="text-slate-500 dark:text-slate-400 text-base md:text-lg max-w-2xl font-medium mx-auto">
                        Experience the next generation of autonomous workflow management.
                    </p>
                </div>

                <div className="w-full max-w-7xl grid grid-cols-1 lg:grid-cols-12 gap-5 lg:gap-10 items-start px-4">
                    <div className="lg:col-span-5 flex flex-col gap-4">

                        {/* Card 1: Deploy Agents */}
                        <div className="group relative bg-white dark:bg-gray-800 rounded-lg p-4 shadow-clay hover:shadow-clay-hover hover:-translate-y-1 transition-all duration-300 border border-transparent dark:border-gray-700 cursor-default">
                            <div className="flex items-center gap-4">
                                <div className="shrink-0 relative w-14 h-14 md:w-16 md:h-16 rounded-2xl overflow-hidden bg-[#0dccf2]/10 flex items-center justify-center">
                                    <Image src="https://lh3.googleusercontent.com/aida-public/AB6AXuCUuvdXPzvzTITK_D7K5y1Z5JZ_1rFw_JjoFPR4QaX9_YasypyrIcbQG192jBZksXxzI_rRZ90lM55zoOijsRI-_IcmlA7XzGayNxYQnCv-V4s0JqzUo5Aj5GqKNiCQWHQR6-WSIj1V6XDyFEBNA3MWSZJQtV7tLhjnVqAfUzZ_60U7QhsskkJbTrlBwswYScPVjEWvH-gKYRLHHRY5ZnudSfLJCH5jt6hSnFozWMZP1s949gb945u1D_bAvlhb95FShU8mchrKBo" alt="3D render of a smooth clay robot head" fill className="object-cover opacity-70" sizes="64px" />
                                    <Bot className="relative z-10 w-7 h-7 text-[#0dccf2]" />
                                </div>
                                <div className="flex flex-col justify-center flex-grow">
                                    <h3 className="text-lg font-bold text-slate-900 dark:text-white group-hover:text-[#0dccf2] transition-colors">
                                        Deploy Agents
                                    </h3>
                                    <p className="text-slate-500 dark:text-slate-400 text-xs font-medium leading-relaxed">
                                        Deploy intelligent workers that adapt to your business needs in real-time.
                                    </p>
                                </div>
                                <div className="shrink-0 text-[#0dccf2] opacity-0 group-hover:opacity-100 transition-opacity -translate-x-4 group-hover:translate-x-0 duration-300">
                                    <ArrowRight className="w-5 h-5" />
                                </div>
                            </div>
                        </div>

                        {/* Card 2: Architect Workflows */}
                        <div className="group relative bg-white dark:bg-gray-800 rounded-lg p-4 shadow-clay hover:shadow-clay-hover hover:-translate-y-1 transition-all duration-300 border border-transparent dark:border-gray-700 cursor-default">
                            <div className="flex items-center gap-4">
                                <div className="shrink-0 relative w-14 h-14 md:w-16 md:h-16 rounded-2xl overflow-hidden bg-[#0dccf2]/10 flex items-center justify-center">
                                    <Image src="https://lh3.googleusercontent.com/aida-public/AB6AXuB_4PF5k4kLQhc5LBxD5NVkpL5xbck_HLQSgmbquWz9LAtVafPFSzS68uKonBZZEgdN5awTdc3IK7p61dWOtMHc4dB2GJs-BzQctlr3JXz8sRjxlMf9Aut6nKZJIdnafW208DcrZjZ4melQ8zR-Gf5DE1RZgRhq_WByEhE60NrCwdB8zW3Os-5wX9DnbukvQBhuD8lgn_NLRrQf_zTujqvp5yCiUhg7VTUOOGS3j5-dWq2zfVMLVIbuDePsQnlYrqNwZafzSNsBCEU" alt="3D isometric connected nodes" fill className="object-cover opacity-70" sizes="64px" />
                                    <Workflow className="relative z-10 w-7 h-7 text-[#0dccf2]" />
                                </div>
                                <div className="flex flex-col justify-center flex-grow">
                                    <h3 className="text-lg font-bold text-slate-900 dark:text-white group-hover:text-[#0dccf2] transition-colors">
                                        Architect Workflows
                                    </h3>
                                    <p className="text-slate-500 dark:text-slate-400 text-xs font-medium leading-relaxed">
                                        Visualise complex decision trees and optimize paths instantly.
                                    </p>
                                </div>
                                <div className="shrink-0 text-[#0dccf2] opacity-0 group-hover:opacity-100 transition-opacity -translate-x-4 group-hover:translate-x-0 duration-300">
                                    <ArrowRight className="w-5 h-5" />
                                </div>
                            </div>
                        </div>

                        {/* Card 3: Instant Launch */}
                        <div className="group relative bg-white dark:bg-gray-800 rounded-lg p-4 shadow-clay hover:shadow-clay-hover hover:-translate-y-1 transition-all duration-300 border border-transparent dark:border-gray-700 cursor-default">
                            <div className="flex items-center gap-4">
                                <div className="shrink-0 relative w-14 h-14 md:w-16 md:h-16 rounded-2xl overflow-hidden bg-[#0dccf2]/10 flex items-center justify-center">
                                    <Image src="https://lh3.googleusercontent.com/aida-public/AB6AXuBsoOAGA0TyTXcmh4QELbaabYXBOrPidu8vOXQCJjYhpWHfbfnTJ1GeNot2nxjsr6IMkb9qcuqEw-fCvEr5e5CDBR_rJ6AuyHU4VJkTdLXzZdW_qDg56j6QfAKNu1Yu-Gjt1gkhZ7XwZ8kPC5WOIPFUBtzVBfVsHnKNVsKAyXutFXlzI619-7ZjUyqxKxEPWuLW1buGamxVf9nTJdpvEp2k-mvFZlCj0cxr_Gd_VL77UL1vm0FCcWB5IawDX7wyS_y4foGJJ5MfCk" alt="3D glowing teal rocket ship" fill className="object-cover opacity-70" sizes="64px" />
                                    <Rocket className="relative z-10 w-7 h-7 text-[#0dccf2]" />
                                </div>
                                <div className="flex flex-col justify-center flex-grow">
                                    <h3 className="text-lg font-bold text-slate-900 dark:text-white group-hover:text-[#0dccf2] transition-colors">
                                        Instant Launch
                                    </h3>
                                    <p className="text-slate-500 dark:text-slate-400 text-xs font-medium leading-relaxed">
                                        Push your trained agents to production environments in seconds.
                                    </p>
                                </div>
                                <div className="shrink-0 text-[#0dccf2] opacity-0 group-hover:opacity-100 transition-opacity -translate-x-4 group-hover:translate-x-0 duration-300">
                                    <ArrowRight className="w-5 h-5" />
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Right Column: Player */}
                    <div className="lg:col-span-7 flex flex-col h-full min-h-[350px]">
                        <div className="relative w-full h-full min-h-[260px] lg:min-h-[390px] rounded-lg overflow-hidden shadow-2xl group/player bg-gray-900">
                            <Image src="https://lh3.googleusercontent.com/aida-public/AB6AXuDyP713RQHpnjkRYBzjtDUjrt1wm3n_EpT6FT3AWUJnQqgXcJgtkp_OE_llC6N6HM17AW-6zFAxcmL6_HG7wD9bdxQi6unGdUHD7qU76OuDnCUHu0SWHK662UyqOofIB-sWiU2sCXpGsGGRdgr1k5Zd0c40oZIqMWJKxKkNGWtdCmC4rjqqYc-GB5YQ2zRyRWoCWa0VxzUh7QztOSRsh-nIUlgBU0eXV-yUNb4TEzmPulJSY_Eg4vB1hpFA8wT-7RlriYaCuoj_QR0" alt="Modern dashboard interface" fill className="object-cover transition-transform duration-700 group-hover/player:scale-105" sizes="(max-width: 1024px) 100vw, 58vw" />
                            <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-black/20 to-transparent"></div>

                            <div className="absolute inset-0 flex items-center justify-center z-20">
                                <button className="relative group/btn flex items-center justify-center">
                                    <div className="absolute inset-0 bg-[#0dccf2] rounded-full opacity-20 animate-ping"></div>
                                    <div className="relative bg-[#0dccf2] hover:bg-[#0bb5d6] text-white rounded-full p-4 lg:p-6 transition-all duration-300 transform group-hover/btn:scale-110 shadow-[0_0_30px_rgba(13,204,242,0.6)]">
                                        <Play className="w-6 h-6 lg:w-8 lg:h-8 fill-white" />
                                    </div>
                                </button>
                            </div>

                            <div className="absolute top-6 right-6 z-20">
                                <div className="glass-panel px-4 py-2 rounded-full flex items-center gap-2">
                                    <span className="relative flex h-3 w-3">
                                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                                        <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
                                    </span>
                                    <span className="text-white text-xs font-bold tracking-wide uppercase">Human in the Loop</span>
                                </div>
                            </div>

                            <div className="absolute bottom-6 left-6 right-6 z-20">
                                <div className="glass-panel p-4 rounded-xl flex flex-col gap-3">
                                    <div className="group/progress relative h-1.5 bg-white/20 rounded-full cursor-pointer overflow-hidden">
                                        <div className="absolute top-0 left-0 h-full w-[35%] bg-[#0dccf2] rounded-full"></div>
                                        <div className="absolute top-0 left-0 h-full w-full opacity-0 group-hover/progress:opacity-100 bg-white/10 transition-opacity"></div>
                                    </div>
                                    <div className="flex items-center justify-between text-white">
                                        <div className="flex items-center gap-4">
                                            <button className="hover:text-[#0dccf2] transition-colors">
                                                <Pause className="w-4 h-4 fill-current" />
                                            </button>
                                            <div className="flex items-center gap-1 text-xs font-medium font-mono">
                                                <span>00:34</span>
                                                <span className="opacity-50">/</span>
                                                <span className="opacity-50">02:15</span>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-4">
                                            <button className="hover:text-[#0dccf2] transition-colors">
                                                <Volume2 className="w-4 h-4" />
                                            </button>
                                            <button className="hover:text-[#0dccf2] transition-colors">
                                                <Settings className="w-4 h-4" />
                                            </button>
                                            <button className="hover:text-[#0dccf2] transition-colors">
                                                <Maximize className="w-4 h-4" />
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </section>
    );
}
