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
import { useEffect, useState } from "react";
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
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Search } from "lucide-react";

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
  const [searchQuery, setSearchQuery] = useState("");

  const businessesLoaded = userBusinesses !== undefined;
  const hasBusinesses = (userBusinesses?.length || 0) > 0;

  // Select first business when loaded
  useEffect(() => {
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

  const normalizedQuery = searchQuery.trim().toLowerCase();

  const filteredInitiatives = (() => {
    const list = initiatives || [];
    if (!normalizedQuery) return list;
    return list.filter((i) =>
      [i.title, i.status, i.priority].some((f) => String(f).toLowerCase().includes(normalizedQuery))
    );
  })();

  const filteredAgents = (() => {
    const list = agents || [];
    if (!normalizedQuery) return list;
    return list.filter((a) =>
      [a.name, a.type, a.isActive ? "active" : "inactive"].some((f) =>
        String(f).toLowerCase().includes(normalizedQuery)
      )
    );
  })();

  const filteredWorkflows = (() => {
    const list = workflows || [];
    if (!normalizedQuery) return list;
    return list.filter((w) =>
      [w.name, w.description, w.isActive ? "active" : "inactive"].some((f) =>
        String(f).toLowerCase().includes(normalizedQuery)
      )
    );
  })();

  const stats = [
    { label: "Initiatives", value: initiatives?.length ?? 0 },
    { label: "AI Agents", value: agents?.length ?? 0 },
    { label: "Workflows", value: workflows?.length ?? 0 },
  ];

  return (
    <SidebarProvider>
      <Sidebar variant="inset" collapsible="offcanvas" className="bg-gradient-to-b from-emerald-700 via-emerald-800 to-teal-900 text-white shadow-xl">
        <SidebarHeader>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-white/70" aria-hidden />
            <SidebarInput
              placeholder="Search (Initiatives, Agents, Workflows)…"
              aria-label="Search"
              value={searchQuery}
              onChange={(e: any) => setSearchQuery(e.target.value)}
              className="pl-9 pr-3 h-9 bg-white text-emerald-900 placeholder-emerald-600 border-transparent rounded-full focus-visible:ring-2 focus-visible:ring-emerald-400/50 focus-visible:border-emerald-300 transition-shadow shadow-sm"
            />
          </div>
        </SidebarHeader>

        <SidebarContent>
          <SidebarGroup>
            <SidebarGroupLabel className="text-emerald-200/90 uppercase tracking-wide">Menu</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    onClick={() => scrollToSection("overview")}
                    tooltip="Overview"
                    className="text-white hover:bg-white/10 active:bg-white/15 focus-visible:ring-emerald-400/40 rounded-xl"
                  >
                    <Home />
                    <span>Dashboard</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    onClick={() => scrollToSection("initiatives-section")}
                    tooltip="Initiatives"
                    className="text-white hover:bg-white/10 active:bg-white/15 focus-visible:ring-emerald-400/40 rounded-xl"
                  >
                    <Layers />
                    <span>Initiatives</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    onClick={() => scrollToSection("agents-section")}
                    tooltip="AI Agents"
                    className="text-white hover:bg-white/10 active:bg-white/15 focus-visible:ring-emerald-400/40 rounded-xl"
                  >
                    <BotIcon />
                    <span>AI Agents</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    onClick={() => scrollToSection("workflows-section")}
                    tooltip="Workflows"
                    className="text-white hover:bg-white/10 active:bg-white/15 focus-visible:ring-emerald-400/40 rounded-xl"
                  >
                    <WorkflowIcon />
                    <span>Workflows</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>

          <SidebarSeparator className="bg-white/15" />

          <SidebarGroup>
            <SidebarGroupLabel className="text-emerald-200/90 uppercase tracking-wide">Organization</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    onClick={() => scrollToSection("business-info")}
                    tooltip="Business Info"
                    className="text-white hover:bg-white/10 active:bg-white/15 focus-visible:ring-emerald-400/40 rounded-xl"
                  >
                    <SettingsIcon />
                    <span>Business Info</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    onClick={() => scrollToSection("overview")}
                    tooltip="Analytics"
                    className="text-white hover:bg-white/10 active:bg-white/15 focus-visible:ring-emerald-400/40 rounded-xl"
                  >
                    <BarChart3 />
                    <span>Analytics</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        </SidebarContent>

        <SidebarFooter>
          {/* Premium profile card with plan and status; optimized for mobile */}
          <div className="rounded-2xl bg-white/10 px-3 py-3 ring-1 ring-white/15 space-y-3 sm:px-4 sm:py-4">
            <div className="flex items-center gap-3">
              <div className="relative">
                <Avatar className="h-10 w-10 sm:h-11 sm:w-11 border border-white/30 ring-2 ring-emerald-600/60">
                  <AvatarFallback className="bg-emerald-700 text-white text-sm">
                    {String(user?.companyName || user?.email || "U")
                      .split(" ")
                      .map((s: string) => s[0])
                      .join("")
                      .slice(0, 2)
                      .toUpperCase()}
                  </AvatarFallback>
                </Avatar>
                <span
                  className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full bg-emerald-400 ring-2 ring-emerald-900"
                  aria-label="Online"
                />
              </div>
              <div className="min-w-0">
                <div className="text-sm font-semibold truncate text-white">
                  {user?.companyName || "Your Organization"}
                </div>
                <div className="text-xs text-white/80 truncate">
                  {user?.email || "user@example.com"}
                </div>
              </div>
            </div>
            <div className="flex items-center justify-between gap-3">
              <span className="text-xs text-emerald-100/90 bg-emerald-700/40 border border-white/15 px-2 py-1 rounded-full">
                {selectedBusiness?.tier ? `${selectedBusiness.tier} plan` : "Starter"}
              </span>
              <span className="text-xs text-emerald-100/90 flex items-center gap-1 bg-emerald-700/40 border border-white/15 px-2 py-1 rounded-full">
                <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-400"></span>
                Online
              </span>
            </div>
          </div>
        </SidebarFooter>
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
            <Card className="bg-white">
              <CardContent className="p-6">
                <div className="animate-pulse h-6 w-44 rounded bg-muted" />
              </CardContent>
            </Card>
          ) : !hasBusinesses ? (
            <Card className="bg-white">
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
                  <Card key={s.label} className="bg-white">
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
                <Card className="lg:col-span-2 bg-white" id="initiatives-section">
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
                        {(filteredInitiatives || []).map((i: Initiative) => (
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
                        {((filteredInitiatives || []).length === 0) && (
                          <TableRow>
                            <TableCell colSpan={4} className="text-muted-foreground">
                              {normalizedQuery ? "No results match your search." : "No initiatives yet."}
                            </TableCell>
                          </TableRow>
                        )}
                      </TableBody>
                    </Table>
                  </CardContent>
                </Card>

                <div className="space-y-6">
                  <Card className="bg-white">
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

                  <Card id="business-info" className="bg-white">
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
                <Card id="agents-section" className="bg-white">
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
                        {(filteredAgents || []).map((a: Agent) => (
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
                        {((filteredAgents || []).length === 0) && (
                          <TableRow>
                            <TableCell colSpan={3} className="text-muted-foreground">
                              {normalizedQuery ? "No results match your search." : "No agents yet."}
                            </TableCell>
                          </TableRow>
                        )}
                      </TableBody>
                    </Table>
                  </CardContent>
                </Card>

                <Card id="workflows-section" className="bg-white">
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
                        {(filteredWorkflows || []).map((w: Workflow) => (
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
                        {((filteredWorkflows || []).length === 0) && (
                          <TableRow>
                            <TableCell colSpan={4} className="text-muted-foreground">
                              {normalizedQuery
                                ? "No results match your search."
                                : "No workflows yet. Try seeding templates, then create from template."}
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