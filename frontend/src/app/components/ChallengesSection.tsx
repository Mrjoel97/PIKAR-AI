import React from 'react';
import Image from 'next/image';
import { Layers, Hourglass, XCircle, ArrowDown } from 'lucide-react';
import FadeIn from '../components/ui/FadeIn';

const cards = [
    {
        icon: Layers,
        img: "/assets/stressed-worker.png",
        imgAlt: "Stressed professional",
        title: "Drowning in Repetitive Tasks",
        desc: "You spend 60% of your day on admin work that doesn\u2019t move the needle, leaving zero time for strategy.",
        delay: 0.1,
    },
    {
        icon: Hourglass,
        img: "/assets/pensive-exec.png",
        imgAlt: "Thinking executive",
        title: "Decisions That Take Forever",
        desc: "Market analysis? Competitor research? By the time you manually gather data, the opportunity is gone.",
        delay: 0.15,
    },
    {
        icon: XCircle,
        img: "/assets/team-bottleneck.png",
        imgAlt: "Team frustration",
        title: "Team Bottlenecks Everywhere",
        desc: "Talent wasted on mundane work. Knowledge silos slow everything down to a frustrating crawl.",
        delay: 0.2,
    },
] as const;

export default function ChallengesSection() {
    return (
        <section className="relative w-full py-8 md:py-10 px-4 font-sans overflow-hidden">

            {/* Background Image (Real Office) */}
            <div className="absolute inset-0 z-0">
                <Image
                    alt="Modern white office background"
                    className="w-full h-full object-cover opacity-100"
                    src="/assets/office-bg.png"
                    width={1920}
                    height={1080}
                />
            </div>

            <div className="relative z-10 max-w-4xl mx-auto w-full">

                {/* Header */}
                <div className="text-center mb-6 space-y-1.5">
                    <h2 className="font-display text-2xl md:text-3xl font-bold tracking-tight text-slate-900 font-neural-display drop-shadow-sm">
                        Sound Familiar?
                    </h2>
                    <p className="max-w-lg mx-auto text-xs md:text-sm text-slate-700 font-bold leading-relaxed font-neural-sans drop-shadow-sm">
                        These challenges are costing you hours every week—and <span className="text-[#047857] font-extrabold">holding your business back.</span>
                    </p>
                </div>

                {/* Cards Grid */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-6">
                    {cards.map((card) => (
                        <FadeIn key={card.title} delay={card.delay}>
                            <div className="group rounded-xl p-3 transition-[transform,box-shadow] duration-300 hover:-translate-y-1 bg-white/80 border border-white/60 shadow-[0_4px_20px_rgb(0,0,0,0.1)] hover:shadow-[0_8px_25px_rgb(0,0,0,0.15)]">
                                <div className="flex flex-col h-full">
                                    <div className="flex justify-between items-start mb-3">
                                        <div className="w-8 h-8 rounded-lg bg-[#064e3b] flex items-center justify-center shadow-md text-[#34d399]">
                                            <card.icon className="w-4 h-4" />
                                        </div>
                                        <div className="w-12 h-12 rounded-md overflow-hidden shadow-sm ring-1 ring-white shrink-0">
                                            <Image
                                                alt={card.imgAlt}
                                                className="w-full h-full object-cover transform group-hover:scale-110 transition-transform duration-500"
                                                src={card.img}
                                                width={48}
                                                height={48}
                                            />
                                        </div>
                                    </div>
                                    <h3 className="font-display text-base font-bold text-slate-900 mb-1.5 font-neural-display leading-tight">
                                        {card.title}
                                    </h3>
                                    <p className="text-[10px] md:text-xs text-slate-700 leading-relaxed font-neural-sans font-medium">
                                        {card.desc}
                                    </p>
                                </div>
                            </div>
                        </FadeIn>
                    ))}
                </div>

                {/* Bottom CTA */}
                <div className="flex flex-col items-center space-y-3">
                    <h4 className="font-display text-lg md:text-xl font-bold text-slate-800 text-center px-4 font-neural-display">
                        What if your business ran on <span className="italic text-[#10b981]">autopilot</span>—intelligently?
                    </h4>
                    <a href="#features" className="relative group cursor-pointer" aria-label="Scroll to features">
                        <div className="absolute inset-0 bg-[#34d399]/40 rounded-full blur-xl group-hover:bg-[#34d399]/60 transition-colors"></div>
                        <div className="relative w-10 h-10 md:w-12 md:h-12 bg-[#34d399] rounded-full flex items-center justify-center text-[#064e3b] shadow-lg shadow-[#34d399]/30 transition-transform duration-300 group-hover:scale-110 active:scale-95">
                            <ArrowDown className="w-5 h-5 md:w-6 md:h-6" />
                        </div>
                    </a>
                </div>

            </div>
        </section>
    );
}
