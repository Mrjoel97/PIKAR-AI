"use client";

import React from 'react';
import {
    Brain,
    Activity,
    Network,
    Shield,
    Users,
    Mic,
    Server,
    Zap,
    Lock,
    CheckCircle2,
    RefreshCw
} from 'lucide-react';

export default function NeuralGridSection() {
    return (
        <section className="relative w-full py-6 px-4 bg-[#0d2d2d] overflow-hidden text-[#e2e8f0] font-neural-sans">
            <div className="absolute inset-0 bg-neural-grid-pattern pointer-events-none z-0"></div>
            <div className="absolute inset-0 pointer-events-none z-0 overflow-hidden">
                <div className="stream-v left-[20%] top-0 bottom-0" style={{ animationDelay: '0s' }}></div>
                <div className="stream-v left-[50%] top-0 bottom-0" style={{ animationDelay: '1.5s' }}></div>
                <div className="stream-v left-[80%] top-0 bottom-0" style={{ animationDelay: '0.8s' }}></div>
                <div className="stream-h top-[30%] left-0 right-0" style={{ animationDelay: '2s' }}></div>
                <div className="stream-h top-[70%] left-0 right-0" style={{ animationDelay: '0.5s' }}></div>
            </div>

            <div className="text-center max-w-2xl mx-auto mb-4 relative z-10">
                <div className="inline-flex items-center justify-center px-2 py-0.5 mb-1.5 rounded-full bg-[#17cfaa]/10 border border-[#17cfaa]/20 backdrop-blur-sm shadow-[0_0_10px_rgba(23,207,170,0.2)]">
                    <span className="w-1 h-1 rounded-full bg-[#17cfaa] animate-pulse mr-1.5"></span>
                    <span className="text-[#17cfaa] text-[8px] font-bold tracking-widest uppercase">System V2.0 Online</span>
                </div>
                <h2 className="font-neural-display text-xl md:text-2xl font-bold tracking-tight mb-1 leading-tight text-white drop-shadow-lg">
                    Pikar AI <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#17cfaa] to-teal-200 neon-text-neural">Neural Grid</span>
                </h2>
                <p className="text-[9px] md:text-[10px] text-slate-400 max-w-md mx-auto font-light tracking-wide leading-relaxed">
                    Next-generation autonomous agent orchestration.
                </p>
            </div>

            <div className="w-full max-w-4xl mx-auto grid grid-cols-1 md:grid-cols-2 lg:grid-cols-12 gap-2.5 relative z-10">

                {/* 1. Neural Logic Core (7 cols) */}
                <div className="card-liquid-neural p-3 lg:col-span-7 flex flex-col min-h-[150px] group relative overflow-hidden">
                    <div className="relative z-20 flex justify-between items-center mb-1">
                        <div className="flex flex-col z-30">
                            <div className="flex items-center gap-1.5 mb-0.5">
                                <div className="w-5 h-5 rounded bg-gradient-to-br from-[#17cfaa]/20 to-transparent flex items-center justify-center text-[#17cfaa] shadow-[inset_0_0_8px_rgba(23,207,170,0.2)] border border-[#17cfaa]/10">
                                    <Brain className="w-3 h-3" />
                                </div>
                                <h3 className="font-neural-display text-xs font-bold text-white tracking-wide">Neural Core</h3>
                            </div>
                            <p className="text-slate-400 text-[8px] max-w-xs leading-relaxed font-light pl-0.5">Autonomous workflow construction.</p>
                        </div>
                        <div className="px-1.5 py-0.5 rounded-full bg-black/40 border border-[#17cfaa]/20 text-[7px] font-mono text-[#17cfaa] backdrop-blur-sm z-30">
                            v2.4.0
                        </div>
                    </div>

                    <div className="relative flex-1 w-full min-h-[80px] mt-0.5 rounded-lg overflow-hidden border border-[#17cfaa]/5 bg-black/10">
                        <svg className="absolute inset-0 w-full h-full pointer-events-none" viewBox="0 0 600 240">
                            <defs>
                                <linearGradient id="lineGrad" x1="0%" x2="100%" y1="0%" y2="0%">
                                    <stop offset="0%" style={{ stopColor: '#17cfaa', stopOpacity: 0 }}></stop>
                                    <stop offset="50%" style={{ stopColor: '#17cfaa', stopOpacity: 0.5 }}></stop>
                                    <stop offset="100%" style={{ stopColor: '#17cfaa', stopOpacity: 0 }}></stop>
                                </linearGradient>
                            </defs>
                            <path className="opacity-40" d="M100 60 Q 250 60, 270 100" fill="none" stroke="url(#lineGrad)" strokeWidth="1"></path>
                            <path className="opacity-40" d="M100 180 Q 250 180, 270 140" fill="none" stroke="url(#lineGrad)" strokeWidth="1"></path>
                            <path className="opacity-40" d="M500 60 Q 350 60, 330 100" fill="none" stroke="url(#lineGrad)" strokeWidth="1"></path>
                            <path className="opacity-40" d="M500 180 Q 350 180, 330 140" fill="none" stroke="url(#lineGrad)" strokeWidth="1"></path>
                            <circle className="animate-pulse" cx="100" cy="60" fill="#17cfaa" r="2"></circle>
                            <circle className="animate-pulse" cx="100" cy="180" fill="#17cfaa" r="2" style={{ animationDelay: '0.5s' }}></circle>
                            <circle className="animate-pulse" cx="500" cy="60" fill="#17cfaa" r="2" style={{ animationDelay: '1s' }}></circle>
                            <circle className="animate-pulse" cx="500" cy="180" fill="#17cfaa" r="2" style={{ animationDelay: '1.5s' }}></circle>
                        </svg>

                        <div className="absolute inset-0 flex items-center justify-center">
                            <div className="brain-chip w-10 h-10 rounded-lg relative flex items-center justify-center z-10 border border-[#17cfaa]/30 group-hover:scale-110 transition-transform duration-500 shadow-[0_0_15px_rgba(23,207,170,0.15)]">
                                <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAiIGhlaWdodD0iMjAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHBhdGggZD0iTTEgMWgydjJIMUMxeiIgZmlsbD0iIzE3Y2ZhYSIgZmlsbC1vcGFjaXR5PSIwLjEiLz48L3N2Zz4=')] opacity-40 bg-cover bg-center"></div>
                                <Brain className="w-5 h-5 text-[#17cfaa] drop-shadow-[0_0_6px_rgba(23,207,170,0.8)]" />
                            </div>
                        </div>

                        <div className="absolute top-1.5 left-2 bg-black/50 backdrop-blur-md border border-[#17cfaa]/20 px-1 py-0.5 rounded text-[7px] text-[#17cfaa] font-mono tracking-wider shadow-lg">
                            1.2M OPS
                        </div>
                        <div className="absolute bottom-1.5 right-2 bg-black/50 backdrop-blur-md border border-[#17cfaa]/20 px-1 py-0.5 rounded text-[7px] text-[#17cfaa] font-mono tracking-wider shadow-lg">
                            NEURAL-L4
                        </div>
                    </div>

                    <div className="tech-footer-neural mt-1.5 pt-1.5">
                        <span className="flex items-center gap-1.5 text-[8px] font-medium tracking-wider text-slate-400">
                            <span className="w-1 h-1 rounded-full bg-emerald-500 shadow-[0_0_4px_#10b981]"></span>
                            &lt;12ms
                        </span>
                        <div className="flex gap-3 text-[8px] font-medium tracking-wider text-slate-500">
                            <span>MODEL: V2</span>
                            <span className="text-[#17cfaa]">OPTIMAL</span>
                        </div>
                    </div>
                </div>

                {/* 2. Live Metrics (5 cols) */}
                <div className="card-liquid-neural p-3 lg:col-span-5 flex flex-col relative overflow-hidden group min-h-[150px]">
                    <div className="relative z-20 mb-1 flex justify-between items-center">
                        <div>
                            <div className="flex items-center gap-1.5 mb-0.5">
                                <div className="w-5 h-5 rounded bg-gradient-to-br from-[#17cfaa]/20 to-transparent flex items-center justify-center text-[#17cfaa] shadow-[inset_0_0_8px_rgba(23,207,170,0.2)] border border-[#17cfaa]/10">
                                    <Activity className="w-3 h-3" />
                                </div>
                                <h3 className="font-neural-display text-xs font-bold text-white tracking-wide">Metrics</h3>
                            </div>
                            <p className="text-slate-400 text-[8px] pl-0.5">Real-time pulse.</p>
                        </div>
                        <div className="text-right bg-black/20 px-1.5 py-0.5 rounded border border-white/5">
                            <span className="text-sm font-neural-display font-bold text-transparent bg-clip-text bg-gradient-to-br from-white to-slate-400">98.4</span>
                            <span className="text-[7px] text-[#17cfaa] block tracking-widest font-bold">EFFICIENCY</span>
                        </div>
                    </div>

                    <div className="flex-1 grid grid-cols-2 gap-2 items-center pb-0.5">
                        <div className="relative flex items-center justify-center aspect-square max-h-[70px]">
                            <svg className="w-full h-full transform -rotate-90 drop-shadow-md" viewBox="0 0 100 100">
                                <circle cx="50" cy="50" fill="transparent" r="42" stroke="#0f3030" strokeWidth="6"></circle>
                                <circle className="drop-shadow-[0_0_8px_rgba(23,207,170,0.5)] animate-[dash_3s_ease-in-out_infinite_alternate]" cx="50" cy="50" fill="transparent" r="42" stroke="#17cfaa" strokeDasharray="264" strokeDashoffset="60" strokeLinecap="round" strokeWidth="6"></circle>
                            </svg>
                            <div className="absolute inset-0 flex flex-col items-center justify-center">
                                <Zap className="w-3.5 h-3.5 text-[#17cfaa] animate-pulse drop-shadow-[0_0_5px_rgba(23,207,170,0.8)]" />
                                <span className="text-[8px] text-slate-300 mt-0.5 font-bold">45K</span>
                            </div>
                        </div>
                        <div className="h-[70px] flex items-end justify-between gap-1 px-1.5 bg-black/10 rounded-lg border border-white/5 p-1.5">
                            <div className="w-1/4 h-full flex flex-col justify-end gap-0.5">
                                <div className="w-full h-[30%] bar-liquid-secondary"></div>
                                <div className="w-full h-[40%] bar-liquid group-hover:h-[50%] transition-all duration-500 shadow-[0_0_8px_rgba(23,207,170,0.3)]"></div>
                            </div>
                            <div className="w-1/4 h-full flex flex-col justify-end gap-0.5">
                                <div className="w-full h-[40%] bar-liquid-secondary"></div>
                                <div className="w-full h-[60%] bar-liquid group-hover:h-[80%] transition-all duration-500 delay-75 shadow-[0_0_8px_rgba(23,207,170,0.3)]"></div>
                            </div>
                            <div className="w-1/4 h-full flex flex-col justify-end gap-0.5">
                                <div className="w-full h-[25%] bar-liquid-secondary"></div>
                                <div className="w-full h-[50%] bar-liquid group-hover:h-[45%] transition-all duration-500 delay-100 shadow-[0_0_8px_rgba(23,207,170,0.3)]"></div>
                            </div>
                            <div className="w-1/4 h-full flex flex-col justify-end gap-0.5 relative">
                                <div className="absolute -top-4 left-1/2 -translate-x-1/2 text-[#17cfaa] text-[7px] font-bold bg-[#17cfaa]/10 px-0.5 py-px rounded border border-[#17cfaa]/20">
                                    +12%
                                </div>
                                <div className="w-full h-[55%] bar-liquid-secondary"></div>
                                <div className="w-full h-[75%] bar-liquid group-hover:h-[90%] transition-all duration-500 delay-150 shadow-[0_0_8px_rgba(23,207,170,0.3)]"></div>
                            </div>
                        </div>
                    </div>

                    <div className="tech-footer-neural mt-auto pt-1">
                        <span className="flex items-center gap-1.5 text-[8px] text-slate-400">
                            <RefreshCw className="w-2 h-2 animate-spin text-[#17cfaa]" /> ACTIVE
                        </span>
                        <span className="text-[8px] text-slate-500 font-medium">PK: 45K</span>
                    </div>
                </div>

                {/* 3. Integrations (3 cols) */}
                <div className="card-liquid-neural p-3 lg:col-span-3 flex flex-col justify-between relative group min-h-[100px]">
                    <div className="mb-0.5 z-20">
                        <div className="flex items-center gap-1.5 mb-0.5">
                            <div className="w-5 h-5 rounded bg-orange-500/10 text-orange-400 border border-orange-500/20 flex items-center justify-center shadow-[inset_0_0_6px_rgba(251,146,60,0.1)]">
                                <Network className="w-3 h-3" />
                            </div>
                            <h3 className="font-neural-display text-xs font-bold text-white tracking-wide">Connect</h3>
                        </div>
                        <p className="text-[8px] text-slate-400 leading-tight pl-0.5">100+ platforms.</p>
                    </div>

                    <div className="flex -space-x-1.5 relative z-10 pl-1 mb-0.5 py-1">
                        <div className="w-6 h-6 rounded-md bg-[#1e293b] flex items-center justify-center border border-slate-700 shadow-md transform transition-transform group-hover:-translate-y-1 hover:z-30 hover:scale-105">
                            <span className="text-[8px] font-bold text-[#E01E5A]">#</span>
                        </div>
                        <div className="w-6 h-6 rounded-md bg-[#1e293b] flex items-center justify-center border border-slate-700 shadow-md z-10 transform transition-transform group-hover:-translate-y-2 delay-75 hover:z-30 hover:scale-105">
                            <span className="text-[8px] font-bold text-[#00A1E0]">SF</span>
                        </div>
                        <div className="w-6 h-6 rounded-md bg-[#1e293b] flex items-center justify-center border border-slate-700 shadow-md z-20 transform transition-transform group-hover:-translate-y-1 delay-100 hover:z-30 hover:scale-105">
                            <div className="w-3.5 h-3.5 bg-blue-600 rounded flex items-center justify-center text-white font-bold text-[6px]">J</div>
                        </div>
                        <div className="w-6 h-6 rounded-md bg-[#0f2222] flex items-center justify-center border border-dashed border-slate-600 shadow-md z-30 text-slate-500 text-[7px] hover:z-40 hover:border-slate-400 hover:text-slate-300 transition-colors cursor-pointer">
                            +40
                        </div>
                    </div>

                    <div className="tech-footer-neural pt-1">
                        <span className="text-[7px] text-slate-500">SYNC: &lt;2ms</span>
                        <span className="text-[#17cfaa] text-[7px] font-bold tracking-wider">READY</span>
                    </div>
                </div>

                {/* 4. Enterprise Secure (4 cols) */}
                <div className="card-liquid-neural p-3 lg:col-span-4 flex flex-col justify-between group min-h-[100px]">
                    <div className="flex justify-between items-start">
                        <div className="flex-1 pr-1">
                            <div className="flex items-center gap-1.5 mb-1">
                                <div className="w-5 h-5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center justify-center shadow-[inset_0_0_6px_rgba(16,185,129,0.1)]">
                                    <Shield className="w-3 h-3" />
                                </div>
                                <h3 className="font-neural-display text-xs font-bold text-white tracking-wide">Secure</h3>
                            </div>
                            <p className="text-[8px] text-slate-400 mb-1.5 leading-tight">SOC2 Type II Encrypted.</p>

                            <div className="w-full bg-slate-800/50 rounded-full h-1 mb-0.5 overflow-hidden border border-white/5">
                                <div className="bg-gradient-to-r from-emerald-600 to-emerald-400 h-full rounded-full w-[98%] shadow-[0_0_8px_rgba(16,185,129,0.4)]"></div>
                            </div>
                        </div>
                        <div className="ml-1 w-7 h-7 rounded-full bg-gradient-to-br from-emerald-900/40 to-transparent border border-emerald-500/30 flex items-center justify-center group-hover:shadow-[0_0_20px_rgba(16,185,129,0.2)] transition-all duration-500">
                            <Lock className="w-3.5 h-3.5 text-emerald-400 drop-shadow-[0_0_4px_rgba(16,185,129,0.8)]" />
                        </div>
                    </div>
                    <div className="tech-footer-neural mt-auto pt-1">
                        <span className="text-emerald-600/70 text-[8px] font-mono">AES-256</span>
                        <span className="text-emerald-500 text-[8px] font-bold tracking-wider flex items-center gap-1">
                            <CheckCircle2 className="w-2 h-2" /> VERIFIED
                        </span>
                    </div>
                </div>

                {/* 5. Squad Mode (5 cols) */}
                <div className="card-liquid-neural p-3 lg:col-span-5 flex flex-col justify-between min-h-[100px] relative overflow-hidden">
                    <div className="absolute top-0 right-0 p-1.5 opacity-10 pointer-events-none">
                        <Users className="w-10 h-10 text-pink-500" />
                    </div>
                    <div className="flex justify-between items-start mb-1 relative z-10">
                        <div>
                            <div className="flex items-center gap-1.5 mb-0.5">
                                <div className="w-5 h-5 rounded bg-pink-500/10 text-pink-400 border border-pink-500/20 flex items-center justify-center shadow-[inset_0_0_6px_rgba(236,72,153,0.1)]">
                                    <Users className="w-3 h-3" />
                                </div>
                                <h3 className="font-neural-display text-xs font-bold text-white tracking-wide">Squad</h3>
                            </div>
                            <p className="text-[8px] text-slate-400 mt-0.5 leading-tight">Multi-agent sync.</p>
                        </div>
                        <div className="flex items-center gap-1 bg-green-500/10 px-1.5 py-0.5 rounded-full border border-green-500/20">
                            <span className="w-1 h-1 bg-green-500 rounded-full shadow-[0_0_4px_#22c55e] animate-pulse"></span>
                            <span className="text-[7px] text-green-400 font-bold tracking-wider">LIVE</span>
                        </div>
                    </div>
                    <div className="flex -space-x-1.5 mb-1 relative z-10 py-0.5 pl-1">
                        <div className="w-6 h-6 rounded-full border-2 border-[#0d2d2d] bg-gradient-to-br from-pink-400 to-pink-600 flex items-center justify-center text-[7px] font-bold text-white hover:scale-110 hover:z-20 cursor-pointer transition-all">A</div>
                        <div className="w-6 h-6 rounded-full border-2 border-[#0d2d2d] bg-gradient-to-br from-violet-400 to-violet-600 flex items-center justify-center text-[7px] font-bold text-white hover:scale-110 hover:z-20 cursor-pointer transition-all">B</div>
                        <div className="w-6 h-6 rounded-full border-2 border-[#0d2d2d] bg-gradient-to-br from-cyan-400 to-cyan-600 flex items-center justify-center text-[7px] font-bold text-white hover:scale-110 hover:z-20 cursor-pointer transition-all">C</div>
                        <div className="w-6 h-6 rounded-full border-2 border-[#0d2d2d] bg-slate-800 flex items-center justify-center text-[8px] text-white font-bold tracking-wider hover:bg-slate-700 transition-colors cursor-pointer hover:scale-110 hover:z-20">
                            +12
                        </div>
                    </div>
                    <div className="tech-footer-neural pt-1">
                        <span className="text-[8px] text-slate-500 font-medium tracking-wide">UNLIMITED</span>
                        <span className="text-[8px] text-pink-400 font-medium tracking-wide">2ms</span>
                    </div>
                </div>

                {/* 6. System Health (5 cols) */}
                <div className="card-liquid-neural p-3 lg:col-span-5 flex flex-col justify-between min-h-[100px] group">
                    <div className="flex justify-between items-start mb-1">
                        <div className="flex items-center gap-1.5">
                            <div className="w-5 h-5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 flex items-center justify-center shadow-[inset_0_0_6px_rgba(59,130,246,0.1)]">
                                <Server className="w-3 h-3" />
                            </div>
                            <div>
                                <h3 className="font-neural-display text-xs font-bold text-white tracking-wide">Health</h3>
                                <p className="text-[7px] text-slate-400 mt-0.5">Cluster Status</p>
                            </div>
                        </div>
                        <div className="flex items-center gap-1 bg-blue-500/10 px-1.5 py-0.5 rounded border border-blue-500/20 shadow-[0_0_8px_rgba(59,130,246,0.1)]">
                            <div className="w-1 h-1 rounded-full bg-blue-400 animate-pulse"></div>
                            <span className="text-[7px] text-blue-400 font-mono font-bold tracking-wider">ONLINE</span>
                        </div>
                    </div>

                    <div className="grid grid-cols-3 gap-1.5 py-0.5">
                        <div className="bg-[#0f1a1a] rounded p-1.5 border border-white/5 text-center group-hover:border-blue-500/30 transition-all duration-300 hover:bg-[#142222]">
                            <p className="text-[7px] text-slate-500 uppercase tracking-widest mb-0.5">Uptime</p>
                            <p className="text-[10px] font-bold text-white font-mono">99.9%</p>
                        </div>
                        <div className="bg-[#0f1a1a] rounded p-1.5 border border-white/5 text-center group-hover:border-blue-500/30 transition-all duration-300 hover:bg-[#142222]">
                            <p className="text-[7px] text-slate-500 uppercase tracking-widest mb-0.5">Latency</p>
                            <p className="text-[10px] font-bold text-white font-mono">12ms</p>
                        </div>
                        <div className="bg-[#0f1a1a] rounded p-1.5 border border-white/5 text-center group-hover:border-blue-500/30 transition-all duration-300 hover:bg-[#142222]">
                            <p className="text-[7px] text-slate-500 uppercase tracking-widest mb-0.5">Nodes</p>
                            <p className="text-[10px] font-bold text-white font-mono">4.2k</p>
                        </div>
                    </div>

                    <div className="w-full bg-slate-800/50 rounded-full h-1 mt-1.5 overflow-hidden border border-white/5">
                        <div className="bg-gradient-to-r from-blue-600 to-blue-400 h-full rounded-full w-[98%] shadow-[0_0_8px_rgba(59,130,246,0.5)]"></div>
                    </div>
                </div>

                {/* 7. Voice Command (7 cols) */}
                <div className="card-liquid-neural p-0 lg:col-span-7 lg:row-span-1 min-h-[100px] flex flex-col relative overflow-hidden">
                    <div className="p-3 pb-0 z-20 flex justify-between items-start">
                        <div className="flex items-center gap-1.5">
                            <div className="w-5 h-5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/20 flex items-center justify-center shadow-[inset_0_0_6px_rgba(168,85,247,0.1)]">
                                <Mic className="w-3 h-3" />
                            </div>
                            <div>
                                <h3 className="font-neural-display text-xs font-bold text-white tracking-wide">Voice Gen-4</h3>
                                <p className="text-[8px] text-slate-400 mt-0.5">NLP v4.0 Active</p>
                            </div>
                        </div>
                        <div className="px-1.5 py-0.5 rounded border border-purple-500/20 bg-purple-500/5 text-[7px] text-purple-300 font-mono">
                            Auto-Detect
                        </div>
                    </div>

                    <div className="flex-1 flex flex-col justify-center items-center relative z-10 -mt-2">
                        <div className="bg-black/40 backdrop-blur-md border border-purple-500/20 px-2.5 py-0.5 rounded-full text-center shadow-[0_2px_15px_rgba(147,51,234,0.15)] mb-1.5">
                            <p className="text-[8px] font-medium text-slate-100 font-mono tracking-wide">&quot;Deploy&quot;</p>
                        </div>
                        <div className="flex items-center gap-0.5 h-5">
                            {/* Extended wave animation */}
                            {/* Extended wave animation - Deterministic values to prevent hydration mismatch */}
                            {[
                                { h: '8px', d: '0.6s' }, { h: '12px', d: '0.8s' }, { h: '6px', d: '0.5s' },
                                { h: '14px', d: '0.9s' }, { h: '10px', d: '0.7s' }, { h: '13px', d: '0.6s' },
                                { h: '7px', d: '0.8s' }, { h: '11px', d: '0.5s' }, { h: '9px', d: '0.7s' },
                                { h: '13px', d: '0.9s' }, { h: '5px', d: '0.6s' }, { h: '8px', d: '0.8s' }
                            ].map((bar, i) => (
                                <div key={i}
                                    className="w-0.5 bg-gradient-to-t from-purple-600 to-purple-400 rounded-full animate-[bounce_1s_infinite]"
                                    style={{
                                        height: bar.h,
                                        animationDuration: bar.d,
                                        animationDelay: `${i * 0.05}s`
                                    }}
                                ></div>
                            ))}
                        </div>
                    </div>

                    <div className="absolute bottom-0 left-0 right-0 h-8 bg-gradient-to-t from-purple-900/20 to-transparent pointer-events-none"></div>
                    <div className="absolute bottom-0 left-0 right-0 px-3 pb-1.5 z-20">
                        <div className="tech-footer-neural border-t-purple-900/30 flex justify-between text-[8px]">
                            <span className="text-purple-400/70 font-medium">50+ LANGS</span>
                            <span className="text-purple-400 font-bold tracking-wider flex items-center gap-1"><span className="w-1 h-1 rounded-full bg-purple-500 animate-pulse"></span> LISTENING</span>
                        </div>
                    </div>
                </div>

            </div>
        </section>
    );
}
