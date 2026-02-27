import dynamic from 'next/dynamic';
import { Suspense } from 'react';
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
const InteractiveVideoShowcase = dynamic(() => import("./components/InteractiveVideoShowcase"), { loading: () => <SectionSkeleton /> });
const ProductSystem = dynamic(() => import("./components/ProductSystem"), { loading: () => <SectionSkeleton /> });
const NeuralGridSection = dynamic(() => import("./components/NeuralGridSection"), { loading: () => <SectionSkeleton /> });
const EducationHubSection = dynamic(() => import("./components/EducationHubSection"), { loading: () => <SectionSkeleton /> });
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

                {/* --- MARQUEE LOGO STRIP (Static/Near-fold) --- */}
                <MarqueeSection />

                {/* --- CHALLENGES SECTION --- */}
                <FadeIn delay={0.2}>
                    <ChallengesSection />
                </FadeIn>

                {/* --- CORE CAPABILITIES SECTION --- */}
                <FadeIn>
                    <CoreCapabilitiesSection />
                </FadeIn>

                {/* --- BUILT FOR GROWTH SECTION --- */}
                <FadeIn>
                    <BuiltForGrowthSection />
                </FadeIn>

                {/* --- HUMAN IN THE LOOP SECTION --- */}
                <FadeIn>
                    <HumanInTheLoopSection />
                </FadeIn>

                {/* --- INTERACTIVE VIDEO SHOWCASE --- */}
                <FadeIn>
                    <InteractiveVideoShowcase />
                </FadeIn>

                {/* --- PRODUCT SYSTEM SECTION --- */}
                <FadeIn>
                    <ProductSystem />
                </FadeIn>

                {/* --- NEURAL GRID SECTION --- */}
                <FadeIn>
                    <NeuralGridSection />
                </FadeIn>

                {/* --- EDUCATION HUB SECTION --- */}
                <div className="mt-8 lg:mt-12">
                    <FadeIn>
                        <EducationHubSection />
                    </FadeIn>
                </div>

                {/* --- PRICING SECTION --- */}
                <FadeIn>
                    <PricingSection />
                </FadeIn>

                {/* --- CONTACT SECTION --- */}
                <FadeIn>
                    <ContactSection />
                </FadeIn>

                {/* --- TESTIMONIALS SECTION --- */}
                <section id="testimonials">
                    <FadeIn>
                        <TestimonialsSection />
                    </FadeIn>
                </section>

                {/* --- FAQ SECTION --- */}
                <FadeIn>
                    <FAQSection />
                </FadeIn>

                {/* --- FOOTER --- */}
                <Footer />
            </main>

        </div>
    );
}