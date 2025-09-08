import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
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
  RotateCcw,
  Loader2,
  Brain,
  Building2,
  Lightbulb,
  CheckCircle2,
  ArrowRight,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { useNavigate } from "react-router";
import { useLocation } from "react-router";
import { useEffect, useState, useRef } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogDescription, DialogTrigger } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Play } from "lucide-react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  SidebarProvider,
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarInput,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
  SidebarSeparator,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { Home, Layers, Bot as BotIcon, Workflow as WorkflowIcon, Settings as SettingsIcon } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Search } from "lucide-react";
import { Slider } from "@/components/ui/slider";
import { Skeleton } from "@/components/ui/skeleton";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import type { FullAppInspectionReport, InspectionStatus } from "@/convex/inspector";

type Business = {
  _id: string;
  name: string;
  tier: "solopreneur" | "startup" | "sme" | "enterprise";
  industry: string;
};

// Add: Quality & Compliance types
type Incident = {
  _id: string;
  businessId: string;
  title: string;
  description?: string;
  severity: "low" | "medium" | "high" | "critical";
  category?: string;
  status?: "open" | "investigating" | "resolved";
  reportedBy?: string;
  createdAt?: number;
};

type Risk = {
  _id: string;
  businessId: string;
  title: string;
  description?: string;
  score?: number;
  owner?: string;
  status?: "open" | "mitigating" | "closed";
};

type Nonconformity = {
  _id: string;
  businessId: string;
  title: string;
  description?: string;
  severity?: "low" | "medium" | "high" | "critical";
  status?: "open" | "investigating" | "resolved";
};

type Sop = {
  _id: string;
  businessId: string;
  name: string;
  version?: string;
  url?: string;
};

type ComplianceCheck = {
  _id: string;
  businessId: string;
  subject?: string;
  status?: "pass" | "fail" | "warning";
  issues?: Array<{ code: string; message: string }>;
  createdAt?: number;
};

type AuditLog = {
  _id: string;
  businessId: string;
  action: string;
  actor?: string;
  metadata?: any;
  createdAt?: number;
};

type Initiative = {
  _id: string;
  title: string;
  status: "draft" | "active" | "paused" | "completed";
  priority: "low" | "medium" | "high" | "urgent";
  metrics: { targetROI: number; currentROI: number; completionRate: number };
};

type Agent = {
  _id: string;
  name: string;
  type: string;
  isActive: boolean;
};

type Workflow = {
  _id: string;
  name: string;
  description: string;
  isActive: boolean;
  // stats from listWorkflows
  runCount?: number;
  completedRuns?: number;
  lastRunStatus?: string | null;
};

// Add: MMRPolicy type
type MMRPolicy = {
  sensitive: number; // % human review for sensitive content
  drafts: number;    // % human review for drafts
  default: number;   // % human review default
  notes?: string;
};

// Add: Objective type
type Objective = {
  id: string;
  title: string;
  timeframe: "Q1" | "Q2" | "Q3" | "Q4" | "This Month" | "This Quarter" | "This Year";
  createdAt: number;
  progress?: number; // aggregate from KRs later
};

// Add: SnapTask type
type SnapTask = {
  id: string;
  title: string;
  priority: number; // higher = more important (S.N.A.P normalized)
  due?: number | null;
  status: "todo" | "done";
  createdAt: number;
};

// Add: InitiativeFeedback type
type InitiativeFeedback = {
  id: string;
  initiativeId: string;
  phase: "Discovery" | "Planning" | "Build" | "Test" | "Launch";
  note: string;
  createdAt: number;
};

