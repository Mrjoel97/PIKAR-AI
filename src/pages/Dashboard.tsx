import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { useAuth } from "@/hooks/use-auth";
import { api } from "@/convex/_generated/api";
import { Id } from "@/convex/_generated/dataModel";
import { useQuery, useMutation, useAction } from "convex/react";
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
  LogOut,
  Workflow,
  Eye,
  ArrowUp,
  ArrowDown,
  Pause,
  RotateCcw
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { useNavigate } from "react-router";
import { useEffect, useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Play } from "lucide-react";

export default function Dashboard() {
  const { user, isLoading, isAuthenticated, signOut } = useAuth();
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
  const [selectedWorkspace, setSelectedWorkspace] = useState<any>(null);
  const [showInitiativeModal, setShowInitiativeModal] = useState(false);
  const [showAgentConfig, setShowAgentConfig] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState<any>(null);
  const [seedingAgents, setSeedingAgents] = useState(false);
  const [togglingAgent, setTogglingAgent] = useState<string | null>(null);

  // Workflow states
  const [showWorkflowModal, setShowWorkflowModal] = useState(false);
  const [showTemplateGallery, setShowTemplateGallery] = useState(false);
  const [showWorkflowBuilder, setShowWorkflowBuilder] = useState(false);
  const [showWorkflowRuns, setShowWorkflowRuns] = useState(false);
  const [selectedWorkflow, setSelectedWorkflow] = useState<any>(null);
  const [selectedRun, setSelectedRun] = useState<any>(null);
  const [runningWorkflow, setRunningWorkflow] = useState<string | null>(null);
  const [seedingTemplates, setSeedingTemplates] = useState(false);

  // Add: Agent Config dialog state
  const [agentConfigOpen, setAgentConfigOpen] = useState(false);
  const [agentBeingConfigured, setAgentBeingConfigured] = useState<any | null>(null);
  const [cfgModel, setCfgModel] = useState<string>("");
  const [cfgParamsJSON, setCfgParamsJSON] = useState<string>("{}");
  const [cfgTriggersCSV, setCfgTriggersCSV] = useState<string>("");
  const [savingAgentConfig, setSavingAgentConfig] = useState(false);

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
  // Add: update config mutation
  const updateAgentConfig = useMutation(api.aiAgents.updateConfig);

  // Workflow queries and mutations
  const workflows = useQuery(
    api.workflows.listWorkflows,
    selectedWorkspace ? { businessId: selectedWorkspace._id } : "skip"
  );
  const templates = useQuery(api.workflows.listTemplates);
  const workflowRuns = useQuery(
    api.workflows.listWorkflowRuns,
    selectedWorkflow ? { workflowId: selectedWorkflow._id } : "skip"
  );
  const selectedRunData = useQuery(
    api.workflows.getWorkflowRun,
    selectedRun ? { runId: selectedRun._id } : "skip"
  );

  const createWorkflow = useMutation(api.workflows.createWorkflow);
  const createFromTemplate = useMutation(api.workflows.createFromTemplate);
  const runWorkflow = useAction(api.workflows.runWorkflow);
  const toggleWorkflow = useMutation(api.workflows.toggleWorkflow);
  const seedTemplates = useMutation(api.workflows.seedTemplates);
  const approveRunStep = useMutation(api.workflows.approveRunStep);

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

  // Workflow handlers
  const handleCreateWorkflow = async (data: any) => {
    if (!selectedWorkspace || !user) return;
    
    try {
      await createWorkflow({
        businessId: selectedWorkspace._id,
        name: data.name,
        description: data.description,
        trigger: data.trigger,
        triggerConfig: data.triggerConfig || {},
        approvalPolicy: data.approvalPolicy || { type: "none", approvers: [] },
        associatedAgentIds: data.associatedAgentIds || [],
        createdBy: user._id
      });
      toast.success("Workflow created successfully");
      setShowWorkflowModal(false);
    } catch (error) {
      toast.error("Failed to create workflow");
    }
  };

  const handleCreateFromTemplate = async (templateId: string) => {
    if (!selectedWorkspace || !user) return;
    
    try {
      await createFromTemplate({
        businessId: selectedWorkspace._id,
        templateId: templateId as Id<"workflowTemplates">,
        createdBy: user._id
      });
      toast.success("Workflow created from template");
      setShowTemplateGallery(false);
    } catch (error) {
      toast.error("Failed to create workflow from template");
    }
  };

  const handleRunWorkflow = async (workflowId: string, dryRun = false) => {
    if (!user) return;
    
    setRunningWorkflow(workflowId);
    try {
      await runWorkflow({
        workflowId: workflowId as Id<"workflows">,
        startedBy: user._id,
        dryRun
      });
      toast.success(dryRun ? "Dry run started" : "Workflow started");
    } catch (error) {
      toast.error("Failed to run workflow");
    } finally {
      setRunningWorkflow(null);
    }
  };

  const handleToggleWorkflow = async (workflowId: string, isActive: boolean) => {
    try {
      await toggleWorkflow({
        workflowId: workflowId as Id<"workflows">,
        isActive
      });
      toast.success(`Workflow ${isActive ? "activated" : "deactivated"}`);
    } catch (error) {
      toast.error("Failed to toggle workflow");
    }
  };

  const handleSeedTemplates = async () => {
    setSeedingTemplates(true);
    try {
      const count = await seedTemplates({});
      toast.success(`Seeded ${count} workflow templates`);
    } catch (error) {
      toast.error("Failed to seed templates");
    } finally {
      setSeedingTemplates(false);
    }
  };

  const handleApproveStep = async (runStepId: string, approved: boolean) => {
    try {
      await approveRunStep({
        runStepId: runStepId as Id<"workflowRunSteps">,
        approved,
        note: approved ? "Approved via dashboard" : "Rejected via dashboard"
      });
      toast.success(approved ? "Step approved" : "Step rejected");
    } catch (error) {
      toast.error("Failed to process approval");
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
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 dark:from-slate-900 dark:via-slate-800 dark:to-slate-900">
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
      <main className="container mx-auto px-6 py-8">
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

          {/* Right Column - Enhanced with Workflows */}
          <div className="lg:col-span-2 space-y-8">
            {/* Workflows Section */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
            >
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
                        <Workflow className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                      </div>
                      <div>
                        <CardTitle>Orchestration & Workflows</CardTitle>
                        <CardDescription>
                          Automate complex business processes with AI agents
                        </CardDescription>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setShowTemplateGallery(true)}
                      >
                        <Eye className="h-4 w-4" />
                        Templates
                      </Button>
                      <Button
                        size="sm"
                        onClick={() => setShowWorkflowModal(true)}
                      >
                        <Plus className="h-4 w-4" />
                        Create Workflow
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {/* Workflow Stats */}
                    <div className="grid grid-cols-3 gap-4">
                      <div className="text-center p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
                        <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                          {workflows?.length || 0}
                        </div>
                        <div className="text-sm text-muted-foreground">Active Workflows</div>
                      </div>
                      <div className="text-center p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
                        <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                          {workflows?.reduce((sum, w) => sum + w.completedRuns, 0) || 0}
                        </div>
                        <div className="text-sm text-muted-foreground">Completed Runs</div>
                      </div>
                      <div className="text-center p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                        <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                          {templates?.length || 0}
                        </div>
                        <div className="text-sm text-muted-foreground">Templates</div>
                      </div>
                    </div>

                    {/* Workflow List */}
                    <div className="space-y-3">
                      {workflows?.map((workflow) => (
                        <div
                          key={workflow._id}
                          className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50 transition-colors"
                        >
                          <div className="flex items-center gap-3">
                            <div className={`w-3 h-3 rounded-full ${workflow.isActive ? 'bg-green-500' : 'bg-gray-400'}`} />
                            <div>
                              <div className="font-medium">{workflow.name}</div>
                              <div className="text-sm text-muted-foreground">
                                {workflow.trigger.replace(/_/g, " ")} • {workflow.runCount} runs
                                {workflow.lastRunStatus && (
                                  <span className={`ml-2 px-2 py-1 text-xs rounded-full ${
                                    workflow.lastRunStatus === "completed" ? "bg-green-100 text-green-700" :
                                    workflow.lastRunStatus === "failed" ? "bg-red-100 text-red-700" :
                                    "bg-yellow-100 text-yellow-700"
                                  }`}>
                                    {workflow.lastRunStatus}
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => {
                                setSelectedWorkflow(workflow);
                                setShowWorkflowRuns(true);
                              }}
                            >
                              <Eye className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleRunWorkflow(workflow._id)}
                              disabled={runningWorkflow === workflow._id}
                            >
                              {runningWorkflow === workflow._id ? (
                                <RotateCcw className="h-4 w-4 animate-spin" />
                              ) : (
                                <Play className="h-4 w-4" />
                              )}
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleToggleWorkflow(workflow._id, !workflow.isActive)}
                            >
                              {workflow.isActive ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                            </Button>
                          </div>
                        </div>
                      ))}
                      
                      {(!workflows || workflows.length === 0) && (
                        <div className="text-center py-8 text-muted-foreground">
                          <Workflow className="h-12 w-12 mx-auto mb-4 opacity-50" />
                          <p>No workflows yet. Create one from a template or start from scratch.</p>
                          <div className="flex justify-center gap-2 mt-4">
                            <Button
                              variant="outline"
                              onClick={handleSeedTemplates}
                              disabled={seedingTemplates}
                            >
                              {seedingTemplates ? (
                                <RotateCcw className="h-4 w-4 animate-spin mr-2" />
                              ) : (
                                <Zap className="h-4 w-4 mr-2" />
                              )}
                              Seed Templates
                            </Button>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
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
                                <span className="text-muted-foreground"> — {w.agentType.replace(/_/g, " ")}</span>
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

        <Dialog open={agentConfigOpen} onOpenChange={setAgentConfigOpen}>
          <DialogContent className="rounded-2xl">
            <DialogHeader>
              <DialogTitle>Configure Agent{agentBeingConfigured ? `: ${agentBeingConfigured.name}` : ""}</DialogTitle>
            </DialogHeader>
            <div className="grid gap-4">
              <div className="space-y-2">
                <Label htmlFor="cfg-model">Model</Label>
                <Input
                  id="cfg-model"
                  placeholder="e.g., gpt-4o-mini"
                  value={cfgModel}
                  onChange={(e) => setCfgModel(e.target.value)}
                  disabled={savingAgentConfig}
                  className="neu-inset rounded-xl"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="cfg-params">Parameters (JSON)</Label>
                <Textarea
                  id="cfg-params"
                  placeholder='{"temperature": 0.7}'
                  value={cfgParamsJSON}
                  onChange={(e) => setCfgParamsJSON(e.target.value)}
                  disabled={savingAgentConfig}
                  rows={6}
                  className="neu-inset rounded-xl font-mono text-xs"
                />
                <p className="text-[11px] text-muted-foreground">
                  Must be valid JSON. Example: {"{"}"temperature": 0.7, "top_p": 0.9{"}"}
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="cfg-triggers">Triggers (comma separated)</Label>
                <Input
                  id="cfg-triggers"
                  placeholder="e.g., new_lead, weekly_digest"
                  value={cfgTriggersCSV}
                  onChange={(e) => setCfgTriggersCSV(e.target.value)}
                  disabled={savingAgentConfig}
                  className="neu-inset rounded-xl"
                />
              </div>
            </div>

            <DialogFooter className="gap-2">
              <Button
                variant="outline"
                onClick={() => setAgentConfigOpen(false)}
                disabled={savingAgentConfig}
                className="neu-flat rounded-xl"
              >
                Cancel
              </Button>
              <Button
                onClick={async () => {
                  if (!agentBeingConfigured) return;
                  // Validate JSON
                  let params: Record<string, any> = {};
                  try {
                    params = cfgParamsJSON.trim() ? JSON.parse(cfgParamsJSON) : {};
                  } catch (e) {
                    toast.error("Parameters must be valid JSON");
                    return;
                  }
                  // Build triggers
                  const triggers = cfgTriggersCSV
                    .split(",")
                    .map((t) => t.trim())
                    .filter((t) => t.length > 0);

                  setSavingAgentConfig(true);
                  try {
                    await updateAgentConfig({
                      id: agentBeingConfigured._id,
                      configuration: {
                        model: cfgModel || "gpt-4o-mini",
                        parameters: params as any,
                        triggers,
                      },
                    });
                    toast.success("Agent configuration updated");
                    setAgentConfigOpen(false);
                  } catch (e) {
                    console.error(e);
                    toast.error("Failed to update configuration");
                  } finally {
                    setSavingAgentConfig(false);
                  }
                }}
                disabled={savingAgentConfig}
                className="neu-raised rounded-xl"
              >
                {savingAgentConfig ? (
                  <span className="inline-flex items-center">
                    <Activity className="mr-2 h-4 w-4 animate-spin" />
                    Saving...
                  </span>
                ) : (
                  "Save"
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Template Gallery Dialog */}
        <Dialog open={showTemplateGallery} onOpenChange={setShowTemplateGallery}>
          <DialogContent className="max-w-4xl">
            <DialogHeader>
              <DialogTitle>Workflow Template Gallery</DialogTitle>
              <DialogDescription>
                Choose from pre-built workflow templates to get started quickly
              </DialogDescription>
            </DialogHeader>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-h-96 overflow-y-auto">
              {templates?.map((template) => (
                <Card key={template._id} className="cursor-pointer hover:shadow-md transition-shadow">
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div>
                        <CardTitle className="text-lg">{template.name}</CardTitle>
                        <div className="text-sm text-muted-foreground mb-2">{template.category}</div>
                        <CardDescription>{template.description}</CardDescription>
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-1 mt-2">
                      {template.industryTags.map((tag) => (
                        <span
                          key={tag}
                          className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded-full"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2 mb-4">
                      <div className="text-sm font-medium">Steps ({template.steps.length}):</div>
                      {template.steps.slice(0, 3).map((step, idx) => (
                        <div key={idx} className="text-sm text-muted-foreground flex items-center gap-2">
                          <div className="w-2 h-2 bg-blue-500 rounded-full" />
                          {step.title}
                        </div>
                      ))}
                      {template.steps.length > 3 && (
                        <div className="text-sm text-muted-foreground">
                          +{template.steps.length - 3} more steps
                        </div>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        className="flex-1"
                      >
                        Preview
                      </Button>
                      <Button
                        size="sm"
                        className="flex-1"
                        onClick={() => handleCreateFromTemplate(template._id)}
                      >
                        Create from Template
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </DialogContent>
        </Dialog>

        {/* Workflow Runs Dialog */}
        <Dialog open={showWorkflowRuns} onOpenChange={setShowWorkflowRuns}>
          <DialogContent className="max-w-4xl">
            <DialogHeader>
              <DialogTitle>Workflow Runs - {selectedWorkflow?.name}</DialogTitle>
              <DialogDescription>
                View execution history and manage approvals
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 max-h-96 overflow-y-auto">
              {workflowRuns?.map((run) => (
                <div
                  key={run._id}
                  className="border rounded-lg p-4 hover:bg-muted/50 transition-colors cursor-pointer"
                  onClick={() => setSelectedRun(run)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`w-3 h-3 rounded-full ${
                        run.status === "completed" ? "bg-green-500" :
                        run.status === "failed" ? "bg-red-500" :
                        run.status === "awaiting_approval" ? "bg-yellow-500" :
                        "bg-blue-500"
                      }`} />
                      <div>
                        <div className="font-medium">
                          Run #{run._id.slice(-6)} {run.dryRun && "(Dry Run)"}
                        </div>
                        <div className="text-sm text-muted-foreground">
                          Started {new Date(run.startedAt).toLocaleString()}
                          {run.finishedAt && ` • Finished ${new Date(run.finishedAt).toLocaleString()}`}
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className={`text-sm font-medium ${
                        run.status === "completed" ? "text-green-600" :
                        run.status === "failed" ? "text-red-600" :
                        run.status === "awaiting_approval" ? "text-yellow-600" :
                        "text-blue-600"
                      }`}>
                        {run.status.replace(/_/g, " ")}
                      </div>
                      <div className="text-sm text-muted-foreground">
                        {run.summary.completedSteps}/{run.summary.totalSteps} steps
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
            
            {/* Run Details */}
            {selectedRun && selectedRunData && (
              <div className="border-t pt-4">
                <h4 className="font-medium mb-3">Run Steps</h4>
                <div className="space-y-2">
                  {selectedRunData.steps.map((step) => (
                    <div key={step._id} className="flex items-center justify-between p-3 border rounded">
                      <div className="flex items-center gap-3">
                        <div className={`w-3 h-3 rounded-full ${
                          step.status === "completed" ? "bg-green-500" :
                          step.status === "failed" ? "bg-red-500" :
                          step.status === "awaiting_approval" ? "bg-yellow-500" :
                          "bg-gray-400"
                        }`} />
                        <div>
                          <div className="font-medium">Step {step.stepId.slice(-6)}</div>
                          <div className="text-sm text-muted-foreground">{step.status}</div>
                        </div>
                      </div>
                      {step.status === "awaiting_approval" && (
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleApproveStep(step._id, false)}
                          >
                            Reject
                          </Button>
                          <Button
                            size="sm"
                            onClick={() => handleApproveStep(step._id, true)}
                          >
                            Approve
                          </Button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </DialogContent>
        </Dialog>

        {/* Create Workflow Dialog */}
        <Dialog open={showWorkflowModal} onOpenChange={setShowWorkflowModal}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create New Workflow</DialogTitle>
              <DialogDescription>
                Set up a new automated workflow for your business processes
              </DialogDescription>
            </DialogHeader>
            <CreateWorkflowForm
              onSubmit={handleCreateWorkflow}
              onCancel={() => setShowWorkflowModal(false)}
              agents={agents}
            />
          </DialogContent>
        </Dialog>
      </main>
    </div>
  );
}

// Create Workflow Form Component
function CreateWorkflowForm({ onSubmit, onCancel, agents }: any) {
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    trigger: "manual" as const,
    triggerConfig: {},
    approvalPolicy: { type: "none" as const, approvers: [] },
    associatedAgentIds: []
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <Label htmlFor="name">Workflow Name</Label>
        <Input
          id="name"
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          placeholder="Enter workflow name"
          required
        />
      </div>
      
      <div>
        <Label htmlFor="description">Description</Label>
        <Textarea
          id="description"
          value={formData.description}
          onChange={(e) => setFormData({ ...formData, description: e.target.value })}
          placeholder="Describe what this workflow does"
          required
        />
      </div>
      
      <div>
        <Label htmlFor="trigger">Trigger Type</Label>
        <Select
          value={formData.trigger}
          onValueChange={(value) => setFormData({ ...formData, trigger: value as any })}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="manual">Manual</SelectItem>
            <SelectItem value="schedule">Scheduled</SelectItem>
            <SelectItem value="event">Event-based</SelectItem>
          </SelectContent>
        </Select>
      </div>
      
      <div>
        <Label htmlFor="approval">Approval Policy</Label>
        <Select
          value={formData.approvalPolicy.type}
          onValueChange={(value) => setFormData({ 
            ...formData, 
            approvalPolicy: { type: value as any, approvers: [] }
          })}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="none">No Approval Required</SelectItem>
            <SelectItem value="single">Single Manager Approval</SelectItem>
            <SelectItem value="tiered">Tiered Approval</SelectItem>
          </SelectContent>
        </Select>
      </div>
      
      <div className="flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit">Create Workflow</Button>
      </div>
    </form>
  );
}