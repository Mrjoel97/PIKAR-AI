import React, { useEffect, useMemo, useState } from "react";
import { WorkflowTemplate } from "@/api/entities";
import { Workflow } from "@/api/entities";
import { WorkflowStep } from "@/api/entities";
import { AuditLog } from "@/api/entities";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Sparkles, Loader2, Eye, X } from "lucide-react";
import { toast } from "sonner";
import { createPageUrl } from "@/utils";

const categoryMapToWorkflow = (tplCategory) => {
  const map = {
    data_management: "operations",
    notifications: "operations",
    analysis: "market_analysis",
    automation: "operations",
    compliance: "compliance",
    reporting: "operations",
  };
  return map[tplCategory] || "custom";
};

export default function TemplateGallery() {
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("all");
  const [difficulty, setDifficulty] = useState("all");
  const [deployingId, setDeployingId] = useState(null);
  const [preview, setPreview] = useState(null);

  useEffect(() => {
    (async () => {
      setLoading(true);
      const list = await WorkflowTemplate.list("-usage_count", 100);
      setTemplates(list);
      setLoading(false);
    })();
  }, []);

  const categories = useMemo(() => {
    const set = new Set(templates.map((t) => t.category));
    return ["all", ...Array.from(set)];
  }, [templates]);

  const difficulties = ["all", "beginner", "intermediate", "advanced"];

  const filtered = useMemo(() => {
    return templates.filter((t) => {
      const q = query.toLowerCase();
      const matchesQuery =
        !q ||
        t.template_name.toLowerCase().includes(q) ||
        (t.template_description || "").toLowerCase().includes(q) ||
        (t.tags || []).some((tag) => tag.toLowerCase().includes(q));
      const matchesCat = category === "all" || t.category === category;
      const matchesDiff = difficulty === "all" || t.difficulty === difficulty;
      return matchesQuery && matchesCat && matchesDiff;
    });
  }, [templates, query, category, difficulty]);

  const handleDeploy = async (tpl) => {
    if (!tpl?.template_config?.steps?.length) {
      toast.error("Template has no steps to deploy");
      return;
    }
    setDeployingId(tpl.id);
    try {
      const wf = await Workflow.create({
        workflow_name: tpl.template_name,
        workflow_description: tpl.template_description,
        workflow_category: categoryMapToWorkflow(tpl.category),
        total_steps: tpl.template_config.steps.length,
        estimated_duration: tpl.estimated_duration || `${tpl.template_config.steps.length} min`,
        workflow_status: "draft",
      });

      const steps = [...tpl.template_config.steps].sort((a, b) => (a.step_order || 0) - (b.step_order || 0));
      for (const s of steps) {
        await WorkflowStep.create({
          workflow_id: wf.id,
          step_order: s.step_order,
          agent_name: s.agent_name,
          step_prompt: s.step_prompt || "",
          step_input: s.step_input_schema || {},
          step_status: "pending",
        });
      }

      await AuditLog.create({
        action_type: "workflow_creation",
        success: true,
        workflow_id: String(wf.id),
        action_details: {
          event: "template_deploy",
          template_id: tpl.id,
          template_name: tpl.template_name,
          steps_created: steps.length,
        },
        risk_level: "low",
      });

      try {
        await WorkflowTemplate.update(tpl.id, { usage_count: (tpl.usage_count || 0) + 1 });
      } catch (_) {}

      toast.success("Template deployed");
      window.location.href = createPageUrl(`WorkflowDetails?id=${wf.id}`);
    } catch (e) {
      toast.error(`Failed to deploy: ${e?.message || "Unknown error"}`);
    } finally {
      setDeployingId(null);
    }
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-yellow-600" />
            <CardTitle>Workflow Template Gallery</CardTitle>
          </div>
          <CardDescription>Use a template to create a workflow instantly</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            <Input
              placeholder="Search templates..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full md:w-72"
            />
            <Select value={category} onValueChange={setCategory}>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="Category" />
              </SelectTrigger>
              <SelectContent>
                {categories.map((c) => (
                  <SelectItem key={c} value={c}>{c.replace(/_/g, " ")}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={difficulty} onValueChange={setDifficulty}>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="Difficulty" />
              </SelectTrigger>
              <SelectContent>
                {difficulties.map((d) => (
                  <SelectItem key={d} value={d}>{d}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {loading ? (
            <div className="flex items-center justify-center h-24">
              <Loader2 className="w-6 h-6 animate-spin" />
            </div>
          ) : filtered.length === 0 ? (
            <div className="text-sm text-gray-500">No templates found.</div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filtered.map((tpl) => (
                <Card key={tpl.id} className="hover:shadow-md transition-shadow">
                  <CardHeader>
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <CardTitle className="text-lg">{tpl.template_name}</CardTitle>
                        <CardDescription>{tpl.template_description}</CardDescription>
                        <div className="mt-2 flex flex-wrap gap-2">
                          <Badge variant="outline">{tpl.category}</Badge>
                          <Badge variant="secondary">{tpl.difficulty || "beginner"}</Badge>
                          <Badge variant="secondary">{(tpl.template_config?.steps || []).length} steps</Badge>
                        </div>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {Array.isArray(tpl.tags) && tpl.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {tpl.tags.slice(0, 4).map((t, i) => (
                          <Badge key={i} variant="secondary" className="text-[10px]">#{t}</Badge>
                        ))}
                      </div>
                    )}
                    <div className="flex gap-2">
                      <Button 
                        onClick={() => handleDeploy(tpl)} 
                        disabled={deployingId === tpl.id}
                        className="flex-1"
                      >
                        {deployingId === tpl.id ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
                        Deploy
                      </Button>
                      <Button variant="outline" onClick={() => setPreview(tpl)}>
                        <Eye className="w-4 h-4" />
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {preview && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <Card className="w-full max-w-2xl">
            <CardHeader className="flex items-center justify-between">
              <CardTitle>{preview.template_name}</CardTitle>
              <Button variant="ghost" size="icon" onClick={() => setPreview(null)}>
                <X className="w-4 h-4" />
              </Button>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="text-sm text-gray-600">{preview.template_description}</div>
              <div className="text-xs text-gray-500">
                Required integrations: {(preview.template_config?.required_integrations || []).join(", ") || "None"}
              </div>
              <div className="border rounded-lg overflow-hidden">
                <div className="bg-gray-50 px-3 py-2 text-xs font-medium">Steps</div>
                <ul className="divide-y max-h-64 overflow-auto">
                  {(preview.template_config?.steps || []).map((s, i) => (
                    <li key={i} className="p-3 text-sm">
                      <div className="font-medium">{s.step_order}. {s.agent_name}</div>
                      <div className="text-gray-600 mt-1">{s.step_prompt}</div>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="flex justify-end">
                <Button onClick={() => { setPreview(null); handleDeploy(preview); }}>
                  Use this template
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}