"use client";

import {
    Globe,
    Code2,
    Cloud,
    Brain,
    Users,
    Cpu,
    Database,
    Layers
} from "lucide-react";
import FadeIn from "../components/ui/FadeIn";

export default function MarqueeSection() {
    return (
        <FadeIn delay={0.1}>
            <section className="py-8 sm:py-12 overflow-hidden bg-white relative">
                <div className="text-center mb-8">
                    <p className="text-sm font-medium text-[var(--muted-foreground)] uppercase tracking-wider">Trusted by leading innovators</p>
                </div>
                <div className="absolute inset-y-0 left-0 w-16 sm:w-32 bg-gradient-to-r from-white to-transparent z-10" />
                <div className="absolute inset-y-0 right-0 w-16 sm:w-32 bg-gradient-to-l from-white to-transparent z-10" />
                <div className="flex gap-8 sm:gap-16 whitespace-nowrap animate-marquee">
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
                        <div key={i} className="flex items-center gap-3 text-base sm:text-xl font-bold text-[var(--foreground)] opacity-40 hover:opacity-100 transition-opacity cursor-pointer">
                            <company.icon className="h-5 w-5 sm:h-6 sm:w-6" /> {company.name}
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
                        <div key={`dup-${i}`} className="flex items-center gap-3 text-base sm:text-xl font-bold text-[var(--foreground)] opacity-40 hover:opacity-100 transition-opacity cursor-pointer">
                            <company.icon className="h-5 w-5 sm:h-6 sm:w-6" /> {company.name}
                        </div>
                    ))}
                </div>
            </section>
        </FadeIn>
    );
}
