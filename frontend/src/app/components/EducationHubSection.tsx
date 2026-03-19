"use client";

import React from 'react';
import { BookOpen, MonitorPlay, Users, ArrowRight, GraduationCap } from 'lucide-react';

export default function EducationHubSection() {
    return (
        <section className="w-full lg:h-[65vh] flex flex-col lg:flex-row overflow-hidden relative border-t-2 border-black">
            {/* LEFT PANEL */}
            <div className="lg:w-[40%] w-full h-[300px] lg:h-full relative bg-black border-b-2 lg:border-b-0 lg:border-r-2 border-black flex">
                {/* Branding Text Removed as per request */}

                <div className="relative w-full h-full overflow-hidden group">
                    <div className="absolute inset-0 bg-gradient-to-br from-gray-800 via-gray-900 to-black opacity-60 mix-blend-luminosity scale-100 group-hover:scale-105 transition-transform duration-1000 ease-linear"></div>
                    <div className="absolute inset-0 bg-gradient-to-t from-black via-transparent to-black opacity-80 pointer-events-none"></div>
                    <div className="absolute inset-0 bg-blueprint-grid bg-blueprint-size opacity-10 pointer-events-none"></div>
                    <div className="absolute inset-0 bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.25)_50%),linear-gradient(90deg,rgba(255,0,0,0.06),rgba(0,255,0,0.02),rgba(0,0,255,0.06))] bg-[length:100%_2px,3px_100%] pointer-events-none opacity-20"></div>

                    <div className="absolute bottom-0 left-0 w-full p-4 lg:p-6 text-white z-10 bg-gradient-to-t from-black/90 to-transparent">
                        <div className="flex items-center gap-2 mb-2">
                            <div className="relative w-2.5 h-2.5">
                                <span className="absolute inline-flex h-full w-full rounded-full bg-[#00ff41] opacity-75 animate-ping"></span>
                                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-[#00ff41]"></span>
                            </div>
                            <span className="font-mono text-[10px] font-bold tracking-[0.2em] uppercase text-[#00ff41]">Live Feed</span>
                        </div>
                        <div className="grid grid-cols-2 gap-3 text-[9px] md:text-[10px] font-mono opacity-80 border-t border-white/20 pt-2">
                            <div>
                                <p className="text-white/50 mb-0.5">OPERATOR_ID</p>
                                <p>PK-884-XJ</p>
                            </div>
                            <div className="text-right">
                                <p className="text-white/50 mb-0.5">SESSION_TIME</p>
                                <p>04:22:19</p>
                            </div>
                        </div>
                    </div>

                    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-24 h-24 border border-white/20 rounded-full flex items-center justify-center opacity-40 pointer-events-none">
                        <div className="w-0.5 h-0.5 bg-white rounded-full"></div>
                        <div className="absolute top-0 w-[1px] h-3 bg-white"></div>
                        <div className="absolute bottom-0 w-[1px] h-3 bg-white"></div>
                        <div className="absolute left-0 h-[1px] w-3 bg-white"></div>
                        <div className="absolute right-0 h-[1px] w-3 bg-white"></div>
                    </div>
                </div>
            </div>

            {/* RIGHT PANEL */}
            <div className="lg:w-[60%] w-full h-full bg-white relative overflow-y-auto lg:overflow-hidden flex flex-col font-mono text-[#0a0a0a]">
                <div className="absolute inset-0 bg-blueprint-grid bg-blueprint-size pointer-events-none opacity-40"></div>

                <div className="relative z-10 p-4 lg:p-6 h-full flex flex-col justify-between">
                    <div className="flex justify-between items-end mb-3 border-b-2 border-black pb-2 bg-white/50 backdrop-blur-sm">
                        <div className="flex-1">
                            <span className="bg-black text-white px-1.5 py-0.5 text-[9px] font-mono uppercase font-bold tracking-widest inline-block mb-1">System: Education</span>
                            <p className="text-[10px] font-mono text-gray-600 max-w-md leading-tight">
                                {`// INITIALIZING LEARNING MODULES`}<br />
                                Select a node to begin data transfer.
                            </p>
                        </div>
                        <div className="hidden md:block font-mono text-[9px] text-right text-gray-800">
                            <span className="block font-bold">V.2.0.4</span>
                            <span className="block text-gray-500">STABLE_BUILD</span>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2 lg:gap-3 flex-grow min-h-0">

                        {/* 01 SYNC DOCS */}
                        <a className="group relative bg-white border border-black p-3 flex flex-col justify-between hover:bg-black hover:text-white transition-all duration-200 hover:shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] hover:-translate-y-0.5 h-full min-h-[100px]" href="#">
                            <div className="flex justify-between items-start">
                                <BookOpen className="w-4 h-4 group-hover:text-[#00ff41] transition-colors" />
                                <span className="font-mono text-[8px] border border-current px-1 py-px rounded-sm">01</span>
                            </div>
                            <div className="mt-2">
                                <h3 className="font-display font-bold text-base uppercase leading-none mb-1">SYNC_<br />DOCS</h3>
                                <p className="font-mono text-[8px] opacity-70 leading-tight">Full API integration protocols.</p>
                            </div>
                        </a>

                        {/* 02 STREAM GUIDES */}
                        <a className="group relative bg-white border border-black p-3 flex flex-col justify-between hover:bg-black hover:text-white transition-all duration-200 hover:shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] hover:-translate-y-0.5 h-full min-h-[100px]" href="#">
                            <div className="flex justify-between items-start">
                                <MonitorPlay className="w-4 h-4 group-hover:text-[#00ff41] transition-colors" />
                                <span className="font-mono text-[8px] border border-current px-1 py-px rounded-sm">02</span>
                            </div>
                            <div className="mt-2">
                                <h3 className="font-display font-bold text-base uppercase leading-none mb-1">STREAM_<br />GUIDES</h3>
                                <p className="font-mono text-[8px] opacity-70 leading-tight">Visual ingestion modules.</p>
                            </div>
                        </a>

                        {/* 03 JOIN NODE - Reduced Size */}
                        <a className="group relative bg-white border border-black p-3 md:col-span-1 lg:row-span-2 flex flex-col hover:bg-black hover:text-white transition-all duration-200 hover:shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] hover:-translate-y-0.5 h-full min-h-0" href="#">
                            <div className="flex justify-between items-start mb-2">
                                <Users className="w-4 h-4 group-hover:text-[#00ff41] transition-colors" />
                                <span className="font-mono text-[8px] border border-current px-1 py-px rounded-sm">03</span>
                            </div>
                            <h3 className="font-display font-bold text-base uppercase leading-none mb-1">JOIN_<br />NODE</h3>
                            <p className="font-mono text-[8px] opacity-70 leading-tight mb-2">Swarm intelligence. Share configurations.</p>
                            <div className="mt-auto pt-2 border-t border-dashed border-gray-400 group-hover:border-gray-600">
                                <div className="flex justify-between items-center font-mono text-[8px] uppercase mb-1">
                                    <span>Nodes</span>
                                    <span className="text-green-600 group-hover:text-[#00ff41]">● Online</span>
                                </div>
                                <div className="w-full bg-gray-200 h-0.5 mt-1 group-hover:bg-gray-800">
                                    <div className="bg-black group-hover:bg-white h-full w-[85%]"></div>
                                </div>
                                <div className="flex gap-0.5 mt-2">
                                    <div className="h-3 w-0.5 bg-current opacity-20"></div>
                                    <div className="h-3 w-0.5 bg-current opacity-40"></div>
                                    <div className="h-3 w-0.5 bg-current opacity-60"></div>
                                    <div className="h-3 w-0.5 bg-current opacity-80"></div>
                                    <div className="h-3 w-0.5 bg-current opacity-100"></div>
                                </div>
                            </div>
                        </a>

                        {/* HERO CARD - Reduced Size */}
                        <div className="relative md:col-span-2 bg-[#f4f4f5] border border-black p-0 flex flex-col sm:flex-row overflow-hidden group hover:shadow-[2px_2px_0px_0px_rgba(0,0,0,1)] transition-all duration-200 min-h-[100px]">
                            <div className="absolute inset-0 bg-[radial-gradient(#000_1px,transparent_1px)] [background-size:16px_16px] opacity-10 pointer-events-none"></div>

                            <div className="p-3 sm:p-4 flex-1 relative z-10 flex flex-col justify-center">
                                <div className="inline-flex items-center gap-2 mb-1">
                                    <span className="bg-black text-white text-[8px] font-bold px-1.5 py-px uppercase tracking-wider">Free Access</span>
                                </div>
                                <h2 className="font-display text-xl md:text-2xl font-bold uppercase leading-[0.9] mb-1.5 text-black group-hover:text-black">
                                    Zero to AI<br />
                                    <span className="text-transparent bg-clip-text bg-gradient-to-r from-black to-gray-600">Hero</span>
                                </h2>
                                <p className="font-mono text-[8px] md:text-[9px] text-gray-600 mb-2 max-w-sm leading-tight">
                                    Exec training sequence. Build agents.
                                </p>
                                <button className="w-max bg-black text-white hover:bg-[#00ff41] hover:text-black transition-colors px-3 py-1.5 font-mono text-[8px] font-bold uppercase tracking-widest flex items-center gap-1.5 border border-black">
                                    Start
                                    <ArrowRight className="w-3 h-3" />
                                </button>
                            </div>

                            <div className="w-full sm:w-1/3 bg-white border-t sm:border-t-0 sm:border-l border-black p-3 flex items-center justify-center relative group-hover:bg-black transition-colors duration-300">
                                <GraduationCap className="w-8 h-8 text-black group-hover:text-white transition-colors duration-300" />
                                <div className="absolute top-2 left-2 w-2 h-2 border-t border-l border-black group-hover:border-white transition-colors"></div>
                                <div className="absolute bottom-2 right-2 w-2 h-2 border-b border-r border-black group-hover:border-white transition-colors"></div>
                            </div>
                        </div>

                    </div>
                </div>
            </div>
        </section>
    );
}
