import React, { useEffect, useMemo, useRef, useState } from "react";
import { useLocation, Link } from "react-router-dom";
import { Workflow } from "@/api/entities";
import { WorkflowStep } from "@/api/entities";
import { AuditLog } from "@/api/entities";
import WorkflowExecutor from "@/components/workflow/WorkflowExecutor";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { createPageUrl } from "@/utils";
import { toast } from "sonner";
import {
  Play,
  RotateCcw,
  XCircle,
  RefreshCw,
  History,
  Bot,
  Clock,
  CheckCircle2,
  AlertTriangle,
  ArrowLeft
} from "lucide-react";

function useQuery() {
  const { search } = useLocation();
  return useMemo(() => new URLSearchParams(search), [search]);
}

function statusBadgeClass(status) {
  switch (status) {
    case "active": return "bg-blue-100 text-blue-800";
    case "completed": return "bg-green-100 text-green-800";
    case "failed": return "bg-red-100 text-red-800";
    case "draft": return "bg-gray-100 text-gray-800";
    case "running": return "bg-blue-100 text-blue-800";
    case "pending": return "bg-gray-100 text-gray-800";
    default: return "bg-gray-100 text-gray-800";
  }
}

export default function WorkflowDetails() {
  const query = useQuery();
  const workflowId = query.get("id");
  const [workflow, setWorkflow] = useState(null);
  const [steps, setSteps] = useState([]);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [executing, setExecuting] = useState(false);
  const intervalRef = useRef(null);

  const sortedSteps = useMemo(
    () => [...steps].sort((a, b) => (a.step_order || 0) - (b.step_order || 0)),
    [steps]
  );

  const completedCount = useMemo(
    () => steps.filter((s) => s.step_status === "completed").length,
    [steps]
  );
  const failedCount = useMemo(
    () => steps.filter((s) => s.step_status === "failed").length,
    [steps]
  );
  const progress = useMemo(() => {
    const total = steps.length || 1;
    return Math.round((completedCount / total) * 100);
  }, [completedCount, steps.length]);

  const loadData = async () => {
    if (!workflowId) return;
    const wfArr = await Workflow.filter({ id: workflowId });
    const wf = Array.isArray(wfArr) ? wfArr[0] : null;
    const st = await WorkflowStep.filter({ workflow_id: workflowId });
    const lg = await AuditLog.filter({ workflow_id: String(workflowId) });
    setWorkflow(wf || null);
    setSteps(st || []);
    setLogs((lg || []).slice().reverse());
  };

  useEffect(() => {
    (async () => {
      setLoading(true);
      await loadData();
      setLoading(false);
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workflowId]);

  // Poll while active or while any step is running
  useEffect(() => {
    if (!workflowId) return;
    const shouldPoll =
      !workflow ||
      workflow.workflow_status === "active" ||
      steps.some((s) => s.step_status === "running");

    if (!shouldPoll) return;

    intervalRef.current = setInterval(loadData, 1500);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workflowId, workflow, steps]);

  const handleExecute = async () => {
    if (!workflowId) return;
    setExecuting(true);
    await WorkflowExecutor.run(workflowId, { mode: "remaining", maxRetries: 2 });
    toast.success("Workflow execution started");
    setExecuting(false);
    loadData();
  };

  const handleRerunFailed = async () => {
    if (!workflowId) return;
    setExecuting(true);
    await WorkflowExecutor.rerunFailed(workflowId, { maxRetries: 2 });
    toast.success("Re-running failed steps");
    setExecuting(false);
    loadData();
  };

  const handleCancel = async () => {
    if (!workflowId) return;
    await WorkflowExecutor.cancel(workflowId);
    toast.success("Cancellation requested");
    loadData();
  };

  const handleRetryStep = async (step) => {
    setExecuting(true);
    await WorkflowExecutor.runStep(workflowId, step.id, { maxRetries: 2 });
    toast.success(`Step ${step.step_order} retried`);
    setExecuting(false);
    loadData();
  };

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto">
        <Card>
          <CardHeader><CardTitle>Loading workflow...</CardTitle></CardHeader>
          <CardContent className="py-10">
            <div className="w-8 h-8 border-4 border-gray-200 border-t-emerald-900 rounded-full animate-spin mx-auto" />
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!workflow) {
    return (
      <div className="max-w-3xl mx-auto">
        <Card>
          <CardHeader>
            <CardTitle>Workflow not found</CardTitle>
            <CardDescription>Ensure the URL includes a valid id parameter.</CardDescription>
          </CardHeader>
          <CardContent>
            <Link to={createPageUrl("Orchestrate")}>
              <Button variant="outline">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back to Orchestration
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto space-y-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">{workflow.workflow_name}</h1>
          <p className="text-gray-600">{workflow.workflow_description}</p>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <Badge className={statusBadgeClass(workflow.workflow_status)}>
              {workflow.workflow_status}
            </Badge>
            <Badge variant="outline" className="capitalize">
              {String(workflow.workflow_category).replace(/_/g, " ")}
            </Badge>
            <Badge variant="secondary">{steps.length} steps</Badge>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button onClick={loadData} variant="outline">
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
          <Button onClick={handleExecute} disabled={executing} className="bg-blue-600 hover:bg-blue-700">
            <Play className="w-4 h-4 mr-2" />
            Execute
          </Button>
          <Button onClick={handleRerunFailed} disabled={executing} variant="outline">
            <RotateCcw className="w-4 h-4 mr-2" />
            Rerun Failed
          </Button>
          <Button onClick={handleCancel} disabled={executing} variant="destructive">
            <XCircle className="w-4 h-4 mr-2" />
            Cancel
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bot className="w-5 h-5 text-emerald-900" />
            Steps
          </CardTitle>
          <CardDescription>Monitor and control each step</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <div className="flex justify-between text-sm mb-2">
              <span>Progress</span>
              <span>
                {completedCount}/{steps.length} completed
              </span>
            </div>
            <Progress value={progress} className="h-2" />
          </div>

          <div className="space-y-3">
            {sortedSteps.map((s) => (
              <div
                key={s.id}
                className="p-4 border rounded-xl flex items-start justify-between hover:bg-gray-50"
              >
                <div>
                  <div className="flex items-center gap-3">
                    <div className="text-sm font-medium">
                      Step {s.step_order}: {s.agent_name}
                    </div>
                    <Badge className={statusBadgeClass(s.step_status)}>{s.step_status}</Badge>
                  </div>
                  {s.step_prompt ? (
                    <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                      {s.step_prompt}
                    </p>
                  ) : null}
                  {s.step_output?.text && (
                    <div className="mt-2 text-xs text-gray-700 bg-gray-50 rounded-lg p-2 border">
                      <span className="font-medium">Output preview:</span>{" "}
                      {String(s.step_output.text).slice(0, 200)}
                      {String(s.step_output.text).length > 200 ? "..." : ""}
                    </div>
                  )}
                  {s.step_output?.error?.message && (
                    <div className="mt-2 text-xs text-red-700 bg-red-50 rounded-lg p-2 border border-red-200">
                      <span className="font-medium">Error:</span> {s.step_output.error.message}
                    </div>
                  )}
                </div>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleRetryStep(s)}
                    disabled={executing}
                  >
                    <RotateCcw className="w-4 h-4 mr-2" />
                    Retry
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <History className="w-5 h-5 text-emerald-900" />
            Run History
          </CardTitle>
          <CardDescription>Recent audit events</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          {logs.length === 0 ? (
            <div className="text-sm text-gray-500">No audit events yet.</div>
          ) : (
            <ul className="space-y-2">
              {logs.slice(0, 30).map((l) => (
                <li key={l.id} className="text-sm p-2 border rounded-lg flex items-center gap-2">
                  {l.success ? (
                    <CheckCircle2 className="w-4 h-4 text-green-600" />
                  ) : (
                    <AlertTriangle className="w-4 h-4 text-red-600" />
                  )}
                  <span className="font-medium">{l.action_type}</span>
                  <span className="text-gray-500">•</span>
                  <span className="truncate">{String(l.action_details?.event || "event")}</span>
                  <span className="ml-auto text-xs text-gray-500">
                    {new Date(l.created_date).toLocaleString()}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <div className="flex justify-between">
        <Link to={createPageUrl("Orchestrate")}>
          <Button variant="outline">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Orchestration
          </Button>
        </Link>
        <Link to={createPageUrl("CreateWorkflow")}>
          <Button>New Workflow</Button>
        </Link>
      </div>
    </div>
  );
}