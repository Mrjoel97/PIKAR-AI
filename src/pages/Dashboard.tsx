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
  RotateCcw
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { useNavigate } from "react-router";
import { useEffect, useState, useMemo } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
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

// ... keep existing code (types local to this file)
type Business = {
  _id: string;
  name: string;
  tier: "solopreneur" | "startup" | "sme" | "enterprise";
  industry: string;
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
  lastRunAt?: number | null;
};

export default function Dashboard() {
  const navigate = useNavigate();
  const { isLoading: authLoading, isAuthenticated, user, signIn } = useAuth();

  const userBusinesses = useQuery(api.businesses.getUserBusinesses, {});
  const [selectedBusinessId, setSelectedBusinessId] = useState<string | null>(null);

  const businessesLoaded = userBusinesses !== undefined;
  const hasBusinesses = (userBusinesses?.length || 0) > 0;

  // Select first business when loaded
  useMemo(() => {
    if (!selectedBusinessId && hasBusinesses) {
      setSelectedBusinessId(userBusinesses![0]._id);
    }
  }, [hasBusinesses, selectedBusinessId, userBusinesses]);

  const initiatives = useQuery(
    api.initiatives.getByBusiness,
    selectedBusinessId ? { businessId: selectedBusinessId as any } : ("skip" as any)
  );
  const agents = useQuery(
    api.aiAgents.getByBusiness,
    selectedBusinessId ? { businessId: selectedBusinessId as any } : ("skip" as any)
  );
  const workflows = useQuery(
    api.workflows.listWorkflows,
    selectedBusinessId ? { businessId: selectedBusinessId as any } : ("skip" as any)
  );

  const createBusiness = useMutation(api.businesses.create);
  const seedAgents = useMutation(api.aiAgents.seedEnhancedForBusiness);
  const seedTemplates = useMutation(api.workflows.seedTemplates);
  const runWorkflow = useAction(api.workflows.runWorkflow);

  const scrollToSection = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  if (authLoading) {
    return (
      <div className="max-w-6xl mx-auto p-6">
        <div className="animate-pulse h-8 w-40 rounded bg-muted mb-4" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="h-28 rounded-lg bg-muted" />
          <div className="h-28 rounded-lg bg-muted" />
          <div className="h-28 rounded-lg bg-muted" />
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center px-6">
        <Card className="max-w-md w-full">
          <CardHeader>
            <CardTitle>Welcome</CardTitle>
            <CardDescription>Sign in to view your dashboard.</CardDescription>
          </CardHeader>
          <CardContent className="flex gap-3">
            <Button onClick={() => navigate("/auth")}>Sign In</Button>
            <Button variant="outline" onClick={() => navigate("/")}>Go Home</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const handleQuickCreateBusiness = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const name = String(fd.get("name") || "").trim();
    const industry = String(fd.get("industry") || "").trim();
    const tier = (String(fd.get("tier") || "startup") as Business["tier"]);
    if (!name || !industry) {
      toast("Please provide a name and industry.");
      return;
    }
    try {
      const id = await createBusiness({
        name,
        tier,
        industry,
        description: undefined,
        website: undefined,
      } as any);
      toast("Business created");
      setSelectedBusinessId(id as any);
    } catch (err: any) {
      toast(err.message || "Failed to create business");
    }
  };

  const handleSeedAgents = async () => {
    if (!selectedBusinessId) return;
    try {
      await seedAgents({ businessId: selectedBusinessId as any });
      toast("AI agents seeded");
    } catch (e: any) {
      toast(e.message || "Failed to seed agents");
    }
  };

  const handleSeedTemplates = async () => {
    try {
      await seedTemplates({});
      toast("Workflow templates seeded");
    } catch (e: any) {
      toast(e.message || "Failed to seed templates");
    }
  };

  const selectedBusiness = userBusinesses?.find(b => b._id === selectedBusinessId) as Business | undefined;

  const stats = [
    { label: "Initiatives", value: initiatives?.length ?? 0 },
    { label: "AI Agents", value: agents?.length ?? 0 },
    { label: "Workflows", value: workflows?.length ?? 0 },
  ];

  return (
    <SidebarProvider>
      <Sidebar variant="inset" collapsible="offcanvas">
        <SidebarHeader>
          <SidebarInput placeholder="Search..." aria-label="Search" />
        </SidebarHeader>

        <SidebarContent>
          <SidebarGroup>
            <SidebarGroupLabel>Navigation</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                <SidebarMenuItem>
                  <SidebarMenuButton onClick={() => scrollToSection("overview")} tooltip="Overview">
                    <Home />
                    <span>Overview</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
                <SidebarMenuItem>
                  <SidebarMenuButton onClick={() => scrollToSection("initiatives-section")} tooltip="Initiatives">
                    <Layers />
                    <span>Initiatives</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
                <SidebarMenuItem>
                  <SidebarMenuButton onClick={() => scrollToSection("agents-section")} tooltip="AI Agents">
                    <BotIcon />
                    <span>AI Agents</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
                <SidebarMenuItem>
                  <SidebarMenuButton onClick={() => scrollToSection("workflows-section")} tooltip="Workflows">
                    <WorkflowIcon />
                    <span>Workflows</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>

          <SidebarSeparator />

          <SidebarGroup>
            <SidebarGroupLabel>Account</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                <SidebarMenuItem>
                  <SidebarMenuButton onClick={() => scrollToSection("business-info")} tooltip="Business Info">
                    <SettingsIcon />
                    <span>Business Info</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        </SidebarContent>

        <SidebarFooter />
        <SidebarRail />
      </Sidebar>

      <SidebarInset>
        <div id="overview" className="max-w-6xl mx-auto px-4 md:px-6 py-6 space-y-6">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div className="flex items-center gap-2">
              <SidebarTrigger />
              <div>
                <h1 className="text-2xl font-semibold">Dashboard</h1>
                <p className="text-sm text-muted-foreground">Welcome back{user?.companyName ? `, ${user.companyName}` : ""}.</p>
              </div>
            </div>

            <div className="flex flex-col sm:flex-row gap-3">
              {businessesLoaded && hasBusinesses ? (
                <Select
                  value={selectedBusinessId ?? ""}
                  onValueChange={(v) => setSelectedBusinessId(v)}
                >
                  <SelectTrigger className="min-w-56">
                    <SelectValue placeholder="Select business" />
                  </SelectTrigger>
                  <SelectContent>
                    {userBusinesses!.map((b) => (
                      <SelectItem key={b._id} value={b._id}>
                        {b.name} <span className="text-muted-foreground">• {b.tier}</span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              ) : null}
              <Button variant="outline" onClick={() => navigate("/onboarding")}>Onboarding</Button>
            </div>
          </div>

          {!businessesLoaded ? (
            <Card>
              <CardContent className="p-6">
                <div className="animate-pulse h-6 w-44 rounded bg-muted" />
              </CardContent>
            </Card>
          ) : !hasBusinesses ? (
            <Card>
              <CardHeader>
                <CardTitle>Create your first business</CardTitle>
                <CardDescription>Get started by creating a business profile.</CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleQuickCreateBusiness} className="grid grid-cols-1 md:grid-cols-5 gap-3">
                  <Input name="name" placeholder="Business name" className="md:col-span-2" />
                  <Input name="industry" placeholder="Industry" className="md:col-span-2" />
                  <Select name="tier" defaultValue="startup" onValueChange={() => {}}>
                    <SelectTrigger><SelectValue placeholder="Tier" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="solopreneur">Solopreneur</SelectItem>
                      <SelectItem value="startup">Startup</SelectItem>
                      <SelectItem value="sme">SME</SelectItem>
                      <SelectItem value="enterprise">Enterprise</SelectItem>
                    </SelectContent>
                  </Select>
                  <div className="md:col-span-5 flex gap-2">
                    <Button type="submit">Create</Button>
                    <Button type="button" variant="outline" onClick={() => navigate("/onboarding")}>
                      Use guided onboarding
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {stats.map((s) => (
                  <Card key={s.label}>
                    <CardHeader className="pb-2">
                      <CardDescription>{s.label}</CardDescription>
                      <CardTitle className="text-2xl">{s.value}</CardTitle>
                    </CardHeader>
                    <CardContent className="pt-0">
                      <div className="text-xs text-muted-foreground">Updated in real time</div>
                    </CardContent>
                  </Card>
                ))}
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <Card className="lg:col-span-2" id="initiatives-section">
                  <CardHeader className="flex flex-row items-center justify-between">
                    <div>
                      <CardTitle>Initiatives</CardTitle>
                      <CardDescription>Track ROI and completion.</CardDescription>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Title</TableHead>
                          <TableHead>Status</TableHead>
                          <TableHead>Priority</TableHead>
                          <TableHead className="text-right">ROI</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {(initiatives || []).map((i: Initiative) => (
                          <TableRow key={i._id}>
                            <TableCell className="max-w-[220px] truncate">{i.title}</TableCell>
                            <TableCell>
                              <Badge variant="secondary">{i.status}</Badge>
                            </TableCell>
                            <TableCell>
                              <Badge variant={i.priority === "urgent" || i.priority === "high" ? "destructive" : "outline"}>
                                {i.priority}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-right">
                              {Math.round(i.metrics.currentROI)}% / {Math.round(i.metrics.targetROI)}%
                            </TableCell>
                          </TableRow>
                        ))}
                        {((initiatives || []).length === 0) && (
                          <TableRow>
                            <TableCell colSpan={4} className="text-muted-foreground">No initiatives yet.</TableCell>
                          </TableRow>
                        )}
                      </TableBody>
                    </Table>
                  </CardContent>
                </Card>

                <div className="space-y-6">
                  <Card>
                    <CardHeader className="flex flex-row items-center justify-between">
                      <div>
                        <CardTitle>Quick actions</CardTitle>
                        <CardDescription>Seed useful data for demos.</CardDescription>
                      </div>
                    </CardHeader>
                    <CardContent className="flex flex-wrap gap-2">
                      <Button onClick={handleSeedAgents}>Seed AI Agents</Button>
                      <Button variant="outline" onClick={handleSeedTemplates}>Seed Workflow Templates</Button>
                    </CardContent>
                  </Card>

                  <Card id="business-info">
                    <CardHeader>
                      <CardTitle>Business</CardTitle>
                      <CardDescription>{selectedBusiness?.name}</CardDescription>
                    </CardHeader>
                    <CardContent className="text-sm text-muted-foreground space-y-1">
                      <div>Tier: <span className="text-foreground font-medium">{selectedBusiness?.tier}</span></div>
                      <div>Industry: <span className="text-foreground font-medium">{selectedBusiness?.industry}</span></div>
                    </CardContent>
                  </Card>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <Card id="agents-section">
                  <CardHeader className="flex flex-row items-center justify-between">
                    <div>
                      <CardTitle>AI Agents</CardTitle>
                      <CardDescription>Operational assistants.</CardDescription>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Name</TableHead>
                          <TableHead>Type</TableHead>
                          <TableHead>Status</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {(agents || []).map((a: Agent) => (
                          <TableRow key={a._id}>
                            <TableCell className="max-w-[200px] truncate">{a.name}</TableCell>
                            <TableCell><Badge variant="outline">{a.type}</Badge></TableCell>
                            <TableCell>
                              <Badge variant={a.isActive ? "secondary" : "outline"}>
                                {a.isActive ? "Active" : "Inactive"}
                              </Badge>
                            </TableCell>
                          </TableRow>
                        ))}
                        {((agents || []).length === 0) && (
                          <TableRow>
                            <TableCell colSpan={3} className="text-muted-foreground">No agents yet.</TableCell>
                          </TableRow>
                        )}
                      </TableBody>
                    </Table>
                  </CardContent>
                </Card>

                <Card id="workflows-section">
                  <CardHeader className="flex flex-row items-center justify-between">
                    <div>
                      <CardTitle>Workflows</CardTitle>
                      <CardDescription>Automation pipelines.</CardDescription>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Name</TableHead>
                          <TableHead>Runs</TableHead>
                          <TableHead>Status</TableHead>
                          <TableHead className="text-right">Action</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {(workflows || []).map((w: Workflow) => (
                          <TableRow key={w._id}>
                            <TableCell className="max-w-[220px] truncate">{w.name}</TableCell>
                            <TableCell>
                              <span className="text-foreground">{w.runCount ?? 0}</span>
                              <span className="text-muted-foreground"> (done {w.completedRuns ?? 0})</span>
                            </TableCell>
                            <TableCell>
                              <Badge variant={w.isActive ? "secondary" : "outline"}>
                                {w.isActive ? "Active" : "Inactive"}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-right">
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={async () => {
                                  try {
                                    if (!user?._id) {
                                      toast("Please sign in again.");
                                      return;
                                    }
                                    const runId = await runWorkflow({
                                      workflowId: w._id as any,
                                      startedBy: user._id as any,
                                      dryRun: false,
                                    } as any);
                                    toast(`Workflow started: ${String(runId).slice(0, 6)}...`);
                                  } catch (e: any) {
                                    toast(e.message || "Failed to start workflow");
                                  }
                                }}
                              >
                                Run
                              </Button>
                            </TableCell>
                          </TableRow>
                        ))}
                        {((workflows || []).length === 0) && (
                          <TableRow>
                            <TableCell colSpan={4} className="text-muted-foreground">
                              No workflows yet. Try seeding templates, then create from template.
                            </TableCell>
                          </TableRow>
                        )}
                      </TableBody>
                    </Table>
                  </CardContent>
                </Card>
              </div>
            </>
          )}
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
}