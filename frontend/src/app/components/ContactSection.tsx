"use client";

import React, { useState } from 'react';
import { Mail, Phone, MapPin, ArrowRight, User, AtSign, Send, CheckCircle } from 'lucide-react';
import { motion } from 'framer-motion';

export default function ContactSection() {
    const [isSubmitted, setIsSubmitted] = useState(false);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        // Simulate sending a message
        setTimeout(() => {
            setIsSubmitted(true);
        }, 500);
    };

    return (
        <section className="font-display bg-[#f6f8f8] text-[#0d1b19] flex flex-col lg:flex-row antialiased h-auto">
            {/* Left Column: Content */}
            <div className="relative w-full lg:w-5/12 flex flex-col justify-center p-6 lg:p-8 xl:p-12 bg-[#f6f8f8] bg-[radial-gradient(#cbd5e1_1.5px,transparent_1.5px)] bg-[length:16px_16px]">
                <div className="max-w-sm mx-auto lg:mx-0 flex flex-col h-full justify-center">
                    {/* Branding */}
                    <div className="mb-4">
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-[#0fbd9a]/10 text-[#0fbd9a] text-xs font-bold tracking-wide uppercase">
                            Get in Touch
                        </span>
                    </div>
                    {/* Headline */}
                    <h2 className="text-2xl lg:text-3xl font-extrabold tracking-tight text-[#0d1b19] leading-[1.1] mb-3">
                        Let’s Build the <span className="text-[#0fbd9a]">Future</span> Together
                    </h2>
                    {/* Subheadline */}
                    <p className="text-sm text-gray-600 font-medium leading-relaxed mb-6">
                        Have questions about our AI agents or custom enterprise workflows? Our team is ready to help you scale efficiently and securely.
                    </p>

                    {/* Contact Cards (Claymorphism) */}
                    <div className="space-y-3">
                        {/* Email Card */}
                        <div className="bg-white shadow-[4px_4px_8px_#d1d5db,-4px_-4px_8px_#ffffff] hover:shadow-[6px_6px_10px_#d1d5db,-6px_-6px_10px_#ffffff] hover:-translate-y-0.5 transition-all duration-200 flex items-center gap-3 p-3 rounded-xl group cursor-pointer">
                            <div className="flex items-center justify-center shrink-0 w-8 h-8 rounded-full bg-[#0fbd9a]/10 text-[#0fbd9a] transition-colors group-hover:bg-[#0fbd9a] group-hover:text-white">
                                <Mail className="w-4 h-4" />
                            </div>
                            <div className="flex flex-col">
                                <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Email Us</span>
                                <span className="text-sm font-bold text-[#0d1b19]">hello@pikar.ai</span>
                            </div>
                            <div className="ml-auto text-gray-300 group-hover:text-[#0fbd9a] transition-colors">
                                <ArrowRight className="w-4 h-4" />
                            </div>
                        </div>

                        {/* Phone Card */}
                        <div className="bg-white shadow-[4px_4px_8px_#d1d5db,-4px_-4px_8px_#ffffff] hover:shadow-[6px_6px_10px_#d1d5db,-6px_-6px_10px_#ffffff] hover:-translate-y-0.5 transition-all duration-200 flex items-center gap-3 p-3 rounded-xl group cursor-pointer">
                            <div className="flex items-center justify-center shrink-0 w-8 h-8 rounded-full bg-[#0fbd9a]/10 text-[#0fbd9a] transition-colors group-hover:bg-[#0fbd9a] group-hover:text-white">
                                <Phone className="w-4 h-4" />
                            </div>
                            <div className="flex flex-col">
                                <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Call Us</span>
                                <span className="text-sm font-bold text-[#0d1b19]">+1 (555) 000-0000</span>
                            </div>
                            <div className="ml-auto text-gray-300 group-hover:text-[#0fbd9a] transition-colors">
                                <ArrowRight className="w-4 h-4" />
                            </div>
                        </div>

                        {/* Location Card */}
                        <div className="bg-white shadow-[4px_4px_8px_#d1d5db,-4px_-4px_8px_#ffffff] hover:shadow-[6px_6px_10px_#d1d5db,-6px_-6px_10px_#ffffff] hover:-translate-y-0.5 transition-all duration-200 flex items-center gap-3 p-3 rounded-xl group cursor-pointer">
                            <div className="flex items-center justify-center shrink-0 w-8 h-8 rounded-full bg-[#0fbd9a]/10 text-[#0fbd9a] transition-colors group-hover:bg-[#0fbd9a] group-hover:text-white">
                                <MapPin className="w-4 h-4" />
                            </div>
                            <div className="flex flex-col">
                                <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Visit HQ</span>
                                <span className="text-sm font-bold text-[#0d1b19]">San Francisco, CA</span>
                            </div>
                            <div className="ml-auto text-gray-300 group-hover:text-[#0fbd9a] transition-colors">
                                <ArrowRight className="w-4 h-4" />
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Right Column: Form */}
            <div className="relative w-full lg:w-7/12 min-h-[400px] lg:h-auto bg-[#f6f8f8] bg-[radial-gradient(#cbd5e1_1.5px,transparent_1.5px)] bg-[length:16px_16px] flex items-center justify-center p-4 lg:p-8">
                {/* Claymorphic Container */}
                <div className="w-full max-w-md p-6 lg:p-8 rounded-[1.5rem] relative overflow-hidden bg-[linear-gradient(145deg,#0e302e,#091e1d)]">
                    {/* Decorative glow */}
                    <div className="absolute top-[-20%] right-[-10%] w-[150px] h-[150px] bg-[#0fbd9a]/20 rounded-full blur-[50px] pointer-events-none"></div>
                    <div className="absolute bottom-[-10%] left-[-10%] w-[100px] h-[100px] bg-teal-500/10 rounded-full blur-[40px] pointer-events-none"></div>

                    <div className="relative z-10 flex flex-col h-full min-h-[300px] justify-center">
                        {isSubmitted ? (
                            <motion.div
                                initial={{ opacity: 0, scale: 0.8 }}
                                animate={{ opacity: 1, scale: 1 }}
                                className="flex flex-col items-center justify-center h-full text-center space-y-4"
                            >
                                {/* 3D Icon styling - Puffy Green Circle with Checkmark */}
                                <div className="w-16 h-16 bg-[#0fbd9a] rounded-full flex items-center justify-center shadow-[6px_6px_12px_rgba(0,0,0,0.3),-4px_-4px_12px_rgba(255,255,255,0.1),inset_0px_-2px_0px_rgba(0,0,0,0.1)]">
                                    <CheckCircle className="w-8 h-8 text-[#0d2d2d]" strokeWidth={3} />
                                </div>
                                <div className="space-y-1.5">
                                    <h3 className="text-xl font-bold text-white mb-1">Message Sent!</h3>
                                    <p className="text-white/60 text-xs max-w-xs mx-auto">Thank you for reaching out. Our team will get back to you within 24 hours.</p>
                                </div>
                                <button onClick={() => setIsSubmitted(false)} className="text-[#0fbd9a] hover:text-white transition-colors font-bold text-[10px] uppercase tracking-wider flex items-center gap-1.5 mt-2 cursor-pointer">
                                    Send another message
                                </button>
                            </motion.div>
                        ) : (
                            <>
                                <div className="mb-6">
                                    <h2 className="text-xl font-bold text-white mb-1">Start a Conversation</h2>
                                    <p className="text-white/60 text-xs">Fill out the form below and our team will get back to you within 24 hours.</p>
                                </div>

                                <form className="space-y-4 flex-1 flex flex-col justify-center" onSubmit={handleSubmit}>
                                    {/* Name Input */}
                                    <div className="space-y-1">
                                        <label className="block text-xs font-medium text-[#0fbd9a] ml-3" htmlFor="name">Full Name</label>
                                        <div className="relative">
                                            <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-[#0fbd9a]/50">
                                                <User className="w-3.5 h-3.5" />
                                            </div>
                                            <input
                                                className="w-full rounded-full py-2.5 pl-10 pr-4 text-sm text-white placeholder:text-white/30 bg-[rgba(15,189,154,0.05)] backdrop-blur-md border border-[rgba(15,189,154,0.2)] shadow-[inset_1px_1px_3px_rgba(0,0,0,0.2),inset_-1px_-1px_3px_rgba(255,255,255,0.05)] focus:bg-[rgba(15,189,154,0.1)] focus:border-[rgba(15,189,154,0.6)] focus:outline-none focus:shadow-[inset_1px_1px_3px_rgba(0,0,0,0.3),0_0_10px_rgba(15,189,154,0.2)] transition-all duration-300"
                                                id="name"
                                                placeholder="John Doe"
                                                type="text"
                                                required
                                            />
                                        </div>
                                    </div>

                                    {/* Email Input */}
                                    <div className="space-y-1">
                                        <label className="block text-xs font-medium text-[#0fbd9a] ml-3" htmlFor="email">Work Email</label>
                                        <div className="relative">
                                            <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-[#0fbd9a]/50">
                                                <AtSign className="w-3.5 h-3.5" />
                                            </div>
                                            <input
                                                className="w-full rounded-full py-2.5 pl-10 pr-4 text-sm text-white placeholder:text-white/30 bg-[rgba(15,189,154,0.05)] backdrop-blur-md border border-[rgba(15,189,154,0.2)] shadow-[inset_1px_1px_3px_rgba(0,0,0,0.2),inset_-1px_-1px_3px_rgba(255,255,255,0.05)] focus:bg-[rgba(15,189,154,0.1)] focus:border-[rgba(15,189,154,0.6)] focus:outline-none focus:shadow-[inset_1px_1px_3px_rgba(0,0,0,0.3),0_0_10px_rgba(15,189,154,0.2)] transition-all duration-300"
                                                id="email"
                                                placeholder="john@company.com"
                                                type="email"
                                                required
                                            />
                                        </div>
                                    </div>

                                    {/* Message Input */}
                                    <div className="space-y-1">
                                        <label className="block text-xs font-medium text-[#0fbd9a] ml-3" htmlFor="message">How can we help?</label>
                                        <div className="relative">
                                            <textarea
                                                className="w-full rounded-[1.5rem] py-2.5 px-4 text-sm text-white placeholder:text-white/30 bg-[rgba(15,189,154,0.05)] backdrop-blur-md border border-[rgba(15,189,154,0.2)] shadow-[inset_1px_1px_3px_rgba(0,0,0,0.2),inset_-1px_-1px_3px_rgba(255,255,255,0.05)] focus:bg-[rgba(15,189,154,0.1)] focus:border-[rgba(15,189,154,0.6)] focus:outline-none focus:shadow-[inset_1px_1px_3px_rgba(0,0,0,0.3),0_0_10px_rgba(15,189,154,0.2)] transition-all duration-300 resize-none"
                                                id="message"
                                                placeholder="Tell us about your project needs..."
                                                rows={3}
                                                required
                                            ></textarea>
                                        </div>
                                    </div>

                                    {/* Submit Button */}
                                    <div className="pt-2">
                                        <button className="w-full cursor-pointer py-3 rounded-full text-sm font-bold flex items-center justify-center gap-2 group bg-white text-[#0d2d2d] shadow-[4px_4px_8px_rgba(0,0,0,0.3),-2px_-2px_8px_rgba(255,255,255,0.1),inset_0px_-2px_0px_rgba(0,0,0,0.1)] active:translate-y-[1px] active:shadow-[1px_1px_3px_rgba(0,0,0,0.3),-1px_-1px_3px_rgba(255,255,255,0.1),inset_0px_-1px_0px_rgba(0,0,0,0.1)] transition-all duration-200" type="submit">
                                            Send Message
                                            <Send className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
                                        </button>
                                    </div>
                                </form>
                            </>
                        )}
                    </div>
                </div>
            </div>
        </section>
    );
}
