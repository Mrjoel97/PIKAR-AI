"use client";

import React from "react";
import Link from "next/link";
import {
    Mail,
    Box,
    Building2,
    Library,
    Shield,
    Bolt,
    Linkedin,
    Github,
    Facebook
} from "lucide-react";

export default function Footer() {
    return (
        <>
        <script
            type="application/ld+json"
            dangerouslySetInnerHTML={{
                __html: JSON.stringify({
                    "@context": "https://schema.org",
                    "@type": "Organization",
                    "name": "Pikar AI",
                    "url": "https://pikar.ai",
                    "logo": "https://pikar.ai/logo.png",
                    "contactPoint": {
                        "@type": "ContactPoint",
                        "email": "hello@pikar.ai",
                        "contactType": "sales"
                    },
                    "sameAs": []
                })
            }}
        />
        <footer className="relative z-10 w-full pt-5 pb-3 px-3 md:px-6 lg:px-12 overflow-hidden text-white" style={{ backgroundImage: 'linear-gradient(to bottom, #0a2e2e, var(--teal-900), #061a1a)' }}>
            {/* Background elements */}
            {/* Background elements */}
            <div className="absolute inset-0 pointer-events-none z-0 opacity-20"
                style={{
                    backgroundImage: "radial-gradient(rgba(255,255,255,0.2) 1px, transparent 1px)",
                    backgroundSize: "24px 24px"
                }}>
            </div>
            <div className="absolute top-[-20%] left-[-10%] w-[200px] h-[200px] bg-teal-500/10 rounded-full blur-[60px] pointer-events-none"></div>
            <div className="absolute bottom-[-10%] right-[-10%] w-[300px] h-[300px] bg-emerald-500/10 rounded-full blur-[60px] pointer-events-none"></div>

            <div className="max-w-7xl mx-auto relative z-10">
                {/* Newsletter Section */}
                <div className="max-w-4xl mx-auto text-center mb-4 relative">
                    <div className="inline-flex items-center gap-1.5 px-1.5 py-0.5 rounded-full bg-[#17cfaa]/10 text-[#17cfaa] text-[9px] font-bold tracking-wide mb-2 uppercase">
                        <span className="w-1 h-1 rounded-full bg-[#17cfaa]"></span>
                        Newsletter
                    </div>
                    <h2 className="text-xl md:text-2xl font-extrabold text-white mb-1 tracking-tight">
                        Stay in the loop
                    </h2>
                    <p className="text-xs text-teal-100/70 mb-3 max-w-lg mx-auto leading-relaxed font-sans">
                        Get the latest AI automation tips, product updates, and exclusive offers directly to your inbox.
                    </p>
                    <div className="p-0.5 rounded-xl max-w-md mx-auto flex items-center shadow-sm bg-white/5 backdrop-blur-md border border-white/10">
                        <div className="pl-2 text-teal-200/50">
                            <Mail className="w-3.5 h-3.5" />
                        </div>
                        <input
                            className="w-full bg-transparent border-none focus:ring-0 text-white placeholder-teal-200/30 py-1.5 px-3 text-xs outline-none"
                            placeholder="Enter your email address"
                            type="email"
                        />
                        <button className="bg-[#17cfaa] hover:bg-[#13a588] text-white font-bold text-[10px] py-1.5 px-4 rounded-lg shadow-lg transition-all duration-300 transform hover:-translate-y-0.5 whitespace-nowrap">
                            Subscribe
                        </button>
                    </div>
                </div>

                {/* Links Grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-y-4 gap-x-4 mb-3">
                    {/* Product Column */}
                    <div className="flex flex-col gap-2">
                        <div className="flex items-center gap-2 text-white font-bold text-xs mb-1">
                            <span className="p-1 rounded-md bg-[#17cfaa]/10 text-[#17cfaa]">
                                <Box className="w-3.5 h-3.5" />
                            </span>
                            Product
                        </div>
                        <ul className="flex flex-col gap-2">
                            {['Features', 'Pricing', 'Integrations', 'API', 'Changelog'].map((item) => (
                                <li key={item}>
                                    <a className="text-teal-100/60 hover:text-[#17cfaa] transition-colors text-[10px] font-medium cursor-pointer">
                                        {item}
                                    </a>
                                </li>
                            ))}
                        </ul>
                    </div>

                    {/* Company Column */}
                    <div className="flex flex-col gap-2">
                        <div className="flex items-center gap-2 text-white font-bold text-xs mb-1">
                            <span className="p-1 rounded-md bg-[#17cfaa]/10 text-[#17cfaa]">
                                <Building2 className="w-3.5 h-3.5" />
                            </span>
                            Company
                        </div>
                        <ul className="flex flex-col gap-2">
                            {['About', 'Careers', 'Blog', 'Press', 'Contact'].map((item) => (
                                <li key={item}>
                                    <a className="text-teal-100/60 hover:text-[#17cfaa] transition-colors text-[10px] font-medium cursor-pointer">
                                        {item}
                                    </a>
                                </li>
                            ))}
                        </ul>
                    </div>

                    {/* Resources Column */}
                    <div className="flex flex-col gap-2">
                        <div className="flex items-center gap-2 text-white font-bold text-xs mb-1">
                            <span className="p-1 rounded-md bg-[#17cfaa]/10 text-[#17cfaa]">
                                <Library className="w-3.5 h-3.5" />
                            </span>
                            Resources
                        </div>
                        <ul className="flex flex-col gap-2">
                            {['Documentation', 'Tutorials', 'Community', 'Support', 'Status'].map((item) => (
                                <li key={item}>
                                    <a className="text-teal-100/60 hover:text-[#17cfaa] transition-colors text-[10px] font-medium cursor-pointer">
                                        {item}
                                    </a>
                                </li>
                            ))}
                        </ul>
                    </div>

                    {/* Legal Column */}
                    <div className="flex flex-col gap-2">
                        <div className="flex items-center gap-2 text-white font-bold text-xs mb-1">
                            <span className="p-1 rounded-md bg-[#17cfaa]/10 text-[#17cfaa]">
                                <Shield className="w-3.5 h-3.5" />
                            </span>
                            Legal
                        </div>
                        <ul className="flex flex-col gap-2">
                            {['Privacy Policy', 'Terms of Service', 'Security', 'Cookies'].map((item) => (
                                <li key={item}>
                                    {item === 'Privacy Policy' ? (
                                        <Link href="/privacy" className="text-teal-100/60 hover:text-[#17cfaa] transition-colors text-[10px] font-medium cursor-pointer">
                                            {item}
                                        </Link>
                                    ) : item === 'Terms of Service' ? (
                                        <Link href="/terms" className="text-teal-100/60 hover:text-[#17cfaa] transition-colors text-[10px] font-medium cursor-pointer">
                                            {item}
                                        </Link>
                                    ) : (
                                        <a className="text-teal-100/60 hover:text-[#17cfaa] transition-colors text-[10px] font-medium cursor-pointer">
                                            {item}
                                        </a>
                                    )}
                                </li>
                            ))}
                        </ul>
                    </div>
                </div>

                {/* Bottom Bar */}
                <div className="border-t border-white/10 pt-3 flex flex-col md:flex-row justify-between items-center gap-3">
                    <div className="flex items-center gap-3">
                        <div className="flex items-center gap-2 text-white">
                            <span className="w-6 h-6 rounded-full bg-[#17cfaa] flex items-center justify-center text-white shadow-lg shadow-[#17cfaa]/30">
                                <Bolt className="w-4 h-4 fill-current" />
                            </span>
                            <span className="font-extrabold text-base tracking-tight">Pikar AI</span>
                        </div>
                        <span className="hidden md:inline text-teal-100/20">|</span>
                        <p className="text-[10px] text-teal-100/40 font-medium">
                            © 2024 Pikar AI Inc. All rights reserved.
                        </p>
                    </div>

                    <div className="flex gap-3">
                        {[
                            { Icon: Linkedin, href: "#" },
                            { Icon: Linkedin, href: "#" }, // Placeholder for generic social icon 1
                            { Icon: Github, href: "#" },
                            { Icon: Facebook, href: "#" }
                        ].map((social, index) => (
                            <a
                                key={index}
                                href={social.href}
                                className="w-6 h-6 rounded-full flex items-center justify-center text-teal-100/80 transition-all duration-300 hover:bg-white/10 hover:text-white hover:shadow-lg hover:-translate-y-1 bg-white/5 border border-white/10 backdrop-blur-sm"
                            >
                                <social.Icon className="w-3 h-3 fill-current" />
                            </a>
                        ))}
                    </div>
                </div>
            </div>
        </footer>
        </>
    );
}
