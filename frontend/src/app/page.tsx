import dynamic from 'next/dynamic';
import Navbar from "./components/Navbar";
import HeroSection from "./components/HeroSection";
import StatisticsSection from "./components/StatisticsSection";
import MarqueeSection from "./components/MarqueeSection";
import Footer from "./components/Footer";

// Lazy load below-the-fold content
const ChallengesSection = dynamic(() => import("./components/ChallengesSection"));
const CoreCapabilitiesSection = dynamic(() => import("./components/CoreCapabilitiesSection"));
const BuiltForGrowthSection = dynamic(() => import("./components/BuiltForGrowthSection"));
const HumanInTheLoopSection = dynamic(() => import("./components/HumanInTheLoopSection"));
const InteractiveVideoShowcase = dynamic(() => import("./components/InteractiveVideoShowcase"));
const ProductSystem = dynamic(() => import("./components/ProductSystem"));
const NeuralGridSection = dynamic(() => import("./components/NeuralGridSection"));
const EducationHubSection = dynamic(() => import("./components/EducationHubSection"));
const PricingSection = dynamic(() => import("./components/PricingSection"));
const ContactSection = dynamic(() => import("./components/ContactSection"));
const TestimonialsSection = dynamic(() => import("./components/TestimonialsSection"));
const FAQSection = dynamic(() => import("./components/FAQSection")); // Changed to dynamic import
const FadeIn = dynamic(() => import("./components/ui/FadeIn")); // Lazy load the animation wrapper too

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