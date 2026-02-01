"use client";

import React, { useState } from 'react';
import { Plus } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function FAQSection() {
    const [openIndex, setOpenIndex] = useState<number | null>(null);

    const toggleAccordion = (index: number) => {
        setOpenIndex(openIndex === index ? null : index);
    };

    const faqs = [
        {
            question: "How do Pikar AI agents learn my business logic?",
            answer: "Our agents ingest your existing documentation, standard operating procedures (SOPs), and historical workflow data to build a custom semantic model of your business logic. This ensures they act consistently with your company's specific rules and guidelines, refining their understanding over time through feedback loops."
        },
        {
            question: "Is my data secure?",
            answer: "Absolutely. We adhere to strict SOC2 Type II compliance standards. All data is encrypted both in transit (TLS 1.3) and at rest (AES-256). We offer single-tenant deployment options for enterprise clients requiring complete data isolation, ensuring your proprietary information never leaves your controlled environment."
        },
        {
            question: "Can I integrate with custom enterprise tools?",
            answer: "Yes, extensibility is at the core of Pikar AI. Our platform supports a robust API and webhook system that allows seamless integration with legacy ERPs, custom CRMs, and internal databases. You can build custom 'Tool Connectors' that our agents can invoke securely to perform actions across your specific software ecosystem."
        },
        {
            question: "What are the limits on autonomous tasks?",
            answer: "Limits are defined by your plan tier and the 'Confidence Threshold' you set. Agents can autonomously handle tasks up to a certain complexity level. If an agent's confidence score dips below your set threshold (e.g., 85%), the task is automatically routed to a human for review, ensuring safety and accuracy in critical operations."
        },
        {
            question: "Do you offer dedicated support for enterprise?",
            answer: "Yes. Enterprise plans include a dedicated Account Manager, priority 24/7 technical support, and quarterly business reviews. We also provide on-site training sessions and custom implementation engineering to ensure your team maximizes the value of the Pikar AI platform from day one."
        }
    ];

    return (
        <section className="relative w-full flex flex-col items-center justify-start py-10 px-4 sm:px-6 lg:px-8 font-display text-slate-800 bg-[#f6f8f8] overflow-x-hidden">
            {/* Background texture wrapper */}
            {/* Dot Grid Pattern Overlay - Updated to match InteractiveVideoShowcase style but preserved original look somewhat */}
            <div className="absolute inset-0 z-0 opacity-40 pointer-events-none bg-[length:16px_16px] bg-[radial-gradient(#cbd5e1_1.5px,transparent_1.5px)]"></div>

            {/* Decorative Blurs - Reduced sizes */}
            <div className="absolute top-0 left-1/4 w-48 h-48 bg-[#17cfaa]/10 rounded-full blur-2xl -z-10 mix-blend-multiply filter"></div>
            <div className="absolute bottom-0 right-1/4 w-48 h-48 bg-purple-200/40 rounded-full blur-2xl -z-10 mix-blend-multiply filter"></div>

            <div className="relative z-10 w-full max-w-[600px] flex flex-col gap-6">
                {/* Headline - Reduced sizes */}
                <div className="text-center space-y-2">
                    <h2 className="text-[#0e1b18] text-2xl md:text-3xl font-extrabold tracking-tight leading-tight drop-shadow-sm">
                        Got Questions? <br className="hidden sm:block" />
                        <span className="text-transparent bg-clip-text bg-gradient-to-r from-slate-800 to-slate-600">We’ve Got Answers.</span>
                    </h2>
                    <p className="text-slate-500 font-medium text-sm md:text-base max-w-sm mx-auto leading-relaxed">
                        Everything you need to know about integrating Pikar AI agents into your enterprise workflow.
                    </p>
                </div>

                {/* Accordion List */}
                <div className="flex flex-col gap-3 w-full">
                    {faqs.map((faq, index) => (
                        <div key={index} className="group">
                            {/* Clay Card Container - Reduced padding and shadows */}
                            <div
                                onClick={() => toggleAccordion(index)}
                                className={`relative rounded-2xl p-4 md:p-5 flex items-center justify-between gap-4 cursor-pointer bg-[#fcfdfe] transition-all duration-300
                                    ${openIndex === index
                                        ? 'ring-1 ring-[#17cfaa]/40 shadow-[0_0_20px_-5px_rgba(23,207,170,0.15),4px_4px_8px_rgba(166,171,189,0.3),-4px_-4px_8px_rgba(255,255,255,1)]'
                                        : 'shadow-[4px_4px_8px_rgba(166,171,189,0.3),-4px_-4px_8px_rgba(255,255,255,1)]'
                                    }`}
                            >
                                <h3 className="text-[#0e1b18] text-sm md:text-base font-bold leading-snug tracking-tight">{faq.question}</h3>
                                {/* Toggle Icon - Reduced size */}
                                <div className={`flex-shrink-0 h-8 w-8 md:h-9 md:w-9 rounded-full bg-[#fcfdfe] flex items-center justify-center text-[#17cfaa] transition-all duration-300 shadow-[2px_2px_4px_rgba(166,171,189,0.4),-2px_-2px_4px_rgba(255,255,255,1)]
                                    ${openIndex === index ? 'rotate-90 bg-[#17cfaa]/5 shadow-[inset_1px_1px_3px_rgba(166,171,189,0.3),inset_-1px_-1px_3px_rgba(255,255,255,1)]' : ''}
                                `}>
                                    <Plus className={`w-5 h-5 transition-transform duration-300 ${openIndex === index ? 'rotate-45' : ''}`} />
                                </div>
                            </div>

                            {/* Answer Panel */}
                            <AnimatePresence>
                                {openIndex === index && (
                                    <motion.div
                                        initial={{ height: 0, opacity: 0 }}
                                        animate={{ height: "auto", opacity: 1 }}
                                        exit={{ height: 0, opacity: 0 }}
                                        transition={{ duration: 0.3, ease: "easeOut" }}
                                        className="overflow-hidden"
                                    >
                                        <div className="px-1 pt-1 pb-1">
                                            {/* Glassmorphic Inner Panel - Reduced padding and margin */}
                                            <div className="rounded-xl bg-white/40 backdrop-blur-md border border-white/60 shadow-sm p-4 md:p-5 mt-[-10px] mx-1 relative z-0">
                                                <p className="text-slate-600 text-xs md:text-sm leading-relaxed font-medium">
                                                    {faq.answer}
                                                </p>
                                            </div>
                                        </div>
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </div>
                    ))}
                </div>

                {/* Bottom CTA Hint - Reduced padding */}
                <div className="text-center pt-4">
                    <p className="text-slate-500 font-medium text-xs md:text-sm">
                        Still have questions? <a className="text-[#17cfaa] hover:text-[#17cfaa]/80 font-bold transition-colors underline decoration-2 underline-offset-4" href="#">Contact our sales team</a>
                    </p>
                </div>
            </div>
        </section>
    );
}
