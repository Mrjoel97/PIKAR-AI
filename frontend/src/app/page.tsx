"use client";

import dynamic from "next/dynamic";
import { 
  ArrowRight, 
  CheckCircle2, 
  Play, 
  Cpu, 
  Globe, 
  Shield, 
  Zap,
  MessageSquare
} from "lucide-react";

// Dynamic import for ThreeJS to avoid SSR issues
const ThreeBackground = dynamic(() => import("./components/ThreeBackground"), { ssr: false });

export default function Home() {
  return (
    <div className="relative min-h-screen flex flex-col font-sans selection:bg-yellow-400 selection:text-black">
      
      {/* 3D Background Layer */}
      <ThreeBackground />

      {/* Navbar */}
      <header className="fixed top-0 left-0 right-0 z-50 border-b border-white/10 bg-black/50 backdrop-blur-md transition-all">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
          <div className="flex items-center gap-2 font-bold tracking-tighter text-xl text-white">
            <div className="h-6 w-6 rounded-full bg-gradient-to-tr from-yellow-400 to-yellow-600" />
            PIKAR<span className="text-zinc-500">.AI</span>
          </div>
          <nav className="hidden md:flex gap-8 text-sm font-medium text-zinc-400">
            <a href="#features" className="hover:text-white transition-colors">Features</a>
            <a href="#solutions" className="hover:text-white transition-colors">Solutions</a>
            <a href="#testimonials" className="hover:text-white transition-colors">Testimonials</a>
            <a href="#pricing" className="hover:text-white transition-colors">Pricing</a>
          </nav>
          <div className="flex items-center gap-4">
             <a href="#" className="hidden text-sm font-medium text-zinc-400 hover:text-white sm:block">Sign In</a>
             <button className="rounded-full bg-white px-5 py-2 text-sm font-medium text-black hover:bg-zinc-200 transition-colors">
               Get Started
             </button>
          </div>
        </div>
      </header>

      <main className="flex-grow">
        
        {/* --- HERO SECTION --- */}
        <section className="relative pt-32 pb-20 px-6 overflow-hidden">
          {/* Nano Banana Image Prompt: "Abstract visualization of AI transformation, golden neural networks merging with corporate glass structures, volumetric lighting, 8k, cinematic, surreal." */}
          <div className="absolute top-0 left-0 w-full h-[800px] bg-gradient-to-b from-purple-900/20 to-black pointer-events-none z-[-1]" />
          
          <div className="mx-auto max-w-5xl text-center">
            {/* New to AI? Tag */}
            <div className="mb-8 flex justify-center">
              <span className="inline-flex items-center gap-2 rounded-full border border-yellow-500/30 bg-yellow-500/10 px-4 py-1.5 text-sm font-medium text-yellow-500">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-yellow-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-yellow-500"></span>
                </span>
                New to AI? Start here
              </span>
            </div>

            <h1 className="text-5xl md:text-7xl lg:text-8xl font-bold tracking-tight text-white leading-[1.1] mb-8">
              Transform Your Business <br />
              and Ideas With <span className="text-transparent bg-clip-text bg-gradient-to-r from-yellow-400 to-yellow-200">AI</span>
            </h1>

            <p className="mx-auto max-w-2xl text-xl text-zinc-400 leading-relaxed mb-10">
              The enterprise-grade framework for orchestrating autonomous multi-agent systems. 
              Deploy intelligent swarms that evolve with your business.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <button className="h-14 px-8 rounded-full bg-yellow-400 text-black font-bold text-lg flex items-center justify-center min-w-[180px] hover:bg-yellow-300 transition-colors shadow-[0_0_20px_rgba(250,204,21,0.3)]">
                Start Building <ArrowRight className="ml-2 h-5 w-5" />
              </button>
              <button className="h-14 px-8 rounded-full border border-zinc-800 bg-zinc-900/50 text-white font-medium text-lg flex items-center justify-center min-w-[180px] hover:bg-zinc-800 transition-colors backdrop-blur-sm">
                View Demo
              </button>
            </div>
          </div>
        </section>


        {/* --- STATISTICS SECTION --- */}
        <section className="border-y border-white/5 bg-zinc-950/50 backdrop-blur-sm">
          <div className="mx-auto max-w-7xl px-6 py-12">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
              {[
                { label: "Active Agents", value: "10k+" },
                { label: "Tasks Processed", value: "50M+" },
                { label: "Enterprise Users", value: "500+" },
                { label: "Uptime", value: "99.99%" },
              ].map((stat, i) => (
                <div key={i} className="flex flex-col gap-1">
                  <span className="text-3xl md:text-4xl font-bold text-white tracking-tight">{stat.value}</span>
                  <span className="text-sm font-medium text-zinc-500 uppercase tracking-wider">{stat.label}</span>
                </div>
              ))}
            </div>
          </div>
        </section>


        {/* --- MARQUEE LOGO STRIP --- */}
        <section className="py-10 overflow-hidden bg-black relative">
          <div className="absolute inset-y-0 left-0 w-32 bg-gradient-to-r from-black to-transparent z-10" />
          <div className="absolute inset-y-0 right-0 w-32 bg-gradient-to-l from-black to-transparent z-10" />
          <div className="flex gap-12 whitespace-nowrap animate-[marquee_30s_linear_infinite] opacity-50 grayscale hover:grayscale-0 transition-all duration-500">
             {/* Placeholders for logos */}
             {Array.from({ length: 10 }).map((_, i) => (
               <div key={i} className="flex items-center gap-2 text-xl font-bold text-white">
                 <Globe className="h-6 w-6" /> GLOBAL CORP {i + 1}
               </div>
             ))}
             {Array.from({ length: 10 }).map((_, i) => (
               <div key={`dup-${i}`} className="flex items-center gap-2 text-xl font-bold text-white">
                 <Globe className="h-6 w-6" /> GLOBAL CORP {i + 1}
               </div>
             ))}
          </div>
        </section>


        {/* --- WHAT TO EXPECT --- */}
        <section className="py-24 px-6 bg-zinc-950">
          <div className="mx-auto max-w-7xl">
            <div className="grid md:grid-cols-2 gap-16 items-center">
              <div>
                <h2 className="text-3xl md:text-5xl font-bold text-white mb-6">What to Expect</h2>
                <div className="space-y-6">
                  {[
                    "Seamless Integration with existing stacks",
                    "Real-time orchestration of agent swarms",
                    "Enterprise-grade security and compliance",
                    "Self-healing autonomous workflows"
                  ].map((item, i) => (
                    <div key={i} className="flex items-start gap-4">
                      <div className="mt-1 h-6 w-6 rounded-full bg-green-500/20 flex items-center justify-center flex-shrink-0">
                        <CheckCircle2 className="h-4 w-4 text-green-500" />
                      </div>
                      <p className="text-lg text-zinc-400">{item}</p>
                    </div>
                  ))}
                </div>
              </div>
              {/* Remotion Video Placeholder */}
              <div className="relative aspect-video rounded-2xl overflow-hidden border border-white/10 bg-zinc-900 shadow-2xl">
                 <div className="absolute inset-0 flex items-center justify-center flex-col gap-4">
                    <div className="h-16 w-16 rounded-full bg-white/10 backdrop-blur-md flex items-center justify-center border border-white/20 cursor-pointer hover:scale-110 transition-transform">
                      <Play className="h-6 w-6 text-white ml-1" />
                    </div>
                    <p className="text-sm text-zinc-500 font-mono">Interactive Remotion Demo</p>
                 </div>
                 {/* 
                    Ideally: 
                    <Player
                      component={MyVideo}
                      durationInFrames={120}
                      fps={30}
                      compositionWidth={1920}
                      compositionHeight={1080}
                      style={{ width: '100%', height: '100%' }}
                    />
                 */}
              </div>
            </div>
          </div>
        </section>


        {/* --- FEATURES --- */}
        <section id="features" className="py-24 px-6 bg-black relative">
          <div className="mx-auto max-w-7xl">
            <div className="text-center max-w-3xl mx-auto mb-16">
              <h2 className="text-3xl md:text-5xl font-bold text-white mb-6">Engineered for Scale</h2>
              <p className="text-zinc-400 text-lg">
                Everything you need to build, deploy, and manage intelligent agents in production.
              </p>
            </div>
            
            <div className="grid md:grid-cols-3 gap-8">
              {[
                { 
                  icon: Cpu, 
                  title: "Neural Orchestration", 
                  desc: "Advanced routing algorithms that dispatch tasks to the most capable agents in real-time." 
                },
                { 
                  icon: Shield, 
                  title: "Military-Grade Security", 
                  desc: "SOC2 compliant infrastructure with automated audit trails and role-based access control." 
                },
                { 
                  icon: Zap, 
                  title: "Instant Deployment", 
                  desc: "One-click deploy to global edge networks. Zero configuration required for standard agents." 
                }
              ].map((feature, i) => (
                <div key={i} className="group relative p-8 rounded-2xl border border-white/10 bg-zinc-900/50 hover:bg-zinc-900 transition-colors">
                  <div className="absolute inset-0 bg-gradient-to-b from-yellow-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity rounded-2xl" />
                  <feature.icon className="h-10 w-10 text-yellow-400 mb-6" />
                  <h3 className="text-xl font-bold text-white mb-3">{feature.title}</h3>
                  <p className="text-zinc-400 leading-relaxed">{feature.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        
        {/* --- CHALLENGES & SOLUTIONS --- */}
        <section id="solutions" className="py-24 px-6 bg-zinc-950">
          <div className="mx-auto max-w-7xl">
             <div className="grid lg:grid-cols-2 gap-12">
                <div className="space-y-8">
                   <h2 className="text-3xl md:text-4xl font-bold text-white">The Challenge</h2>
                   <div className="p-6 rounded-xl bg-red-950/10 border border-red-900/20">
                      <h4 className="text-red-400 font-bold mb-2">Fragmentation</h4>
                      <p className="text-zinc-400">Traditional automation is brittle and disconnected, leading to maintenance nightmares.</p>
                   </div>
                   <div className="p-6 rounded-xl bg-red-950/10 border border-red-900/20">
                      <h4 className="text-red-400 font-bold mb-2">Scalability Limits</h4>
                      <p className="text-zinc-400">Human-in-the-loop workflows cannot scale linearly with business demand.</p>
                   </div>
                </div>
                <div className="space-y-8">
                   <h2 className="text-3xl md:text-4xl font-bold text-white">The Pikar Solution</h2>
                   <div className="p-6 rounded-xl bg-green-950/10 border border-green-900/20">
                      <h4 className="text-green-400 font-bold mb-2">Unified Fabric</h4>
                      <p className="text-zinc-400">A single cohesive layer for all agent interactions, data flow, and state management.</p>
                   </div>
                   <div className="p-6 rounded-xl bg-green-950/10 border border-green-900/20">
                      <h4 className="text-green-400 font-bold mb-2">Infinite Scale</h4>
                      <p className="text-zinc-400">Serverless agent architecture that scales to zero and up to millions of concurrent ops.</p>
                   </div>
                </div>
             </div>
          </div>
        </section>


        {/* --- WHAT'S NEW (BLOG MARQUEE) --- */}
        <section className="py-20 bg-black overflow-hidden border-t border-white/5">
          <div className="mx-auto max-w-7xl px-6 mb-10">
            <h2 className="text-2xl font-bold text-white">Latest from the Lab</h2>
          </div>
          <div className="flex gap-6 animate-[marquee_40s_linear_infinite] hover:pause">
             {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="flex-shrink-0 w-[300px] p-6 rounded-xl border border-white/10 bg-zinc-900 hover:border-yellow-500/50 transition-colors group cursor-pointer">
                   <div className="text-xs text-yellow-500 font-mono mb-3">UPDATE v2.{i}</div>
                   <h3 className="text-lg font-bold text-white mb-2 group-hover:text-yellow-400 transition-colors">Introducing Swarm Protocol {i}</h3>
                   <p className="text-sm text-zinc-500">How we reduced agent latency by 400% using Rust-based kernels.</p>
                </div>
             ))}
             {/* Duplicate for smooth loop */}
             {[1, 2, 3, 4, 5].map((i) => (
                <div key={`dup-${i}`} className="flex-shrink-0 w-[300px] p-6 rounded-xl border border-white/10 bg-zinc-900 hover:border-yellow-500/50 transition-colors group cursor-pointer">
                   <div className="text-xs text-yellow-500 font-mono mb-3">UPDATE v2.{i}</div>
                   <h3 className="text-lg font-bold text-white mb-2 group-hover:text-yellow-400 transition-colors">Introducing Swarm Protocol {i}</h3>
                   <p className="text-sm text-zinc-500">How we reduced agent latency by 400% using Rust-based kernels.</p>
                </div>
             ))}
          </div>
        </section>


        {/* --- LEARNING HUB --- */}
        <section className="py-24 px-6 bg-zinc-950">
           <div className="mx-auto max-w-7xl text-center">
              <h2 className="text-3xl font-bold text-white mb-12">Learning Hub</h2>
              <div className="grid md:grid-cols-3 gap-6">
                 {['Agent Basics', 'Advanced Architecture', 'API Reference'].map((topic, i) => (
                    <a key={i} href="#" className="block group">
                       <div className="h-40 rounded-t-xl bg-zinc-900 border border-white/5 group-hover:bg-zinc-800 transition-colors flex items-center justify-center">
                          <span className="text-4xl">📚</span>
                       </div>
                       <div className="p-6 rounded-b-xl border-x border-b border-white/5 bg-black text-left">
                          <h3 className="font-bold text-white mb-1 group-hover:text-yellow-400 transition-colors">{topic}</h3>
                          <p className="text-sm text-zinc-500">Master the fundamentals.</p>
                       </div>
                    </a>
                 ))}
              </div>
           </div>
        </section>


        {/* --- TESTIMONIALS --- */}
        <section id="testimonials" className="py-24 px-6 bg-black border-t border-white/5">
          <div className="mx-auto max-w-7xl">
            <h2 className="text-3xl font-bold text-center text-white mb-16">Trusted by Innovators</h2>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
               {[1, 2, 3].map((i) => (
                 <div key={i} className="p-8 rounded-2xl bg-zinc-900/30 border border-white/5">
                    <div className="flex gap-1 text-yellow-500 mb-4">★★★★★</div>
                    <p className="text-zinc-300 mb-6">&quot;Pikar transformed how we handle data processing. What used to take a team of 10 is now handled by 3 autonomous agents.&quot;</p>
                    <div className="flex items-center gap-4">
                       <div className="h-10 w-10 rounded-full bg-zinc-700" />
                       <div>
                          <div className="text-white font-bold">Sarah Jenkins</div>
                          <div className="text-xs text-zinc-500">CTO, TechFlow</div>
                       </div>
                    </div>
                 </div>
               ))}
            </div>
          </div>
        </section>


        {/* --- CTA SECTION --- */}
        <section className="py-32 px-6 bg-gradient-to-b from-zinc-900 to-black text-center">
           <div className="mx-auto max-w-3xl">
              <h2 className="text-4xl md:text-5xl font-bold text-white mb-8">Ready to evolve?</h2>
              <p className="text-xl text-zinc-400 mb-10">Join thousands of developers building the next generation of software.</p>
              <button className="h-16 px-10 rounded-full bg-white text-black font-bold text-xl hover:bg-zinc-200 transition-colors">
                 Get Started for Free
              </button>
           </div>
        </section>


        {/* --- CONTACT FORM --- */}
        <section className="py-24 px-6 bg-black border-t border-white/10">
           <div className="mx-auto max-w-xl">
              <h2 className="text-3xl font-bold text-white mb-8 text-center">Contact Sales</h2>
              <form className="space-y-4">
                 <div className="grid grid-cols-2 gap-4">
                    <input type="text" placeholder="First Name" className="w-full h-12 rounded-lg bg-zinc-900 border border-white/10 px-4 text-white focus:outline-none focus:border-yellow-500 transition-colors" />
                    <input type="text" placeholder="Last Name" className="w-full h-12 rounded-lg bg-zinc-900 border border-white/10 px-4 text-white focus:outline-none focus:border-yellow-500 transition-colors" />
                 </div>
                 <input type="email" placeholder="Work Email" className="w-full h-12 rounded-lg bg-zinc-900 border border-white/10 px-4 text-white focus:outline-none focus:border-yellow-500 transition-colors" />
                 <textarea placeholder="Tell us about your project" rows={4} className="w-full rounded-lg bg-zinc-900 border border-white/10 p-4 text-white focus:outline-none focus:border-yellow-500 transition-colors" />
                 <button type="submit" className="w-full h-12 rounded-lg bg-yellow-500 text-black font-bold hover:bg-yellow-400 transition-colors">
                    Send Message
                 </button>
              </form>
           </div>
        </section>

      </main>


      {/* --- FOOTER --- */}
      <footer className="border-t border-white/10 bg-black py-16 px-6">
         <div className="mx-auto max-w-7xl grid md:grid-cols-4 gap-12 text-sm text-zinc-400">
            <div className="col-span-1 md:col-span-2">
               <div className="font-bold text-white text-xl mb-4">PIKAR.AI</div>
               <p className="max-w-xs">The future of autonomous agent orchestration.</p>
            </div>
            <div>
               <h4 className="font-bold text-white mb-4">Product</h4>
               <ul className="space-y-2">
                  <li><a href="#" className="hover:text-white">Features</a></li>
                  <li><a href="#" className="hover:text-white">Integration</a></li>
                  <li><a href="#" className="hover:text-white">Pricing</a></li>
                  <li><a href="#" className="hover:text-white">Changelog</a></li>
               </ul>
            </div>
            <div>
               <h4 className="font-bold text-white mb-4">Company</h4>
               <ul className="space-y-2">
                  <li><a href="#" className="hover:text-white">About</a></li>
                  <li><a href="#" className="hover:text-white">Blog</a></li>
                  <li><a href="#" className="hover:text-white">Careers</a></li>
                  <li><a href="#" className="hover:text-white">Contact</a></li>
               </ul>
            </div>
         </div>
         <div className="mx-auto max-w-7xl mt-16 pt-8 border-t border-white/5 text-xs text-zinc-600 flex justify-between">
            <div>© 2026 Pikar AI. All rights reserved.</div>
            <div className="flex gap-4">
               <a href="#">Privacy Policy</a>
               <a href="#">Terms of Service</a>
            </div>
         </div>
      </footer>


      {/* --- FLOATING AI BUTTON --- */}
      <div className="fixed bottom-6 right-6 z-50">
         <button className="h-14 w-14 rounded-full bg-yellow-400 text-black shadow-lg shadow-yellow-500/20 flex items-center justify-center hover:scale-110 transition-transform cursor-pointer group">
            <MessageSquare className="h-6 w-6" />
            <span className="absolute right-full mr-4 bg-white text-black px-3 py-1 rounded-lg text-sm font-medium opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
               Ask AI Assistant
            </span>
         </button>
      </div>

    </div>
  );
}