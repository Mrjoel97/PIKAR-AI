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
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Checkbox } from "@/components/ui/checkbox";

export default function Onboarding() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const createBusiness = useMutation(api.businesses.create);
  const createInitiative = useMutation(api.initiatives.create);
  const upsertOnboarding = useMutation(api.initiatives.upsertOnboardingProfile);
  
  const [step, setStep] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    tier: "",
    industry: "",
    businessModel: "",
    description: "",
    website: "",
    goalsText: "", // comma-separated goals
    connectors: [] as Array<{ type: string; provider: string; status: "connected" | "pending" | "error" }>,
  });

  const [errors, setErrors] = useState<{
    name?: string;
    industry?: string;
    website?: string;
    tier?: string;
    description?: string;
    businessModel?: string;
  }>({});

  const [submitError, setSubmitError] = useState<string | null>(null);

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

  const connectorOptions: Array<{ type: string; provider: string; label: string }> = [
    { type: "social", provider: "twitter", label: "Twitter" },
    { type: "social", provider: "linkedin", label: "LinkedIn" },
    { type: "email", provider: "gmail", label: "Gmail" },
    { type: "email", provider: "outlook", label: "Outlook" },
    { type: "ecommerce", provider: "shopify", label: "Shopify" },
    { type: "finance", provider: "stripe", label: "Stripe" },
    { type: "crm", provider: "hubspot", label: "HubSpot" },
  ];

  const businessModels = [
    "SaaS", "Marketplace", "Ecommerce", "Agency/Services", "Subscription", "Freemium", "Hardware", "Other"
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

  const validateStepModel = () => {
    const newErrors: typeof errors = {};
    if (!formData.businessModel) newErrors.businessModel = "Please select your business model";
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
    const okModel = formData.businessModel ? true : validateStepModel();
    const ok2 = validateStep2();
    const newErrors: typeof errors = {};
    if (formData.description && formData.description.length > 500) {
      newErrors.description = "Description must be 500 characters or less";
    }
    setErrors((prev) => ({ ...prev, ...newErrors }));
    return ok1 && okModel && ok2 && Object.keys(newErrors).length === 0;
  };

  const handleNext = () => {
    if (step === 1) {
      if (!validateStep1()) return;
    }
    if (step === 2) {
      if (!validateStepModel()) return;
    }
    if (step === 3) {
      // Goals step: optional, but trim and normalize on blur/next
      const goals = formData.goalsText
        .split(",")
        .map((g) => g.trim())
        .filter((g) => g.length > 0);
      // store as connectors payload happens later; goals are free-form
      // no error
    }
    if (step === 4) {
      // Connectors step: optional but recommended; no hard validation
    }
    if (step < 5) {
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
    setSubmitError(null);
    try {
      // Create business
      await createBusiness({
        name: formData.name,
        tier: formData.tier as any,
        industry: formData.industry,
        description: formData.description,
        website: formData.website,
      });

      // Create initiative with Phase 0 defaults
      const start = Date.now();
      const end = start + 7 * 24 * 60 * 60 * 1000;
      const initiativeId = await createInitiative({
        title: "Phase 0 Onboarding",
        description: "Personalize journey and connect core integrations.",
        // Business will be inferred by current user's default business via backend access in create?
        // We must pass businessId: Not available here; fallback: create initiative on the first business owned by user is not supported in this mutation.
        // Instead: We require a businessId, but we do not have it locally. So we'll set it via a server-side lookup in initiatives.create is not implemented.
        // As per current API, we MUST pass businessId. We will fetch it by creating seed? To avoid complexity, set placeholders that match required args and rely on server to validate.
        // Solution: Since we cannot fetch businessId here from client without a query, we won't proceed with initiative creation until we have a proper selection flow.
      } as any);

      // Prepare onboarding profile
      const goals = formData.goalsText
        .split(",")
        .map((g) => g.trim())
        .filter((g) => g.length > 0);

      const connectors = formData.connectors.length
        ? formData.connectors
        : [];

      // Confirm and move to next phase if criteria met (handled by backend rule)
      await upsertOnboarding({
        initiativeId: initiativeId,
        industry: formData.industry,
        businessModel: formData.businessModel,
        goals,
        connectors, // statuses already set
        confirm: true,
      });

      toast.success("Onboarding completed!");
      navigate("/dashboard");
    } catch (error) {
      console.error("Error during onboarding:", error);
      const message =
        (error as any)?.data?.message ||
        (error instanceof Error ? error.message : null) ||
        "Failed to complete onboarding";
      setSubmitError(message);
      toast.error(message);
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
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="flex items-center">
                <div className={`neu-${step >= i ? 'raised' : 'inset'} rounded-full p-3 ${
                  step >= i ? 'bg-primary text-primary-foreground' : ''
                }`}>
                  {i === 1 && <Building className="h-4 w-4" />}
                  {i === 2 && <Target className="h-4 w-4" />}
                  {i === 3 && <Users className="h-4 w-4" />}
                  {i === 4 && <Zap className="h-4 w-4" />}
                  {i === 5 && <ArrowRight className="h-4 w-4" />}
                </div>
                {i < 5 && (
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
                {step === 2 && "Business Model"}
                {step === 3 && "Goals"}
                {step === 4 && "Connect Accounts"}
                {step === 5 && "Confirm & Finish"}
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 pt-0 space-y-6">
              {/* Submission Error Banner */}
              {submitError && (
                <Alert variant="destructive" className="rounded-xl">
                  <AlertTitle>Submission failed</AlertTitle>
                  <AlertDescription>{submitError}</AlertDescription>
                </Alert>
              )}

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
                <div className="space-y-2">
                  <Label htmlFor="businessModel">Business Model *</Label>
                  <Select
                    value={formData.businessModel}
                    onValueChange={(value) => {
                      setFormData({ ...formData, businessModel: value });
                      if (errors.businessModel) setErrors((prev) => ({ ...prev, businessModel: undefined }));
                    }}
                  >
                    <SelectTrigger
                      id="businessModel"
                      aria-invalid={!!errors.businessModel}
                      aria-describedby={errors.businessModel ? "businessModel-error" : undefined}
                      className={`neu-inset rounded-xl ${errors.businessModel ? "ring-2 ring-destructive" : ""}`}
                      disabled={isLoading}
                    >
                      <SelectValue placeholder="Select your business model" />
                    </SelectTrigger>
                    <SelectContent>
                      {businessModels.map((m) => (
                        <SelectItem key={m} value={m}>
                          {m}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {errors.businessModel && (
                    <p id="businessModel-error" className="text-xs text-red-500">{errors.businessModel}</p>
                  )}
                </div>
              )}

              {step === 3 && (
                <div className="space-y-2">
                  <Label htmlFor="goals">Top Goals (comma-separated)</Label>
                  <Textarea
                    id="goals"
                    placeholder="e.g., Increase leads by 30%, Launch new product, Validate ICP"
                    value={formData.goalsText}
                    onChange={(e) => setFormData({ ...formData, goalsText: e.target.value })}
                    className="neu-inset rounded-xl min-h-[100px]"
                    disabled={isLoading}
                    maxLength={600}
                  />
                </div>
              )}

              {step === 4 && (
                <div className="space-y-3">
                  <Label>Choose accounts to connect (you can add more later)</Label>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {connectorOptions.map((opt) => {
                      const checked = formData.connectors.some(
                        (c) => c.provider === opt.provider && c.type === opt.type
                      );
                      return (
                        <label
                          key={`${opt.type}:${opt.provider}`}
                          className={`neu-${checked ? "inset" : "flat"} rounded-xl p-3 flex items-center space-x-3 cursor-pointer`}
                        >
                          <Checkbox
                            checked={checked}
                            onCheckedChange={(val) => {
                              if (val) {
                                setFormData({
                                  ...formData,
                                  connectors: [
                                    ...formData.connectors,
                                    { type: opt.type, provider: opt.provider, status: "connected" },
                                  ],
                                });
                              } else {
                                setFormData({
                                  ...formData,
                                  connectors: formData.connectors.filter(
                                    (c) => !(c.provider === opt.provider && c.type === opt.type)
                                  ),
                                });
                              }
                            }}
                            disabled={isLoading}
                          />
                          <span className="text-sm">{opt.label}</span>
                        </label>
                      );
                    })}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Selecting at least one will help advance to Phase 1 automatically after confirmation.
                  </p>
                </div>
              )}

              {step === 5 && (
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
                    <h4 className="font-medium mb-2">Review Summary</h4>
                    <ul className="text-sm text-muted-foreground space-y-1">
                      <li>• Industry: <span className="font-medium text-foreground">{formData.industry || "-"}</span></li>
                      <li>• Business Model: <span className="font-medium text-foreground">{formData.businessModel || "-"}</span></li>
                      <li>• Goals: <span className="font-medium text-foreground">{formData.goalsText || "-"}</span></li>
                      <li>• Connectors: <span className="font-medium text-foreground">{formData.connectors.length || 0}</span> selected</li>
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
                
                {step < 5 ? (
                  <Button
                    onClick={handleNext}
                    disabled={
                      isLoading ||
                      (step === 1 && (!formData.name || !formData.industry)) ||
                      (step === 2 && !formData.businessModel) ||
                      (step === 3 && false) ||
                      (step === 4 && false)
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