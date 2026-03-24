"use client";

import React, { useRef, useEffect } from "react";
import {
    ArrowRight,
    Bot,
    Workflow,
    Rocket
} from "lucide-react";

export default function InteractiveVideoShowcase() {
    const videoRef = useRef<HTMLVideoElement>(null);

    useEffect(() => {
        const video = videoRef.current;
        if (!video) return;
        // Mobile browsers block autoplay unless triggered after user interaction or muted.
        // Explicitly call play() to handle cases where the autoPlay attribute is ignored.
        video.play().catch(() => {
            // Autoplay blocked — video stays paused with poster/first frame visible
        });
    }, []);

    return (
        <section id="video" className="relative w-full py-12 px-4 sm:px-6 lg:px-8 mx-auto overflow-hidden bg-[#f5f8f8] dark:bg-[#101f22] transition-colors duration-300">
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
                                <div className="shrink-0 w-14 h-14 md:w-16 md:h-16 rounded-2xl bg-gradient-to-br from-[#3bbf97]/20 to-[#3bbf97]/5 flex items-center justify-center">
                                    <Bot className="w-7 h-7 text-[#3bbf97]" />
                                </div>
                                <div className="flex flex-col justify-center flex-grow">
                                    <h3 className="text-lg font-bold text-slate-900 dark:text-white group-hover:text-[#3bbf97] transition-colors">
                                        Deploy Agents
                                    </h3>
                                    <p className="text-slate-500 dark:text-slate-400 text-xs font-medium leading-relaxed">
                                        Deploy intelligent workers that adapt to your business needs in real-time.
                                    </p>
                                </div>
                                <div className="shrink-0 text-[#3bbf97] opacity-0 group-hover:opacity-100 transition-opacity -translate-x-4 group-hover:translate-x-0 duration-300">
                                    <ArrowRight className="w-5 h-5" />
                                </div>
                            </div>
                        </div>

                        {/* Card 2: Architect Workflows */}
                        <div className="group relative bg-white dark:bg-gray-800 rounded-lg p-4 shadow-clay hover:shadow-clay-hover hover:-translate-y-1 transition-all duration-300 border border-transparent dark:border-gray-700 cursor-default">
                            <div className="flex items-center gap-4">
                                <div className="shrink-0 w-14 h-14 md:w-16 md:h-16 rounded-2xl bg-gradient-to-br from-[#3bbf97]/20 to-[#3bbf97]/5 flex items-center justify-center">
                                    <Workflow className="w-7 h-7 text-[#3bbf97]" />
                                </div>
                                <div className="flex flex-col justify-center flex-grow">
                                    <h3 className="text-lg font-bold text-slate-900 dark:text-white group-hover:text-[#3bbf97] transition-colors">
                                        Architect Workflows
                                    </h3>
                                    <p className="text-slate-500 dark:text-slate-400 text-xs font-medium leading-relaxed">
                                        Visualise complex decision trees and optimize paths instantly.
                                    </p>
                                </div>
                                <div className="shrink-0 text-[#3bbf97] opacity-0 group-hover:opacity-100 transition-opacity -translate-x-4 group-hover:translate-x-0 duration-300">
                                    <ArrowRight className="w-5 h-5" />
                                </div>
                            </div>
                        </div>

                        {/* Card 3: Instant Launch */}
                        <div className="group relative bg-white dark:bg-gray-800 rounded-lg p-4 shadow-clay hover:shadow-clay-hover hover:-translate-y-1 transition-all duration-300 border border-transparent dark:border-gray-700 cursor-default">
                            <div className="flex items-center gap-4">
                                <div className="shrink-0 w-14 h-14 md:w-16 md:h-16 rounded-2xl bg-gradient-to-br from-[#3bbf97]/20 to-[#3bbf97]/5 flex items-center justify-center">
                                    <Rocket className="w-7 h-7 text-[#3bbf97]" />
                                </div>
                                <div className="flex flex-col justify-center flex-grow">
                                    <h3 className="text-lg font-bold text-slate-900 dark:text-white group-hover:text-[#3bbf97] transition-colors">
                                        Instant Launch
                                    </h3>
                                    <p className="text-slate-500 dark:text-slate-400 text-xs font-medium leading-relaxed">
                                        Push your trained agents to production environments in seconds.
                                    </p>
                                </div>
                                <div className="shrink-0 text-[#3bbf97] opacity-0 group-hover:opacity-100 transition-opacity -translate-x-4 group-hover:translate-x-0 duration-300">
                                    <ArrowRight className="w-5 h-5" />
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Right Column: MP4 Video */}
                    <div className="lg:col-span-7 flex flex-col h-full min-h-[350px]">
                        <div className="relative w-full h-full min-h-[260px] lg:min-h-[390px] rounded-lg overflow-hidden shadow-2xl bg-[#0a2e2e]">
                            <video
                                ref={videoRef}
                                autoPlay
                                loop
                                muted
                                playsInline
                                preload="auto"
                                className="w-full h-full object-cover"
                            >
                                <source src="/video/landing-demo.mp4" type="video/mp4" />
                            </video>
                        </div>
                    </div>
                </div>
            </div>
        </section>
    );
}
