"use client";

import React from 'react';
import Image from 'next/image';
import { Settings, Eye, Lock, RefreshCcw, ArrowUpRight, ArrowRight } from 'lucide-react';
import { motion } from 'framer-motion';

export default function HumanInTheLoopSection() {
    return (
        <section className="relative flex w-full flex-col lg:flex-row overflow-hidden bg-[#11211e] font-display">
            {/* Left Content Side */}
            <div className="flex flex-col justify-center w-full lg:w-1/2 p-6 md:p-10 lg:p-12 xl:pr-16 relative z-10">
                <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none -z-10">
                    <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-[#17cfaa]/5 rounded-full blur-[120px]"></div>
                </div>

                <div className="flex flex-col gap-5 max-w-2xl mx-auto lg:mx-0">
                    <div className="flex flex-col gap-2">
                        <motion.div
                            initial={{ opacity: 0, scale: 0.9 }}
                            whileInView={{ opacity: 1, scale: 1 }}
                            viewport={{ once: true }}
                            className="inline-flex items-center gap-2 px-3 py-0.5 rounded-full bg-[#17cfaa]/10 border border-[#17cfaa]/20 w-fit"
                        >
                            <Settings className="text-[#17cfaa] w-3.5 h-3.5" />
                            <span className="text-[#17cfaa] text-xs font-bold uppercase tracking-wider">Human in the Loop</span>
                        </motion.div>
                        <motion.h2
                            initial={{ opacity: 0, y: 10 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.1 }}
                            viewport={{ once: true }}
                            className="text-3xl md:text-4xl lg:text-5xl font-extrabold leading-tight tracking-tight text-white"
                        >
                            Human Intent. <br />
                            <span className="text-[#17cfaa] drop-shadow-[0_0_30px_rgba(23,207,170,0.4)]">AI Velocity.</span>
                        </motion.h2>
                        <motion.h2
                            initial={{ opacity: 0, y: 10 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.2 }}
                            viewport={{ once: true }}
                            className="text-base md:text-lg text-gray-400 font-medium leading-relaxed max-w-lg mt-1"
                        >
                            Pikar AI keeps humans at the center of the intelligence cycle. Review, refine, and deploy autonomous agents with total control.
                        </motion.h2>
                    </div>

                    <div className="flex flex-col gap-2 mt-2">
                        {/* Feature 1 */}
                        <motion.div
                            initial={{ opacity: 0, x: -20 }}
                            whileInView={{ opacity: 1, x: 0 }}
                            transition={{ delay: 0.3 }}
                            viewport={{ once: true }}
                            className="group flex items-center gap-3 p-2.5 rounded-xl transition-all duration-300 hover:bg-white/5 border border-transparent hover:border-white/5 cursor-pointer"
                        >
                            <div className="flex-shrink-0 flex items-center justify-center w-10 h-10 rounded-full text-[#17cfaa] group-hover:text-white group-hover:bg-[#17cfaa] transition-colors duration-300 shadow-[inset_2px_2px_4px_0_rgba(255,255,255,0.1),inset_-2px_-2px_4px_0_rgba(0,0,0,0.3),4px_4px_8px_0_rgba(0,0,0,0.25)] bg-gradient-to-br from-[#132521] to-[#1a3530]">
                                <Eye className="w-5 h-5" />
                            </div>
                            <div className="flex flex-col">
                                <h3 className="text-base font-bold text-white">Real-time Oversight</h3>
                                <p className="text-xs text-gray-400">Monitor agent reasoning as it happens.</p>
                            </div>
                            <div className="ml-auto opacity-0 group-hover:opacity-100 transition-opacity text-[#17cfaa]">
                                <ArrowRight className="w-5 h-5" />
                            </div>
                        </motion.div>

                        {/* Feature 2 */}
                        <motion.div
                            initial={{ opacity: 0, x: -20 }}
                            whileInView={{ opacity: 1, x: 0 }}
                            transition={{ delay: 0.4 }}
                            viewport={{ once: true }}
                            className="group flex items-center gap-3 p-2.5 rounded-xl transition-all duration-300 hover:bg-white/5 border border-transparent hover:border-white/5 cursor-pointer"
                        >
                            <div className="flex-shrink-0 flex items-center justify-center w-10 h-10 rounded-full text-[#17cfaa] group-hover:text-white group-hover:bg-[#17cfaa] transition-colors duration-300 shadow-[inset_2px_2px_4px_0_rgba(255,255,255,0.1),inset_-2px_-2px_4px_0_rgba(0,0,0,0.3),4px_4px_8px_0_rgba(0,0,0,0.25)] bg-gradient-to-br from-[#132521] to-[#1a3530]">
                                <Lock className="w-5 h-5" />
                            </div>
                            <div className="flex flex-col">
                                <h3 className="text-base font-bold text-white">Manual Override Protocols</h3>
                                <p className="text-xs text-gray-400">Intervene instantly with kill-switches.</p>
                            </div>
                            <div className="ml-auto opacity-0 group-hover:opacity-100 transition-opacity text-[#17cfaa]">
                                <ArrowRight className="w-5 h-5" />
                            </div>
                        </motion.div>

                        {/* Feature 3 */}
                        <motion.div
                            initial={{ opacity: 0, x: -20 }}
                            whileInView={{ opacity: 1, x: 0 }}
                            transition={{ delay: 0.5 }}
                            viewport={{ once: true }}
                            className="group flex items-center gap-3 p-2.5 rounded-xl transition-all duration-300 hover:bg-white/5 border border-transparent hover:border-white/5 cursor-pointer"
                        >
                            <div className="flex-shrink-0 flex items-center justify-center w-10 h-10 rounded-full text-[#17cfaa] group-hover:text-white group-hover:bg-[#17cfaa] transition-colors duration-300 shadow-[inset_2px_2px_4px_0_rgba(255,255,255,0.1),inset_-2px_-2px_4px_0_rgba(0,0,0,0.3),4px_4px_8px_0_rgba(0,0,0,0.25)] bg-gradient-to-br from-[#132521] to-[#1a3530]">
                                <RefreshCcw className="w-5 h-5" />
                            </div>
                            <div className="flex flex-col">
                                <h3 className="text-base font-bold text-white">Adaptive Feedback Loops</h3>
                                <p className="text-xs text-gray-400">Teach agents through correction.</p>
                            </div>
                            <div className="ml-auto opacity-0 group-hover:opacity-100 transition-opacity text-[#17cfaa]">
                                <ArrowRight className="w-5 h-5" />
                            </div>
                        </motion.div>
                    </div>

                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.6 }}
                        viewport={{ once: true }}
                        className="mt-3 flex flex-col sm:flex-row gap-3"
                    >
                        <button className="flex items-center justify-center gap-2 px-6 py-2.5 bg-[#17cfaa] hover:bg-[#15bd9b] text-[#11211e] text-sm font-bold rounded-lg transition-all duration-200 shadow-[0_0_20px_-5px_rgba(23,207,170,0.5)] hover:translate-y-[-2px] cursor-pointer">
                            <span>Start Integration</span>
                            <ArrowUpRight className="w-4 h-4" />
                        </button>
                        <button className="flex items-center justify-center gap-2 px-6 py-2.5 bg-transparent border border-gray-700 hover:border-[#17cfaa] text-white text-sm font-semibold rounded-lg transition-all duration-200 hover:bg-[#17cfaa]/5 cursor-pointer">
                            <span>View Documentation</span>
                        </button>
                    </motion.div>
                </div>
            </div>

            {/* Right Visual Side */}
            <div className="relative w-full lg:w-1/2 min-h-[400px] lg:h-auto group perspective-1000">
                <div className="absolute inset-0 w-full h-full">
                    <Image
                        src="https://lh3.googleusercontent.com/aida-public/AB6AXuA3-2rijrMcnkjsjvGdoHln6QHRpi4HXxb-yWENVVODBepFAA5FozsHogwPAepoUAeHcrCYG4ZWXM8AwN2AdzNjYI-ikVqHAZvjWiI6TQZ-_29i4NHFIIdnVYI-S_bZ-m_YmR6tNPDv8Ca-UiDfDh71eFh7MikodhasUbq4huwOF-Ac3nEgLrf4nwj80VifH7G8Sun4Mde2m3RT00apiRP6O87sddbFesHWiBX0jVurCAwUovxanQtr16FVb2Sf1UyENvGxGA9Orkw"
                        alt="Human in the loop visualization"
                        fill
                        className="object-cover"
                        sizes="(max-width: 1024px) 100vw, 50vw"
                        priority={false}
                    />
                    <div className="absolute inset-0 bg-gradient-to-r from-[#11211e] via-[#11211e]/80 to-transparent lg:bg-gradient-to-l lg:via-[#11211e]/30 lg:from-transparent"></div>
                    <div className="absolute inset-0 bg-[#11211e]/40 mix-blend-multiply"></div>
                </div>

                <div className="absolute inset-0 flex items-center justify-center pointer-events-none p-6 lg:p-10">
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95, rotateY: 10 }}
                        whileInView={{ opacity: 0.9, scale: 1, rotateY: 0 }}
                        transition={{ duration: 0.8 }}
                        viewport={{ once: true }}
                        className="w-full h-full max-h-[80vh] max-w-2xl rounded-2xl relative overflow-hidden border-t border-l border-white/10 flex flex-col shadow-[inset_1px_1px_2px_rgba(255,255,255,0.05),inset_-1px_-1px_2px_rgba(0,0,0,0.2),0_10px_30px_-10px_rgba(0,0,0,0.5)] bg-[#162a26]/60 backdrop-blur-xl"
                    >
                        <div className="absolute inset-0" style={{ backgroundImage: "radial-gradient(rgba(23, 207, 170, 0.15) 1px, transparent 1px)", backgroundSize: "30px 30px" }}></div>

                        {/* Card Header */}
                        <div className="flex justify-between items-center p-4 border-b border-white/5 bg-black/20 flex-shrink-0">
                            <div className="flex gap-2 items-center">
                                <span className="w-3 h-3 rounded-full bg-red-500"></span>
                                <span className="w-3 h-3 rounded-full bg-yellow-500"></span>
                                <span className="w-3 h-3 rounded-full bg-green-500"></span>
                            </div>
                            <div className="text-[#17cfaa] font-mono text-xs uppercase tracking-widest flex items-center gap-2">
                                <span className="w-2 h-2 rounded-full bg-[#17cfaa] animate-pulse"></span>
                                System Active
                            </div>
                        </div>

                        {/* Card Content & Graph */}
                        <div className="p-6 flex flex-col h-full gap-4 overflow-hidden">
                            <div className="flex-1 relative min-h-[150px]">
                                <svg className="w-full h-full absolute inset-0" preserveAspectRatio="xMidYMid meet" viewBox="0 0 500 250" xmlns="http://www.w3.org/2000/svg">
                                    <defs>
                                        <filter height="140%" id="glow-filter" width="140%" x="-20%" y="-20%">
                                            <feGaussianBlur result="coloredBlur" stdDeviation="4"></feGaussianBlur>
                                            <feMerge>
                                                <feMergeNode in="coloredBlur"></feMergeNode>
                                                <feMergeNode in="SourceGraphic"></feMergeNode>
                                            </feMerge>
                                        </filter>
                                        <linearGradient id="line-gradient" x1="0%" x2="100%" y1="0%" y2="0%">
                                            <stop offset="0%" style={{ stopColor: "#17cfaa", stopOpacity: 0.1 }}></stop>
                                            <stop offset="50%" style={{ stopColor: "#17cfaa", stopOpacity: 1 }}></stop>
                                            <stop offset="100%" style={{ stopColor: "#17cfaa", stopOpacity: 0.1 }}></stop>
                                        </linearGradient>
                                    </defs>
                                    <motion.path
                                        initial={{ pathLength: 0 }}
                                        whileInView={{ pathLength: 1 }}
                                        transition={{ duration: 2, ease: "easeInOut" }}
                                        d="M50,150 Q150,50 250,100 T450,150" fill="none" filter="url(#glow-filter)" stroke="url(#line-gradient)" strokeWidth="2"
                                    ></motion.path>
                                    <motion.path
                                        initial={{ pathLength: 0 }}
                                        whileInView={{ pathLength: 1 }}
                                        transition={{ duration: 2, delay: 0.5, ease: "easeInOut" }}
                                        d="M50,150 Q150,250 250,200 T450,150" fill="none" filter="url(#glow-filter)" opacity="0.6" stroke="url(#line-gradient)" strokeWidth="2"
                                    ></motion.path>
                                    <circle cx="50" cy="150" fill="#17cfaa" filter="url(#glow-filter)" r="6"></circle>
                                    <circle cx="250" cy="100" fill="#17cfaa" filter="url(#glow-filter)" r="4"></circle>
                                    <circle cx="250" cy="200" fill="#17cfaa" filter="url(#glow-filter)" r="4"></circle>
                                    <circle cx="450" cy="150" fill="#fff" filter="url(#glow-filter)" r="8" stroke="#17cfaa" strokeWidth="3"></circle>

                                    <g transform="translate(60, 130)">
                                        <rect fill="#0f172a" fillOpacity="0.8" height="24" rx="4" stroke="#17cfaa" strokeWidth="0.5" width="80"></rect>
                                        <text fill="#17cfaa" fontFamily="monospace" fontSize="10" x="10" y="16">INPUT_V2</text>
                                    </g>
                                    <g transform="translate(380, 110)">
                                        <rect fill="#0f172a" fillOpacity="0.8" height="24" rx="4" stroke="#ffffff" strokeWidth="0.5" width="100"></rect>
                                        <text fill="#ffffff" fontFamily="monospace" fontSize="10" x="10" y="16">CONFIDENCE: 98%</text>
                                    </g>
                                </svg>
                            </div>

                            {/* Terminal Output */}
                            <div className="h-20 bg-black/40 rounded-lg p-2 font-mono text-[9px] text-[#17cfaa]/80 overflow-hidden border border-[#17cfaa]/10 flex-shrink-0">
                                <div className="flex flex-col gap-0.5">
                                    <span className="opacity-50">&gt; Initializing neural handshake...</span>
                                    <span className="opacity-70">&gt; Protocol 778 accepted.</span>
                                    <span>&gt; Human operator [ID: ADMIN] authorized override.</span>
                                    <span className="text-white">&gt; Optimizing decision tree... DONE.</span>
                                </div>
                            </div>
                        </div>

                        <div className="absolute bottom-0 right-0 w-64 h-64 bg-[#17cfaa]/20 blur-[80px] rounded-full pointer-events-none"></div>
                    </motion.div>
                </div>
            </div>
        </section>
    );
}
