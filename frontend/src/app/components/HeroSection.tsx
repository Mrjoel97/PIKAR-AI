import { BarChart3, Zap, ArrowRight, Bot, Code2, Search, CheckCircle2 } from "lucide-react";

export default function HeroSection() {
    return (
        <section className="relative pt-24 sm:pt-32 pb-12 sm:pb-16 px-6 overflow-hidden min-h-[80vh] sm:min-h-[90vh] flex flex-col justify-center" style={{ backgroundImage: 'linear-gradient(to bottom, #0a2e2e, var(--teal-900), #061a1a)' }}>
            {/* Grid background */}
            <div
                className="absolute inset-0 pointer-events-none opacity-[0.25]"
                style={{
                    backgroundImage: `
            linear-gradient(rgba(86, 171, 145, 0.5) 1px, transparent 1px),
            linear-gradient(90deg, rgba(86, 171, 145, 0.5) 1px, transparent 1px)
          `,
                    backgroundSize: '60px 60px',
                    maskImage: 'radial-gradient(ellipse at center, black 50%, transparent 85%)',
                    WebkitMaskImage: 'radial-gradient(ellipse at center, black 50%, transparent 85%)'
                }}
            />

            {/* Glowing Orbs */}
            <div className="absolute top-10 left-1/4 w-[300px] h-[300px] sm:w-[500px] sm:h-[500px] bg-[var(--teal-500)]/10 rounded-full blur-[120px] pointer-events-none" />
            <div className="absolute bottom-0 right-1/4 w-[260px] h-[260px] sm:w-[400px] sm:h-[400px] bg-purple-500/10 rounded-full blur-[100px] pointer-events-none" />

            <div className="mx-auto max-w-7xl relative z-10 w-full">
                {/* Header Text */}
                <div
                    className="text-center max-w-3xl mx-auto mb-16 animate-[fadeInUp_0.6s_ease-out_both]"
                >
                    <h1 className="text-2xl sm:text-3xl md:text-4xl lg:text-6xl font-bold tracking-tight text-white leading-[1.1] mb-6 drop-shadow-2xl" style={{ fontFamily: 'var(--font-display)' }}>
                        Stop Running<br />
                        <span className="text-transparent bg-clip-text bg-gradient-to-r from-[var(--teal-200)] to-[var(--teal-400)]">10 Jobs Alone.</span>
                    </h1>

                    <p className="mx-auto max-w-2xl text-base text-[var(--teal-100)]/70 leading-relaxed mb-8 font-sans">
                        Pikar-AI gives founders and operators a coordinated AI executive team for research, ops, finance, and growth work that usually eats the week.
                    </p>

                    <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-4">
                        <a
                            href="#waitlist"
                            className="group relative px-6 py-3 rounded-full bg-gradient-to-r from-[var(--teal-500)] to-[var(--teal-600)] text-white font-bold text-xs shadow-lg shadow-[var(--teal-500)]/25 hover:shadow-[var(--teal-400)]/40 hover:scale-105 transition-all overflow-hidden"
                        >
                            <div className="absolute inset-0 bg-white/20 group-hover:translate-x-full transition-transform duration-500 skew-x-12 -translate-x-[120%]" />
                            <span className="relative flex items-center gap-2">
                                Join Waitlist <ArrowRight className="h-4 w-4" />
                            </span>
                        </a>
                        <a
                            href="#system"
                            className="px-6 py-3 rounded-full border border-white/20 text-white/90 font-bold text-xs hover:bg-white/10 transition-colors"
                        >
                            <span className="relative flex items-center gap-2">
                                See the System
                            </span>
                        </a>
                    </div>

                    <p className="mx-auto max-w-md text-[11px] text-[var(--teal-100)]/55 font-sans uppercase tracking-[0.2em]">
                        Early access for founders. Beta workflows roll out in waves.
                    </p>
                </div>

                {/* 3-Column Glass Layout */}
                <div className="grid lg:grid-cols-12 gap-6 items-center">

                    {/* LEFT: Floating Glass Metrics (Previously Phone) */}
                    <div className="lg:col-span-3 space-y-4 hidden lg:block">
                        <div className="animate-[fadeInLeft_0.6s_ease-out_0.2s_both]">
                            {/* Card 1: Founder Problem */}
                            <div className="backdrop-blur-xl bg-white/5 border border-white/10 rounded-2xl p-5 shadow-2xl relative overflow-hidden group hover:bg-white/10 transition-colors">
                                <div className="absolute top-0 right-0 p-3 opacity-20">
                                    <Bot className="w-12 h-12 text-white" />
                                </div>
                                <p className="text-[var(--teal-200)] text-xs font-semibold uppercase tracking-wider mb-1">Founder Reality</p>
                                <div className="flex items-baseline gap-1">
                                    <span className="text-3xl font-bold text-white tracking-tight">10 Jobs</span>
                                </div>
                                <p className="text-white/40 text-[10px] mt-2">Pikar-AI is built to reduce the hat-switching that slows growth.</p>
                                <div className="absolute bottom-0 left-0 h-1 bg-gradient-to-r from-[var(--teal-400)] to-transparent w-full" />
                            </div>
                        </div>

                        <div className="animate-[fadeInLeft_0.6s_ease-out_0.4s_both]">
                            {/* Card 2: Approval Layer */}
                            <div className="backdrop-blur-xl bg-white/5 border border-white/10 rounded-2xl p-5 shadow-2xl relative overflow-hidden group hover:bg-white/10 transition-colors">
                                <div className="absolute top-0 right-0 p-3 opacity-20">
                                    <Zap className="w-12 h-12 text-purple-300" />
                                </div>
                                <p className="text-purple-200 text-xs font-semibold uppercase tracking-wider mb-1">Control Layer</p>
                                <div className="flex items-baseline gap-1">
                                    <span className="text-3xl font-bold text-white tracking-tight">Human-Led</span>
                                </div>
                                <p className="text-white/40 text-[10px] mt-2">You approve the critical moves while the system does the heavy lifting.</p>
                                <div className="absolute bottom-0 left-0 h-1 bg-gradient-to-r from-purple-400 to-transparent w-full" />
                            </div>
                        </div>
                    </div>

                    {/* CENTER: Main Agent Orchestrator Dashboard */}
                    <div className="lg:col-span-6 animate-[fadeInUp_0.6s_ease-out_0.3s_both]">
                        <div className="backdrop-blur-2xl bg-[#0f172a]/40 border border-white/10 rounded-[2rem] overflow-hidden shadow-[0_0_50px_-12px_rgba(45,212,191,0.2)] ring-1 ring-white/5 relative">
                            {/* Glass Reflection */}
                            <div className="absolute inset-0 bg-gradient-to-br from-white/10 via-transparent to-transparent pointer-events-none" />

                            {/* Dashboard Header */}
                            <div className="px-6 py-4 border-b border-white/5 flex items-center justify-between bg-black/20">
                                <div className="flex items-center gap-3">
                                    <div className="w-3 h-3 rounded-full bg-red-400/80" />
                                    <div className="w-3 h-3 rounded-full bg-yellow-400/80" />
                                    <div className="w-3 h-3 rounded-full bg-green-400/80" />
                                    <div className="h-6 w-[1px] bg-white/10 mx-1" />
                                    <span className="text-white/80 text-sm font-medium tracking-wide">AI Executive System</span>
                                </div>
                                <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-[var(--teal-500)]/20 border border-[var(--teal-500)]/30">
                                    <div className="w-1.5 h-1.5 rounded-full bg-[var(--teal-400)] animate-pulse" />
                                    <span className="text-[var(--teal-200)] text-[10px] font-bold uppercase tracking-wider">Founder Mode</span>
                                </div>
                            </div>

                            {/* Dashboard Body */}
                            <div className="p-6 space-y-6">
                                {/* Top Row: Stats */}
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="bg-white/5 rounded-xl p-4 border border-white/5">
                                        <p className="text-white/50 text-xs uppercase tracking-wider mb-2">Cross-Functional Coverage</p>
                                        <div className="h-16 flex items-end gap-1">
                                            {[30, 45, 35, 60, 50, 75, 65, 80, 70, 95].map((h, i) => (
                                                <div key={i} className="flex-1 bg-[var(--teal-500)] opacity-50 rounded-t-sm" style={{ height: `${h}%` }} />
                                            ))}
                                        </div>
                                    </div>
                                    <div className="bg-white/5 rounded-xl p-4 border border-white/5 flex flex-col justify-center relative overflow-hidden">
                                        <div className="absolute -right-4 -bottom-4 w-24 h-24 bg-[var(--teal-500)]/20 rounded-full blur-2xl" />
                                        <p className="text-white/50 text-xs uppercase tracking-wider mb-1">Approval Layer</p>
                                        <p className="text-5xl font-bold text-white tracking-tighter">Human</p>
                                        <p className="text-[var(--teal-400)] text-[10px] mt-1">Keep control of critical actions</p>
                                    </div>
                                </div>

                                {/* Active Agents List */}
                                <div>
                                    <p className="text-white/50 text-xs uppercase tracking-wider mb-3 pl-1">Active Executive Roles</p>
                                    <div className="space-y-3">
                                        {/* Agent 1 */}
                                        <div className="flex items-center justify-between p-3 rounded-xl bg-white/5 border border-white/5 hover:bg-white/10 transition-colors">
                                            <div className="flex items-center gap-3">
                                                <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center border border-blue-500/30">
                                                    <Search className="w-5 h-5 text-blue-400" />
                                                </div>
                                                <div>
                                                    <p className="text-white text-sm font-semibold">Market Research Lead</p>
                                                    <p className="text-white/40 text-[10px]">Analyzing the founder playbook...</p>
                                                </div>
                                            </div>
                                            <div className="px-2 py-1 rounded bg-blue-500/10 border border-blue-500/20 text-blue-400 text-[10px] font-medium">Running</div>
                                        </div>

                                        {/* Agent 2 */}
                                        <div className="flex items-center justify-between p-3 rounded-xl bg-white/5 border border-white/5 hover:bg-white/10 transition-colors">
                                            <div className="flex items-center gap-3">
                                                <div className="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center border border-purple-500/30">
                                                    <Code2 className="w-5 h-5 text-purple-400" />
                                                </div>
                                                <div>
                                                    <p className="text-white text-sm font-semibold">Operations Lead</p>
                                                    <p className="text-white/40 text-[10px]">Turning ideas into shipped workflows...</p>
                                                </div>
                                            </div>
                                            <div className="px-2 py-1 rounded bg-purple-500/10 border border-purple-500/20 text-purple-400 text-[10px] font-medium">Running</div>
                                        </div>

                                        {/* Agent 3 */}
                                        <div className="flex items-center justify-between p-3 rounded-xl bg-white/5 border border-white/5 hover:bg-white/10 transition-colors">
                                            <div className="flex items-center gap-3">
                                                <div className="w-10 h-10 rounded-lg bg-[var(--teal-500)]/20 flex items-center justify-center border border-[var(--teal-500)]/30">
                                                    <BarChart3 className="w-5 h-5 text-[var(--teal-400)]" />
                                                </div>
                                                <div>
                                                    <p className="text-white text-sm font-semibold">Growth Analyst</p>
                                                    <p className="text-white/40 text-[10px]">Surfacing traction signals and next moves...</p>
                                                </div>
                                            </div>
                                            <div className="px-2 py-1 rounded bg-[var(--teal-500)]/10 border border-[var(--teal-500)]/20 text-[var(--teal-400)] text-[10px] font-medium">Running</div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* RIGHT: Floating Phone (Notification) */}
                    <div className="lg:col-span-3 hidden lg:block relative animate-[fadeInRight_0.6s_ease-out_0.4s_both]">
                        {/* Glass Phone Frame */}
                        <div className="backdrop-blur-lg bg-black/40 border-[4px] border-white/10 rounded-[2.5rem] p-1 shadow-2xl relative max-w-[240px] mx-auto overflow-hidden">
                            {/* Screen */}
                            <div className="bg-[var(--teal-950)] rounded-[2.2rem] h-[400px] relative overflow-hidden flex flex-col">
                                {/* Status Bar */}
                                <div className="h-6 flex justify-between items-center px-6 mt-3 text-[10px] text-white/60">
                                    <span>9:41</span>
                                    <div className="flex gap-1">
                                        <div className="w-3 h-3 bg-white/60 rounded-full" />
                                        <div className="w-3 h-3 bg-white/30 rounded-full" />
                                    </div>
                                </div>

                                {/* Phone Content - Notification Center */}
                                <div className="mt-8 px-4 flex-1">
                                    <p className="text-white/40 text-center text-xs mb-4">Wednesday, Jan 28</p>

                                    {/* Glass Notification 1 */}
                                    <div className="backdrop-blur-md bg-white/10 border border-white/10 p-3 rounded-2xl mb-3 shadow-lg">
                                        <div className="flex gap-3">
                                            <div className="w-9 h-9 rounded-xl bg-[var(--teal-600)] flex items-center justify-center shrink-0">
                                                <Bot className="text-white w-5 h-5" />
                                            </div>
                                            <div>
                                                <div className="flex justify-between items-start w-full gap-2">
                                                    <p className="text-white text-xs font-bold">Pikar AI</p>
                                                    <span className="text-white/40 text-[9px]">Now</span>
                                                </div>
                                                <p className="text-white/90 text-[11px] leading-tight mt-0.5">
                                                    Waitlist invites queued.<br />Your early-access rollout plan is ready.
                                                </p>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Glass Notification 2 */}
                                    <div className="backdrop-blur-md bg-white/5 border border-white/5 p-3 rounded-2xl mb-3">
                                        <div className="flex gap-3">
                                            <div className="w-9 h-9 rounded-xl bg-purple-600 flex items-center justify-center shrink-0">
                                                <Code2 className="text-white w-5 h-5" />
                                            </div>
                                            <div>
                                                <div className="flex justify-between items-start w-full gap-2">
                                                    <p className="text-white text-xs font-bold">Ops Agent</p>
                                                    <span className="text-white/40 text-[9px]">2m ago</span>
                                                </div>
                                                <p className="text-white/90 text-[11px] leading-tight mt-0.5">
                                                    Landing-page waitlist flow prepared for founder review.
                                                </p>
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                {/* Home Indicator */}
                                <div className="absolute bottom-2 left-1/2 -translate-x-1/2 w-24 h-1 bg-white/20 rounded-full" />
                            </div>
                        </div>

                        {/* Floating Badge behind phone */}
                        <div className="absolute -bottom-6 -right-4 backdrop-blur-xl bg-[var(--teal-500)] text-white p-3 rounded-2xl shadow-xl border border-white/20 animate-bounce delay-1000">
                            <CheckCircle2 className="w-6 h-6" />
                        </div>
                    </div>
                </div>

                {/* Mobile Fallback */}
                <div className="lg:hidden mt-12 px-4">
                    <div className="backdrop-blur-xl bg-white/5 border border-white/10 rounded-2xl p-6 text-center">
                        <p className="text-white text-sm font-semibold mb-2">Pikar AI Executive System</p>
                        <p className="text-4xl font-bold text-[var(--teal-200)]">10</p>
                        <p className="text-white/40 text-xs">specialized agents for founder leverage</p>
                    </div>
                </div>

            </div>
        </section>
    );
}
