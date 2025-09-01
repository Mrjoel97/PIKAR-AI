import runAgent from "@/components/workflow/runAgent";
import { Workflow } from "@/api/entities";
import { WorkflowStep } from "@/api/entities";
import { AuditLog } from "@/api/entities";

const cancellations = new Map(); // workflowId -> boolean
const running = new Set(); // workflowId currently running

const DEFAULT_STEP_TIMEOUT_MS = 5 * 60 * 1000;
const DEFAULT_MAX_RETRIES = 2;
const DEFAULT_DELAY_BETWEEN_STEPS_MS = 250;

function sleep(ms) {
  return new Promise((res) => setTimeout(res, ms));
}

async function logEvent(data) {
  try {
    await AuditLog.create({
      action_type: "workflow_execution",
      success: data.success ?? true,
      workflow_id: data.workflow_id ? String(data.workflow_id) : undefined,
      agent_name: data.agent_name || undefined,
      action_details: data,
      risk_level: data.risk_level || "low",
    });
  } catch (_) {
    // best-effort
  }
}

function sortSteps(steps) {
  return [...steps].sort((a, b) => (a.step_order || 0) - (b.step_order || 0));
}

async function fetchSteps(workflow_id) {
  const steps = await WorkflowStep.filter({ workflow_id });
  return sortSteps(steps || []);
}

async function updateWorkflowStatusFromSteps(workflow_id) {
  const steps = await fetchSteps(workflow_id);
  const total = steps.length || 1;
  const completed = steps.filter((s) => s.step_status === "completed").length;
  const failed = steps.filter((s) => s.step_status === "failed").length;
  const runningCount = steps.filter((s) => s.step_status === "running").length;

  let workflow_status = "active";
  if (failed > 0) workflow_status = "failed";
  if (completed === total) workflow_status = "completed";
  if (runningCount === 0 && completed === 0 && failed === 0) workflow_status = "draft";

  await Workflow.update(workflow_id, { workflow_status });
  return { completed, total, failed, workflow_status };
}

function withTimeout(promise, ms) {
  return Promise.race([
    promise,
    new Promise((_, reject) =>
      setTimeout(
        () => reject(Object.assign(new Error(`Step timed out after ${ms}ms`), { code: "timeout" })),
        ms
      )
    ),
  ]);
}

async function runSingleStepInternal(step, { workflow_id, maxRetries, timeoutMs }) {
  const startTs = Date.now();
  let attempt = 0;
  let lastError = null;

  while (attempt <= maxRetries) {
    attempt += 1;

    await WorkflowStep.update(step.id, { step_status: "running" });
    await logEvent({
      workflow_id,
      agent_name: step.agent_name,
      event: "step_start",
      step_id: step.id,
      attempt,
      success: true,
      at: new Date().toISOString(),
    });

    try {
      const file_urls =
        (step.step_input &&
          (step.step_input.file_urls || step.step_input.files || step.step_input.context_files)) ||
        [];
      const exec = (async () => {
        const { text, raw } = await runAgent(step.agent_name, {
          prompt: step.step_prompt,
          input: step.step_input || {},
          file_urls: Array.isArray(file_urls) ? file_urls : [],
        });
        return { text, raw };
      })();

      const { text, raw } = await withTimeout(exec, timeoutMs);

      const durationSec = Math.max(1, Math.round((Date.now() - startTs) / 1000));
      await WorkflowStep.update(step.id, {
        step_status: "completed",
        step_output: {
          text,
          raw_preview: typeof raw === "string" ? raw.slice(0, 4000) : (text ? String(text).slice(0, 4000) : ""),
        },
        execution_time: durationSec,
      });

      await logEvent({
        workflow_id,
        agent_name: step.agent_name,
        event: "step_complete",
        step_id: step.id,
        attempt,
        success: true,
        at: new Date().toISOString(),
        output_preview: text ? String(text).slice(0, 400) : "",
      });

      return { status: "completed", text };
    } catch (err) {
      lastError = err;
      const durationSec = Math.max(1, Math.round((Date.now() - startTs) / 1000));

      await WorkflowStep.update(step.id, {
        step_status: "failed",
        step_output: { error: { message: err?.message || String(err), code: err?.code || "error" } },
        execution_time: durationSec,
      });

      await logEvent({
        workflow_id,
        agent_name: step.agent_name,
        event: "step_failure",
        step_id: step.id,
        attempt,
        success: false,
        at: new Date().toISOString(),
        error_message: err?.message || String(err),
      });

      if (attempt <= maxRetries) {
        // Exponential backoff with jitter
        const base = 500 * Math.pow(2, attempt - 1);
        const jitter = Math.floor(Math.random() * 250);
        await sleep(base + jitter);
        continue;
      }

      return { status: "failed", error: lastError };
    }
  }

  return { status: "failed", error: lastError };
}

