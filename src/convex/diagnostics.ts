import { v } from "convex/values";
import { mutation, query } from "./_generated/server";
import { getCurrentUser } from "./users";

type Task = {
  title: string;
  frequency: "daily" | "weekly" | "monthly";
  description: string;
};

type Workflow = {
  name: string;
  agentType:
    | "content_creation"
    | "sales_intelligence"
    | "customer_support"
    | "marketing_automation"
    | "operations"
    | "analytics";
  templateId: string;
};

export const run = mutation({
  args: {
    businessId: v.id("businesses"),
    inputs: v.optional(
      v.object({
        goals: v.optional(v.array(v.string())),
        signals: v.optional(v.record(v.string(), v.any())),
        phase: v.optional(v.union(v.literal("discovery"), v.literal("planning"))),
      })
    ),
  },
  handler: async (ctx, args) => {
    const user = await getCurrentUser(ctx);
    if (!user) {
      throw new Error("User must be authenticated");
    }

    const business = await ctx.db.get(args.businessId);
    if (!business || (business.ownerId !== user._id && !business.teamMembers.includes(user._id))) {
      throw new Error("Access denied");
    }

    // Simple tier-based heuristics
    const tier = business.tier;
    const baseKpis = {
      roiTarget: tier === "enterprise" ? 0.35 : tier === "sme" ? 0.25 : tier === "startup" ? 0.2 : 0.15,
      completionRateTarget: tier === "enterprise" ? 0.9 : tier === "sme" ? 0.85 : tier === "startup" ? 0.8 : 0.75,
    };

    const tasks: Array<Task> = [
      // Daily
      {
        title: "Review agent activity",
        frequency: "daily",
        description: "Check tasks completed and any failures across active agents.",
      },
      {
        title: "Prioritize initiative tasks",
        frequency: "daily",
        description: "Reorder tasks to align with current business goals.",
      },
      // Weekly
      {
        title: "Optimize prompts and parameters",
        frequency: "weekly",
        description: "Tune model configs for performance and accuracy.",
      },
      {
        title: "Sales/Marketing sync",
        frequency: "weekly",
        description: "Align content & outreach with latest insights.",
      },
      // Monthly
      {
        title: "KPI review & target adjustment",
        frequency: "monthly",
        description: "Compare actuals vs targets; update goals for upcoming cycle.",
      },
      {
        title: "Workflow audit",
        frequency: "monthly",
        description: "Retire low-impact automations; double down on high ROI steps.",
      },
    ];

    // Tier adjustments
    if (tier === "solopreneur") {
      tasks.push({
        title: "Single-channel focus",
        frequency: "weekly",
        description: "Focus on one channel (eg. email or LinkedIn) to build consistency.",
      });
    }
    if (tier === "startup") {
      tasks.push({
        title: "Lead qualification automation",
        frequency: "weekly",
        description: "Implement AI triage for inbound to increase sales throughput.",
      });
    }
    if (tier === "sme") {
      tasks.push({
        title: "Cross-team reporting",
        frequency: "monthly",
        description: "Share AI insights with leadership for resource planning.",
      });
    }
    if (tier === "enterprise") {
      tasks.push({
        title: "Compliance validation",
        frequency: "monthly",
        description: "Verify integrations and workflows meet policy requirements.",
      });
    }

    const workflows: Array<Workflow> = [
      {
        name: "CreateWorkflow: Content Sprint",
        agentType: "content_creation",
        templateId: "wf_content_sprint_v1",
      },
      {
        name: "CreateWorkflow: Pipeline Nurture",
        agentType: "marketing_automation",
        templateId: "wf_pipeline_nurture_v1",
      },
      {
        name: "CreateWorkflow: Lead Scoring",
        agentType: "sales_intelligence",
        templateId: "wf_lead_scoring_v1",
      },
    ];

    const kpis = {
      targetROI: baseKpis.roiTarget,
      targetCompletionRate: baseKpis.completionRateTarget,
    };

    const diagnosticId = await ctx.db.insert("diagnostics", {
      businessId: args.businessId,
      createdBy: user._id,
      phase: args.inputs?.phase ?? "discovery",
      inputs: {
        goals: args.inputs?.goals ?? [],
        signals: args.inputs?.signals ?? {},
      },
      outputs: {
        tasks,
        workflows,
        kpis,
      },
      runAt: Date.now(),
    });

    return diagnosticId;
  },
});

export const getLatest = query({
  args: { businessId: v.id("businesses") },
  handler: async (ctx, args) => {
    const user = await getCurrentUser(ctx);
    if (!user) {
      return null;
    }

    const business = await ctx.db.get(args.businessId);
    if (!business || (business.ownerId !== user._id && !business.teamMembers.includes(user._id))) {
      return null;
    }

    const list = await ctx.db
      .query("diagnostics")
      .withIndex("by_business", (q) => q.eq("businessId", args.businessId))
      .collect();

    if (list.length === 0) return null;
    // Latest by runAt (stored field); list is filtered by index and small in scope
    return list.reduce((a, b) => (a.runAt > b.runAt ? a : b));
  },
});

export const getDiff = query({
  args: { businessId: v.id("businesses") },
  handler: async (ctx, args) => {
    const user = await getCurrentUser(ctx);
    if (!user) return null;

    const business = await ctx.db.get(args.businessId);
    if (!business || (business.ownerId !== user._id && !business.teamMembers.includes(user._id))) {
      return null;
    }

    const list = await ctx.db
      .query("diagnostics")
      .withIndex("by_business", (q) => q.eq("businessId", args.businessId))
      .collect();

    if (list.length < 2) return null;

    // Sort by runAt descending and pick the latest two
    const sorted = [...list].sort((a, b) => b.runAt - a.runAt);
    const latest = sorted[0];
    const previous = sorted[1];

    // Compute KPI deltas
    const kpisDelta = {
      targetROI: latest.outputs.kpis.targetROI - previous.outputs.kpis.targetROI,
      targetCompletionRate:
        latest.outputs.kpis.targetCompletionRate - previous.outputs.kpis.targetCompletionRate,
    };

    // Compute task diffs by title
    const prevTaskTitles = new Set(previous.outputs.tasks.map((t) => t.title));
    const latestTaskTitles = new Set(latest.outputs.tasks.map((t) => t.title));
    const tasks = {
      added: latest.outputs.tasks.filter((t) => !prevTaskTitles.has(t.title)),
      removed: previous.outputs.tasks.filter((t) => !latestTaskTitles.has(t.title)),
    };

    // Compute workflow diffs by templateId
    const prevWorkflowIds = new Set(previous.outputs.workflows.map((w) => w.templateId));
    const latestWorkflowIds = new Set(latest.outputs.workflows.map((w) => w.templateId));
    const workflows = {
      added: latest.outputs.workflows.filter((w) => !prevWorkflowIds.has(w.templateId)),
      removed: previous.outputs.workflows.filter((w) => !latestWorkflowIds.has(w.templateId)),
    };

    return {
      kpisDelta,
      tasks,
      workflows,
      currentRunAt: latest.runAt,
      previousRunAt: previous.runAt,
    };
  },
});