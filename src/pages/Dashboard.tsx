import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { useAuth } from "@/hooks/use-auth";
import { api } from "@/convex/_generated/api";
import { useQuery, useAction } from "convex/react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router";
import {
  Bot,
  BarChart3,
  TrendingUp,
  Brain,
  Plus,
  Settings,
  Building2,
  Loader2,
  Search,
} from "lucide-react";
import type { FullAppInspectionReport } from "@/convex/inspector";

function JourneyBand() {
  const navigate = useNavigate();
  const phases: Array<{ id: number; name: string; description: string; actions: Array<{ label: string; onClick: () => void }> }> = [
    {
      id: 0,
      name: "Onboarding",
      description: "Define industry, model, goals and connect integrations.",
      actions: [{ label: "Guided Onboarding", onClick: () => navigate("/onboarding") }],
    },
    {
      id: 1,
      name: "Discovery",
      description: "Analyze signals; clarify target customers.",
      actions: [{ label: "Open Analytics", onClick: () => navigate("/analytics") }],
    },
    {
      id: 2,
      name: "Planning",
      description: "Draft strategy; add checkpoints & assumptions.",
      actions: [{ label: "Open Workflows", onClick: () => navigate("/workflows") }],
    },
    {
      id: 3,
      name: "Foundation",
      description: "Baseline setup: domains, CRM, payments.",
      actions: [{ label: "Onboarding Checks", onClick: () => navigate("/onboarding") }],
    },
    {
      id: 4,
      name: "Execution",
      description: "Run campaigns and orchestrations.",
      actions: [{ label: "Orchestrate", onClick: () => navigate("/workflows") }],
    },
    {
      id: 5,
      name: "Scale",
      description: "Duplicate winners; expand markets.",
      actions: [{ label: "Analytics", onClick: () => navigate("/analytics") }],
    },
    {
      id: 6,
      name: "Sustain",
      description: "Continuous improvement & audits.",
      actions: [{ label: "Compliance", onClick: () => window.scrollTo({ top: 0, behavior: "smooth" }) }],
    },
  ];

  return (
    <Card className="mb-8">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg">Initiative Journey</CardTitle>
        <CardDescription>Track from setup to sustainability</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-7 gap-3">
          {phases.map((p) => (
            <div key={p.id} className="rounded-lg border p-3">
              <div className="text-sm font-medium">{p.name}</div>
              <div className="text-xs text-muted-foreground mb-2">{p.description}</div>
              <div className="flex flex-wrap gap-2">
                {p.actions.map((a, i) => (
                  <Button key={i} variant="outline" size="sm" onClick={a.onClick}>
                    {a.label}
                  </Button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export default function Dashboard() {
  const { isLoading: authLoading, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  const currentBusiness = useQuery(api.businesses.currentUserBusiness);
  const businesses = useQuery(api.businesses.getByOwner);
  const agents = useQuery(
    api.aiAgents.getByBusiness,
    currentBusiness ? { businessId: currentBusiness._id } : "skip"
  );
  const workflows = useQuery(
    api.workflows.getByBusiness,
    currentBusiness ? { businessId: currentBusiness._id } : "skip"
  );
  const initiative = useQuery(
    api.initiatives.getByBusiness,
    currentBusiness ? { businessId: currentBusiness._id } : "skip"
  );
  const diagnostics = useQuery(
    api.diagnostics.getLatest,
    currentBusiness ? { businessId: currentBusiness._id } : "skip"
  );

  // Inspector state
  const [inspectionOpen, setInspectionOpen] = useState(false);
  const [isRunningInspection, setIsRunningInspection] = useState(false);
  const [inspectionReport, setInspectionReport] = useState<FullAppInspectionReport | null>(null);
  const runInspection = useAction(api.inspector.runInspection);

  // Redirects
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      navigate("/auth");
    }
  }, [authLoading, isAuthenticated, navigate]);

  useEffect(() => {
    if (!authLoading && isAuthenticated && businesses !== undefined && (businesses as any[]).length === 0) {
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
      value: agents?.filter((a: any) => a.status === "active").length ?? 0,
      icon: Bot,
      description: "AI agents running",
    },
    {
      title: "Workflows",
      value: workflows?.filter((w: any) => w.status === "active").length ?? 0,
      icon: Brain,
      description: "Active workflows",
    },
    {
      title: "Success Rate",
      value:
        agents && agents.length > 0
          ? Math.round(
              agents.reduce((acc: number, a: any) => acc + (a.metrics?.successRate ?? 0), 0) /
                agents.length
            )
          : 0,
      icon: TrendingUp,
      description: "Average success rate",
      suffix: "%",
    },
    {
      title: "Total Runs",
      value: agents?.reduce((acc: number, a: any) => acc + (a.metrics?.totalRuns ?? 0), 0) ?? 0,
      icon: BarChart3,
      description: "Total executions",
    },
  ];

  const handleRunInspection = async () => {
    setIsRunningInspection(true);
    try {
      const result = await runInspection({});
      setInspectionReport(result as FullAppInspectionReport);
    } finally {
      setIsRunningInspection(false);
    }
  };

  const downloadReport = () => {
    if (!inspectionReport) return;
    const blob = new Blob([JSON.stringify(inspectionReport, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `inspection-report-${new Date().toISOString()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const getStatusBadge = (status: string) => {
    const label = (status || "").toUpperCase();
    return <Badge>{label}</Badge>;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
      <div className="container mx-auto px-4 py-8">
        {/* Journey Band */}
        <JourneyBand />

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
                  {stat.value}
                  {stat.suffix}
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
                        <div
                          className={`w-2 h-2 rounded-full ${
                            agent.status === "active"
                              ? "bg-green-500"
                              : agent.status === "training"
                              ? "bg-yellow-500"
                              : "bg-gray-500"
                          }`}
                        />
                        <div className="flex-1">
                          <p className="text-sm font-medium">{agent.name}</p>
                          <p className="text-xs text-muted-foreground">
                            {(agent.metrics?.totalRuns ?? 0)} runs • {(agent.metrics?.successRate ?? 0)}% success
                          </p>
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {agent.metrics?.lastRun
                            ? new Date(agent.metrics.lastRun).toLocaleDateString()
                            : "Never"}
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
                    <Button variant="outline" className="h-20 flex-col" onClick={() => navigate("/agents")}>
                      <Bot className="h-6 w-6 mb-2" />
                      <span className="text-sm">New Agent</span>
                    </Button>
                    <Button variant="outline" className="h-20 flex-col" onClick={() => navigate("/workflows")}>
                      <Brain className="h-6 w-6 mb-2" />
                      <span className="text-sm">New Workflow</span>
                    </Button>
                    <Button variant="outline" className="h-20 flex-col" onClick={() => navigate("/analytics")}>
                      <BarChart3 className="h-6 w-6 mb-2" />
                      <span className="text-sm">View Analytics</span>
                    </Button>
                    <Button variant="outline" className="h-20 flex-col" onClick={() => navigate("/business")}>
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
                        <div
                          className={`w-3 h-3 rounded-full ${
                            agent.status === "active"
                              ? "bg-green-500"
                              : agent.status === "training"
                              ? "bg-yellow-500"
                              : "bg-gray-500"
                          }`}
                        />
                        <div>
                          <h3 className="font-medium">{agent.name}</h3>
                          <p className="text-sm text-muted-foreground capitalize">
                            {String(agent.type || "").replace("_", " ")}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center space-x-4">
                        <div className="text-right">
                          <p className="text-sm font-medium">{agent.metrics?.totalRuns ?? 0} runs</p>
                          <p className="text-xs text-muted-foreground">{agent.metrics?.successRate ?? 0}% success</p>
                        </div>
                        <Button variant="outline" size="sm">Configure</Button>
                      </div>
                    </div>
                  ))}
                  {(!agents || agents.length === 0) && (
                    <div className="text-center py-8">
                      <Bot className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                      <p className="text-sm text-muted-foreground mb-4">No agents created yet</p>
                      <Button onClick={() => navigate("/agents")}>Create Your First Agent</Button>
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
                        <div
                          className={`w-3 h-3 rounded-full ${
                            workflow.status === "active"
                              ? "bg-green-500"
                              : workflow.status === "draft"
                              ? "bg-yellow-500"
                              : "bg-gray-500"
                          }`}
                        />
                        <div>
                          <h3 className="font-medium">{workflow.name}</h3>
                          <p className="text-sm text-muted-foreground">{workflow.description}</p>
                        </div>
                      </div>
                      <div className="flex items-center space-x-4">
                        <div className="text-right">
                          <p className="text-sm font-medium">{workflow.metrics?.totalRuns ?? 0} runs</p>
                          <p className="text-xs text-muted-foreground">{workflow.metrics?.successRate ?? 0}% success</p>
                        </div>
                        <Button variant="outline" size="sm">Edit</Button>
                      </div>
                    </div>
                  ))}
                  {(!workflows || workflows.length === 0) && (
                    <div className="text-center py-8">
                      <Brain className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                      <p className="text-sm text-muted-foreground mb-4">No workflows created yet</p>
                      <Button onClick={() => navigate("/workflows")}>Create Your First Workflow</Button>
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
                  <Button onClick={() => navigate("/analytics")}>View Full Analytics</Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* System Health Inspector */}
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
                      <Button onClick={handleRunInspection} disabled={isRunningInspection} size="sm">
                        {isRunningInspection ? "Running..." : "Run Inspection"}
                      </Button>

                      {inspectionReport && (
                        <Button onClick={downloadReport} variant="outline" size="sm">
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
                              {inspectionReport.results.map(
                                (result: FullAppInspectionReport["results"][number], index: number) => (
                                  <TableRow key={index}>
                                    <TableCell className="font-medium">{result.module}</TableCell>
                                    <TableCell>{result.check}</TableCell>
                                    <TableCell>{getStatusBadge(result.status)}</TableCell>
                                    <TableCell>
                                      <TooltipProvider>
                                        <Tooltip>
                                          <TooltipTrigger asChild>
                                            <div className="max-w-xs truncate cursor-help">{result.evidence}</div>
                                          </TooltipTrigger>
                                          <TooltipContent className="max-w-sm">
                                            <p>{result.evidence}</p>
                                            {result.triggered_ai_tasks && result.triggered_ai_tasks.length > 0 && (
                                              <div className="mt-2">
                                                <div className="font-medium">Suggested AI Tasks:</div>
                                                <ul className="list-disc list-inside text-sm">
                                                  {result.triggered_ai_tasks.map((task: string, i: number) => (
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
                                )
                              )}
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