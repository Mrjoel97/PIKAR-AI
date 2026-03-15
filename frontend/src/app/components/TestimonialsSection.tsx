"use client";

import React from 'react';
import Image from 'next/image';
import { Star } from 'lucide-react';
import styles from './TestimonialsSection.module.css';
import { TESTIMONIALS } from '@/data/mockData';

const TestimonialsSection = () => {
    // Duplicate data for infinite marquee effect
    const marqueeData = [...TESTIMONIALS, ...TESTIMONIALS];

    return (
        <div className="relative z-10 w-full py-8 lg:py-12 bg-[#f0f4f8] text-[#1e293b] font-sans antialiased overflow-hidden flex flex-col justify-center">
            {/* Background Elements */}
            <div className="absolute inset-0 bg-[#f0f4f8] z-0 pointer-events-none">
                <div className={`absolute inset-0 ${styles.bgDotPattern} opacity-40`}></div>
                <div className={`absolute top-[10%] left-[5%] w-24 h-24 ${styles.claySphere} ${styles.animateFloat} z-0 opacity-80`}></div>
                <div className={`absolute bottom-[20%] right-[8%] w-32 h-32 ${styles.claySphereTeal} ${styles.animateFloat2} z-0 opacity-60`}></div>
                <div className={`absolute top-[40%] right-[20%] w-16 h-16 ${styles.claySphere} ${styles.animateFloat} delay-700 z-0 opacity-50 blur-[1px]`}></div>
                <div className={`absolute bottom-[10%] left-[20%] w-20 h-20 ${styles.claySphere} ${styles.animateFloat2} delay-1000 z-0 opacity-70`}></div>
            </div>

            <div className="relative z-10 w-full">
                <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 mb-12 text-center">
                    <div className="inline-flex items-center justify-center p-1.5 mb-6 rounded-full bg-white shadow-[5px_5px_10px_rgba(163,177,198,0.2),-5px_-5px_10px_rgba(255,255,255,1)]">
                        <span className="px-4 py-1 rounded-full bg-[#17cfaa]/10 text-[#17cfaa] text-xs font-bold uppercase tracking-wider border border-[#17cfaa]/20">
                            Social Proof
                        </span>
                    </div>
                    <h2 className="font-display text-3xl md:text-4xl lg:text-5xl font-bold text-[#1e293b] tracking-tight leading-none mb-6 drop-shadow-sm">
                        Trusted by the Best
                    </h2>
                    <p className="text-xl text-[#64748b] max-w-2xl mx-auto font-normal leading-relaxed">
                        Join thousands of product teams who rely on Pikar AI to streamline their daily operations with precision.
                    </p>
                </div>

                <div className="w-full relative group">
                    <div className="absolute left-0 top-0 bottom-0 w-32 md:w-64 z-20 bg-gradient-to-r from-[#f0f4f8] via-[#f0f4f8]/80 to-transparent pointer-events-none"></div>
                    <div className="absolute right-0 top-0 bottom-0 w-32 md:w-64 z-20 bg-gradient-to-l from-[#f0f4f8] via-[#f0f4f8]/80 to-transparent pointer-events-none"></div>

                    <div className="flex w-full overflow-hidden py-6">
                        <div className={`flex ${styles.animateMarquee} min-w-full items-center gap-8 pl-8 group-hover:[animation-play-state:paused]`}>
                            {marqueeData.map((testimonial, index) => (
                                <div
                                    key={`${testimonial.id}-${index}`}
                                    className={`${styles.clayCard} w-[380px] md:w-[420px] flex-shrink-0 p-8 flex flex-col gap-6`}
                                >
                                    <div className="flex items-center gap-4">
                                        <div className="size-16 rounded-full bg-white p-1 shadow-md">
                                            <div className="relative w-full h-full rounded-full overflow-hidden bg-gray-200">
                                                <Image src={testimonial.image} alt={testimonial.name} fill className="object-cover" sizes="56px" />
                                            </div>
                                        </div>
                                        <div>
                                            <h3 className="text-[#1e293b] font-bold text-xl font-display">{testimonial.name}</h3>
                                            <p className="text-[#64748b] text-sm font-medium">{testimonial.role}</p>
                                        </div>
                                    </div>
                                    <div className="flex gap-1">
                                        {[1, 2, 3, 4, 5].map((_, i) => (
                                            <Star key={i} className="w-5 h-5 fill-amber-400 text-amber-500 drop-shadow-sm" />
                                        ))}
                                    </div>
                                    <p className="text-[#1e293b] text-[16px] leading-relaxed font-medium">
                                        &quot;{testimonial.quote}&quot;
                                    </p>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default TestimonialsSection;
