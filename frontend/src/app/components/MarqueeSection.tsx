import {
    Globe,
    Code2,
    Cloud,
    Database,
    Layers,
    Zap,
    CreditCard,
    Brain
} from "lucide-react";

const technologies = [
    { name: "Google Cloud", icon: Globe },
    { name: "Supabase", icon: Database },
    { name: "Redis", icon: Zap },
    { name: "Slack", icon: Code2 },
    { name: "Salesforce", icon: Cloud },
    { name: "Jira", icon: Layers },
    { name: "Stripe", icon: CreditCard },
    { name: "Canva", icon: Brain }
] as const;

export default function MarqueeSection() {
    return (
        <section className="py-8 sm:py-12 overflow-hidden bg-white relative">
            <div className="text-center mb-8">
                <p className="text-sm font-medium text-[var(--muted-foreground)] uppercase tracking-wider">Built with industry-leading technology</p>
            </div>
            <div className="absolute inset-y-0 left-0 w-16 sm:w-32 bg-gradient-to-r from-white to-transparent z-10" />
            <div className="absolute inset-y-0 right-0 w-16 sm:w-32 bg-gradient-to-l from-white to-transparent z-10" />
            <div className="flex gap-8 sm:gap-16 whitespace-nowrap animate-marquee">
                {technologies.map((tech, i) => (
                    <div key={i} className="flex items-center gap-3 text-base sm:text-xl font-bold text-[var(--foreground)] opacity-40 hover:opacity-100 transition-opacity cursor-pointer">
                        <tech.icon className="h-5 w-5 sm:h-6 sm:w-6" /> {tech.name}
                    </div>
                ))}
                {technologies.map((tech, i) => (
                    <div key={`dup-${i}`} className="flex items-center gap-3 text-base sm:text-xl font-bold text-[var(--foreground)] opacity-40 hover:opacity-100 transition-opacity cursor-pointer">
                        <tech.icon className="h-5 w-5 sm:h-6 sm:w-6" /> {tech.name}
                    </div>
                ))}
            </div>
        </section>
    );
}
