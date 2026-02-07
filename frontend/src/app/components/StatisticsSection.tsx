"use client";

import { motion } from "framer-motion";
import { Cpu, BarChart3, Users, Clock } from "lucide-react";
import FadeIn from "../components/ui/FadeIn";

export default function StatisticsSection() {
    return (
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
    );
}