// Add: Initiative Journey phases model (Phase 0–6)
const journeyPhases: Array<{
  id: number;
  title: string;
  description: string;
  actions: Array<{ label: string; onClick: () => void }>;
}> = [
  {
    id: 0,
    title: "Onboarding",
    description:
      "Define industry, model, goals. Connect social, email, e‑commerce, finance to tailor your setup.",
    actions: [
      { label: "Guided Onboarding", onClick: () => navigate("/onboarding") },
    ],
  },
  {
    id: 1,
    title: "Discovery",
    description:
      "Analyze current signals (web/social). Clarify target customers via quick surveys & link to Strategy.",
    actions: [
      { label: "Open Analytics", onClick: () => navigate("/analytics") },
      {
        label: "Strategy Agent",
        onClick: () => navigate("/ai-agents"),
      },
    ],
  },
  {
    id: 2,
    title: "Planning & Design",
    description:
      "Auto-draft strategy from Discovery. Mind‑map ideas. Add DTFL checkpoints and test assumptions.",
    actions: [
      { label: "SNAP Tasks", onClick: () => scrollToSection("tasks-section") },
      { label: "OKRs", onClick: () => scrollToSection("okrs-section") },
    ],
  },
  {
    id: 3,
    title: "Foundation",
    description:
      "Baseline setup: social accounts, email domain, brand assets, CRM & payments. Check SEO readiness.",
    actions: [
      { label: "Onboarding Checks", onClick: () => navigate("/onboarding") },
      { label: "Open Workflows", onClick: () => navigate("/workflows") },
    ],
  },
  {
    id: 4,
    title: "Execution",
    description:
      "Run campaigns with Orchestrate. Get live status and assign tasks. Human review via MMR.",
    actions: [
      { label: "Orchestrate", onClick: () => navigate("/workflows") },
      { label: "MMR Settings", onClick: () => scrollToSection("mmr-section") },
    ],
  },
  {
    id: 5,
    title: "Scale",
    description:
      "Duplicate winners for new markets, translate content, and simulate network effects.",
    actions: [
      { label: "Workflows", onClick: () => navigate("/workflows") },
      { label: "Analytics", onClick: () => navigate("/analytics") },
    ],
  },
  {
    id: 6,
    title: "Sustainability",
    description:
      "Continuous improvement: track metrics, schedule QMS audits, and log learnings in KnowledgeHub.",
    actions: [
      { label: "Compliance", onClick: () => scrollToSection("compliance-section") },
      { label: "OKRs", onClick: () => scrollToSection("okrs-section") },
    ],
  },
];

/**
 * Global helpers so they are in scope anywhere in this module (menu configs, etc).
 * These avoid TDZ issues and duplicate declarations.
 */
function navigate(path: string) {
  // Use client-side navigation by assigning to location; avoids needing hooks in non-React scopes.
  window.location.assign(path);
}

function scrollToSection(id: string) {
  const el = document.getElementById(id);
  if (el) el.scrollIntoView({ behavior: "smooth", block: "start", inline: "nearest" });
}

