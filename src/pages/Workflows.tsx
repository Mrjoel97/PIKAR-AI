import { useNavigate } from "react-router";
import { useAuth } from "@/hooks/use-auth";
import { useQuery, useMutation } from "convex/react";
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
import { Play, Square, Copy, Settings, BarChart3, Clock, Webhook, Calendar } from "lucide-react";

export default function WorkflowsPage() {
  const navigate = useNavigate();
  const { isLoading: authLoading, isAuthenticated } = useAuth();
  const [selectedWorkflow, setSelectedWorkflow] = useState<string | null>(null);
  const [newWorkflowOpen, setNewWorkflowOpen] = useState(false);
  const [triggerDialogOpen, setTriggerDialogOpen] = useState(false);
  const [approvalDialogOpen, setApprovalDialogOpen] = useState(false);

  const businesses = useQuery(api.businesses.getUserBusinesses, {});
  const firstBizId = businesses?.[0]?._id;

  const workflows = useQuery(api.workflows.listWorkflows, 
    firstBizId ? { businessId: firstBizId } : "skip");
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
  const runWorkflow = useMutation(api.workflows.run);
  const updateTrigger = useMutation(api.workflows.updateTrigger);

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
    tags: ""
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
        template: false,
        tags: formData.tags.split(",").map(t => t.trim()).filter(Boolean)
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

  const handleRunWorkflow = async (workflowId: string, mode: "run" | "dry") => {
    try {
      await runWorkflow({ workflowId: workflowId as any, mode });
      toast.success(`Workflow ${mode === "dry" ? "dry run" : "execution"} started`);
    } catch (error) {
      toast.error(`Failed to ${mode === "dry" ? "dry run" : "run"} workflow`);
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
            {workflows?.map((workflow) => (
              <Card key={workflow._id}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {getTriggerIcon(workflow.trigger.type)}
                      <CardTitle className="text-lg">{workflow.name}</CardTitle>
                      {workflow.template && <Badge variant="secondary">Template</Badge>}
                    </div>
                    <div className="flex gap-2">
                      <Button size="sm" variant="outline" onClick={() => handleRunWorkflow(workflow._id, "dry")}>
                        <Square className="h-4 w-4 mr-1" />
                        Dry Run
                      </Button>
                      <Button size="sm" onClick={() => handleRunWorkflow(workflow._id, "run")}>
                        <Play className="h-4 w-4 mr-1" />
                        Run
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => setSelectedWorkflow(workflow._id)}>
                        <BarChart3 className="h-4 w-4 mr-1" />
                        Executions
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
                      {workflow.tags.map((tag) => (
                        <Badge key={tag} variant="outline" className="text-xs">{tag}</Badge>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="templates" className="space-y-4">
          <div className="grid gap-4">
            {templates?.map((template) => (
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
                      {template.tags.map((tag) => (
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
            {suggested?.map((suggestion, index) => (
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