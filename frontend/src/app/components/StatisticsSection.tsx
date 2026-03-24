import { Cpu, BarChart3, Users, Clock } from "lucide-react";

const stats = [
    { label: "AI Agents", value: "10", icon: Cpu },
    { label: "Business Functions", value: "10+", icon: BarChart3 },
    { label: "Integrations", value: "100+", icon: Users },
    { label: "Uptime Target", value: "99.9%", icon: Clock },
] as const;

export default function StatisticsSection() {
    return (
        <section className="bg-[var(--muted)] border-y border-[var(--border)]">
            <div className="mx-auto max-w-7xl px-6 py-6">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {stats.map((stat, i) => (
                        <div
                            key={i}
                            className="flex flex-col items-center gap-1 p-3 rounded-xl bg-white/80 shadow-md ring-1 ring-black/5 cursor-pointer transition-[transform,box-shadow] duration-200 hover:-translate-y-0.5 hover:shadow-lg"
                        >
                            <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-[var(--teal-100)] to-[var(--teal-50)] flex items-center justify-center">
                                <stat.icon className="h-4 w-4 text-[var(--teal-600)]" />
                            </div>
                            <span className="text-lg md:text-xl font-bold text-[var(--foreground)] tracking-tight" style={{ fontFamily: 'var(--font-display)' }}>{stat.value}</span>
                            <span className="text-[10px] font-semibold text-[var(--muted-foreground)] uppercase tracking-wider">{stat.label}</span>
                        </div>
                    ))}
                </div>
            </div>
        </section>
    );
}
