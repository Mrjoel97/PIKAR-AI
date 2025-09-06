import { useEffect, useState, useMemo } from "react";
import { useNavigate } from "react-router";
import { useQuery, useAction, useMutation } from "convex/react";
import { api } from "@/convex/_generated/api";
import { useAuth } from "@/hooks/use-auth";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { toast } from "sonner";

type Business = {
  _id: string;
  name: string;
  tier: "solopreneur" | "startup" | "sme" | "enterprise";
  industry: string;
};

type WorkflowT = {
  _id: string;
  name: string;
  description: string;
  isActive: boolean;
  runCount?: number;
  completedRuns?: number;
  lastRunStatus?: string | null;
  lastRunAt?: number | null;
};

type Template = {
  _id: string;
  name: string;
  category: string;
  description: string;
  steps: Array<{ type: "agent" | "approval" | "delay"; title: string }>;
};

export default function WorkflowsPage() {
  const navigate = useNavigate();
  const { isLoading: authLoading, isAuthenticated, user } = useAuth();

  const userBusinesses = useQuery(api.businesses.getUserBusinesses, {});
  const [selectedBusinessId, setSelectedBusinessId] = useState<string | null>(null);
  const [globalSearch, setGlobalSearch] = useState("");
  const [workflowSearch, setWorkflowSearch] = useState("");
  const [tab, setTab] = useState<"all" | "templates">("all");

  const templates = useQuery(api.workflows.listTemplates, {} as any);

  const simulate = useAction(api.workflows.simulateWorkflow);
  const saveBlueprint = useMutation(api.workflows.createBlueprintFromWorkflow);

  useEffect(() => {
    if (!selectedBusinessId && (userBusinesses?.length || 0) > 0) {
      setSelectedBusinessId(userBusinesses![0]._id);
    }
  }, [selectedBusinessId, userBusinesses]);

  const workflows = useQuery(
    api.workflows.listWorkflows,
    selectedBusinessId ? ({ businessId: selectedBusinessId } as any) : ("skip" as any)
  );
  const seedTemplates = useMutation(api.workflows.seedTemplates);
  const runWorkflow = useAction(api.workflows.runWorkflow);
  const createFromTemplate = useMutation(api.workflows.createFromTemplate);

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
            <CardDescription>Sign in to view your workflows.</CardDescription>
          </CardHeader>
          <CardContent className="flex gap-3">
            <Button onClick={() => navigate("/auth")}>Sign In</Button>
            <Button variant="outline" onClick={() => navigate("/")}>Go Home</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const normalizedGlobal = globalSearch.trim().toLowerCase();
  const normalizedLocal = workflowSearch.trim().toLowerCase();
  const filteredWorkflows = (workflows || []).filter((w: WorkflowT) => {
    const fields = [w.name, w.description, w.isActive ? "active" : "inactive"].map((x) =>
      String(x).toLowerCase()
    );
    const matches = (q: string) => fields.some((f) => f.includes(q));
    const okGlobal = normalizedGlobal ? matches(normalizedGlobal) : true;
    const okLocal = normalizedLocal ? matches(normalizedLocal) : true;
    return okGlobal && okLocal;
  });

  return (
    <div className="max-w-6xl mx-auto px-4 md:px-6 py-6 space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Workflows</h1>
          <p className="text-sm text-muted-foreground">Automation pipelines.</p>
        </div>
        <div className="flex flex-col sm:flex-row gap-3">
          {userBusinesses && userBusinesses.length > 0 ? (
            <Select value={selectedBusinessId ?? ""} onValueChange={(v) => setSelectedBusinessId(v)}>
              <SelectTrigger className="min-w-56">
                <SelectValue placeholder="Select business" />
              </SelectTrigger>
              <SelectContent>
                {userBusinesses.map((b: Business) => (
                  <SelectItem key={b._id} value={b._id}>
                    {b.name} <span className="text-muted-foreground">• {b.tier}</span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : null}
          <Input
            value={globalSearch}
            onChange={(e) => setGlobalSearch(e.target.value)}
            placeholder="Search (Initiatives, Agents, Workflows)…"
            className="h-9"
          />
          <Button variant="outline" onClick={() => navigate("/onboarding")}>Onboarding</Button>
        </div>
      </div>

      <Card className="bg-white">
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Workflows</CardTitle>
            <CardDescription>View and run workflows.</CardDescription>
          </div>
          <div className="w-full max-w-xs">
            <Input
              value={workflowSearch}
              onChange={(e) => setWorkflowSearch(e.target.value)}
              placeholder="Search workflows…"
              className="h-9"
              aria-label="Search workflows"
            />
          </div>
        </CardHeader>
        <CardContent>
          <Tabs value={tab} onValueChange={(v: string) => setTab(v === "templates" ? "templates" : "all")} className="w-full">
            <TabsList>
              <TabsTrigger value="all">All Workflows</TabsTrigger>
              <TabsTrigger value="templates">Templates</TabsTrigger>
            </TabsList>

            <TabsContent value="all" className="mt-4">
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
                  {filteredWorkflows.map((w: WorkflowT) => (
                    <TableRow key={w._id}>
                      <TableCell className="max-w-[240px] truncate">{w.name}</TableCell>
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
                        <div className="flex justify-end gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={async () => {
                              if (!user?._id) {
                                toast("You must be signed in to run workflows.");
                                return;
                              }
                              try {
                                const runId = await runWorkflow({
                                  workflowId: w._id as any,
                                  startedBy: user._id as any,
                                  dryRun: false,
                                } as any);
                                toast(`Workflow started: ${String(runId).slice(0, 6)}...`);
                              } catch (e: any) {
                                toast(e?.message || "Failed to start workflow");
                              }
                            }}
                          >
                            Run
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={async () => {
                              try {
                                const result = await simulate({
                                  workflowId: w._id as any,
                                  params: {}, // extend with runtime params in future UI
                                } as any);
                                const summary = result?.summary;
                                const checks = (result?.complianceChecks || []).length;
                                toast(
                                  `Dry run: ${summary?.totalSteps ?? 0} steps • Agents: ${summary?.agentSteps ?? 0} • Approvals: ${summary?.approvalSteps ?? 0} • Delays: ${summary?.delaySteps ?? 0}` +
                                  (checks ? ` • Compliance checks: ${checks}` : "")
                                );
                              } catch (e: any) {
                                toast(e?.message || "Failed to simulate workflow");
                              }
                            }}
                          >
                            Dry Run
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={async () => {
                              try {
                                const id = await saveBlueprint({
                                  workflowId: w._id as any,
                                  name: `${w.name} (Blueprint)`,
                                  description: w.description,
                                  category: "Custom",
                                } as any);
                                if (id) {
                                  toast("Saved as template (Custom). Check the Templates tab.");
                                  setTab("templates");
                                }
                              } catch (e: any) {
                                toast(e?.message || "Failed to save as template");
                              }
                            }}
                          >
                            Save as Template
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                  {filteredWorkflows.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={4} className="text-muted-foreground">
                        {workflowSearch || globalSearch
                          ? "No results match your search."
                          : "No workflows yet. Try the Templates tab to create from templates."}
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TabsContent>

            <TabsContent value="templates" className="mt-4">
              <div className="space-y-4">
                <div className="rounded-lg border p-4 bg-white">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="text-sm font-medium">Workflow Templates</div>
                      <div className="text-sm text-muted-foreground">
                        Seed ready-made automations tailored for solopreneurs. Seeding is safe and won't duplicate templates.
                      </div>
                      <div className="mt-1 text-xs text-muted-foreground">
                        {Array.isArray(templates) ? `${templates.length} templates available` : "Loading templates…"}
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        onClick={async () => {
                          try {
                            await seedTemplates({});
                            toast("Workflow templates are ready.");
                          } catch (e: any) {
                            toast(e.message || "Failed to seed templates");
                          }
                        }}
                      >
                        Seed Templates
                      </Button>
                      <Button variant="outline" onClick={() => setTab("all")}>
                        View All Workflows
                      </Button>
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {(templates || []).map((t: Template) => (
                    <div
                      key={t._id}
                      className="rounded-xl border bg-white p-4 hover:shadow-sm transition-shadow"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="text-base font-semibold truncate">{t.name}</div>
                          <div className="mt-1 text-xs text-muted-foreground line-clamp-2">{t.description}</div>
                        </div>
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-100">
                          {t.category}
                        </span>
                      </div>

                      <div className="mt-3 space-y-2">
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-300" aria-hidden />
                          {t.steps.length} steps
                        </div>
                        <div className="flex flex-wrap gap-1.5">
                          {t.steps.slice(0, 4).map((s, idx) => (
                            <span
                              key={idx}
                              className="text-[10px] px-2 py-0.5 rounded-full bg-muted text-foreground border"
                            >
                              {s.type}
                            </span>
                          ))}
                          {t.steps.length > 4 && (
                            <span className="text-[10px] px-2 py-0.5 rounded-full bg-muted text-foreground border">
                              +{t.steps.length - 4} more
                            </span>
                          )}
                        </div>
                      </div>

                      <div className="mt-4 flex justify-end">
                        <Button
                          size="sm"
                          disabled={!selectedBusinessId || !user?._id}
                          onClick={async () => {
                            if (!selectedBusinessId || !user?._id) {
                              toast("Select a business first.");
                              return;
                            }
                            try {
                              await createFromTemplate({
                                businessId: selectedBusinessId as any,
                                templateId: t._id as any,
                                createdBy: user._id as any,
                              } as any);
                              toast("Workflow created from template.");
                              setTab("all");
                            } catch (e: any) {
                              toast(e.message || "Failed to create workflow from template");
                            }
                          }}
                        >
                          Use template
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>

                {Array.isArray(templates) && templates.length === 0 && (
                  <div className="rounded-md border bg-white p-6 text-sm text-muted-foreground text-center">
                    No templates yet. Click "Seed Templates" to add 20+ templates.
                  </div>
                )}
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}