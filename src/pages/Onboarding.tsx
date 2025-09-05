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
import { ArrowRight, Building, Target, Users, Zap, Loader2 } from "lucide-react";
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

  const [errors, setErrors] = useState<{
    name?: string;
    industry?: string;
    website?: string;
    tier?: string;
    description?: string;
  }>({});

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

  const isValidUrl = (value: string) => {
    try {
      const url = new URL(value);
      // require protocol and hostname
      return !!url.protocol && !!url.hostname;
    } catch {
      return false;
    }
  };

  const validateStep1 = () => {
    const newErrors: typeof errors = {};
    if (!formData.name.trim()) newErrors.name = "Business name is required";
    else if (formData.name.trim().length < 2)
      newErrors.name = "Business name must be at least 2 characters";

    if (!formData.industry) newErrors.industry = "Please select your industry";

    if (formData.website.trim()) {
      const val = formData.website.trim();
      const prefixed = /^https?:\/\//i.test(val) ? val : `https://${val}`;
      if (!isValidUrl(prefixed)) newErrors.website = "Enter a valid URL (e.g., https://example.com)";
    }

    setErrors((prev) => ({ ...prev, ...newErrors }));
    return Object.keys(newErrors).length === 0;
  };

  const validateStep2 = () => {
    const newErrors: typeof errors = {};
    if (!formData.tier) newErrors.tier = "Please choose a business size";
    setErrors((prev) => ({ ...prev, ...newErrors }));
    return Object.keys(newErrors).length === 0;
  };

  const validateBeforeSubmit = () => {
    const ok1 = validateStep1();
    const ok2 = validateStep2();
    const newErrors: typeof errors = {};
    if (formData.description && formData.description.length > 500) {
      newErrors.description = "Description must be 500 characters or less";
    }
    setErrors((prev) => ({ ...prev, ...newErrors }));
    return ok1 && ok2 && Object.keys(newErrors).length === 0;
  };

  const handleNext = () => {
    if (step === 1) {
      if (!validateStep1()) return;
    }
    if (step === 2) {
      if (!validateStep2()) return;
    }
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
    if (!validateBeforeSubmit()) {
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
                      onChange={(e) => {
                        setFormData({ ...formData, name: e.target.value });
                        if (errors.name) setErrors((prev) => ({ ...prev, name: undefined }));
                      }}
                      onBlur={() => {
                        if (!formData.name.trim()) {
                          setErrors((prev) => ({ ...prev, name: "Business name is required" }));
                        } else if (formData.name.trim().length < 2) {
                          setErrors((prev) => ({ ...prev, name: "Business name must be at least 2 characters" }));
                        }
                      }}
                      aria-invalid={!!errors.name}
                      aria-describedby={errors.name ? "name-error" : undefined}
                      className={`neu-inset rounded-xl ${errors.name ? "ring-2 ring-destructive" : ""}`}
                      maxLength={100}
                      disabled={isLoading}
                    />
                    {errors.name && (
                      <p id="name-error" className="text-xs text-red-500">{errors.name}</p>
                    )}
                  </div>
                  
                  <div className="space-y-2">
                    <Label htmlFor="industry">Industry *</Label>
                    <Select 
                      value={formData.industry} 
                      onValueChange={(value) => {
                        setFormData({ ...formData, industry: value });
                        if (errors.industry) setErrors((prev) => ({ ...prev, industry: undefined }));
                      }}
                    >
                      <SelectTrigger
                        id="industry"
                        aria-invalid={!!errors.industry}
                        aria-describedby={errors.industry ? "industry-error" : undefined}
                        className={`neu-inset rounded-xl ${errors.industry ? "ring-2 ring-destructive" : ""}`}
                        disabled={isLoading}
                      >
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
                    {errors.industry && (
                      <p id="industry-error" className="text-xs text-red-500">{errors.industry}</p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="website">Website (Optional)</Label>
                    <Input
                      id="website"
                      placeholder="https://yourwebsite.com"
                      value={formData.website}
                      onChange={(e) => {
                        setFormData({ ...formData, website: e.target.value });
                        if (errors.website) setErrors((prev) => ({ ...prev, website: undefined }));
                      }}
                      onBlur={() => {
                        if (formData.website.trim()) {
                          const val = formData.website.trim();
                          const prefixed = /^https?:\/\//i.test(val) ? val : `https://${val}`;
                          if (!isValidUrl(prefixed)) {
                            setErrors((prev) => ({ ...prev, website: "Enter a valid URL (e.g., https://example.com)" }));
                          }
                        }
                      }}
                      aria-invalid={!!errors.website}
                      aria-describedby={errors.website ? "website-error" : undefined}
                      className={`neu-inset rounded-xl ${errors.website ? "ring-2 ring-destructive" : ""}`}
                      maxLength={200}
                      disabled={isLoading}
                    />
                    {errors.website && (
                      <p id="website-error" className="text-xs text-red-500">{errors.website}</p>
                    )}
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
                        } ${errors.tier ? "ring-2 ring-destructive" : ""} ${isLoading ? "opacity-60 cursor-not-allowed" : ""}`}
                        onClick={() => {
                          if (isLoading) return;
                          setFormData({ ...formData, tier: tier.value });
                          if (errors.tier) setErrors((prev) => ({ ...prev, tier: undefined }));
                        }}
                        role="button"
                        aria-pressed={formData.tier === tier.value}
                        aria-disabled={isLoading}
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
                  {errors.tier && (
                    <p className="text-xs text-red-500">{errors.tier}</p>
                  )}
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
                      onChange={(e) => {
                        setFormData({ ...formData, description: e.target.value });
                        if (errors.description) setErrors((prev) => ({ ...prev, description: undefined }));
                      }}
                      onBlur={() => {
                        if (formData.description && formData.description.length > 500) {
                          setErrors((prev) => ({ ...prev, description: "Description must be 500 characters or less" }));
                        }
                      }}
                      aria-invalid={!!errors.description}
                      aria-describedby={errors.description ? "description-error" : undefined}
                      className={`neu-inset rounded-xl min-h-[120px] ${errors.description ? "ring-2 ring-destructive" : ""}`}
                      maxLength={600}
                      disabled={isLoading}
                    />
                    {errors.description && (
                      <p id="description-error" className="text-xs text-red-500">{errors.description}</p>
                    )}
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
                  disabled={step === 1 || isLoading}
                  className="neu-flat rounded-xl"
                >
                  Back
                </Button>
                
                {step < 3 ? (
                  <Button
                    onClick={handleNext}
                    disabled={
                      isLoading ||
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
                    {isLoading ? (
                      <span className="inline-flex items-center">
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Creating...
                      </span>
                    ) : (
                      <>
                        Complete Setup
                        <ArrowRight className="ml-2 h-4 w-4" />
                      </>
                    )}
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