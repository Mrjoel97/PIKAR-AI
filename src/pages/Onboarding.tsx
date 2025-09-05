import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useAuth } from "@/hooks/use-auth";
import { api } from "@/convex/_generated/api";
import { useMutation } from "convex/react";
import { motion } from "framer-motion";
import { ArrowRight, Building, Target, Users, Zap } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router";
import { toast } from "sonner";

export default function Onboarding() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const createBusiness = useMutation(api.businesses.create);
  
  const [step, setStep] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    tier: "",
    industry: "",
    description: "",
    website: "",
  });

  const industries = [
    "Technology", "Healthcare", "Finance", "Retail", "Manufacturing",
    "Education", "Real Estate", "Marketing", "Consulting", "Other"
  ];

  const tiers = [
    { value: "solopreneur", label: "Solopreneur", description: "Individual entrepreneur" },
    { value: "startup", label: "Startup", description: "Growing team (2-10 people)" },
    { value: "sme", label: "SME", description: "Established business (11-100 people)" },
    { value: "enterprise", label: "Enterprise", description: "Large organization (100+ people)" }
  ];

  const handleNext = () => {
    if (step < 3) {
      setStep(step + 1);
    }
  };

  const handleBack = () => {
    if (step > 1) {
      setStep(step - 1);
    }
  };

  const handleSubmit = async () => {
    if (!formData.name || !formData.tier || !formData.industry) {
      toast.error("Please fill in all required fields");
      return;
    }

    setIsLoading(true);
    try {
      await createBusiness({
        name: formData.name,
        tier: formData.tier as any,
        industry: formData.industry,
        description: formData.description,
        website: formData.website,
      });
      
      toast.success("Business profile created successfully!");
      navigate("/dashboard");
    } catch (error) {
      console.error("Error creating business:", error);
      toast.error("Failed to create business profile");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
      className="min-h-screen bg-gradient-to-br from-background via-background to-accent/10 flex items-center justify-center p-4"
    >
      <div className="w-full max-w-2xl">
        {/* Header */}
        <motion.div
          initial={{ y: -20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.6 }}
          className="text-center mb-8"
        >
          <div className="neu-raised rounded-xl p-3 w-fit mx-auto mb-4">
            <img src="./logo.svg" alt="Pikar AI" className="h-8 w-8" />
          </div>
          <h1 className="text-3xl font-bold tracking-tight mb-2">Welcome to Pikar AI</h1>
          <p className="text-muted-foreground">Let's set up your business profile to get started</p>
        </motion.div>

        {/* Progress Indicator */}
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="flex items-center justify-center mb-8"
        >
          <div className="flex items-center space-x-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="flex items-center">
                <div className={`neu-${step >= i ? 'raised' : 'inset'} rounded-full p-3 ${
                  step >= i ? 'bg-primary text-primary-foreground' : ''
                }`}>
                  {i === 1 && <Building className="h-4 w-4" />}
                  {i === 2 && <Target className="h-4 w-4" />}
                  {i === 3 && <Zap className="h-4 w-4" />}
                </div>
                {i < 3 && (
                  <div className={`w-8 h-0.5 mx-2 ${
                    step > i ? 'bg-primary' : 'bg-border'
                  }`} />
                )}
              </div>
            ))}
          </div>
        </motion.div>

        {/* Form Card */}
        <motion.div
          key={step}
          initial={{ x: 20, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          transition={{ duration: 0.5 }}
        >
          <Card className="neu-raised rounded-2xl border-0">
            <CardHeader>
              <CardTitle className="text-xl font-semibold">
                {step === 1 && "Business Information"}
                {step === 2 && "Business Type"}
                {step === 3 && "Additional Details"}
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 pt-0 space-y-6">
              {step === 1 && (
                <>
                  <div className="space-y-2">
                    <Label htmlFor="name">Business Name *</Label>
                    <Input
                      id="name"
                      placeholder="Enter your business name"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      className="neu-inset rounded-xl"
                    />
                  </div>
                  
                  <div className="space-y-2">
                    <Label htmlFor="industry">Industry *</Label>
                    <Select 
                      value={formData.industry} 
                      onValueChange={(value) => setFormData({ ...formData, industry: value })}
                    >
                      <SelectTrigger className="neu-inset rounded-xl">
                        <SelectValue placeholder="Select your industry" />
                      </SelectTrigger>
                      <SelectContent>
                        {industries.map((industry) => (
                          <SelectItem key={industry} value={industry}>
                            {industry}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="website">Website (Optional)</Label>
                    <Input
                      id="website"
                      placeholder="https://yourwebsite.com"
                      value={formData.website}
                      onChange={(e) => setFormData({ ...formData, website: e.target.value })}
                      className="neu-inset rounded-xl"
                    />
                  </div>
                </>
              )}

              {step === 2 && (
                <div className="space-y-4">
                  <Label>Business Size *</Label>
                  <div className="grid grid-cols-1 gap-4">
                    {tiers.map((tier) => (
                      <div
                        key={tier.value}
                        className={`neu-${formData.tier === tier.value ? 'inset' : 'flat'} rounded-xl p-4 cursor-pointer transition-all ${
                          formData.tier === tier.value ? 'ring-2 ring-primary' : ''
                        }`}
                        onClick={() => setFormData({ ...formData, tier: tier.value })}
                      >
                        <div className="flex items-center justify-between">
                          <div>
                            <h3 className="font-medium">{tier.label}</h3>
                            <p className="text-sm text-muted-foreground">{tier.description}</p>
                          </div>
                          <Users className="h-5 w-5 text-muted-foreground" />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {step === 3 && (
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="description">Business Description (Optional)</Label>
                    <Textarea
                      id="description"
                      placeholder="Tell us about your business goals and challenges..."
                      value={formData.description}
                      onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                      className="neu-inset rounded-xl min-h-[120px]"
                    />
                  </div>
                  
                  <div className="neu-inset rounded-xl p-4">
                    <h4 className="font-medium mb-2">What's Next?</h4>
                    <ul className="text-sm text-muted-foreground space-y-1">
                      <li>• Set up your first AI agents</li>
                      <li>• Configure data integrations</li>
                      <li>• Create your first initiative</li>
                      <li>• Start automating your workflows</li>
                    </ul>
                  </div>
                </div>
              )}

              {/* Navigation Buttons */}
              <div className="flex justify-between pt-6">
                <Button
                  variant="outline"
                  onClick={handleBack}
                  disabled={step === 1}
                  className="neu-flat rounded-xl"
                >
                  Back
                </Button>
                
                {step < 3 ? (
                  <Button
                    onClick={handleNext}
                    disabled={
                      (step === 1 && (!formData.name || !formData.industry)) ||
                      (step === 2 && !formData.tier)
                    }
                    className="neu-raised rounded-xl bg-primary hover:bg-primary/90"
                  >
                    Next
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                ) : (
                  <Button
                    onClick={handleSubmit}
                    disabled={isLoading}
                    className="neu-raised rounded-xl bg-primary hover:bg-primary/90"
                  >
                    {isLoading ? "Creating..." : "Complete Setup"}
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </motion.div>
  );
}
