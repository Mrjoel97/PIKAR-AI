"use client";

// Copyright (c) 2024-2026 Pikar AI. All rights reserved.
// Proprietary and confidential. See LICENSE file for details.


import { Brain, Menu, X } from "lucide-react";
import { useState } from "react";

export default function Navbar() {
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

    return (
        <header className="fixed top-4 left-0 right-0 z-50">
            <nav className="mx-auto max-w-7xl px-6 py-3 flex items-center justify-between">
                <a href="/" className="flex items-center gap-3">
                    {/* Brain icon in rounded box */}
                    <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-[#1a8a6e] to-[#0d6b4f] flex items-center justify-center shadow-lg">
                        <Brain className="h-5 w-5 text-white" />
                    </div>
                    {/* Logo text */}
                    <span className="text-xl font-bold tracking-tight text-white" style={{ fontFamily: 'var(--font-display)' }}>
                        Pikar <span className="text-[#56ab91]">AI</span>
                    </span>
                </a>

                <div className="hidden md:flex items-center gap-1 bg-white/10 backdrop-blur-md border border-white/10 rounded-full px-2 py-1.5 shadow-xl shadow-black/5 translate-x-[10%]">
                    {["Features", "Solutions", "Testimonials", "Pricing"].map((item) => (
                        <a
                            key={item}
                            href={`#${item.toLowerCase()}`}
                            className="text-sm font-medium text-white/80 hover:text-white hover:scale-105 active:scale-95 px-4 py-1.5 rounded-full relative transition-all duration-150"
                        >
                            {item}
                        </a>
                    ))}
                </div>

                <div className="flex items-center gap-3">
                    <a href="/auth/login" className="hidden text-sm font-medium text-white/70 hover:text-white sm:block cursor-pointer transition-colors px-4 py-2 rounded-full border border-white/20 hover:border-white/40">Sign In</a>
                    <a href="#waitlist" className="bg-[var(--teal-400)] hover:bg-[var(--teal-300)] text-white text-sm font-semibold px-5 py-2.5 rounded-full transition-colors cursor-pointer">
                        Join Waitlist
                    </a>
                    <button
                        className="md:hidden p-2 rounded-lg border border-white/20 bg-white/10 text-white hover:bg-white/20 transition-colors"
                        aria-label="Toggle menu"
                        aria-expanded={isMobileMenuOpen}
                        onClick={() => setIsMobileMenuOpen((open) => !open)}
                    >
                        {isMobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
                    </button>
                </div>
            </nav>

            <div className={`md:hidden fixed inset-0 z-40 ${isMobileMenuOpen ? 'pointer-events-auto' : 'pointer-events-none'}`}>
                <div
                    className={`absolute inset-0 bg-black/50 transition-opacity ${isMobileMenuOpen ? 'opacity-100' : 'opacity-0'}`}
                    onClick={() => setIsMobileMenuOpen(false)}
                />
                <div
                    className={`absolute top-0 right-0 h-full w-72 bg-[#0a2e2e] border-l border-white/10 shadow-2xl transform transition-transform ${isMobileMenuOpen ? 'translate-x-0' : 'translate-x-full'}`}
                >
                    <div className="flex items-center justify-between px-5 py-4 border-b border-white/10">
                        <div className="flex items-center gap-3">
                            <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-[#1a8a6e] to-[#0d6b4f] flex items-center justify-center shadow-lg">
                                <Brain className="h-5 w-5 text-white" />
                            </div>
                            <span className="text-lg font-bold tracking-tight text-white" style={{ fontFamily: 'var(--font-display)' }}>
                                Pikar <span className="text-[#56ab91]">AI</span>
                            </span>
                        </div>
                        <button
                            className="p-2 rounded-lg hover:bg-white/10 text-white"
                            aria-label="Close menu"
                            onClick={() => setIsMobileMenuOpen(false)}
                        >
                            <X className="h-5 w-5" />
                        </button>
                    </div>

                    <div className="px-5 py-6 space-y-4">
                        {["Features", "Solutions", "Testimonials", "Pricing"].map((item) => (
                            <a
                                key={item}
                                href={`#${item.toLowerCase()}`}
                                className="block text-sm font-semibold text-white/80 hover:text-white transition-colors"
                                onClick={() => setIsMobileMenuOpen(false)}
                            >
                                {item}
                            </a>
                        ))}

                        <div className="pt-4 border-t border-white/10 space-y-3">
                            <a
                                href="/auth/login"
                                className="block w-full text-center text-sm font-semibold text-white/80 hover:text-white border border-white/20 rounded-full py-2"
                            >
                                Sign In
                            </a>
                            <a
                                href="#waitlist"
                                onClick={() => setIsMobileMenuOpen(false)}
                                className="block w-full text-center bg-[var(--teal-400)] hover:bg-[var(--teal-300)] text-white text-sm font-semibold py-2.5 rounded-full transition-colors"
                            >
                                Join Waitlist
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        </header>
    );
}
