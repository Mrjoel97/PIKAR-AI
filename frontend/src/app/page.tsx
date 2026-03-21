import dynamic from 'next/dynamic';
import Navbar from "./components/Navbar";
import HeroSection from "./components/HeroSection";
import StatisticsSection from "./components/StatisticsSection";
import MarqueeSection from "./components/MarqueeSection";
import Footer from "./components/Footer";
// FadeIn is a tiny CSS-based component - import statically (no dynamic overhead)
import FadeIn from "./components/ui/FadeIn";

// Lazy load below-the-fold content with loading fallback
const ChallengesSection = dynamic(() => import("./components/ChallengesSection"), { loading: () => <SectionSkeleton /> });
const CoreCapabilitiesSection = dynamic(() => import("./components/CoreCapabilitiesSection"), { loading: () => <SectionSkeleton /> });
const BuiltForGrowthSection = dynamic(() => import("./components/BuiltForGrowthSection"), { loading: () => <SectionSkeleton /> });
const HumanInTheLoopSection = dynamic(() => import("./components/HumanInTheLoopSection"), { loading: () => <SectionSkeleton /> });
const InteractiveVideoShowcase = dynamic(() => import("./components/InteractiveVideoShowcase"), { ssr: false, loading: () => <SectionSkeleton /> });
const PricingSection = dynamic(() => import("./components/PricingSection"), { loading: () => <SectionSkeleton /> });
const ContactSection = dynamic(() => import("./components/ContactSection"), { loading: () => <SectionSkeleton /> });
const TestimonialsSection = dynamic(() => import("./components/TestimonialsSection"), { loading: () => <SectionSkeleton /> });
const FAQSection = dynamic(() => import("./components/FAQSection"), { loading: () => <SectionSkeleton /> });

/** Lightweight skeleton for lazy-loaded sections */
function SectionSkeleton() {
  return <div className="w-full min-h-[200px]" aria-hidden="true" />;
}

export default function Home() {
    return (
        <div className="relative min-h-screen flex flex-col font-sans selection:bg-[var(--teal-200)] selection:text-[var(--teal-900)]">

            {/* Navbar - Static for immediate interactivity */}
            <Navbar />

            <main className="flex-grow">

                {/* --- HERO SECTION (Static for LCP) --- */}
                <HeroSection />

                {/* --- STATISTICS SECTION (Static/Near-fold) --- */}
                <StatisticsSection />

                {/* --- MARQUEE TRUST STRIP (Static/Near-fold) --- */}
                <MarqueeSection />

                {/* --- CHALLENGES / PAIN POINTS --- */}
                <FadeIn delay={0.2}>
                    <ChallengesSection />
                </FadeIn>

                {/* --- CORE CAPABILITIES (Solution) --- */}
                <FadeIn>
                    <CoreCapabilitiesSection />
                </FadeIn>

                {/* --- HUMAN IN THE LOOP (Differentiator) --- */}
                <FadeIn>
                    <HumanInTheLoopSection />
                </FadeIn>

                {/* --- TESTIMONIALS (Social Proof — BEFORE pricing) --- */}
                <section id="testimonials">
                    <FadeIn>
                        <TestimonialsSection />
                    </FadeIn>
                </section>

                {/* --- BUILT FOR GROWTH / PERSONAS --- */}
                <FadeIn>
                    <BuiltForGrowthSection />
                </FadeIn>

                {/* --- INTERACTIVE VIDEO SHOWCASE --- */}
                <FadeIn>
                    <InteractiveVideoShowcase />
                </FadeIn>

                {/* --- PRICING SECTION --- */}
                <FadeIn>
                    <PricingSection />
                </FadeIn>

                {/* --- FAQ SECTION (Objection Handling — right after pricing) --- */}
                <FadeIn>
                    <FAQSection />
                </FadeIn>

                {/* --- CONTACT SECTION --- */}
                <FadeIn>
                    <ContactSection />
                </FadeIn>

                {/* --- FOOTER --- */}
                <Footer />
            </main>

        </div>
    );
}
