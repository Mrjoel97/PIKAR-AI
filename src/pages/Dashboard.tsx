import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/hooks/use-auth";
import { api } from "@/convex/_generated/api";
import { useQuery } from "convex/react";
import { useMutation } from "convex/react";
import { motion } from "framer-motion";
import { 
  Bot, 
  BarChart3, 
  Target, 
  Users, 
  Plus,
  Settings,
  TrendingUp,
  Activity,
  Zap,
  LogOut
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { useNavigate } from "react-router";
import { useEffect, useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

export default function Dashboard() {
  const { isLoading, isAuthenticated, user, signOut } = useAuth();
  const navigate = useNavigate();
  const [isSigningOut, setIsSigningOut] = useState(false);
  const [phaseTab, setPhaseTab] = useState<"discovery" | "planning">("discovery");
  const [goalText, setGoalText] = useState("");
  const [signalsText, setSignalsText] = useState("");
  const [runningTransformation, setRunningTransformation] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [initTitle, setInitTitle] = useState("");
  const [initDesc, setInitDesc] = useState("");
  const [initPriority, setInitPriority] = useState<"low" | "medium" | "high" | "urgent">("medium");
  const [initTargetROI, setInitTargetROI] = useState<string>("0.2"); // 20% default
  const [initStartDate, setInitStartDate] = useState<string>("");
  const [initEndDate, setInitEndDate] = useState<string>("");
  const [creatingInitiative, setCreatingInitiative] = useState(false);

  // Add: helper to prefill example inputs for quick testing
  const loadExampleInputs = () => {
    setGoalText("Increase ROI, Improve completion rate, Grow top-of-funnel leads");
    setSignalsText(JSON.stringify({ traffic: 1200, emailOpenRate: 0.21, budget: 5000, teamCapacity: 3 }, null, 2));
    toast("Loaded example goals and signals");
  };

  const businesses = useQuery(api.businesses.getUserBusinesses);

  const runDiagnostic = useMutation(api.diagnostics.run);
  const latestDiagnostic = useQuery(
    api.diagnostics.getLatest,
    businesses && businesses.length > 0
      ? { businessId: businesses[0]._id }
      : "skip" // Use Convex hook sentinel instead of undefined
  );
  const [runningDiag, setRunningDiag] = useState(false);
  const latestDiff = useQuery(
    api.diagnostics.getDiff,
    businesses && businesses.length > 0 ? { businessId: businesses[0]._id } : "skip"
  );

  const initiatives = useQuery(
    api.initiatives.getByBusiness,
    businesses && businesses.length > 0 ? { businessId: businesses[0]._id } : "skip"
  );
  const createInitiative = useMutation(api.initiatives.create);
  const updateInitiativeStatus = useMutation(api.initiatives.updateStatus);

  // Add: Agents list + mutations
  const agents = useQuery(
    api.aiAgents.getByBusiness,
    businesses && businesses.length > 0 ? { businessId: businesses[0]._id } : "skip"
  );
  const toggleAgent = useMutation(api.aiAgents.toggle);
  const seedAgents = useMutation(api.aiAgents.seedEnhancedForBusiness);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      navigate("/auth");
    }
  }, [isLoading, isAuthenticated, navigate]);

  const handleLogout = async () => {
    setIsSigningOut(true);
    try {
      await signOut();
      toast.success("Signed out successfully");
      navigate("/");
    } catch (err) {
      console.error("Sign out failed:", err);
      toast.error("Failed to sign out. Please try again.");
      setIsSigningOut(false);
    }
  };

  const handleRunDiagnostic = async () => {
    if (!businesses || businesses.length === 0) return;
    setRunningDiag(true);
    try {
      await runDiagnostic({
        businessId: businesses[0]._id,
        inputs: { phase: "discovery", goals: [], signals: {} },
      });
      toast.success("Diagnostic completed");
    } catch (e) {
      console.error(e);
      toast.error("Failed to run diagnostic");
    } finally {
      setRunningDiag(false);
    }
  };

  const handleRunTransformation = async () => {
    if (!businesses || businesses.length === 0) return;
    setRunningTransformation(true);
    try {
      // Parse goals (comma-separated) and signals (JSON, optional)
      const goals =
        goalText
          .split(",")
          .map((g) => g.trim())
          .filter((g) => g.length > 0) || [];
      let signals: Record<string, any> = {};
      if (signalsText.trim().length > 0) {
        try {
          signals = JSON.parse(signalsText);
        } catch (e) {
          toast.error("Signals must be valid JSON");
          setRunningTransformation(false);
          return;
        }
      }

      await runDiagnostic({
        businessId: businesses[0]._id,
        inputs: {
          phase: phaseTab,
          goals,
          signals,
        },
      });
      toast.success(`Diagnostic run (${phaseTab}) completed`);
      // Clear inputs for convenience
      setGoalText("");
      setSignalsText("");
    } catch (e) {
      console.error(e);
      toast.error("Failed to run transformation");
    } finally {
      setRunningTransformation(false);
    }
  };

  const handleCreateInitiative = async () => {
    if (!businesses || businesses.length === 0) return;
    // Basic validations
    if (!initTitle.trim()) {
      toast.error("Title is required");
      return;
    }
    if (!initStartDate || !initEndDate) {
      toast.error("Please provide start and end dates");
      return;
    }
    const start = Date.parse(initStartDate);
    const end = Date.parse(initEndDate);
    if (isNaN(start) || isNaN(end)) {
      toast.error("Invalid dates provided");
      return;
    }
    if (end < start) {
      toast.error("End date must be after start date");
      return;
    }
    let target = Number(initTargetROI);
    if (isNaN(target)) {
      toast.error("Target ROI must be a number (e.g., 0.25 for 25%)");
      return;
    }
    setCreatingInitiative(true);
    try {
      await createInitiative({
        title: initTitle.trim(),
        description: initDesc.trim(),
        businessId: businesses[0]._id,
        priority: initPriority,
        targetROI: target,
        startDate: start,
        endDate: end,
      });
      toast.success("Initiative created");
      // reset and close
      setInitTitle("");
      setInitDesc("");
      setInitPriority("medium");
      setInitTargetROI("0.2");
      setInitStartDate("");
      setInitEndDate("");
      setCreateOpen(false);
    } catch (e) {
      console.error(e);
      toast.error("Failed to create initiative");
    } finally {
      setCreatingInitiative(false);
    }
  };

  const handleUpdateStatus = async (id: string, status: "draft" | "active" | "paused" | "completed") => {
    try {
      await updateInitiativeStatus({ id: id as any, status });
      toast.success("Status updated");
    } catch (e) {
      console.error(e);
      toast.error("Failed to update status");
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="neu-inset rounded-xl p-8">
          <Activity className="h-8 w-8 animate-spin text-primary" />
        </div>
      </div>
    );
  }

  if (!isAuthenticated || !user) {
    return null;
  }

  // If user has no businesses, redirect to onboarding
  if (businesses && businesses.length === 0) {
    navigate("/onboarding");
    return null;
  }

  const currentBusiness = businesses?.[0]; // For now, use the first business

  // Add: tier helpers for conditional sections
  const tierOrder = ["solopreneur", "startup", "sme", "enterprise"] as const;
  const tier = (currentBusiness?.tier as (typeof tierOrder)[number]) || undefined;
  const isAtLeast = (level: (typeof tierOrder)[number]) =>
    !!tier && tierOrder.indexOf(tier) >= tierOrder.indexOf(level);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
      className="min-h-screen bg-gradient-to-br from-background via-background to-accent/10"
    >
      {/* Header */}
      <header className="sticky top-0 z-50 backdrop-blur-lg bg-background/80 border-b border-border/50">
        <div className="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-14 md:h-16">
            <div className="flex items-center space-x-4">
              <motion.div 
                className="flex items-center space-x-3 cursor-pointer"
                onClick={() => navigate("/")}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                <div className="neu-raised rounded-xl p-2">
                  <img src="./logo.svg" alt="Pikar AI" className="h-6 w-6" />
                </div>
                <span className="text-lg font-bold tracking-tight">Pikar AI</span>
              </motion.div>
              
              {currentBusiness && (
                <div className="hidden sm:block">
                  <span className="text-sm text-muted-foreground">•</span>
                  <span className="ml-2 text-sm font-medium">{currentBusiness.name}</span>
                </div>
              )}
            </div>
            
            <div className="flex items-center space-x-2 sm:space-x-3">
              <Button 
                variant="ghost" 
                size="sm"
                className="neu-flat rounded-xl"
                onClick={() => navigate("/settings")}
                aria-label="Open settings"
                title="Settings"
              >
                <Settings className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="neu-flat rounded-xl"
                onClick={handleLogout}
                disabled={isSigningOut}
              >
                {isSigningOut ? (
                  <>
                    <Activity className="h-4 w-4 mr-2 animate-spin" />
                    Signing out...
                  </>
                ) : (
                  <>
                    <LogOut className="h-4 w-4 mr-2" />
                    Logout
                  </>
                )}
              </Button>
              <div className="neu-inset rounded-xl p-2">
                <div className="h-6 w-6 bg-primary rounded-lg flex items-center justify-center">
                  <span className="text-xs font-medium text-primary-foreground">
                    {user.name?.charAt(0) || user.email?.charAt(0) || "U"}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-3 sm:px-6 lg:px-8 py-6 sm:py-8">
        {/* Transformation Hub */}
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.05 }}
          className="mb-8"
        >
          <Card className="neu-raised rounded-2xl border-0">
            <CardHeader className="flex items-center justify-between">
              <CardTitle className="text-xl font-semibold">Transformation Hub</CardTitle>
              <div className="flex items-center gap-2">
                {/* New: Load Example button */}
                <Button
                  variant="outline"
                  size="sm"
                  className="neu-flat rounded-xl"
                  onClick={loadExampleInputs}
                  disabled={runningTransformation}
                  aria-label="Load example inputs"
                  title="Load example inputs"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Load Example
                </Button>
                {/* Existing Run button */}
                <Button
                  variant="outline"
                  size="sm"
                  className="neu-flat rounded-xl"
                  onClick={handleRunTransformation}
                  disabled={runningTransformation || !businesses || businesses.length === 0}
                  aria-label="Run transformation diagnostic"
                  title="Run transformation diagnostic"
                >
                  {runningTransformation ? (
                    <>
                      <Activity className="h-4 w-4 mr-2 animate-spin" />
                      Running...
                    </>
                  ) : (
                    <>
                      <Zap className="h-4 w-4 mr-2" />
                      Run
                    </>
                  )}
                </Button>
              </div>
            </CardHeader>
            <CardContent className="p-6 pt-0">
              <Tabs value={phaseTab} onValueChange={(v) => setPhaseTab(v as "discovery" | "planning")}>
                <TabsList>
                  <TabsTrigger value="discovery">Discovery</TabsTrigger>
                  <TabsTrigger value="planning">Planning</TabsTrigger>
                </TabsList>
                <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                  <TabsContent value="discovery" className="md:col-span-2">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="neu-inset rounded-xl p-4">
                        <div className="text-sm font-medium mb-2">Goals (comma separated)</div>
                        <Input
                          placeholder="Increase ROI, Improve completion rate"
                          value={goalText}
                          onChange={(e) => setGoalText(e.target.value)}
                          disabled={runningTransformation}
                        />
                        <p className="text-xs text-muted-foreground mt-1">
                          Example: Grow top-of-funnel leads, Shorten sales cycle
                        </p>
                      </div>
                      <div className="neu-inset rounded-xl p-4">
                        <div className="text-sm font-medium mb-2">Signals (JSON)</div>
                        <Textarea
                          placeholder='{"traffic": 1200, "emailOpenRate": 0.21}'
                          value={signalsText}
                          onChange={(e) => setSignalsText(e.target.value)}
                          disabled={runningTransformation}
                          rows={5}
                        />
                        <p className="text-xs text-muted-foreground mt-1">
                          Optional structured inputs used for Sense/Normalize.
                        </p>
                      </div>
                    </div>
                  </TabsContent>
                  <TabsContent value="planning" className="md:col-span-2">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="neu-inset rounded-xl p-4">
                        <div className="text-sm font-medium mb-2">Refined Goals (comma separated)</div>
                        <Input
                          placeholder="Narrow focus, Select high-ROI workflows"
                          value={goalText}
                          onChange={(e) => setGoalText(e.target.value)}
                          disabled={runningTransformation}
                        />
                        <p className="text-xs text-muted-foreground mt-1">
                          Specify narrowed priorities for the next cycle.
                        </p>
                      </div>
                      <div className="neu-inset rounded-xl p-4">
                        <div className="text-sm font-medium mb-2">Signals (JSON)</div>
                        <Textarea
                          placeholder='{"budget": 5000, "teamCapacity": 3}'
                          value={signalsText}
                          onChange={(e) => setSignalsText(e.target.value)}
                          disabled={runningTransformation}
                          rows={5}
                        />
                        <p className="text-xs text-muted-foreground mt-1">
                          Provide constraints and resource inputs to plan with.
                        </p>
                      </div>
                    </div>
                  </TabsContent>
                </div>
              </Tabs>
            </CardContent>
          </Card>
        </motion.div>

        {/* Quick Stats */}
        <motion.div
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8"
        >
          <Card className="neu-raised rounded-2xl border-0">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Active Agents</p>
                  <p className="text-2xl font-bold">
                    {agents ? agents.filter((a: any) => a.isActive).length : 0}
                  </p>
                </div>
                <div className="neu-inset rounded-xl p-3">
                  <Bot className="h-5 w-5 text-primary" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="neu-raised rounded-2xl border-0">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Recommended Tasks</p>
                  <p className="text-2xl font-bold">
                    {latestDiagnostic ? latestDiagnostic.outputs.tasks.length : 0}
                  </p>
                </div>
                <div className="neu-inset rounded-xl p-3">
                  <Target className="h-5 w-5 text-primary" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="neu-raised rounded-2xl border-0">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">ROI Target</p>
                  <p className="text-2xl font-bold">
                    {latestDiagnostic
                      ? `+${(latestDiagnostic.outputs.kpis.targetROI * 100).toFixed(0)}%`
                      : "+34%"}
                  </p>
                </div>
                <div className="neu-inset rounded-xl p-3">
                  <TrendingUp className="h-5 w-5 text-primary" />
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="neu-raised rounded-2xl border-0">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Time Saved</p>
                  <p className="text-2xl font-bold">156h</p>
                </div>
                <div className="neu-inset rounded-xl p-3">
                  <Zap className="h-5 w-5 text-primary" />
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Main Dashboard Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column */}
          <div className="lg:col-span-2 space-y-6">
            {/* Active Initiatives */}
            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.2 }}
            >
              <Card className="neu-raised rounded-2xl border-0">
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle className="text-xl font-semibold">Active Initiatives</CardTitle>
                  <Button 
                    size="sm" 
                    className="neu-flat rounded-xl"
                    onClick={() => setCreateOpen(true)}
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    New Initiative
                  </Button>
                </CardHeader>
                <CardContent className="p-6 pt-0">
                  <div className="space-y-4">
                    {!initiatives ? (
                      <div className="neu-inset rounded-xl p-4 text-sm text-muted-foreground">
                        Loading initiatives...
                      </div>
                    ) : initiatives.length === 0 ? (
                      <div className="neu-inset rounded-xl p-4 text-sm">
                        No initiatives yet. Create your first one to get started.
                      </div>
                    ) : (
                      initiatives.map((initiative: any) => {
                        const progress = Math.round((initiative.metrics?.completionRate ?? 0) * 100);
                        return (
                          <div key={initiative._id} className="neu-inset rounded-xl p-4">
                            <div className="flex items-center justify-between mb-2">
                              <div className="min-w-0">
                                <h4 className="font-medium truncate">{initiative.title}</h4>
                                <div className="flex items-center gap-2 mt-1">
                                  <Badge variant="secondary" className="capitalize">
                                    {initiative.status}
                                  </Badge>
                                  <Badge className="capitalize">{initiative.priority}</Badge>
                                </div>
                              </div>
                              <div className="flex items-center gap-2">
                                <Select
                                  value={initiative.status}
                                  onValueChange={(val) =>
                                    handleUpdateStatus(
                                      initiative._id,
                                      val as "draft" | "active" | "paused" | "completed"
                                    )
                                  }
                                >
                                  <SelectTrigger className="w-[140px] neu-flat rounded-xl">
                                    <SelectValue placeholder="Set status" />
                                  </SelectTrigger>
                                  <SelectContent>
                                    <SelectItem value="draft">Draft</SelectItem>
                                    <SelectItem value="active">Active</SelectItem>
                                    <SelectItem value="paused">Paused</SelectItem>
                                    <SelectItem value="completed">Completed</SelectItem>
                                  </SelectContent>
                                </Select>
                              </div>
                            </div>
                            <div className="w-full bg-muted rounded-full h-2">
                              <div 
                                className="bg-primary h-2 rounded-full transition-all duration-300"
                                style={{ width: `${progress}%` }}
                              />
                            </div>
                          </div>
                        );
                      })
                    )}
                  </div>
                </CardContent>
              </Card>
            </motion.div>

            {/* Performance Analytics */}
            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.3 }}
            >
              <Card className="neu-raised rounded-2xl border-0">
                <CardHeader>
                  <CardTitle className="text-xl font-semibold flex items-center">
                    <BarChart3 className="h-5 w-5 mr-2" />
                    Performance Analytics
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-6 pt-0">
                  <div className="h-64 neu-inset rounded-xl flex items-center justify-center">
                    <p className="text-muted-foreground">Analytics chart will be displayed here</p>
                  </div>
                </CardContent>
              </Card>
            </motion.div>

            {/* Add: Tiered sections for Solopreneur */}
            {tier === "solopreneur" && (
              <>
                <motion.div
                  initial={{ y: 20, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ duration: 0.6, delay: 0.35 }}
                >
                  <Card className="neu-raised rounded-2xl border-0">
                    <CardHeader>
                      <CardTitle className="text-xl font-semibold">Quick Start Templates</CardTitle>
                    </CardHeader>
                    <CardContent className="p-6 pt-0">
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        {[
                          { name: "Content Calendar (30d)", desc: "Plan a month of posts fast" },
                          { name: "Lead Magnet", desc: "Build a simple lead capture funnel" },
                          { name: "Welcome Email", desc: "Automated intro to new subscribers" },
                          { name: "Offer Landing Page", desc: "Launch a single offer quickly" },
                        ].map((t) => (
                          <div key={t.name} className="neu-inset rounded-xl p-4">
                            <div className="flex items-center justify-between">
                              <div>
                                <p className="font-medium text-sm">{t.name}</p>
                                <p className="text-xs text-muted-foreground">{t.desc}</p>
                              </div>
                              <Button size="sm" className="neu-flat rounded-xl">Use</Button>
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>

                <motion.div
                  initial={{ y: 20, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ duration: 0.6, delay: 0.4 }}
                >
                  <Card className="neu-raised rounded-2xl border-0">
                    <CardHeader>
                      <CardTitle className="text-xl font-semibold">Simple Analytics</CardTitle>
                    </CardHeader>
                    <CardContent className="p-6 pt-0">
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        {[
                          { label: "This Week Posts", value: "8" },
                          { label: "Leads Captured", value: "32" },
                          { label: "CTR", value: "3.4%" },
                        ].map((m) => (
                          <div key={m.label} className="neu-inset rounded-xl p-4">
                            <div className="text-xs text-muted-foreground">{m.label}</div>
                            <div className="text-xl font-semibold">{m.value}</div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>

                <motion.div
                  initial={{ y: 20, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ duration: 0.6, delay: 0.45 }}
                >
                  <Card className="neu-raised rounded-2xl border-0">
                    <CardHeader>
                      <CardTitle className="text-xl font-semibold">Weekly Tips</CardTitle>
                    </CardHeader>
                    <CardContent className="p-6 pt-0">
                      <ul className="space-y-2 text-sm">
                        {[
                          "Repurpose a top post into a short email to your list.",
                          "Batch-create 5 hooks for your next 3 posts.",
                          "Cross-post content to one new channel for discovery.",
                        ].map((tip, i) => (
                          <li key={i} className="neu-inset rounded-xl p-3">{tip}</li>
                        ))}
                      </ul>
                    </CardContent>
                  </Card>
                </motion.div>
              </>
            )}

            {/* Add: Tiered sections for Startup */}
            {tier === "startup" && (
              <>
                <motion.div
                  initial={{ y: 20, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ duration: 0.6, delay: 0.35 }}
                >
                  <Card className="neu-raised rounded-2xl border-0">
                    <CardHeader>
                      <CardTitle className="text-xl font-semibold">Growth Levers</CardTitle>
                    </CardHeader>
                    <CardContent className="p-6 pt-0">
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        {[
                          { name: "Outbound Sequences", hint: "Warm + cold" },
                          { name: "Content Sprints", hint: "Topical focus" },
                          { name: "Referral Loop", hint: "Lightweight incentives" },
                        ].map((g) => (
                          <div key={g.name} className="neu-inset rounded-xl p-4">
                            <div className="font-medium text-sm">{g.name}</div>
                            <div className="text-xs text-muted-foreground">{g.hint}</div>
                            <div className="mt-3">
                              <Button variant="outline" size="sm" className="neu-flat rounded-xl">Open</Button>
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>

                <motion.div
                  initial={{ y: 20, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ duration: 0.6, delay: 0.4 }}
                >
                  <Card className="neu-raised rounded-2xl border-0">
                    <CardHeader>
                      <CardTitle className="text-xl font-semibold">Experiments (A/B)</CardTitle>
                    </CardHeader>
                    <CardContent className="p-6 pt-0">
                      <div className="space-y-3">
                        {[
                          { name: "Landing Page CTA", status: "Running", uplift: "+8.2%" },
                          { name: "Email Subject Line", status: "Draft", uplift: "-" },
                          { name: "Ad Creative Variant", status: "Queued", uplift: "-" },
                        ].map((e, i) => (
                          <div key={i} className="neu-inset rounded-xl p-3 flex items-center justify-between">
                            <div>
                              <p className="font-medium text-sm">{e.name}</p>
                              <p className="text-xs text-muted-foreground">{e.status}</p>
                            </div>
                            <div className="text-xs text-muted-foreground">{e.uplift}</div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>

                <motion.div
                  initial={{ y: 20, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ duration: 0.6, delay: 0.45 }}
                >
                  <Card className="neu-raised rounded-2xl border-0">
                    <CardHeader>
                      <CardTitle className="text-xl font-semibold">Team Preview</CardTitle>
                    </CardHeader>
                    <CardContent className="p-6 pt-0">
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        {[
                          { role: "Marketing", members: 3 },
                          { role: "Sales", members: 2 },
                          { role: "Ops", members: 1 },
                          { role: "Product", members: 2 },
                        ].map((r, i) => (
                          <div key={i} className="neu-inset rounded-xl p-4">
                            <div className="flex items-center justify-between">
                              <div className="font-medium text-sm">{r.role}</div>
                              <div className="text-xs text-muted-foreground">{r.members} members</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              </>
            )}

            {/* Add: Tiered sections for SME */}
            {tier === "sme" && (
              <>
                <motion.div
                  initial={{ y: 20, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ duration: 0.6, delay: 0.35 }}
                >
                  <Card className="neu-raised rounded-2xl border-0">
                    <CardHeader>
                      <CardTitle className="text-xl font-semibold">Multi-Brand Overview</CardTitle>
                    </CardHeader>
                    <CardContent className="p-6 pt-0">
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        {[
                          { name: "Core Brand", status: "Active", kpi: "+18%" },
                          { name: "Product Line A", status: "Active", kpi: "+9%" },
                          { name: "Experimental", status: "Paused", kpi: "—" },
                        ].map((b) => (
                          <div key={b.name} className="neu-inset rounded-xl p-4">
                            <div className="flex items-center justify-between">
                              <div>
                                <p className="font-medium text-sm">{b.name}</p>
                                <p className="text-xs text-muted-foreground">{b.status}</p>
                              </div>
                              <Badge variant={b.status === "Paused" ? "secondary" : "default"}>
                                {b.kpi}
                              </Badge>
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>

                <motion.div
                  initial={{ y: 20, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ duration: 0.6, delay: 0.4 }}
                >
                  <Card className="neu-raised rounded-2xl border-0">
                    <CardHeader>
                      <CardTitle className="text-xl font-semibold">Governance & Approvals</CardTitle>
                    </CardHeader>
                    <CardContent className="p-6 pt-0">
                      <div className="space-y-3">
                        {[
                          { item: "Campaign: Spring Promo", type: "Marketing", due: "Today" },
                          { item: "Workflow: Lead Scoring v2", type: "Sales", due: "Tomorrow" },
                          { item: "Content: Blog #42", type: "Content", due: "Fri" },
                        ].map((row, i) => (
                          <div key={i} className="neu-inset rounded-xl p-3 flex items-center justify-between">
                            <div>
                              <p className="font-medium text-sm">{row.item}</p>
                              <p className="text-xs text-muted-foreground">
                                {row.type} • Due {row.due}
                              </p>
                            </div>
                            <div className="flex items-center gap-2">
                              <Button variant="outline" size="sm" className="neu-flat rounded-xl">Review</Button>
                              <Button size="sm" className="neu-flat rounded-xl">Approve</Button>
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>

                <motion.div
                  initial={{ y: 20, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ duration: 0.6, delay: 0.45 }}
                >
                  <Card className="neu-raised rounded-2xl border-0">
                    <CardHeader>
                      <CardTitle className="text-xl font-semibold">Compliance Status</CardTitle>
                    </CardHeader>
                    <CardContent className="p-6 pt-0">
                      <div className="neu-inset rounded-xl p-4">
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="text-sm font-medium">Policy Alignment</p>
                            <p className="text-xs text-muted-foreground">Marketing & Data Handling</p>
                          </div>
                          <Badge variant="secondary">Pass</Badge>
                        </div>
                        <div className="mt-3 grid grid-cols-1 sm:grid-cols-3 gap-3 text-sm">
                          <div className="neu-flat rounded-lg p-3">
                            <div className="text-muted-foreground">PII Checks</div>
                            <div className="font-semibold">OK</div>
                          </div>
                          <div className="neu-flat rounded-lg p-3">
                            <div className="text-muted-foreground">Content Policy</div>
                            <div className="font-semibold">OK</div>
                          </div>
                          <div className="neu-flat rounded-lg p-3">
                            <div className="text-muted-foreground">Export Readiness</div>
                            <div className="font-semibold">Ready</div>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              </>
            )}

            {/* Add: Tiered sections for Enterprise */}
            {tier === "enterprise" && (
              <>
                <motion.div
                  initial={{ y: 20, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ duration: 0.6, delay: 0.35 }}
                >
                  <Card className="neu-raised rounded-2xl border-0">
                    <CardHeader>
                      <CardTitle className="text-xl font-semibold">Compliance & Risk</CardTitle>
                    </CardHeader>
                    <CardContent className="p-6 pt-0">
                      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
                        {[
                          { label: "Risk Score", value: "Low", tone: "text-green-600" },
                          { label: "Incidents (30d)", value: "0", tone: "text-foreground" },
                          { label: "Policy Drift", value: "Stable", tone: "text-green-600" },
                          { label: "Audit Coverage", value: "98%", tone: "text-foreground" },
                        ].map((m) => (
                          <div key={m.label} className="neu-inset rounded-xl p-4">
                            <div className="text-xs text-muted-foreground">{m.label}</div>
                            <div className={`text-xl font-semibold ${m.tone}`}>{m.value}</div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>

                <motion.div
                  initial={{ y: 20, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ duration: 0.6, delay: 0.4 }}
                >
                  <Card className="neu-raised rounded-2xl border-0">
                    <CardHeader>
                      <CardTitle className="text-xl font-semibold">Admin Console (Preview)</CardTitle>
                    </CardHeader>
                    <CardContent className="p-6 pt-0">
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                        {[
                          { name: "Users & Roles", desc: "Role-based access" },
                          { name: "Data Regions", desc: "Geo storage prefs" },
                          { name: "Model Registry", desc: "Models & params" },
                        ].map((tile) => (
                          <div key={tile.name} className="neu-inset rounded-xl p-4">
                            <div className="font-medium text-sm">{tile.name}</div>
                            <div className="text-xs text-muted-foreground">{tile.desc}</div>
                            <div className="mt-3">
                              <Button variant="outline" size="sm" className="neu-flat rounded-xl">Open</Button>
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>

                <motion.div
                  initial={{ y: 20, opacity: 0 }}
                  animate={{ y: 0, opacity: 1 }}
                  transition={{ duration: 0.6, delay: 0.45 }}
                >
                  <Card className="neu-raised rounded-2xl border-0">
                    <CardHeader>
                      <CardTitle className="text-xl font-semibold">Audit & Exports</CardTitle>
                    </CardHeader>
                    <CardContent className="p-6 pt-0">
                      <div className="flex flex-wrap gap-3">
                        <Button variant="outline" className="neu-flat rounded-xl">
                          Export Audit Log
                        </Button>
                        <Button variant="outline" className="neu-flat rounded-xl">
                          Download Data Map
                        </Button>
                        <Button className="neu-flat rounded-xl">
                          Generate Compliance Report
                        </Button>
                      </div>
                      <p className="text-xs text-muted-foreground mt-3">
                        Exports reflect current configurations and latest diagnostic targets.
                      </p>
                    </CardContent>
                  </Card>
                </motion.div>
              </>
            )}
          </div>

          {/* Right Column */}
          <div className="space-y-6">
            {/* AI Agents Status */}
            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.4 }}
            >
              <Card className="neu-raised rounded-2xl border-0">
                <CardHeader>
                  <CardTitle className="text-xl font-semibold flex items-center">
                    <Bot className="h-5 w-5 mr-2" />
                    AI Agents
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-6 pt-0">
                  <div className="flex items-center justify-between mb-3">
                    <div className="text-sm text-muted-foreground">
                      {agents ? `${agents.length} total • ${agents.filter((a: any) => a.isActive).length} active` : "Loading..."}
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      className="neu-flat rounded-xl"
                      disabled={!businesses || businesses.length === 0}
                      onClick={async () => {
                        if (!businesses || businesses.length === 0) return;
                        try {
                          await seedAgents({ businessId: businesses[0]._id });
                          toast.success("Enhanced agents seeded");
                        } catch (e) {
                          console.error(e);
                          toast.error("Failed to seed agents");
                        }
                      }}
                    >
                      <Plus className="h-4 w-4 mr-2" />
                      Seed Enhanced Agents
                    </Button>
                  </div>

                  <div className="space-y-3">
                    {!agents ? (
                      <div className="neu-inset rounded-xl p-3 text-sm text-muted-foreground">
                        Loading agents...
                      </div>
                    ) : agents.length === 0 ? (
                      <div className="neu-inset rounded-xl p-3 text-sm">
                        No agents yet. Click "Seed Enhanced Agents" to create a baseline set.
                      </div>
                    ) : (
                      agents.map((agent: any) => (
                        <div key={agent._id} className="neu-inset rounded-xl p-3">
                          <div className="flex items-center justify-between gap-3">
                            <div className="min-w-0">
                              <p className="text-sm font-medium truncate">{agent.name}</p>
                              <p className="text-xs text-muted-foreground">
                                {agent.type.replaceAll("_", " ")} • {agent.performance?.tasksCompleted ?? 0} tasks
                              </p>
                            </div>
                            <div className="flex items-center gap-3">
                              <div
                                className={`h-2 w-2 rounded-full ${
                                  agent.isActive ? "bg-green-500" : "bg-gray-400"
                                }`}
                                title={agent.isActive ? "Active" : "Inactive"}
                                aria-label={agent.isActive ? "Active" : "Inactive"}
                              />
                              <Button
                                variant="outline"
                                size="sm"
                                className="neu-flat rounded-xl"
                                onClick={async () => {
                                  try {
                                    await toggleAgent({ id: agent._id, isActive: !agent.isActive });
                                    toast.success(agent.isActive ? "Agent deactivated" : "Agent activated");
                                  } catch (e) {
                                    console.error(e);
                                    toast.error("Failed to toggle agent");
                                  }
                                }}
                              >
                                {agent.isActive ? "Deactivate" : "Activate"}
                              </Button>
                            </div>
                          </div>
                        </div>
                      ))
                    )}
                  </div>

                  <Button 
                    variant="outline" 
                    className="w-full mt-4 neu-flat rounded-xl"
                    onClick={() => navigate("/agents")}
                  >
                    Manage Agents
                  </Button>
                </CardContent>
              </Card>
            </motion.div>

            {/* Diagnostic Recommendations (add diff surface) */}
            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.45 }}
            >
              <Card className="neu-raised rounded-2xl border-0">
                <CardHeader className="flex items-center justify-between">
                  <CardTitle className="text-xl font-semibold flex items-center">
                    <Zap className="h-5 w-5 mr-2" />
                    Diagnostic Recommendations
                  </CardTitle>
                  <Button
                    variant="outline"
                    size="sm"
                    className="neu-flat rounded-xl"
                    onClick={handleRunDiagnostic}
                    disabled={runningDiag}
                    aria-label="Run diagnostic"
                    title="Run diagnostic"
                  >
                    {runningDiag ? (
                      <>
                        <Activity className="h-4 w-4 mr-2 animate-spin" />
                        Running...
                      </>
                    ) : (
                      <>
                        <Plus className="h-4 w-4 mr-2" />
                        Re-run
                      </>
                    )}
                  </Button>
                </CardHeader>
                <CardContent className="p-6 pt-0 space-y-4">
                  {latestDiff && (
                    <div className="neu-inset rounded-xl p-4">
                      <h4 className="font-medium mb-2">Changes since last run</h4>
                      <div className="grid grid-cols-2 gap-3 text-sm">
                        <div className="neu-flat rounded-lg p-3">
                          <div className="text-muted-foreground">Δ Target ROI</div>
                          <div className={`font-semibold ${latestDiff.kpisDelta.targetROI >= 0 ? "text-green-600" : "text-red-600"}`}>
                            {(latestDiff.kpisDelta.targetROI * 100).toFixed(1)}%
                          </div>
                        </div>
                        <div className="neu-flat rounded-lg p-3">
                          <div className="text-muted-foreground">Δ Completion Rate</div>
                          <div className={`font-semibold ${latestDiff.kpisDelta.targetCompletionRate >= 0 ? "text-green-600" : "text-red-600"}`}>
                            {(latestDiff.kpisDelta.targetCompletionRate * 100).toFixed(1)}%
                          </div>
                        </div>
                      </div>
                      <div className="mt-3 grid grid-cols-1 gap-2">
                        {latestDiff.tasks.added.length > 0 && (
                          <div className="text-xs">
                            <span className="font-medium">Tasks added:</span>{" "}
                            {latestDiff.tasks.added.map((t: any) => t.title).join(", ")}
                          </div>
                        )}
                        {latestDiff.tasks.removed.length > 0 && (
                          <div className="text-xs text-muted-foreground">
                            <span className="font-medium">Tasks removed:</span>{" "}
                            {latestDiff.tasks.removed.map((t: any) => t.title).join(", ")}
                          </div>
                        )}
                        {latestDiff.workflows.added.length > 0 && (
                          <div className="text-xs">
                            <span className="font-medium">Workflows added:</span>{" "}
                            {latestDiff.workflows.added.map((w: any) => w.name).join(", ")}
                          </div>
                        )}
                        {latestDiff.workflows.removed.length > 0 && (
                          <div className="text-xs text-muted-foreground">
                            <span className="font-medium">Workflows removed:</span>{" "}
                            {latestDiff.workflows.removed.map((w: any) => w.name).join(", ")}
                          </div>
                        )}
                      </div>
                      <div className="text-[10px] text-muted-foreground mt-2">
                        Compared {new Date(latestDiff.previousRunAt).toLocaleString()} → {new Date(latestDiff.currentRunAt).toLocaleString()}
                      </div>
                    </div>
                  )}

                  {!latestDiagnostic ? (
                    <div className="neu-inset rounded-xl p-4 text-sm text-muted-foreground">
                      No diagnostic available yet. Click "Re-run" to generate recommendations.
                    </div>
                  ) : (
                    <>
                      <div className="neu-inset rounded-xl p-4">
                        <h4 className="font-medium mb-2">KPI Targets</h4>
                        <div className="grid grid-cols-2 gap-3 text-sm">
                          <div className="neu-flat rounded-lg p-3">
                            <div className="text-muted-foreground">Target ROI</div>
                            <div className="font-semibold">
                              {(latestDiagnostic.outputs.kpis.targetROI * 100).toFixed(0)}%
                            </div>
                          </div>
                          <div className="neu-flat rounded-lg p-3">
                            <div className="text-muted-foreground">Completion Rate</div>
                            <div className="font-semibold">
                              {(latestDiagnostic.outputs.kpis.targetCompletionRate * 100).toFixed(0)}%
                            </div>
                          </div>
                        </div>
                      </div>

                      <div className="space-y-3">
                        {(["daily", "weekly", "monthly"] as const).map((freq) => {
                          const items = latestDiagnostic.outputs.tasks.filter((t: any) => t.frequency === freq);
                          if (items.length === 0) return null;
                          return (
                            <div key={freq} className="neu-inset rounded-xl p-4">
                              <h4 className="font-medium capitalize mb-2">{freq} Tasks</h4>
                              <ul className="space-y-2">
                                {items.map((t: any, idx: number) => (
                                  <li key={idx} className="text-sm">
                                    <span className="font-medium">{t.title}</span>
                                    <span className="text-muted-foreground"> — {t.description}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          );
                        })}
                      </div>

                      <div className="neu-inset rounded-xl p-4">
                        <h4 className="font-medium mb-2">Recommended Workflows</h4>
                        <ul className="space-y-2">
                          {latestDiagnostic.outputs.workflows.map((w: any, idx: number) => (
                            <li key={idx} className="text-sm flex items-center justify-between">
                              <div>
                                <span className="font-medium">{w.name}</span>
                                <span className="text-muted-foreground"> — {w.agentType.replaceAll("_", " ")}</span>
                              </div>
                              <span className="text-xs text-muted-foreground">Template: {w.templateId}</span>
                            </li>
                          ))}
                        </ul>
                      </div>

                      <div className="text-xs text-muted-foreground">
                        Last Run: {new Date(latestDiagnostic.runAt).toLocaleString()}
                      </div>
                    </>
                  )}
                </CardContent>
              </Card>
            </motion.div>

            {/* Recent Activity */}
            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.5 }}
            >
              <Card className="neu-raised rounded-2xl border-0">
                <CardHeader>
                  <CardTitle className="text-xl font-semibold flex items-center">
                    <Activity className="h-5 w-5 mr-2" />
                    Recent Activity
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-6 pt-0">
                  <div className="space-y-3">
                    {[
                      { action: "Content created", time: "2 min ago", agent: "Content Creator" },
                      { action: "Lead qualified", time: "15 min ago", agent: "Sales Intelligence" },
                      { action: "Report generated", time: "1 hour ago", agent: "Analytics Bot" },
                      { action: "Task completed", time: "2 hours ago", agent: "Operations" }
                    ].map((activity, index) => (
                      <div key={index} className="neu-inset rounded-xl p-3">
                        <p className="text-sm font-medium">{activity.action}</p>
                        <div className="flex items-center justify-between mt-1">
                          <p className="text-xs text-muted-foreground">{activity.agent}</p>
                          <p className="text-xs text-muted-foreground">{activity.time}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          </div>
        </div>

        <Dialog open={createOpen} onOpenChange={setCreateOpen}>
          <DialogContent className="rounded-2xl">
            <DialogHeader>
              <DialogTitle>Create Initiative</DialogTitle>
            </DialogHeader>
            <div className="grid gap-4">
              <div className="space-y-2">
                <Label htmlFor="init-title">Title</Label>
                <Input
                  id="init-title"
                  placeholder="e.g., Q4 Marketing Campaign"
                  value={initTitle}
                  onChange={(e) => setInitTitle(e.target.value)}
                  disabled={creatingInitiative}
                  className="neu-inset rounded-xl"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="init-desc">Description</Label>
                <Textarea
                  id="init-desc"
                  placeholder="Briefly describe the initiative goals and scope"
                  value={initDesc}
                  onChange={(e) => setInitDesc(e.target.value)}
                  disabled={creatingInitiative}
                  rows={4}
                  className="neu-inset rounded-xl"
                />
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label>Priority</Label>
                  <Select
                    value={initPriority}
                    onValueChange={(v) =>
                      setInitPriority(v as "low" | "medium" | "high" | "urgent")
                    }
                  >
                    <SelectTrigger className="neu-inset rounded-xl">
                      <SelectValue placeholder="Select priority" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="low">Low</SelectItem>
                      <SelectItem value="medium">Medium</SelectItem>
                      <SelectItem value="high">High</SelectItem>
                      <SelectItem value="urgent">Urgent</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="init-roi">Target ROI (0.0 - 1.0)</Label>
                  <Input
                    id="init-roi"
                    placeholder="0.2 for 20%"
                    value={initTargetROI}
                    onChange={(e) => setInitTargetROI(e.target.value)}
                    disabled={creatingInitiative}
                    className="neu-inset rounded-xl"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Dates</Label>
                  <div className="grid grid-cols-2 gap-2">
                    <Input
                      type="date"
                      value={initStartDate}
                      onChange={(e) => setInitStartDate(e.target.value)}
                      disabled={creatingInitiative}
                      className="neu-inset rounded-xl"
                    />
                    <Input
                      type="date"
                      value={initEndDate}
                      onChange={(e) => setInitEndDate(e.target.value)}
                      disabled={creatingInitiative}
                      className="neu-inset rounded-xl"
                    />
                  </div>
                </div>
              </div>
            </div>
            <DialogFooter className="gap-2">
              <Button
                variant="outline"
                onClick={() => setCreateOpen(false)}
                disabled={creatingInitiative}
                className="neu-flat rounded-xl"
              >
                Cancel
              </Button>
              <Button
                onClick={handleCreateInitiative}
                disabled={creatingInitiative}
                className="neu-raised rounded-xl"
              >
                {creatingInitiative ? (
                  <span className="inline-flex items-center">
                    <Activity className="mr-2 h-4 w-4 animate-spin" />
                    Creating...
                  </span>
                ) : (
                  <>
                    <Plus className="mr-2 h-4 w-4" />
                    Create
                  </>
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </main>
    </motion.div>
  );
}