import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useAuth } from "@/hooks/use-auth";
import { motion } from "framer-motion";
import { 
  ArrowRight, 
  Bot, 
  Brain, 
  BarChart3, 
  Zap, 
  Shield, 
  Users, 
  Target,
  Sparkles,
  CheckCircle,
  BadgeCheck,
  Loader2
} from "lucide-react";
import { useNavigate } from "react-router";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { Menu } from "lucide-react";
import { useState } from "react";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";

export default function Landing() {
  const { isLoading, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [demoOpen, setDemoOpen] = useState(false);

  const handleGetStarted = () => {
    if (isAuthenticated) {
      navigate("/dashboard");
    } else {
      navigate("/auth");
    }
  };

  const features = [
    {
      icon: Bot,
      title: "AI-Powered Agents",
      description: "Deploy specialized AI agents for content creation, sales intelligence, and customer support."
    },
    {
      icon: Brain,
      title: "Intelligent Orchestration",
      description: "Seamlessly coordinate multiple AI agents to execute complex business workflows."
    },
    {
      icon: BarChart3,
      title: "Advanced Analytics",
      description: "Get real-time insights and predictive analytics to optimize your business performance."
    },
    {
      icon: Zap,
      title: "Automated Workflows",
      description: "Streamline operations with intelligent automation that adapts to your business needs."
    },
    {
      icon: Shield,
      title: "Enterprise Security",
      description: "Bank-level security with compliance standards for data protection and privacy."
    },
    {
      icon: Users,
      title: "Team Collaboration",
      description: "Enable seamless collaboration between human teams and AI agents."
    }
  ];

  const tiers = [
    {
      name: "Solopreneur",
      price: "Free",
      description: "Perfect for individual entrepreneurs",
      features: ["2 AI Agents", "Basic Analytics", "Email Support"]
    },
    {
      name: "Startup",
      price: "$49/mo",
      description: "Ideal for growing teams",
      features: ["10 AI Agents", "Advanced Analytics", "Priority Support", "Team Collaboration"]
    },
    {
      name: "SME",
      price: "$199/mo", 
      description: "For established businesses",
      features: ["Unlimited Agents", "Custom Workflows", "API Access", "Dedicated Support"]
    },
    {
      name: "Enterprise",
      price: "Custom",
      description: "For large organizations",
      features: ["White-label Solution", "Custom Integrations", "SLA Guarantee", "On-premise Option"]
    }
  ];

  const trustedLogos = [
    { name: "Stripe", src: "https://cdn.simpleicons.org/stripe/0A2540" },
    { name: "Google", src: "https://cdn.simpleicons.org/google/1A73E8" },
    { name: "Slack", src: "https://cdn.simpleicons.org/slack/4A154B" },
    { name: "Notion", src: "https://cdn.simpleicons.org/notion/0F0F0F" },
    { name: "HubSpot", src: "https://cdn.simpleicons.org/hubspot/FF7A59" },
    { name: "AWS", src: "https://cdn.simpleicons.org/amazonaws/FF9900" },
    { name: "Salesforce", src: "https://cdn.simpleicons.org/salesforce/00A1E0" },
    { name: "Shopify", src: "https://cdn.simpleicons.org/shopify/95BF47" },
  ];

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.8 }}
      className="min-h-screen bg-gradient-to-br from-accent/10 via-background to-primary/5"
    >
      {/* Navigation */}
      <nav className="sticky top-0 z-50 backdrop-blur-lg bg-background/80 border-b border-border/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <motion.div 
              className="flex items-center space-x-3 cursor-pointer"
              onClick={() => navigate("/")}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <div className="neu-raised rounded-xl p-2 bg-primary/10">
                <img src="/logo.svg" alt="Pikar AI" className="h-8 w-8" />
              </div>
              <span className="text-xl font-bold tracking-tight">Pikar AI</span>
            </motion.div>

            {/* Desktop nav */}
            <div className="hidden md:flex items-center gap-6 text-sm">
              <button className="text-muted-foreground hover:text-foreground transition-colors">Home</button>
              <button className="text-muted-foreground hover:text-foreground transition-colors">Features</button>
              <button className="text-muted-foreground hover:text-foreground transition-colors">Pricing</button>
              <button className="text-muted-foreground hover:text-foreground transition-colors">Docs</button>
            </div>

            {/* Desktop actions */}
            <div className="hidden md:flex items-center space-x-3">
              <Button 
                variant="ghost" 
                className="neu-flat rounded-xl"
                onClick={() => navigate("/auth")}
              >
                Sign In
              </Button>
              <Button 
                className="neu-raised rounded-xl bg-primary hover:bg-primary/90"
                onClick={handleGetStarted}
                disabled={isLoading}
              >
                {isLoading ? (
                  <span className="inline-flex items-center">
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Loading...
                  </span>
                ) : (
                  "Get Started"
                )}
              </Button>
            </div>

            {/* Mobile menu */}
            <div className="md:hidden">
              <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
                <SheetTrigger asChild>
                  <Button variant="outline" size="icon" className="neu-flat rounded-xl">
                    <Menu className="h-5 w-5" />
                  </Button>
                </SheetTrigger>
                <SheetContent side="right" className="w-80 sm:w-96">
                  <div className="mt-6 space-y-6">
                    <div className="flex items-center space-x-3">
                      <div className="neu-raised rounded-xl p-2 bg-primary/10">
                        <img src="/logo.svg" alt="Pikar AI" className="h-7 w-7" />
                      </div>
                      <span className="text-lg font-semibold">Pikar AI</span>
                    </div>

                    <div className="grid grid-cols-1 gap-3">
                      <Button variant="ghost" className="justify-start" onClick={() => setMobileOpen(false)}>
                        Home
                      </Button>
                      <Button variant="ghost" className="justify-start" onClick={() => setMobileOpen(false)}>
                        Features
                      </Button>
                      <Button variant="ghost" className="justify-start" onClick={() => setMobileOpen(false)}>
                        Pricing
                      </Button>
                      <Button variant="ghost" className="justify-start" onClick={() => setMobileOpen(false)}>
                        Docs
                      </Button>
                    </div>

                    <div className="pt-2 space-y-3">
                      <Button 
                        variant="outline" 
                        className="w-full neu-flat rounded-xl"
                        onClick={() => {
                          setMobileOpen(false);
                          navigate("/auth");
                        }}
                      >
                        Sign In
                      </Button>
                      <Button 
                        className="w-full neu-raised rounded-xl bg-primary hover:bg-primary/90"
                        onClick={() => {
                          setMobileOpen(false);
                          handleGetStarted();
                        }}
                        disabled={isLoading}
                      >
                        {isLoading ? (
                          <span className="inline-flex items-center">
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Loading...
                          </span>
                        ) : (
                          "Get Started"
                        )}
                      </Button>
                    </div>
                  </div>
                </SheetContent>
              </Sheet>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative py-14 sm:py-20 lg:py-24 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto text-center">
          <motion.div
            initial={{ y: 50, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.8, delay: 0.2 }}
          >
            <div className="inline-flex items-center space-x-2 bg-primary/10 rounded-full px-3 py-1.5 sm:px-4 sm:py-2 mb-6 sm:mb-8 neu-inset">
              <Sparkles className="h-4 w-4 text-primary" />
              <span className="text-xs sm:text-sm font-medium text-primary">AI‑Powered Business Intelligence</span>
            </div>
            
            <h1 className="text-4xl sm:text-6xl md:text-7xl font-bold tracking-tight mb-4 sm:mb-6 leading-[1.15] sm:leading-[1.1]">
              <span className="text-foreground">Transform Your Business</span>
              <br />
              <span className="text-primary">and Ideas</span> <span className="text-foreground">with AI</span>
            </h1>
            
            <p className="text-base sm:text-xl text-muted-foreground max-w-3xl mx-auto mb-8 sm:mb-10 leading-relaxed px-1">
              Pikar AI helps entrepreneurs and businesses evaluate ideas, diagnose problems,
              and integrate with ERP systems using cutting‑edge artificial intelligence.
            </p>
            
            <div className="flex flex-col sm:flex-row gap-3 sm:gap-4 justify-center items-center">
              <Button 
                size="lg" 
                className="w-full sm:w-auto neu-raised rounded-xl bg-primary hover:bg-primary/90 px-8 py-4 text-lg"
                onClick={handleGetStarted}
                disabled={isLoading}
              >
                {isLoading ? (
                  <span className="inline-flex items-center">
                    <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                    Starting...
                  </span>
                ) : (
                  <>
                    Start Free Assessment
                    <ArrowRight className="ml-2 h-5 w-5" />
                  </>
                )}
              </Button>
              <Button 
                size="lg" 
                variant="outline" 
                className="w-full sm:w-auto neu-flat rounded-xl px-8 py-4 text-lg"
                onClick={() => setDemoOpen(true)}
              >
                Watch Demo
              </Button>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Stats row added to match screenshots */}
      <section className="px-4 sm:px-6 lg:px-8 pb-12 sm:pb-16">
        <div className="max-w-6xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            viewport={{ once: true }}
            className="text-center mb-6 sm:mb-8"
          >
            <p className="text-xs sm:text-sm text-muted-foreground tracking-wide">
              Trusted by teams at
            </p>
          </motion.div>

          <div className="relative">
            <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 gap-4 sm:gap-6 items-center">
              {trustedLogos.map((logo, i) => (
                <motion.div
                  key={logo.name}
                  initial={{ opacity: 0, y: 12 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.45, delay: i * 0.05 }}
                  className="neu-inset rounded-xl px-3 py-2 sm:px-4 sm:py-3 bg-card/60"
                >
                  <motion.img
                    src={logo.src}
                    alt={`${logo.name} logo`}
                    className="h-6 sm:h-7 mx-auto opacity-75 saturate-0 hover:opacity-100 hover:saturate-100 transition-all duration-300"
                    animate={{ y: [0, -3, 0] }}
                    transition={{ duration: 3 + (i % 3) * 0.4, repeat: Infinity, repeatType: "loop", ease: "easeInOut" }}
                  />
                </motion.div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-14 sm:py-20 px-4 sm:px-6 lg:px-8 bg-accent/5">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ y: 50, opacity: 0 }}
            whileInView={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.8 }}
            viewport={{ once: true }}
            className="text-center mb-12 sm:mb-16"
          >
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight mb-3 sm:mb-4">
              Powerful AI Capabilities
            </h2>
            <p className="text-base sm:text-xl text-muted-foreground max-w-2xl mx-auto px-2">
              Experience the future of business automation with our comprehensive AI platform
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feature, index) => (
              <motion.div
                key={feature.title}
                initial={{ y: 50, opacity: 0 }}
                whileInView={{ y: 0, opacity: 1 }}
                transition={{ duration: 0.6, delay: index * 0.1 }}
                viewport={{ once: true }}
              >
                <Card className="neu-raised rounded-2xl border-0 h-full hover:shadow-lg transition-all duration-300">
                  <CardContent className="p-8">
                    <div className="neu-inset rounded-xl p-3 w-fit mb-6">
                      <feature.icon className="h-6 w-6 text-primary" />
                    </div>
                    <h3 className="text-xl font-semibold mb-3">{feature.title}</h3>
                    <p className="text-muted-foreground leading-relaxed">{feature.description}</p>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section className="py-14 sm:py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <motion.div
            initial={{ y: 50, opacity: 0 }}
            whileInView={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.8 }}
            viewport={{ once: true }}
            className="text-center mb-12 sm:mb-16"
          >
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight mb-3 sm:mb-4">
              Choose Your Growth Path
            </h2>
            <p className="text-base sm:text-xl text-muted-foreground max-w-2xl mx-auto px-2">
              From solopreneurs to enterprises, we have the perfect plan for your business size
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {tiers.map((tier, index) => (
              <motion.div
                key={tier.name}
                initial={{ y: 50, opacity: 0 }}
                whileInView={{ y: 0, opacity: 1 }}
                transition={{ duration: 0.6, delay: index * 0.1 }}
                viewport={{ once: true }}
              >
                <Card className={`neu-raised rounded-2xl border-0 h-full ${index === 1 ? 'ring-2 ring-primary' : ''}`}>
                  <CardContent className="p-6">
                    {index === 1 && (
                      <div className="text-center mb-4">
                        <span className="bg-primary text-primary-foreground px-3 py-1 rounded-full text-sm font-medium">
                          Most Popular
                        </span>
                      </div>
                    )}
                    <div className="text-center mb-6">
                      <h3 className="text-xl font-semibold mb-2">{tier.name}</h3>
                      <div className="text-3xl font-bold text-primary mb-2">{tier.price}</div>
                      <p className="text-sm text-muted-foreground">{tier.description}</p>
                    </div>
                    <ul className="space-y-3 mb-6">
                      {tier.features.map((feature) => (
                        <li key={feature} className="flex items-center">
                          <CheckCircle className="h-4 w-4 text-primary mr-3 flex-shrink-0" />
                          <span className="text-sm">{feature}</span>
                        </li>
                      ))}
                    </ul>
                    <Button 
                      className="w-full neu-flat rounded-xl"
                      variant={index === 1 ? "default" : "outline"}
                      onClick={handleGetStarted}
                    >
                      Get Started
                    </Button>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-16 px-4 sm:px-6 lg:px-8 bg-gradient-to-r from-primary/10 via-accent/10 to-primary/10">
        <div className="max-w-4xl mx-auto text-center">
          <motion.div
            initial={{ y: 50, opacity: 0 }}
            whileInView={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.8 }}
            viewport={{ once: true }}
          >
            <Target className="h-16 w-16 text-primary mx-auto mb-6" />
            <h2 className="text-4xl font-bold tracking-tight mb-6">
              Ready to Transform Your Business?
            </h2>
            <p className="text-xl text-muted-foreground mb-8 max-w-2xl mx-auto">
              Join thousands of businesses already using Pikar AI to automate operations, boost productivity, and accelerate growth.
            </p>
            <Button 
              size="lg" 
              className="w-full sm:w-auto neu-raised rounded-xl bg-primary hover:bg-primary/90 px-8 py-4 text-lg"
              onClick={handleGetStarted}
              disabled={isLoading}
            >
              {isLoading ? (
                <span className="inline-flex items-center">
                  <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                  Loading...
                </span>
              ) : (
                <>
                  Start Your Free Trial
                  <ArrowRight className="ml-2 h-5 w-5" />
                </>
              )}
            </Button>
          </motion.div>
        </div>
      </section>

      {/* Demo Modal */}
      <Dialog open={demoOpen} onOpenChange={setDemoOpen}>
        <DialogContent className="max-w-3xl w-[92vw] sm:w-[680px] neu-raised rounded-2xl border-0 p-0 overflow-hidden">
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: 8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
            className="w-full"
          >
            <DialogHeader className="px-6 pt-6 pb-3">
              <DialogTitle className="text-xl font-semibold tracking-tight">Pikar AI Demo</DialogTitle>
              <DialogDescription className="text-muted-foreground">
                A quick overview of how Pikar AI helps transform your business with AI‑powered automation.
              </DialogDescription>
            </DialogHeader>

            <div className="px-6 pb-6">
              <div className="aspect-video neu-inset rounded-xl overflow-hidden">
                <iframe
                  className="h-full w-full"
                  src="https://www.youtube.com/embed/dQw4w9WgXcQ"
                  title="Pikar AI Demo"
                  frameBorder="0"
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                  allowFullScreen
                />
              </div>
            </div>
          </motion.div>
        </DialogContent>
      </Dialog>

      {/* Footer */}
      <footer className="py-12 px-4 sm:px-6 lg:px-8 border-t border-border/50">
        <div className="max-w-7xl mx-auto text-center">
          <div className="flex items-center justify-center space-x-3 mb-4">
            <div className="neu-raised rounded-xl p-2">
              <img src="/logo.svg" alt="Pikar AI" className="h-6 w-6" />
            </div>
            <span className="text-lg font-semibold">Pikar AI</span>
          </div>
          <p className="text-muted-foreground mb-4">
            Empowering businesses with intelligent automation
          </p>
          <p className="text-sm text-muted-foreground">
            Built with ❤️ by{" "}
            <a
              href="https://vly.ai"
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary hover:text-primary/80 transition-colors"
            >
              vly.ai
            </a>
          </p>
        </div>
      </footer>
    </motion.div>
  );
}