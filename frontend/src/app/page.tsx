"use client";

import {
    Cpu,
    Globe,
    Users,
    BarChart3,
    Clock,
    Brain,
    Code2,
    Database,
    Cloud,
    Layers
} from "lucide-react";
import { motion } from "framer-motion";
import HeroSection from "./components/HeroSection";
import PricingSection from "./components/PricingSection";
import BuiltForGrowthSection from "./components/BuiltForGrowthSection";
import ChallengesSection from "./components/ChallengesSection";
import CoreCapabilitiesSection from "./components/CoreCapabilitiesSection";
import HumanInTheLoopSection from "./components/HumanInTheLoopSection";
import InteractiveVideoShowcase from "./components/InteractiveVideoShowcase";
import ContactSection from "./components/ContactSection";
import FAQSection from "./components/FAQSection";
import ProductSystem from "./components/ProductSystem";
import NeuralGridSection from "./components/NeuralGridSection";
import EducationHubSection from "./components/EducationHubSection";
import Footer from "./components/Footer";
import TestimonialsSection from "./components/TestimonialsSection";
import FadeIn from "./components/ui/FadeIn";

export default function Home() {
    return (
        <div className="relative min-h-screen flex flex-col font-sans selection:bg-[var(--teal-200)] selection:text-[var(--teal-900)]">

            {/* Navbar - Dark Theme for Hero */}
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

            <main className="flex-grow">

                {/* --- HERO SECTION --- */}
                <HeroSection />

                {/* --- STATISTICS SECTION (Compact) --- */}
                <FadeIn delay={0.2}>
                    <section className="bg-[var(--muted)] border-y border-[var(--border)]">
                        <div className="mx-auto max-w-7xl px-6 py-6">
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                {[
                                    { label: "Active Agents", value: "10k+", icon: Cpu },
                                    { label: "Tasks Processed", value: "50M+", icon: BarChart3 },
                                    { label: "Enterprise Users", value: "500+", icon: Users },
                                    { label: "Uptime", value: "99.99%", icon: Clock },
                                ].map((stat, i) => (
                                    <motion.div
                                        key={i}
                                        className="flex flex-col items-center gap-1 p-3 rounded-xl bg-white/80 backdrop-blur-xl shadow-md ring-1 ring-black/5 cursor-pointer"
                                        whileHover={{ y: -2, boxShadow: "0 15px 30px -10px rgba(0, 0, 0, 0.12)" }}
                                        transition={{ type: "spring", stiffness: 300, damping: 20 }}
                                    >
                                        <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-[var(--teal-100)] to-[var(--teal-50)] flex items-center justify-center">
                                            <stat.icon className="h-4 w-4 text-[var(--teal-600)]" />
                                        </div>
                                        <span className="text-lg md:text-xl font-bold text-[var(--foreground)] tracking-tight" style={{ fontFamily: 'var(--font-display)' }}>{stat.value}</span>
                                        <span className="text-[10px] font-semibold text-[var(--muted-foreground)] uppercase tracking-wider">{stat.label}</span>
                                    </motion.div>
                                ))}
                            </div>
                        </div>
                    </section>
                </FadeIn>

                {/* --- MARQUEE LOGO STRIP --- */}
                <FadeIn delay={0.1}>
                    <section className="py-12 overflow-hidden bg-white relative">
                        <div className="text-center mb-8">
                            <p className="text-sm font-medium text-[var(--muted-foreground)] uppercase tracking-wider">Trusted by leading innovators</p>
                        </div>
                        <div className="absolute inset-y-0 left-0 w-32 bg-gradient-to-r from-white to-transparent z-10" />
                        <div className="absolute inset-y-0 right-0 w-32 bg-gradient-to-l from-white to-transparent z-10" />
                        <div className="flex gap-16 whitespace-nowrap animate-marquee">
                            {[
                                { name: "Google", icon: Globe },
                                { name: "Microsoft", icon: Code2 },
                                { name: "Amazon", icon: Cloud },
                                { name: "OpenAI", icon: Brain },
                                { name: "Meta", icon: Users },
                                { name: "Nvidia", icon: Cpu },
                                { name: "Oracle", icon: Database },
                                { name: "Adobe", icon: Layers }
                            ].map((company, i) => (
                                <div key={i} className="flex items-center gap-3 text-xl font-bold text-[var(--foreground)] opacity-40 hover:opacity-100 transition-opacity cursor-pointer">
                                    <company.icon className="h-6 w-6" /> {company.name}
                                </div>
                            ))}
                            {[
                                { name: "Google", icon: Globe },
                                { name: "Microsoft", icon: Code2 },
                                { name: "Amazon", icon: Cloud },
                                { name: "OpenAI", icon: Brain },
                                { name: "Meta", icon: Users },
                                { name: "Nvidia", icon: Cpu },
                                { name: "Oracle", icon: Database },
                                { name: "Adobe", icon: Layers }
                            ].map((company, i) => (
                                <div key={`dup-${i}`} className="flex items-center gap-3 text-xl font-bold text-[var(--foreground)] opacity-40 hover:opacity-100 transition-opacity cursor-pointer">
                                    <company.icon className="h-6 w-6" /> {company.name}
                                </div>
                            ))}
                        </div>
                    </section>
                </FadeIn>



                {/* --- CHALLENGES SECTION --- */}
                <FadeIn delay={0.2}>
                    <ChallengesSection />
                </FadeIn>

                {/* --- CORE CAPABILITIES SECTION --- */}
                <FadeIn>
                    <CoreCapabilitiesSection />
                </FadeIn>

                {/* --- BUILT FOR GROWTH SECTION --- */}
                <FadeIn>
                    <BuiltForGrowthSection />
                </FadeIn>

                {/* --- HUMAN IN THE LOOP SECTION --- */}
                <FadeIn>
                    <HumanInTheLoopSection />
                </FadeIn>

                {/* --- INTERACTIVE VIDEO SHOWCASE --- */}
                <FadeIn>
                    <InteractiveVideoShowcase />
                </FadeIn>

                {/* --- PRODUCT SYSTEM SECTION --- */}
                <FadeIn>
                    <ProductSystem />
                </FadeIn>

                {/* --- NEURAL GRID SECTION --- */}
                <FadeIn>
                    <NeuralGridSection />
                </FadeIn>

                {/* --- EDUCATION HUB SECTION --- */}
                <div className="mt-8 lg:mt-12">
                    <FadeIn>
                        <EducationHubSection />
                    </FadeIn>
                </div>

                {/* --- PRICING SECTION --- */}
                <FadeIn>
                    <PricingSection />
                </FadeIn>

                {/* --- CONTACT SECTION --- */}
                <FadeIn>
                    <ContactSection />
                </FadeIn>

                {/* --- TESTIMONIALS SECTION --- */}
                <section id="testimonials">
                    <FadeIn>
                        <TestimonialsSection />
                    </FadeIn>
                </section>

                {/* --- FAQ SECTION --- */}
                <FadeIn>
                    <FAQSection />
                </FadeIn>

                {/* --- FOOTER --- */}
                <Footer />
            </main>

        </div>
    );
}