// Journey Band Component
function JourneyBand({ initiative, diagnostics }: { initiative: any; diagnostics: any }) {
  const navigate = useNavigate();
  
  const phases = [
    { id: 0, name: "Setup", description: "Initial configuration" },
    { id: 1, name: "Discovery", description: "Analyze & understand" },
    { id: 2, name: "Planning", description: "Strategy & design" },
    { id: 3, name: "Foundation", description: "Setup & connections" },
    { id: 4, name: "Execution", description: "Run campaigns" },
    { id: 5, name: "Scale", description: "Expand & optimize" },
    { id: 6, name: "Sustain", description: "Continuous improvement" },
  ];

  return (
    <Card className="mb-6">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg">Initiative Journey</CardTitle>
            <CardDescription>
              {initiative ? `Current Phase: ${phases[initiative.currentPhase]?.name}` : "No active initiative"}
            </CardDescription>
          </div>
          {initiative && initiative.currentPhase < 1 && (
            <Button onClick={() => navigate("/onboarding")} size="sm">
              Continue Setup
              <ArrowRight className="h-4 w-4 ml-2" />
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex items-center space-x-2 mb-4">
          {phases.map((phase) => (
            <div key={phase.id} className="flex-1">
              <div className="flex items-center">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium ${
                    initiative && phase.id <= initiative.currentPhase
                      ? "bg-primary text-primary-foreground"
                      : phase.id === (initiative?.currentPhase || 0) + 1
                      ? "bg-primary/20 text-primary border-2 border-primary"
                      : "bg-muted text-muted-foreground"
                  }`}
                >
                  {initiative && phase.id < initiative.currentPhase ? (
                    <CheckCircle2 className="h-4 w-4" />
                  ) : (
                    phase.id
                  )}
                </div>
                {phase.id < phases.length - 1 && (
                  <div
                    className={`flex-1 h-0.5 mx-2 ${
                      initiative && phase.id < initiative.currentPhase
                        ? "bg-primary"
                        : "bg-muted"
                    }`}
                  />
                )}
              </div>
              <div className="mt-2 text-center">
                <div className="text-xs font-medium">{phase.name}</div>
                <div className="text-xs text-muted-foreground">{phase.description}</div>
              </div>
            </div>
          ))}
        </div>

        {diagnostics && (
          <div className="mt-4 p-3 bg-muted/50 rounded-lg">
            <div className="flex items-center space-x-2 mb-2">
              <Lightbulb className="h-4 w-4 text-primary" />
              <span className="text-sm font-medium">Latest Diagnostics</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
              <div>
                <span className="text-muted-foreground">Target ROI:</span>
                <span className="ml-2 font-medium">{diagnostics.outputs.kpis.targetROI}%</span>
              </div>
              <div>
                <span className="text-muted-foreground">Tasks:</span>
                <span className="ml-2 font-medium">{diagnostics.outputs.tasks.length}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Workflows:</span>
                <span className="ml-2 font-medium">{diagnostics.outputs.workflows.length}</span>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function Dashboard() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const navigate = useNavigate();

  // Convex queries
  const currentBusiness = useQuery(api.businesses.currentUserBusiness);
  const initiative = useQuery(
    api.initiatives.getByBusiness,
    currentBusiness ? { businessId: currentBusiness._id } : "skip"
  );
  const diagnostics = useQuery(
    api.diagnostics.getLatest,
    currentBusiness ? { businessId: currentBusiness._id } : "skip"
  );
  const businesses = useQuery(api.businesses.getByOwner);
  const agents = useQuery(
    api.aiAgents.getByBusiness,
    currentBusiness ? { businessId: currentBusiness._id } : "skip"
  );
  const workflows = useQuery(
    api.workflows.getByBusiness,
    currentBusiness ? { businessId: currentBusiness._id } : "skip"
  );

  // Redirect if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      navigate("/auth");
    }
  }, [isAuthenticated, authLoading, navigate]);

  // Redirect to onboarding if no business
  useEffect(() => {
    if (!authLoading && isAuthenticated && businesses !== undefined && businesses.length === 0) {
      navigate("/onboarding");
    }
  }, [authLoading, isAuthenticated, businesses, navigate]);

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated || !currentBusiness) {
    return null;
  }

  const stats = [
    {
      title: "Active Agents",
      value: agents?.filter((a: any) => a.status === "active").length || 0,
      icon: Bot,
      description: "AI agents running",
    },
    {
      title: "Workflows",
      value: workflows?.filter((w: any) => w.status === "active").length || 0,
      icon: Brain,
      description: "Active workflows",
    },
    {
      title: "Success Rate",
      value: agents?.length ? Math.round(agents.reduce((acc: number, a: any) => acc + a.metrics.successRate, 0) / agents.length) : 0,
      icon: TrendingUp,
      description: "Average success rate",
      suffix: "%",
    },
    {
      title: "Total Runs",
      value: agents?.reduce((acc: number, a: any) => acc + a.metrics.totalRuns, 0) || 0,
      icon: BarChart3,
      description: "Total executions",
    },
  ];

  const [inspectionOpen, setInspectionOpen] = useState(false);
  const [inspectionReport, setInspectionReport] = useState<FullAppInspectionReport | null>(null);
  const runInspection = useAction(api.inspector.runInspection);
  const [isRunningInspection, setIsRunningInspection] = useState(false);

  const handleRunInspection = async () => {
    setIsRunningInspection(true);
    try {
      const report = await runInspection({});
      setInspectionReport(report);
      toast.success(`Inspection complete: ${report.summary.passes} passed, ${report.summary.warnings} warnings, ${report.summary.failures} failed`);
    } catch (error) {
      toast.error("Failed to run inspection");
      console.error("Inspection error:", error);
    } finally {
      setIsRunningInspection(false);
    }
  };

  const downloadReport = () => {
    if (!inspectionReport) return;
    
    const blob = new Blob([JSON.stringify(inspectionReport, null, 2)], {
      type: "application/json"
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `inspection-report-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const getStatusBadge = (status: InspectionStatus) => {
    const variants = {
      pass: "default",
      warn: "secondary", 
      fail: "destructive"
    } as const;
    
    const colors = {
      pass: "text-green-700 bg-green-100",
      warn: "text-amber-700 bg-amber-100",
      fail: "text-red-700 bg-red-100"
    };

    return (
      <Badge variant={variants[status]} className={colors[status]}>
        {status.toUpperCase()}
      </Badge>
    );
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
      <div className="container mx-auto px-4 py-8">
        {/* Journey Band */}
        <JourneyBand initiative={initiative} diagnostics={diagnostics} />

        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-8">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
            <p className="text-muted-foreground">
              Welcome back! Here's what's happening with {currentBusiness.name}.
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => navigate("/business")}>
              <Settings className="h-4 w-4 mr-2" />
              Settings
            </Button>
            <Button onClick={() => navigate("/agents")}>
              <Plus className="h-4 w-4 mr-2" />
              New Agent
            </Button>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {stats.map((stat) => (
            <Card key={stat.title}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">{stat.title}</CardTitle>
                <stat.icon className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {stat.value}{stat.suffix}
                </div>
                <p className="text-xs text-muted-foreground">{stat.description}</p>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Main Content Tabs */}
        <Tabs defaultValue="overview" className="space-y-6">
          <TabsList>
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="agents">Agents</TabsTrigger>
            <TabsTrigger value="workflows">Workflows</TabsTrigger>
            <TabsTrigger value="analytics">Analytics</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Recent Activity */}
              <Card>
                <CardHeader>
                  <CardTitle>Recent Activity</CardTitle>
                  <CardDescription>Latest updates from your AI agents</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {agents?.slice(0, 3).map((agent: any) => (
                      <div key={agent._id} className="flex items-center space-x-4">
                        <div className="w-2 h-2 bg-green-500 rounded-full" />
                        <div className="flex-1">
                          <p className="text-sm font-medium">{agent.name}</p>
                          <p className="text-xs text-muted-foreground">
                            {agent.metrics.totalRuns} runs • {agent.metrics.successRate}% success
                          </p>
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {agent.metrics.lastRun ? new Date(agent.metrics.lastRun).toLocaleDateString() : "Never"}
                        </div>
                      </div>
                    ))}
                    {(!agents || agents.length === 0) && (
                      <div className="text-center py-8">
                        <Bot className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                        <p className="text-sm text-muted-foreground">No agents created yet</p>
                        <Button className="mt-2" onClick={() => navigate("/agents")}>
                          Create Your First Agent
                        </Button>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>

              {/* Quick Actions */}
              <Card>
                <CardHeader>
                  <CardTitle>Quick Actions</CardTitle>
                  <CardDescription>Common tasks and shortcuts</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 gap-4">
                    <Button
                      variant="outline"
                      className="h-20 flex-col"
                      onClick={() => navigate("/agents")}
                    >
                      <Bot className="h-6 w-6 mb-2" />
                      <span className="text-sm">New Agent</span>
                    </Button>
                    <Button
                      variant="outline"
                      className="h-20 flex-col"
                      onClick={() => navigate("/workflows")}
                    >
                      <Brain className="h-6 w-6 mb-2" />
                      <span className="text-sm">New Workflow</span>
                    </Button>
                    <Button
                      variant="outline"
                      className="h-20 flex-col"
                      onClick={() => navigate("/analytics")}
                    >
                      <BarChart3 className="h-6 w-6 mb-2" />
                      <span className="text-sm">View Analytics</span>
                    </Button>
                    <Button
                      variant="outline"
                      className="h-20 flex-col"
                      onClick={() => navigate("/business")}
                    >
                      <Building2 className="h-6 w-6 mb-2" />
                      <span className="text-sm">Business Settings</span>
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="agents">
            <Card>
              <CardHeader>
                <CardTitle>AI Agents</CardTitle>
                <CardDescription>Manage your AI-powered automation agents</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {agents?.map((agent: any) => (
                    <div key={agent._id} className="flex items-center justify-between p-4 border rounded-lg">
                      <div className="flex items-center space-x-4">
                        <div className={`w-3 h-3 rounded-full ${
                          agent.status === "active" ? "bg-green-500" : 
                          agent.status === "training" ? "bg-yellow-500" : "bg-gray-500"
                        }`} />
                        <div>
                          <h3 className="font-medium">{agent.name}</h3>
                          <p className="text-sm text-muted-foreground capitalize">{agent.type.replace("_", " ")}</p>
                        </div>
                      </div>
                      <div className="flex items-center space-x-4">
                        <div className="text-right">
                          <p className="text-sm font-medium">{agent.metrics.totalRuns} runs</p>
                          <p className="text-xs text-muted-foreground">{agent.metrics.successRate}% success</p>
                        </div>
                        <Button variant="outline" size="sm">
                          Configure
                        </Button>
                      </div>
                    </div>
                  ))}
                  {(!agents || agents.length === 0) && (
                    <div className="text-center py-8">
                      <Bot className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                      <p className="text-sm text-muted-foreground mb-4">No agents created yet</p>
                      <Button onClick={() => navigate("/agents")}>
                        Create Your First Agent
                      </Button>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="workflows">
            <Card>
              <CardHeader>
                <CardTitle>Workflows</CardTitle>
                <CardDescription>Automated business processes and agent orchestration</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {workflows?.map((workflow: any) => (
                    <div key={workflow._id} className="flex items-center justify-between p-4 border rounded-lg">
                      <div className="flex items-center space-x-4">
                        <div className={`w-3 h-3 rounded-full ${
                          workflow.status === "active" ? "bg-green-500" : 
                          workflow.status === "draft" ? "bg-yellow-500" : "bg-gray-500"
                        }`} />
                        <div>
                          <h3 className="font-medium">{workflow.name}</h3>
                          <p className="text-sm text-muted-foreground">{workflow.description}</p>
                        </div>
                      </div>
                      <div className="flex items-center space-x-4">
                        <div className="text-right">
                          <p className="text-sm font-medium">{workflow.metrics.totalRuns} runs</p>
                          <p className="text-xs text-muted-foreground">{workflow.metrics.successRate}% success</p>
                        </div>
                        <Button variant="outline" size="sm">
                          Edit
                        </Button>
                      </div>
                    </div>
                  ))}
                  {(!workflows || workflows.length === 0) && (
                    <div className="text-center py-8">
                      <Brain className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                      <p className="text-sm text-muted-foreground mb-4">No workflows created yet</p>
                      <Button onClick={() => navigate("/workflows")}>
                        Create Your First Workflow
                      </Button>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="analytics">
            <Card>
              <CardHeader>
                <CardTitle>Analytics</CardTitle>
                <CardDescription>Performance insights and metrics</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-center py-8">
                  <BarChart3 className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <p className="text-sm text-muted-foreground mb-4">Analytics dashboard coming soon</p>
                  <Button onClick={() => navigate("/analytics")}>
                    View Full Analytics
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* Add Inspection Panel */}
        <Card className="mb-8">
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              System Health Inspector
              <Dialog open={inspectionOpen} onOpenChange={setInspectionOpen}>
                <DialogTrigger asChild>
                  <Button variant="outline" size="sm">
                    <Search className="h-4 w-4 mr-2" />
                    Run Inspection
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
                  <DialogHeader>
                    <DialogTitle>Pikar AI Feature Implementation Report</DialogTitle>
                  </DialogHeader>
                  
                  <div className="space-y-4">
                    <div className="flex gap-2">
                      <Button 
                        onClick={handleRunInspection} 
                        disabled={isRunningInspection}
                        size="sm"
                      >
                        {isRunningInspection ? "Running..." : "Run Inspection"}
                      </Button>
                      
                      {inspectionReport && (
                        <Button 
                          onClick={downloadReport}
                          variant="outline" 
                          size="sm"
                        >
                          Export JSON
                        </Button>
                      )}
                    </div>

                    {isRunningInspection && (
                      <div className="space-y-2">
                        <Progress value={undefined} className="w-full" />
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          {Array.from({ length: 6 }).map((_, i) => (
                            <Skeleton key={i} className="h-12 w-full" />
                          ))}
                        </div>
                      </div>
                    )}

                    {inspectionReport && (
                      <div className="space-y-4">
                        {/* Summary */}
                        <Card>
                          <CardHeader className="pb-3">
                            <CardTitle className="text-lg">Summary</CardTitle>
                          </CardHeader>
                          <CardContent>
                            <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-center">
                              <div>
                                <div className="text-2xl font-bold text-green-600">
                                  {inspectionReport.summary.passes}
                                </div>
                                <div className="text-sm text-muted-foreground">Passed</div>
                              </div>
                              <div>
                                <div className="text-2xl font-bold text-amber-600">
                                  {inspectionReport.summary.warnings}
                                </div>
                                <div className="text-sm text-muted-foreground">Warnings</div>
                              </div>
                              <div>
                                <div className="text-2xl font-bold text-red-600">
                                  {inspectionReport.summary.failures}
                                </div>
                                <div className="text-sm text-muted-foreground">Failed</div>
                              </div>
                              <div>
                                <div className="text-2xl font-bold text-red-800">
                                  {inspectionReport.summary.critical_failures}
                                </div>
                                <div className="text-sm text-muted-foreground">Critical</div>
                              </div>
                              <div>
                                <div className="text-2xl font-bold">
                                  {inspectionReport.summary.total_checks}
                                </div>
                                <div className="text-sm text-muted-foreground">Total</div>
                              </div>
                            </div>
                            
                            {inspectionReport.summary.escalation_required && (
                              <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                                <div className="text-red-800 font-medium">⚠️ Escalation Required</div>
                                <div className="text-red-700 text-sm">
                                  Critical failures detected. DevOps and Compliance teams should be notified.
                                </div>
                              </div>
                            )}
                          </CardContent>
                        </Card>

                        <Separator />

                        {/* Results Table */}
                        <div className="rounded-md border">
                          <Table>
                            <TableHeader>
                              <TableRow>
                                <TableHead>Module</TableHead>
                                <TableHead>Check</TableHead>
                                <TableHead>Status</TableHead>
                                <TableHead>Evidence</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {inspectionReport.results.map((result, index) => (
                                <TableRow key={index}>
                                  <TableCell className="font-medium">
                                    {result.module}
                                  </TableCell>
                                  <TableCell>{result.check}</TableCell>
                                  <TableCell>
                                    {getStatusBadge(result.status)}
                                  </TableCell>
                                  <TableCell>
                                    <TooltipProvider>
                                      <Tooltip>
                                        <TooltipTrigger asChild>
                                          <div className="max-w-xs truncate cursor-help">
                                            {result.evidence}
                                          </div>
                                        </TooltipTrigger>
                                        <TooltipContent className="max-w-sm">
                                          <p>{result.evidence}</p>
                                          {result.triggered_ai_tasks && result.triggered_ai_tasks.length > 0 && (
                                            <div className="mt-2">
                                              <div className="font-medium">Suggested AI Tasks:</div>
                                              <ul className="list-disc list-inside text-sm">
                                                {result.triggered_ai_tasks.map((task, i) => (
                                                  <li key={i}>{task}</li>
                                                ))}
                                              </ul>
                                            </div>
                                          )}
                                        </TooltipContent>
                                      </Tooltip>
                                    </TooltipProvider>
                                  </TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </div>
                      </div>
                    )}
                  </div>
                </DialogContent>
              </Dialog>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Run comprehensive validation of all Pikar AI features and modules to identify implementation gaps.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}