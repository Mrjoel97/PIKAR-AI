import { useNavigate } from "react-router";
import { useAuth } from "@/hooks/use-auth";
import { useQuery, useMutation, useAction } from "convex/react";
import { api } from "@/convex/_generated/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { toast } from "sonner";
import { useState } from "react";
import { Play, Copy, BarChart3, Clock, Webhook } from "lucide-react";

export default function WorkflowsPage() {
  const navigate = useNavigate();
  const { isLoading: authLoading, isAuthenticated } = useAuth();
  const [selectedWorkflow, setSelectedWorkflow] = useState<string | null>(null);
  const [newWorkflowOpen, setNewWorkflowOpen] = useState(false);
  const [triggerDialogOpen, setTriggerDialogOpen] = useState(false);
  const [approvalDialogOpen, setApprovalDialogOpen] = useState(false);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [editedPipelines, setEditedPipelines] = useState<Record<string, any[]>>({});
  const [templateTierFilter, setTemplateTierFilter] = useState<string>("all");
  const [templateIndustryFilter, setTemplateIndustryFilter] = useState<string>("all");



  const businesses = useQuery(api.businesses.getUserBusinesses, {});
  const firstBizId = businesses?.[0]?._id;

  const workflows = useQuery(api.workflows.listWorkflows,
    firstBizId ? { businessId: firstBizId } : "skip");
  const simulateWorkflowAction = useAction(api.workflows.simulateWorkflow);
  const complianceScanAction = useAction(api.workflows.checkMarketingCompliance);
  const templates = useQuery(api.workflows.getTemplates,
    firstBizId ? { businessId: firstBizId } : "skip");
  const suggested = useQuery(api.workflows.suggested,
    firstBizId ? { businessId: firstBizId } : "skip");
  const executions = useQuery(api.workflows.getExecutions,
    selectedWorkflow ? {
      workflowId: selectedWorkflow as any,
      paginationOpts: { numItems: 10, cursor: null }
    } : "skip");

  const upsertWorkflow = useMutation(api.workflows.upsertWorkflow);
  const copyFromTemplate = useMutation(api.workflows.copyFromTemplate);
  const updateTrigger = useMutation(api.workflows.updateTrigger);
  const seedBusinessTemplates = useMutation(api.workflows.seedBusinessWorkflowTemplates);

  const [formData, setFormData] = useState({
    name: "",
    description: "",
    triggerType: "manual" as "manual" | "schedule" | "webhook",
    cron: "",
    eventKey: "",
    approvalRequired: false,
    approvalThreshold: 1,
    pipeline: JSON.stringify([
      { kind: "agent", input: "Process request" },
      { kind: "approval", approverRole: "manager" }
    ], null, 2),
    tags: "",
    saveAsTemplate: false,
  });

  if (authLoading) {
    return (
      <div className="max-w-6xl mx-auto p-6">
        <div className="animate-pulse h-8 w-40 rounded bg-muted mb-4" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="h-32 rounded-lg bg-muted" />
          <div className="h-32 rounded-lg bg-muted" />
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
            <CardDescription>Sign in to manage workflows.</CardDescription>
          </CardHeader>
          <CardContent className="flex gap-3">
            <Button onClick={() => navigate("/auth")}>Sign In</Button>
            <Button variant="outline" onClick={() => navigate("/")}>Go Home</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const handleCreateWorkflow = async () => {
    if (!firstBizId || !formData.name.trim()) {
      toast.error("Name is required");
      return;
    }

    try {
      let pipeline;
      try {
        pipeline = JSON.parse(formData.pipeline);
      } catch {
        toast.error("Invalid pipeline JSON");
        return;
      }

      const baseTags = formData.tags.split(",").map(t => t.trim()).filter(Boolean);
      const biz = businesses?.[0];
      const enrichTags = [
        ...(biz?.tier ? ["tier:" + biz.tier] : []),
        ...(biz?.industry ? ["industry:" + biz.industry] : []),
      ];
      await upsertWorkflow({
        businessId: firstBizId,
        name: formData.name.trim(),
        description: formData.description.trim() || undefined,
        trigger: {
          type: formData.triggerType,
          cron: formData.triggerType === "schedule" ? formData.cron : undefined,
          eventKey: formData.triggerType === "webhook" ? formData.eventKey : undefined
        },
        approval: {
          required: formData.approvalRequired,
          threshold: formData.approvalThreshold
        },
        pipeline,
        template: formData.saveAsTemplate,
        tags: Array.from(new Set([...baseTags, ...(formData.saveAsTemplate ? enrichTags : [])]))
      });

      toast.success("Workflow created successfully");
      setNewWorkflowOpen(false);
      setFormData({
        name: "",
        description: "",
        triggerType: "manual",
        cron: "",
        eventKey: "",
        approvalRequired: false,
        approvalThreshold: 1,
        pipeline: JSON.stringify([
          { kind: "agent", input: "Process request" },
          { kind: "approval", approverRole: "manager" }
        ], null, 2),
        tags: ""
      });
    } catch (error) {
      toast.error("Failed to create workflow");
    }
  };

  const handleCopyTemplate = async (templateId: string) => {
    try {
      await copyFromTemplate({ templateId: templateId as any });
      toast.success("Template copied successfully");
    } catch (error) {
      toast.error("Failed to copy template");
    }
  };

  const handleSimulate = async (workflow: any) => {
    try {
      const result = await simulateWorkflowAction({ workflowId: workflow._id });
      toast.success("Simulation complete", { description: `Steps: ${result.summary?.totalSteps ?? 0}, Agent: ${result.summary?.agentSteps ?? 0}, Approval: ${result.summary?.approvalSteps ?? 0}` });
      console.log("Simulation result", result);
    } catch (e: any) {
      toast.error(e?.message || "Simulation failed");
    }
  };

  const handleComplianceScan = async (workflow: any) => {
    if (!firstBizId) return;
    try {
      const content = [workflow.name, workflow.description, JSON.stringify(workflow.pipeline)].filter(Boolean).join(" ");
      const result = await complianceScanAction({
        businessId: firstBizId as any,
        subjectType: "workflow",
        subjectId: String(workflow._id),
        content,
      } as any);
      const flags = result?.flags?.length ?? 0;
      const status = result?.status ?? "unknown";
      toast.success(`Compliance: ${status}`, { description: `${flags} potential flags` });
      console.log("Compliance result", result);
    } catch (e: any) {
      toast.error(e?.message || "Compliance scan failed");
    }
  };

  const getStepKind = (s: any) => s?.kind || s?.type;

  const ensureLocalPipeline = (wf: any) => {
    if (!wf) return;
    setEditedPipelines((prev) => {
      if (prev[wf._id]) return prev;
      return { ...prev, [wf._id]: (wf.pipeline || []).map((x: any) => ({ ...x })) };
    });
  };

  const toggleExpand = (wf: any) => {
    ensureLocalPipeline(wf);
    setExpanded((prev) => ({ ...prev, [wf._id]: !prev[wf._id] }));
  };

  const toggleMMR = (wf: any, index: number, value: boolean) => {
    setEditedPipelines((prev) => {
      const current = prev[wf._id] ? [...prev[wf._id]] : (wf.pipeline || []).map((x: any) => ({ ...x }));
      const step = { ...current[index] };
      step.mmrRequired = value;
      const next = current[index + 1];
      const nextKind = next?.kind || next?.type;

      if (value) {
        // Auto-insert an approval step after this agent if not present
        if (nextKind !== "approval") {
          const biz = businesses?.[0];
          current.splice(index + 1, 0, { kind: "approval", approverRole: getDefaultApproverForTier(biz?.tier), autoInserted: true });
        }
      } else {
        // Remove auto-inserted approval if it exists right after
        if (nextKind === "approval" && next?.autoInserted) {
          current.splice(index + 1, 1);
        }
      }

      current[index] = step;
      return { ...prev, [wf._id]: current };
    });
  };
  const setStepField = (wf: any, index: number, patch: Record<string, any>) => {
    setEditedPipelines((prev) => {
      const current = prev[wf._id] ? [...prev[wf._id]] : (wf.pipeline || []).map((x: any) => ({ ...x }));
      current[index] = { ...current[index], ...patch };
      return { ...prev, [wf._id]: current };
    });
  };
  const getDefaultApproverForTier = (tier?: string) => {
    switch (tier) {
      case "solopreneur": return "Owner";
      case "startup": return "Manager";
      case "sme": return "Team Lead";
      case "enterprise": return "Compliance Lead";
      default: return "Manager";
    }
  };

  const addStep = (wf: any, index: number, kind: "agent" | "approval" | "delay" | "branch") => {
    const biz = businesses?.[0];
    const defaultApproval = getDefaultApproverForTier(biz?.tier);
    setEditedPipelines((prev) => {
      const current = prev[wf._id] ? [...prev[wf._id]] : (wf.pipeline || []).map((x: any) => ({ ...x }));
      const base: any = kind === "agent" ? { kind: "agent", title: "New Agent Step", agentPrompt: "" }
        : kind === "approval" ? { kind: "approval", approverRole: defaultApproval }
        : kind === "delay" ? { kind: "delay", delayMinutes: 60 }
        : { kind: "branch", condition: { metric: "metric", op: ">", value: 0 }, onTrueNext: (index + 2), onFalseNext: (index + 3) };
      current.splice(index + 1, 0, base);
      return { ...prev, [wf._id]: current };
    });
  };

  const removeStep = (wf: any, index: number) => {
    setEditedPipelines((prev) => {
      const current = prev[wf._id] ? [...prev[wf._id]] : (wf.pipeline || []).map((x: any) => ({ ...x }));
      if (current.length <= 1) return prev; // keep at least one step
      current.splice(index, 1);
      return { ...prev, [wf._id]: current };
    });
  };

  const moveStep = (wf: any, index: number, delta: number) => {
    setEditedPipelines((prev) => {
      const current = prev[wf._id] ? [...prev[wf._id]] : (wf.pipeline || []).map((x: any) => ({ ...x }));
      const newIndex = index + delta;
      if (newIndex < 0 || newIndex >= current.length) return prev;
      const [item] = current.splice(index, 1);
      current.splice(newIndex, 0, item);
      return { ...prev, [wf._id]: current };
    });
  };



  const savePipeline = async (wf: any) => {
    try {
      const pipeline = editedPipelines[wf._id] ?? wf.pipeline;
      await upsertWorkflow({
        id: wf._id,
        businessId: wf.businessId,
        name: wf.name,
        description: wf.description,
        trigger: wf.trigger,
        approval: wf.approval,
        pipeline,
        template: !!wf.template,
        tags: wf.tags || [],
      } as any);
      toast.success("Pipeline saved");
    } catch (e: any) {
      toast.error(e?.message || "Failed to save pipeline");
    }
  };

  const handleCreateFromSuggestion = async (suggestion: any) => {
    if (!firstBizId) return;

    try {
      await upsertWorkflow({
        businessId: firstBizId,
        name: suggestion.name,
        description: suggestion.description,
        trigger: suggestion.trigger,
        approval: { required: false, threshold: 0 },
        pipeline: suggestion.pipeline,
        template: false,
        tags: suggestion.tags
      });
      toast.success("Workflow created from suggestion");
    } catch (error) {
      toast.error("Failed to create workflow");
    }
  };

  const getTriggerIcon = (type: string) => {
    switch (type) {
      case "schedule": return <Clock className="h-4 w-4" />;
      case "webhook": return <Webhook className="h-4 w-4" />;
      default: return <Play className="h-4 w-4" />;
    }
  };

  return (
    <div className="max-w-6xl mx-auto px-4 md:px-6 py-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Orchestration & Workflows</h1>
          <p className="text-sm text-muted-foreground">Manage automated workflows and templates.</p>
        </div>

        <Dialog open={newWorkflowOpen} onOpenChange={setNewWorkflowOpen}>
          <DialogTrigger asChild>
            <Button>New Workflow</Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Create New Workflow</DialogTitle>
              <DialogDescription>Configure your automated workflow</DialogDescription>
            </DialogHeader>

            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="name">Name</Label>
                  <Input
                    id="name"
                    value={formData.name}
                    onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="Workflow name"
                  />
                </div>
                <div>
                  <Label htmlFor="trigger">Trigger Type</Label>
                  <Select value={formData.triggerType} onValueChange={(value: any) => setFormData(prev => ({ ...prev, triggerType: value }))}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="manual">Manual</SelectItem>
                      <SelectItem value="schedule">Schedule</SelectItem>
                      <SelectItem value="webhook">Webhook</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div>
                <Label htmlFor="description">Description</Label>
                <Input
                  id="description"
                  value={formData.description}
                  onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                  placeholder="Optional description"
                />
              </div>

              {formData.triggerType === "schedule" && (
                <div>
                  <Label htmlFor="cron">Cron Schedule</Label>
                  <Input
                    id="cron"
                    value={formData.cron}
                    onChange={(e) => setFormData(prev => ({ ...prev, cron: e.target.value }))}
                    placeholder="0 9 * * 1 (Every Monday at 9 AM)"
                  />
                </div>
              )}

              {formData.triggerType === "webhook" && (
                <div>
                  <Label htmlFor="eventKey">Event Key</Label>
                  <Input
                    id="eventKey"
                    value={formData.eventKey}
                    onChange={(e) => setFormData(prev => ({ ...prev, eventKey: e.target.value }))}
                    placeholder="unique-event-key"
                  />
                </div>
              )}

              <div className="flex items-center space-x-2">
                <Switch
                  id="approval"
                  checked={formData.approvalRequired}
                  onCheckedChange={(checked) => setFormData(prev => ({ ...prev, approvalRequired: checked }))}
                />
                <Label htmlFor="approval">Require Approval</Label>
              </div>

              <div className="flex items-center space-x-2">
                <Switch
                  id="template"
                  checked={formData.saveAsTemplate}
                  onCheckedChange={(checked) => setFormData(prev => ({ ...prev, saveAsTemplate: checked }))}
                />
                <Label htmlFor="template">Save as Template</Label>
              </div>

              {formData.approvalRequired && (
                <div>
                  <Label htmlFor="threshold">Approval Threshold</Label>
                  <Input
                    id="threshold"
                    type="number"
                    value={formData.approvalThreshold}
                    onChange={(e) => setFormData(prev => ({ ...prev, approvalThreshold: parseInt(e.target.value) || 1 }))}
                    min="1"
                  />
                </div>
              )}

              <div>
                <Label htmlFor="pipeline">Pipeline (JSON)</Label>
                <Textarea
                  id="pipeline"
                  value={formData.pipeline}
                  onChange={(e) => setFormData(prev => ({ ...prev, pipeline: e.target.value }))}
                  rows={8}
                  className="font-mono text-sm"
                />
              </div>

              <div>
                <Label htmlFor="tags">Tags (comma-separated)</Label>
                <Input
                  id="tags"
                  value={formData.tags}
                  onChange={(e) => setFormData(prev => ({ ...prev, tags: e.target.value }))}
                  placeholder="marketing, automation"
                />
              </div>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setNewWorkflowOpen(false)}>Cancel</Button>
              <Button onClick={handleCreateWorkflow}>Create Workflow</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <Tabs defaultValue="all" className="space-y-4">
        <TabsList>
          <TabsTrigger value="all">All Workflows</TabsTrigger>
          <TabsTrigger value="templates">Templates</TabsTrigger>
          <TabsTrigger value="suggested">Suggested</TabsTrigger>
          <TabsTrigger value="analytics">Analytics</TabsTrigger>
        </TabsList>

        <TabsContent value="all" className="space-y-4">
          <div className="grid gap-4">
            {workflows?.map((workflow: any) => (
              <Card key={workflow._id}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {getTriggerIcon(workflow.trigger.type)}
                      <CardTitle className="text-lg">{workflow.name}</CardTitle>
                      {workflow.template && <Badge variant="secondary">Template</Badge>}
                    </div>
                    <div className="flex gap-2">
                      <Button size="sm" variant="outline" onClick={() => handleSimulate(workflow)}>
                        Simulate
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => handleComplianceScan(workflow)}>
                        Compliance Scan
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => setSelectedWorkflow(workflow._id)}>
                        <BarChart3 className="h-4 w-4 mr-1" />
                        Executions
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => toggleExpand(workflow)}>
                        {expanded[workflow._id] ? "Hide" : "Pipeline"}
                      </Button>
                    </div>
                  </div>
                  {workflow.description && (
                    <CardDescription>{workflow.description}</CardDescription>
                  )}
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-4 text-sm text-muted-foreground">
                    <span>Steps: {workflow.pipeline.length}</span>
                    <span>Trigger: {workflow.trigger.type}</span>
                    {workflow.trigger.cron && <span>Schedule: {workflow.trigger.cron}</span>}
                    {workflow.trigger.eventKey && <span>Event: {workflow.trigger.eventKey}</span>}
                    {workflow.approval.required && <span>Approval Required</span>}
                  </div>
                  {workflow.tags.length > 0 && (
                    <div className="flex gap-1 mt-2">
                      {workflow.tags.map((tag: string) => (
                        <Badge key={tag} variant="outline" className="text-xs">{tag}</Badge>
                      ))}
                    </div>
                  )}
                </CardContent>

	                {expanded[workflow._id] && (
	                  <div className="border-t pt-3 space-y-2">
	                    {(editedPipelines[workflow._id] ?? workflow.pipeline).map((step: any, idx: number) => {
	                      const kind = getStepKind(step);
	                      return (
	                        <div key={idx} className="flex items-center justify-between p-2 border rounded">
	                          <div className="text-sm">
	                            <div className="font-medium capitalize">{kind}</div>
	                            {kind === "branch" && (
	                              <div className="text-xs text-muted-foreground">
	                                IF {step?.condition?.metric} {step?.condition?.op} {String(step?.condition?.value)} THEN → {step?.onTrueNext} ELSE → {step?.onFalseNext}
	                              </div>
	                            )}
	                            {kind === "approval" && (
	                              <div className="text-xs text-muted-foreground">Approver: {step?.approverRole || step?.config?.approverRole || "manager"}</div>
	                            )}
	                            {kind === "delay" && (
	                              <div className="text-xs text-muted-foreground">Delay: {step?.delayMinutes || step?.config?.delayMinutes || 0} min</div>

	                            )}
	                          </div>
                            <div className="mt-1 flex flex-wrap items-center gap-2">
                              <Input
                                className="h-8 w-64"
                                placeholder="Step title (optional)"
                                value={step?.title || ""}
                                onChange={(e) => setStepField(workflow, idx, { title: e.target.value })}
                              />
                              {kind === "approval" && (
                                <Input
                                  className="h-8 w-56"
                                  placeholder="Approver role"
                                  value={step?.approverRole || step?.config?.approverRole || ""}
                                  onChange={(e) => setStepField(workflow, idx, { approverRole: e.target.value })}
                                />
                              )}
                              {kind === "delay" && (
                                <Input
                                  type="number"
                                  className="h-8 w-40"
                                  placeholder="Delay minutes"
                                  value={String(step?.delayMinutes ?? step?.config?.delayMinutes ?? 0)}
                                  onChange={(e) => setStepField(workflow, idx, { delayMinutes: parseInt(e.target.value) || 0 })}
                                />
                              )}
                            </div>
	                          {kind === "agent" && (
	                            <div className="flex items-center gap-2">
	                              <Switch checked={!!step?.mmrRequired} onCheckedChange={(v) => toggleMMR(workflow, idx, !!v)} id={`mmr-${workflow._id}-${idx}`} />
	                              <Label htmlFor={`mmr-${workflow._id}-${idx}`}>Require human review</Label>
	                            </div>
	                          )}
                          <div className="flex items-center gap-1">
                            <Button size="sm" variant="outline" onClick={() => addStep(workflow, idx, "agent")}>+Agent</Button>
                            <Button size="sm" variant="outline" onClick={() => addStep(workflow, idx, "approval")}>+Approval</Button>
                            <Button size="sm" variant="outline" onClick={() => addStep(workflow, idx, "delay")}>+Delay</Button>
                            <Button size="sm" variant="outline" onClick={() => addStep(workflow, idx, "branch")}>+Branch</Button>
                            <Button size="sm" variant="outline" onClick={() => moveStep(workflow, idx, -1)}>Up</Button>
                            <Button size="sm" variant="outline" onClick={() => moveStep(workflow, idx, 1)}>Down</Button>
                            <Button size="sm" variant="destructive" onClick={() => removeStep(workflow, idx)}>Remove</Button>
                          </div>
	                        </div>
	                      );
	                    })}
	                    <div className="pt-1">
	                      <Button size="sm" onClick={() => savePipeline(workflow)}>Save pipeline</Button>
	                    </div>
	                  </div>
	                )}

              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="templates" className="space-y-4">
          <div className="flex items-center gap-2">
            <div className="text-sm text-muted-foreground">Filter:</div>

            <Select value={templateTierFilter} onValueChange={setTemplateTierFilter}>
              <SelectTrigger className="w-36"><SelectValue placeholder="Tier" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Tiers</SelectItem>
                <SelectItem value="solopreneur">Solopreneur</SelectItem>
                <SelectItem value="startup">Startup</SelectItem>
                <SelectItem value="sme">SME</SelectItem>
                <SelectItem value="enterprise">Enterprise</SelectItem>
              </SelectContent>
            </Select>
            <Select value={templateIndustryFilter} onValueChange={setTemplateIndustryFilter}>
              <SelectTrigger className="w-44"><SelectValue placeholder="Industry" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Industries</SelectItem>
                <SelectItem value="software">Software</SelectItem>
                <SelectItem value="services">Services</SelectItem>
                <SelectItem value="retail">Retail</SelectItem>
                <SelectItem value="other">Other</SelectItem>
              </SelectContent>
            </Select>
            <div className="ml-auto">
              <Button variant="outline" size="sm" disabled={!firstBizId} onClick={async () => {
                try {
                  const res = await seedBusinessTemplates({ businessId: firstBizId as any, perTier: 30 } as any);
                  toast.success("Templates seeded", { description: `${res?.inserted ?? 0} inserted` });
                } catch (e: any) {
                  toast.error(e?.message || "Seeding failed");
                }
              }}>Seed 120 templates</Button>
            </div>
          </div>
          <div className="grid gap-4">
            {templates?.filter((t: any) => {
              const tags: string[] = t.tags || [];
              const tierOk = templateTierFilter === "all" || tags.includes(`tier:${templateTierFilter}`);
              const indOk = templateIndustryFilter === "all" || tags.includes(`industry:${templateIndustryFilter}`);
              return tierOk && indOk;
            }).map((template: any) => (
              <Card key={template._id}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="text-lg">{template.name}</CardTitle>
                      {template.description && (
                        <CardDescription>{template.description}</CardDescription>
                      )}
                    </div>
                    <Button onClick={() => handleCopyTemplate(template._id)}>
                      <Copy className="h-4 w-4 mr-1" />
                      Copy Template
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-4 text-sm text-muted-foreground">
                    <span>Steps: {template.pipeline.length}</span>
                    <span>Trigger: {template.trigger.type}</span>
                  </div>
                  {template.tags.length > 0 && (
                    <div className="flex gap-1 mt-2">
                      {template.tags.map((tag: string) => (
                        <Badge key={tag} variant="outline" className="text-xs">{tag}</Badge>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="suggested" className="space-y-4">
          <div className="grid gap-4">
            {suggested?.map((suggestion: any, index: number) => (
              <Card key={index}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="text-lg">{suggestion.name}</CardTitle>
                      <CardDescription>{suggestion.description}</CardDescription>
                    </div>
                    <Button onClick={() => handleCreateFromSuggestion(suggestion)}>
                      Create Workflow
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-4 text-sm text-muted-foreground">
                    <span>Steps: {suggestion.pipeline.length}</span>
                    <span>Trigger: {suggestion.trigger.type}</span>
                  </div>
                  <div className="flex gap-1 mt-2">
                    {suggestion.tags.map((tag: string) => (
                      <Badge key={tag} variant="outline" className="text-xs">{tag}</Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="analytics" className="space-y-4">
          {selectedWorkflow && executions && (
            <Card>
              <CardHeader>
                <CardTitle>Execution History</CardTitle>
                <CardDescription>Recent workflow executions and metrics</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {executions.page.map((execution: any) => (
                    <div key={execution._id} className="flex items-center justify-between p-3 border rounded">
                      <div>
                        <div className="font-medium">{execution.summary}</div>
                        <div className="text-sm text-muted-foreground">
                          {new Date(execution._creationTime).toLocaleString()} • {execution.mode} mode
                        </div>
                      </div>
                      <div className="text-right">
                        <Badge variant={execution.status === "succeeded" ? "default" : "destructive"}>
                          {execution.status}
                        </Badge>
                        <div className="text-sm text-muted-foreground mt-1">
                          ROI: ${execution.metrics.roi.toFixed(2)}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {!selectedWorkflow && (
            <Card>
              <CardHeader>
                <CardTitle>Select a Workflow</CardTitle>
                <CardDescription>Choose a workflow from the "All Workflows" tab to view analytics</CardDescription>
              </CardHeader>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}