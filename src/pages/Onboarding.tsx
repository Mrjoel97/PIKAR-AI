import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useAuth } from "@/hooks/use-auth";
import { api } from "@/convex/_generated/api";
import { useMutation, useQuery } from "convex/react";
import { ArrowLeft, ArrowRight, CheckCircle, Loader2, Plus, X } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router";
import { toast } from "sonner";

const industries = [
  "software", "ecommerce", "healthcare", "finance", "education", 
  "manufacturing", "retail", "consulting", "marketing", "other"
];

const businessModels = [
  "saas", "marketplace", "subscription", "ecommerce", "consulting", 
  "freemium", "advertising", "transaction", "licensing", "other"
];

export default function Onboarding() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const navigate = useNavigate();
  
  const [currentStep, setCurrentStep] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  
  // Form state
  const [selectedIndustry, setSelectedIndustry] = useState("");
  const [selectedBusinessModel, setSelectedBusinessModel] = useState("");
  const [goals, setGoals] = useState<string[]>([]);
  const [newGoal, setNewGoal] = useState("");
  const [connections, setConnections] = useState({
    social: false,
    email: false,
    ecommerce: false,
    finance: false,
  });

  // Convex queries and mutations
  const currentBusiness = useQuery(api.businesses.currentUserBusiness);
  const currentInitiative = useQuery(
    api.initiatives.getByBusiness,
    currentBusiness ? { businessId: currentBusiness._id } : "skip"
  );
  
  const upsertInitiative = useMutation(api.initiatives.upsertForBusiness);
  const updateOnboarding = useMutation(api.initiatives.updateOnboarding);
  const runDiagnostics = useMutation(api.initiatives.runPhase0Diagnostics);
  const advancePhase = useMutation(api.initiatives.advancePhase);

  // Redirect if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      navigate("/auth");
    }
  }, [isAuthenticated, authLoading, navigate]);

  // Pre-populate form if initiative exists
  useEffect(() => {
    if (currentInitiative) {
      setSelectedIndustry(currentInitiative.onboardingProfile.industry);
      setSelectedBusinessModel(currentInitiative.onboardingProfile.businessModel);
      setGoals(currentInitiative.onboardingProfile.goals);
    }
  }, [currentInitiative]);

  const addGoal = () => {
    if (newGoal.trim() && !goals.includes(newGoal.trim())) {
      setGoals([...goals, newGoal.trim()]);
      setNewGoal("");
    }
  };

  const removeGoal = (goalToRemove: string) => {
    setGoals(goals.filter(goal => goal !== goalToRemove));
  };

  const handleNext = () => {
    if (currentStep < 3) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleFinish = async () => {
    if (!currentBusiness) {
      toast("No business found. Please create a business first.");
      return;
    }

    if (!selectedIndustry || !selectedBusinessModel) {
      toast("Please select industry and business model.");
      return;
    }

    setIsLoading(true);
    
    try {
      // Step 1: Upsert initiative
      const initiative = await upsertInitiative({
        businessId: currentBusiness._id,
        industry: selectedIndustry,
        businessModel: selectedBusinessModel,
      });

      if (!initiative) {
        throw new Error("Failed to create initiative");
      }

      // Step 2: Update onboarding profile
      await updateOnboarding({
        initiativeId: initiative._id,
        profile: {
          industry: selectedIndustry,
          businessModel: selectedBusinessModel,
          goals,
        },
      });

      // Step 3: Run diagnostics
      await runDiagnostics({
        businessId: currentBusiness._id,
      });

      // Step 4: Advance to phase 1
      await advancePhase({
        initiativeId: initiative._id,
        toPhase: 1,
      });

      toast("Onboarding completed successfully!");
      navigate("/dashboard");
    } catch (error) {
      console.error("Onboarding error:", error);
      toast("Failed to complete onboarding. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-accent/10 via-background to-primary/5 flex items-center justify-center p-4">
      <Card className="w-full max-w-2xl">
        <CardHeader>
          <CardTitle className="text-2xl text-center">
            Initiative Setup
          </CardTitle>
          <div className="flex justify-center space-x-2 mt-4">
            {[1, 2, 3].map((step) => (
              <div
                key={step}
                className={`w-3 h-3 rounded-full ${
                  step <= currentStep ? "bg-primary" : "bg-muted"
                }`}
              />
            ))}
          </div>
        </CardHeader>
        
        <CardContent className="space-y-6">
          {currentStep === 1 && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">Business Details</h3>
              
              <div className="space-y-2">
                <label className="text-sm font-medium">Industry</label>
                <Select value={selectedIndustry} onValueChange={setSelectedIndustry}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select your industry" />
                  </SelectTrigger>
                  <SelectContent>
                    {industries.map((industry) => (
                      <SelectItem key={industry} value={industry}>
                        {industry.charAt(0).toUpperCase() + industry.slice(1)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Business Model</label>
                <Select value={selectedBusinessModel} onValueChange={setSelectedBusinessModel}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select your business model" />
                  </SelectTrigger>
                  <SelectContent>
                    {businessModels.map((model) => (
                      <SelectItem key={model} value={model}>
                        {model.toUpperCase()}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}

          {currentStep === 2 && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">Goals</h3>
              
              <div className="space-y-2">
                <label className="text-sm font-medium">Add your business goals</label>
                <div className="flex space-x-2">
                  <Input
                    placeholder="Enter a goal..."
                    value={newGoal}
                    onChange={(e) => setNewGoal(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && addGoal()}
                  />
                  <Button onClick={addGoal} size="icon">
                    <Plus className="h-4 w-4" />
                  </Button>
                </div>
              </div>

              {goals.length > 0 && (
                <div className="space-y-2">
                  <label className="text-sm font-medium">Current Goals</label>
                  <div className="space-y-2">
                    {goals.map((goal) => (
                      <div key={goal} className="flex items-center justify-between bg-muted p-2 rounded">
                        <span className="text-sm">{goal}</span>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => removeGoal(goal)}
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {currentStep === 3 && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">Connect Services</h3>
              <p className="text-sm text-muted-foreground">
                Connect your services to get better insights (optional for now)
              </p>
              
              <div className="space-y-3">
                {Object.entries(connections).map(([key, connected]) => (
                  <div key={key} className="flex items-center justify-between p-3 border rounded">
                    <div className="flex items-center space-x-3">
                      <div className={`w-3 h-3 rounded-full ${connected ? "bg-green-500" : "bg-gray-300"}`} />
                      <span className="capitalize">{key}</span>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setConnections(prev => ({ ...prev, [key]: !prev[key as keyof typeof prev] }))}
                    >
                      {connected ? "Connected" : "Connect"}
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="flex justify-between pt-4">
            <Button
              variant="outline"
              onClick={handleBack}
              disabled={currentStep === 1}
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </Button>

            {currentStep < 3 ? (
              <Button
                onClick={handleNext}
                disabled={
                  (currentStep === 1 && (!selectedIndustry || !selectedBusinessModel)) ||
                  (currentStep === 2 && goals.length === 0)
                }
              >
                Next
                <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            ) : (
              <Button
                onClick={handleFinish}
                disabled={isLoading}
              >
                {isLoading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Finishing...
                  </>
                ) : (
                  <>
                    <CheckCircle className="h-4 w-4 mr-2" />
                    Finish
                  </>
                )}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}