"use client";

import React from 'react';
import Image from 'next/image';
import { Brain, Network, ShieldCheck, ArrowRight, BarChart3, Activity } from 'lucide-react';
import { motion } from 'framer-motion';

export default function CoreCapabilitiesSection() {
    return (
        <section className="relative w-full flex flex-col items-center justify-center overflow-x-hidden py-10 px-4 bg-[#112222] font-display">
            {/* Background Effects */}
            <div className="absolute inset-0 z-0 opacity-50 pointer-events-none bg-[radial-gradient(rgba(255,255,255,0.1)_1px,transparent_1px)] bg-[size:16px_16px]"></div>
            <div className="absolute inset-0 z-0 bg-gradient-to-b from-transparent via-[#112222]/50 to-[#112222] pointer-events-none"></div>

            <div className="relative z-10 w-full max-w-4xl flex flex-col gap-4">

                {/* Header */}
                <div className="flex flex-col items-center text-center space-y-1.5 max-w-xl mx-auto">
                    <motion.span
                        initial={{ opacity: 0, y: 10 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        className="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 bg-[#13ecec]/10 border border-[#13ecec]/20 text-[#13ecec] text-[9px] font-semibold uppercase tracking-wider"
                    >
                        <span className="w-1 h-1 rounded-full bg-[#13ecec] animate-pulse"></span>
                        Variant 2.0
                    </motion.span>
                    <motion.h2
                        initial={{ opacity: 0, y: 10 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.1 }}
                        viewport={{ once: true }}
                        className="text-2xl md:text-3xl font-bold tracking-tight text-white"
                    >
                        Core Capabilities
                    </motion.h2>
                    <motion.p
                        initial={{ opacity: 0, y: 10 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.2 }}
                        viewport={{ once: true }}
                        className="text-[#92c9c9] text-sm max-w-md leading-relaxed"
                    >
                        Powering the next generation of intelligent automation with a sophisticated neural engine.
                    </motion.p>
                </div>

                {/* Bento Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 auto-rows-[minmax(120px,auto)]">

                    {/* Neural Processing Hub (Large) */}
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95 }}
                        whileInView={{ opacity: 1, scale: 1 }}
                        viewport={{ once: true }}
                        className="group col-span-1 md:col-span-2 lg:col-span-2 row-span-2 rounded-lg bg-[#193333] border border-white/5 overflow-hidden flex flex-col transition-all duration-300 hover:border-[#13ecec]/30 hover:-translate-y-0.5 hover:shadow-[0_4px_12px_-4px_rgba(19,236,236,0.15)]"
                    >
                        <div className="p-4 flex flex-col h-full relative z-10">
                            <div className="flex items-start justify-between mb-2">
                                <div>
                                    <h3 className="text-lg font-bold text-white mb-0.5">Neural Processing Hub</h3>
                                    <p className="text-[#92c9c9] max-w-xs text-xs leading-snug">Advanced cognitive engine processing millions of data points per second, purpose-built for enterprise-scale automation.</p>
                                </div>
                                <div className="p-1.5 bg-[#13ecec]/10 rounded-md">
                                    <Brain className="text-[#13ecec] w-6 h-6" />
                                </div>
                            </div>
                            <div className="mt-auto pt-3">
                                <button className="flex items-center gap-1.5 text-[#13ecec] text-xs font-medium group-hover:gap-2.5 transition-all cursor-pointer">
                                    <span>Explore architecture</span>
                                    <ArrowRight className="w-3.5 h-3.5" />
                                </button>
                            </div>
                        </div>
                        <div className="absolute right-0 bottom-0 w-full md:w-2/3 h-full opacity-60 md:opacity-100 pointer-events-none mix-blend-lighten">
                            <div className="relative w-full h-full">
                                <Image src="https://lh3.googleusercontent.com/aida-public/AB6AXuBRcK7QNlOzhTNTcyvnZbo2QNIt7F-vy0_paXQOyCN3rMw9YGquEyNZv6gO8FDvj99KhrRjIW64ZJomso6Upi3rPDUZMRoQ3VgNUJ5hMXqXX3TFFbVUViSqZ0lz_lmPohfbMi1rYCDjN2IZwIvw7qEvtUC60UY_UwrmfNc0nc8UGcxsAJm1wMr7n1yVbT_6eXQbwElvEdsZaUVxRsK8YJI9V-T6dINmSG4VXzjqeyzj1YH4xkTk4OzkEBiy9abXeUfS8-m4-q30POY" alt="Neural processing hub" fill className="object-contain object-right-bottom" sizes="(max-width: 768px) 100vw, 50vw" />
                            </div>
                            <div className="absolute inset-0 bg-gradient-to-r from-[#193333] via-[#193333]/50 to-transparent"></div>
                        </div>
                    </motion.div>

                    {/* Global Integrations */}
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.1 }}
                        viewport={{ once: true }}
                        className="group col-span-1 row-span-1 rounded-lg bg-[#193333] border border-white/5 p-3 flex flex-col justify-between relative overflow-hidden transition-all duration-300 hover:border-[#13ecec]/30 hover:-translate-y-0.5 hover:shadow-[0_4px_12px_-4px_rgba(19,236,236,0.15)]"
                    >
                        <div className="relative z-10">
                            <div className="w-8 h-8 rounded-md bg-[#234848] flex items-center justify-center mb-1.5 text-white">
                                <Network className="w-4 h-4" />
                            </div>
                            <h4 className="text-base font-bold text-white mb-0.5">Global Integrations</h4>
                            <p className="text-[#92c9c9] text-[10px] leading-tight">Seamlessly connects with Slack, Salesforce, and Jira.</p>
                        </div>
                        <div className="absolute -right-3 -bottom-3 w-20 h-20 opacity-20 rotate-12 relative">
                            <Image src="https://lh3.googleusercontent.com/aida-public/AB6AXuDVFje4U6eXjHGtWJkOGbu90CxWDqrBjKzPg1dFg6eyfZZaDzZnxkSvuYk-VJdBTdKEtmLcgzSURQTjw_a76YA2MlGxSVHvjTXXh4mhBl_j9HUf5rgYdVjQ4FhleiPaxTE7MTz2lGaLlFJuwm3Vgh8-vd2ryXXe_-LV38vTrh-lUzmfWV1RIOYvOuH8VeXiL5CXzC9HrndJ_WEWsosavMcMtlwJRWAUNJ104_7JTFDqUgSNtIu-F02YZN2coGnOmb4_uyJWhfNHDFs" alt="" fill className="object-contain" sizes="80px" />
                        </div>
                    </motion.div>

                    {/* Security Fortress */}
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.2 }}
                        viewport={{ once: true }}
                        className="group col-span-1 row-span-1 rounded-lg bg-[#193333] border border-white/5 p-3 flex flex-col justify-between relative overflow-hidden transition-all duration-300 hover:border-[#13ecec]/30 hover:-translate-y-0.5 hover:shadow-[0_4px_12px_-4px_rgba(19,236,236,0.15)]"
                    >
                        <div className="relative z-10">
                            <div className="w-8 h-8 rounded-md bg-[#234848] flex items-center justify-center mb-1.5 text-white">
                                <ShieldCheck className="w-4 h-4" />
                            </div>
                            <h4 className="text-base font-bold text-white mb-0.5">Security Fortress</h4>
                            <p className="text-[#92c9c9] text-[10px] leading-tight">Bank-grade encryption with SOC 2 compliant infrastructure.</p>
                        </div>
                        <div className="absolute top-1/2 right-3 -translate-y-1/2 w-12 h-12 rounded-full bg-[#13ecec]/5 blur-lg group-hover:bg-[#13ecec]/10 transition-colors"></div>
                        <div className="absolute bottom-1 right-1 w-10 h-10 opacity-30 relative">
                            <Image src="https://lh3.googleusercontent.com/aida-public/AB6AXuBpzBXRFICvmx8zp8-iBtplG875yBb_DQXlk0eDVX_nxAtIF-KISYfhISxe9j5brVEp3ZXb9unDRmlSehYXYIsvFz774pJhOe-rcbFNLx0cG4fGteQ-o3_lurwAEtsCML2IluSjmbMxuh9GtDOu4Cle5i7Ax-fxzUWHMtVXwo4i-FE9y3bF0v_S8ypcj_GyNuAXmiagbQYZYGbgISMiDd-aGh6hto4etPTqJ3N5LFY6U9h8RleXXbTULaSGNs9qI_10rH3bmwp7m1s" alt="" fill className="object-contain" sizes="40px" />
                        </div>
                    </motion.div>

                    {/* Analytics */}
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.3 }}
                        viewport={{ once: true }}
                        className="group col-span-1 row-span-1 rounded-lg bg-[#193333] border border-white/5 p-3 flex flex-col justify-between relative overflow-hidden transition-all duration-300 hover:border-[#13ecec]/30 hover:-translate-y-0.5 hover:shadow-[0_4px_12px_-4px_rgba(19,236,236,0.15)]"
                    >
                        <div className="flex justify-between items-start relative z-10">
                            <div>
                                <h4 className="text-base font-bold text-white mb-0.5">Analytics</h4>
                                <p className="text-[#92c9c9] text-[10px]">Instant insights.</p>
                            </div>
                            <div className="h-4 px-1.5 bg-[#13ecec]/20 rounded text-[#13ecec] text-[9px] font-bold flex items-center">LIVE</div>
                        </div>
                        <div className="relative h-10 w-full mt-2 rounded bg-black/20 overflow-hidden border border-white/5 flex items-end justify-around pb-0.5 px-2">
                            <div className="w-1/6 bg-[#13ecec]/30 h-[40%] rounded-t-sm animate-pulse" style={{ animationDelay: '0.1s' }}></div>
                            <div className="w-1/6 bg-[#13ecec]/50 h-[70%] rounded-t-sm animate-pulse" style={{ animationDelay: '0.2s' }}></div>
                            <div className="w-1/6 bg-[#13ecec] h-[55%] rounded-t-sm animate-pulse" style={{ animationDelay: '0.3s' }}></div>
                            <div className="w-1/6 bg-[#13ecec]/80 h-[85%] rounded-t-sm animate-pulse" style={{ animationDelay: '0.4s' }}></div>
                            <div className="w-1/6 bg-[#13ecec]/40 h-[60%] rounded-t-sm animate-pulse" style={{ animationDelay: '0.5s' }}></div>
                        </div>
                    </motion.div>

                    {/* Uptime Stat */}
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.4 }}
                        viewport={{ once: true }}
                        className="group col-span-1 row-span-1 rounded-lg bg-gradient-to-br from-[#13ecec]/20 to-[#193333] border border-[#13ecec]/20 p-3 flex flex-col items-center justify-center text-center relative overflow-hidden transition-all duration-300 hover:-translate-y-0.5 hover:shadow-[0_4px_12px_-4px_rgba(19,236,236,0.15)]"
                    >
                        <div className="absolute inset-0 opacity-5 pointer-events-none" style={{ backgroundImage: "url('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyMCIgaGVpZ2h0PSIyMCI+PGNpcmNsZSBjeD0iMiIgY3k9IjIiIHI9IjEiIGZpbGw9IiMxM2VjZWMiLz48L3N2Zz4=')" }}></div>
                        <h4 className="text-xl font-bold text-white mb-0 z-10">99.9%</h4>
                        <p className="text-[#13ecec] text-[10px] font-medium z-10">Uptime Guarantee</p>
                        <p className="text-[#92c9c9] text-[9px] mt-0.5 z-10">Reliability you can trust.</p>
                    </motion.div>

                    {/* Deployment CTA */}
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.5 }}
                        viewport={{ once: true }}
                        className="group col-span-1 md:col-span-2 lg:col-span-3 row-span-1 rounded-lg bg-[#193333] border border-white/5 p-4 flex flex-col md:flex-row items-center justify-between gap-3 relative overflow-hidden transition-all duration-300 hover:border-[#13ecec]/30 hover:-translate-y-0.5"
                    >
                        <div className="relative z-10 max-w-xl text-center md:text-left">
                            <h3 className="text-lg font-bold text-white mb-0.5">Ready to deploy?</h3>
                            <p className="text-[#92c9c9] text-xs">Get started with our enterprise-grade solution today.</p>
                        </div>
                        <div className="relative z-10 flex gap-2.5 w-full md:w-auto">
                            <button className="flex-1 md:flex-none h-8 px-4 rounded bg-[#13ecec] text-[#112222] text-xs font-bold hover:bg-white transition-colors flex items-center justify-center whitespace-nowrap cursor-pointer">
                                Get Started
                            </button>
                            <button className="flex-1 md:flex-none h-8 px-4 rounded border border-white/20 text-white text-xs font-medium hover:bg-white/10 transition-colors flex items-center justify-center whitespace-nowrap cursor-pointer">
                                Contact Sales
                            </button>
                        </div>
                        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[120%] h-[200%] bg-gradient-to-r from-transparent via-[#13ecec]/5 to-transparent rotate-12 pointer-events-none"></div>
                    </motion.div>

                </div>
            </div>
        </section>
    );
}
