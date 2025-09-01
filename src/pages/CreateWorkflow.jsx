import React, { useMemo, useState } from "react";
import { DragDropContext, Droppable, Draggable } from "@hello-pangea/dnd";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Workflow } from "@/api/entities";
import { WorkflowStep } from "@/api/entities";
import { AuditLog } from "@/api/entities";
import { createPageUrl } from "@/utils";
import { toast } from "sonner";
import { Plus, GripVertical, Trash2, Play, Rocket, FlaskConical } from "lucide-react";
import StepInputEditor from "@/components/workflow/StepInputEditor";
import DryRunModal from "@/components/workflow/DryRunModal";
import runAgent from "@/components/workflow/runAgent";
import TemplateGallery from "@/components/workflow/TemplateGallery";

const agentOptions = [
  { value: 'Strategic Planning', label: 'Strategic Planning' },
  { value: 'Content Creation', label: 'Content Creation' },
  { value: 'Customer Support', label: 'Customer Support' },
  { value: 'Sales Intelligence', label: 'Sales Intelligence' },
  { value: 'Data Analysis', label: 'Data Analysis' },
  { value: 'Marketing Automation', label: 'Marketing Automation' },
  { value: 'Financial Analysis', label: 'Financial Analysis' },
  { value: 'HR & Recruitment', label: 'HR & Recruitment' },
  { value: 'Compliance & Risk', label: 'Compliance & Risk' },
  { value: 'Operations Optimization', label: 'Operations Optimization' },
];

const categories = [
  { value: "strategic_planning", label: "Strategic Planning" },
  { value: "market_analysis", label: "Market Analysis" },
  { value: "compliance", label: "Compliance" },
  { value: "financial", label: "Financial" },
  { value: "operations", label: "Operations" },
  { value: "hr", label: "HR" },
  { value: "custom", label: "Custom" },
];

