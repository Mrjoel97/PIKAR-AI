import { httpRouter } from "convex/server";
import { auth } from "./auth";
import { httpAction } from "./_generated/server";
import { api } from "./_generated/api";

const http = httpRouter();

auth.addHttpRoutes(http);

// Add webhook to trigger workflows externally
http.route({
  path: "/api/trigger",
  method: "POST",
  handler: httpAction(async (ctx, req) => {
    try {
      const body = await req.json();
      const { workflowId, startedBy, params, dryRun } = body || {};
      if (!workflowId || !startedBy) {
        return new Response(JSON.stringify({ error: "workflowId and startedBy are required" }), { status: 400 });
      }

      // Optional: simulate only if dryRun is true and no execution
      if (dryRun) {
        const result = await ctx.runAction(api.workflows.simulateWorkflow, { workflowId, params });
        return new Response(JSON.stringify({ ok: true, dryRun: true, result }), { status: 200 });
      }

      const runId = await ctx.runAction(api.workflows.runWorkflow, {
        workflowId,
        startedBy,
        dryRun: !!dryRun,
      });
      return new Response(JSON.stringify({ ok: true, runId }), { status: 200 });
    } catch (e: any) {
      return new Response(JSON.stringify({ error: e?.message || "Failed to trigger workflow" }), { status: 500 });
    }
  }),
});

http.route({
  path: "/api/incidents/report",
  method: "POST",
  handler: httpAction(async (ctx, req) => {
    try {
      const body = await req.json();
      const { businessId, reportedBy, type, description, severity, linkedRiskId } = body || {};
      if (!businessId || !reportedBy || !type || !description || !severity) {
        return new Response(JSON.stringify({ error: "Missing required fields" }), { status: 400 });
      }
      const incidentId = await ctx.runMutation(api.workflows.reportIncident, {
        businessId,
        reportedBy,
        type,
        description,
        severity,
        linkedRiskId: linkedRiskId ?? undefined,
      });
      return new Response(JSON.stringify({ ok: true, incidentId }), { status: 200 });
    } catch (e: any) {
      return new Response(JSON.stringify({ error: e?.message || "Failed to report incident" }), { status: 500 });
    }
  }),
});

http.route({
  path: "/api/compliance/scan",
  method: "POST",
  handler: httpAction(async (ctx, req) => {
    try {
      const body = await req.json();
      const { businessId, subjectType, subjectId, content, checkedBy } = body || {};
      if (!businessId || !subjectType || !subjectId || !content) {
        return new Response(JSON.stringify({ error: "Missing required fields" }), { status: 400 });
      }
      const result = await ctx.runAction(api.workflows.checkMarketingCompliance, {
        businessId,
        subjectType,
        subjectId,
        content,
        checkedBy: checkedBy ?? undefined,
      });
      return new Response(JSON.stringify({ ok: true, result }), { status: 200 });
    } catch (e: any) {
      return new Response(JSON.stringify({ error: e?.message || "Failed to scan compliance" }), { status: 500 });
    }
  }),
});

export default http;