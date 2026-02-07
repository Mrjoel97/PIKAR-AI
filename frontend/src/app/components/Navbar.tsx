"use client";

import { motion } from "framer-motion";
import { Brain } from "lucide-react";

export default function Navbar() {
    return (
        <header className="fixed top-4 left-0 right-0 z-50">
            <nav className="mx-auto max-w-7xl px-6 py-3 flex items-center justify-between">
                <div className="flex items-center gap-3">
                    {/* Brain icon in rounded box */}
                    <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-[#1a8a6e] to-[#0d6b4f] flex items-center justify-center shadow-lg">
                        <Brain className="h-5 w-5 text-white" />
                    </div>
                    {/* Logo text */}
                    <span className="text-xl font-bold tracking-tight text-white" style={{ fontFamily: 'var(--font-display)' }}>
                        Pikar <span className="text-[#56ab91]">AI</span>
                    </span>
                </div>

                <div className="hidden md:flex items-center gap-1 bg-white/10 backdrop-blur-md border border-white/10 rounded-full px-2 py-1.5 shadow-xl shadow-black/5 translate-x-[10%]">
                    {["Features", "Solutions", "Testimonials", "Pricing"].map((item) => (
                        <motion.a
                            key={item}
                            href={`#${item.toLowerCase()}`}
                            className="text-sm font-medium text-white/80 hover:text-white px-4 py-1.5 rounded-full relative transition-colors"
                            whileHover={{ scale: 1.05 }}
                            whileTap={{ scale: 0.95 }}
                            transition={{ type: "spring", stiffness: 400, damping: 17 }}
                        >
                            {item}
                        </motion.a>
                    ))}
                </div>

                <div className="flex items-center gap-3">
                    <a href="/auth/login" className="hidden text-sm font-medium text-white/70 hover:text-white sm:block cursor-pointer transition-colors px-4 py-2 rounded-full border border-white/20 hover:border-white/40">Sign In</a>
                    <a href="/auth/signup" className="bg-[var(--teal-400)] hover:bg-[var(--teal-300)] text-white text-sm font-semibold px-5 py-2.5 rounded-full transition-colors cursor-pointer">
                        Get Started
                    </a>
                </div>
            </nav>
        </header>
    );
}