export default function CreateWorkflow() {
  const [wf, setWf] = useState({
    workflow_name: "",
    workflow_description: "",
    workflow_category: "custom",
  });

  const [steps, setSteps] = useState([
    { id: crypto.randomUUID(), agent_name: "Data Analysis", step_prompt: "", step_input: {}, step_order: 1 },
  ]);

  const [dryRunOpen, setDryRunOpen] = useState(false);
  const [dryRunLoading, setDryRunLoading] = useState(false);
  const [dryRunOutput, setDryRunOutput] = useState("");
  const [dryRunAgent, setDryRunAgent] = useState("");

  const canSave = useMemo(() => wf.workflow_name.trim().length > 0 && steps.length > 0, [wf, steps]);
  const canPublish = useMemo(
    () => canSave && steps.every(s => s.agent_name && s.step_prompt.trim().length > 0),
    [canSave, steps]
  );

  const addStep = () => {
    const next = { id: crypto.randomUUID(), agent_name: agentOptions[0].value, step_prompt: "", step_input: {}, step_order: steps.length + 1 };
    setSteps([...steps, next]);
  };

  const removeStep = (id) => {
    const filtered = steps.filter(s => s.id !== id).map((s, idx) => ({ ...s, step_order: idx + 1 }));
    setSteps(filtered);
  };

  const onDragEnd = (result) => {
    if (!result.destination) return;
    const reordered = Array.from(steps);
    const [moved] = reordered.splice(result.source.index, 1);
    reordered.splice(result.destination.index, 0, moved);
    setSteps(reordered.map((s, idx) => ({ ...s, step_order: idx + 1 })));
  };

  const updateStep = (id, patch) => {
    setSteps(prev => prev.map(s => (s.id === id ? { ...s, ...patch } : s)));
  };

  const handleDryRun = async (step) => {
    setDryRunAgent(step.agent_name);
    setDryRunOpen(true);
    setDryRunLoading(true);
    setDryRunOutput("");
    try {
      const file_urls =
        (step.step_input && (step.step_input.file_urls || step.step_input.files || step.step_input.context_files)) ||
        [];
      const { text } = await runAgent(step.agent_name, {
        prompt: step.step_prompt,
        input: step.step_input || {},
        file_urls: Array.isArray(file_urls) ? file_urls : [],
      });
      setDryRunOutput(text || "No output.");
    } catch (e) {
      setDryRunOutput(`Error: ${e?.message || String(e)}`);
    } finally {
      setDryRunLoading(false);
    }
  };

  const handleSave = async (publish = false) => {
    if (!canSave) {
      toast.error("Please enter a name and add at least one step.");
      return;
    }
    if (publish && !canPublish) {
      toast.error("Each step needs an agent and a prompt before publishing.");
      return;
    }

    const status = publish ? "active" : "draft";
    const est = `${Math.max(steps.length, 1)} min`;

    // Create workflow
    const workflow = await Workflow.create({
      workflow_name: wf.workflow_name.trim(),
      workflow_description: wf.workflow_description || "",
      workflow_category: wf.workflow_category || "custom",
      total_steps: steps.length,
      estimated_duration: est,
      workflow_status: status,
    });

    // Create steps
    const ordered = [...steps].map((s, idx) => ({ ...s, step_order: idx + 1 }));
    for (const s of ordered) {
      await WorkflowStep.create({
        workflow_id: workflow.id,
        step_order: s.step_order,
        agent_name: s.agent_name,
        step_prompt: s.step_prompt || "",
        step_input: s.step_input || {},
        step_status: "pending",
      });
    }

    // Log
    try {
      await AuditLog.create({
        action_type: "workflow_creation",
        success: true,
        workflow_id: String(workflow.id),
        action_details: { event: publish ? "publish" : "save_draft", total_steps: ordered.length },
        risk_level: "low",
      });
    } catch (_) {}

    toast.success(publish ? "Workflow published" : "Draft saved");
    window.location.href = createPageUrl(`WorkflowDetails?id=${workflow.id}`);
  };

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      {/* Template Gallery */}
      <TemplateGallery />

      {/* Builder Header */}
      <Card>
        <CardHeader>
          <CardTitle>Create Custom Workflow</CardTitle>
          <CardDescription>Design a multi-step workflow by selecting agents, prompts, and inputs</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="md:col-span-2 space-y-2">
              <Label htmlFor="wf-name">Workflow Name</Label>
              <Input
                id="wf-name"
                placeholder="e.g., Competitive Research Pipeline"
                value={wf.workflow_name}
                onChange={(e) => setWf({ ...wf, workflow_name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label>Category</Label>
              <Select
                value={wf.workflow_category}
                onValueChange={(v) => setWf({ ...wf, workflow_category: v })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select category" />
                </SelectTrigger>
                <SelectContent>
                  {categories.map(c => (
                    <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="md:col-span-3 space-y-2">
              <Label htmlFor="wf-desc">Description</Label>
              <Textarea
                id="wf-desc"
                placeholder="What does this workflow accomplish?"
                value={wf.workflow_description}
                onChange={(e) => setWf({ ...wf, workflow_description: e.target.value })}
                className="min-h-[80px]"
              />
            </div>
          </div>

          {/* Steps Builder */}
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold">Steps</h3>
            <Button onClick={addStep}>
              <Plus className="w-4 h-4 mr-2" />
              Add Step
            </Button>
          </div>

          <DragDropContext onDragEnd={onDragEnd}>
            <Droppable droppableId="steps">
              {(provided) => (
                <div ref={provided.innerRef} {...provided.droppableProps} className="space-y-4">
                  {steps.map((step, index) => (
                    <Draggable key={step.id} draggableId={step.id} index={index}>
                      {(dragProvided) => (
                        <Card
                          ref={dragProvided.innerRef}
                          {...dragProvided.draggableProps}
                          className="border-emerald-100"
                        >
                          <CardHeader className="flex flex-row items-start justify-between gap-3">
                            <div className="flex items-center gap-3">
                              <div {...dragProvided.dragHandleProps} className="p-2 rounded-lg bg-emerald-50 text-emerald-700">
                                <GripVertical className="w-4 h-4" />
                              </div>
                              <div>
                                <CardTitle className="text-base">Step {index + 1}</CardTitle>
                                <CardDescription>Edit agent, prompt, and inputs</CardDescription>
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              <Badge variant="secondary">{step.agent_name}</Badge>
                              <Button variant="outline" size="icon" onClick={() => handleDryRun(step)} title="Dry Run">
                                <FlaskConical className="w-4 h-4" />
                              </Button>
                              <Button variant="ghost" size="icon" onClick={() => removeStep(step.id)} title="Remove step">
                                <Trash2 className="w-4 h-4" />
                              </Button>
                            </div>
                          </CardHeader>
                          <CardContent className="space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                              <div className="space-y-2">
                                <Label>Agent</Label>
                                <Select
                                  value={step.agent_name}
                                  onValueChange={(v) => updateStep(step.id, { agent_name: v })}
                                >
                                  <SelectTrigger>
                                    <SelectValue placeholder="Select agent" />
                                  </SelectTrigger>
                                  <SelectContent>
                                    {agentOptions.map(opt => (
                                      <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                                    ))}
                                  </SelectContent>
                                </Select>
                              </div>
                              <div className="md:col-span-2 space-y-2">
                                <Label>Prompt</Label>
                                <Input
                                  placeholder="Provide clear instructions for this step"
                                  value={step.step_prompt}
                                  onChange={(e) => updateStep(step.id, { step_prompt: e.target.value })}
                                />
                              </div>
                            </div>

                            <div className="space-y-2">
                              <Label>Input</Label>
                              <StepInputEditor
                                value={step.step_input || {}}
                                onChange={(val) => updateStep(step.id, { step_input: val })}
                              />
                            </div>
                          </CardContent>
                        </Card>
                      )}
                    </Draggable>
                  ))}
                  {provided.placeholder}
                </div>
              )}
            </Droppable>
          </DragDropContext>

          <div className="flex flex-wrap gap-3 justify-end">
            <Button variant="outline" onClick={() => handleSave(false)} disabled={!canSave}>
              <Play className="w-4 h-4 mr-2" />
              Save Draft
            </Button>
            <Button onClick={() => handleSave(true)} disabled={!canPublish} className="bg-emerald-900 hover:bg-emerald-800">
              <Rocket className="w-4 h-4 mr-2" />
              Publish
            </Button>
          </div>
        </CardContent>
      </Card>

      <DryRunModal
        open={dryRunOpen}
        onClose={() => setDryRunOpen(false)}
        agentName={dryRunAgent}
        output={dryRunOutput}
        loading={dryRunLoading}
      />
    </div>
  );
}