async function runStepsSequentially(workflow_id, steps, opts) {
  const { maxRetries, timeoutMs, delayBetweenStepsMs } = opts;
  const results = [];

  for (const step of steps) {
    if (cancellations.get(String(workflow_id))) {
      await logEvent({
        workflow_id,
        event: "workflow_cancelled",
        success: true,
        at: new Date().toISOString(),
      });
      break;
    }

    // Skip already completed steps
    if (step.step_status === "completed") {
      results.push({ step_id: step.id, status: "skipped" });
      continue;
    }

    const res = await runSingleStepInternal(step, { workflow_id, maxRetries, timeoutMs });
    results.push({ step_id: step.id, ...res });
    await updateWorkflowStatusFromSteps(workflow_id);
    await sleep(delayBetweenStepsMs);
  }

  return results;
}

const WorkflowExecutor = {
  async run(workflow_id, options = {}) {
    const wfId = String(workflow_id);
    if (running.has(wfId)) return { status: "already_running" };
    running.add(wfId);
    cancellations.set(wfId, false);

    const {
      mode = "remaining", // "remaining" | "all"
      maxRetries = DEFAULT_MAX_RETRIES,
      timeoutMs = DEFAULT_STEP_TIMEOUT_MS,
      delayBetweenStepsMs = DEFAULT_DELAY_BETWEEN_STEPS_MS,
    } = options;

    await Workflow.update(workflow_id, { workflow_status: "active" });
    await logEvent({
      workflow_id,
      event: "workflow_start",
      success: true,
      at: new Date().toISOString(),
      mode,
    });

    try {
      let steps = await fetchSteps(workflow_id);
      if (mode === "remaining") {
        steps = steps.filter((s) => s.step_status !== "completed");
      } else if (mode === "all") {
        // reset all steps to pending
        for (const s of steps) {
          if (s.step_status !== "pending") {
            await WorkflowStep.update(s.id, { step_status: "pending" });
          }
        }
        steps = await fetchSteps(workflow_id);
      }

      const results = await runStepsSequentially(workflow_id, steps, {
        maxRetries,
        timeoutMs,
        delayBetweenStepsMs,
      });

      const statusSummary = await updateWorkflowStatusFromSteps(workflow_id);
      await logEvent({
        workflow_id,
        event: "workflow_end",
        success: statusSummary.workflow_status === "completed",
        at: new Date().toISOString(),
        summary: statusSummary,
      });

      return { status: statusSummary.workflow_status, results };
    } finally {
      running.delete(wfId);
      cancellations.set(wfId, false);
    }
  },

  async cancel(workflow_id) {
    const wfId = String(workflow_id);
    cancellations.set(wfId, true);
    await logEvent({
      workflow_id,
      event: "workflow_cancel_request",
      success: true,
      at: new Date().toISOString(),
    });
    return { status: "cancelling" };
  },

  async runStep(workflow_id, step_id, options = {}) {
    const { maxRetries = DEFAULT_MAX_RETRIES, timeoutMs = DEFAULT_STEP_TIMEOUT_MS } = options;
    const steps = await fetchSteps(workflow_id);
    const target = steps.find((s) => String(s.id) === String(step_id));
    if (!target) return { status: "not_found" };

    await Workflow.update(workflow_id, { workflow_status: "active" });
    await WorkflowStep.update(target.id, { step_status: "pending" });

    const res = await runSingleStepInternal(target, { workflow_id, maxRetries, timeoutMs });
    const summary = await updateWorkflowStatusFromSteps(workflow_id);
    return { ...res, summary };
  },

  async rerunFailed(workflow_id, options = {}) {
    const { maxRetries = DEFAULT_MAX_RETRIES, timeoutMs = DEFAULT_STEP_TIMEOUT_MS } = options;
    await Workflow.update(workflow_id, { workflow_status: "active" });
    let steps = await fetchSteps(workflow_id);
    const failed = steps.filter((s) => s.step_status === "failed");

    for (const s of failed) {
      await WorkflowStep.update(s.id, { step_status: "pending" });
    }

    steps = await fetchSteps(workflow_id);
    const toRun = steps.filter((s) => s.step_status === "pending");
    const results = await runStepsSequentially(workflow_id, toRun, {
      maxRetries,
      timeoutMs,
      delayBetweenStepsMs: DEFAULT_DELAY_BETWEEN_STEPS_MS,
    });

    const summary = await updateWorkflowStatusFromSteps(workflow_id);
    return { status: summary.workflow_status, results };
  },
};

export default WorkflowExecutor;