import { v } from "convex/values";
import { query, mutation, action, internalMutation, internalQuery, internalAction } from "./_generated/server";
import { internal } from "./_generated/api";
import { Id } from "./_generated/dataModel";

// Queries
export const listWorkflows = query({
  args: { businessId: v.id("businesses") },
  handler: async (ctx, args) => {
    const workflows = await ctx.db
      .query("workflows")
      .withIndex("by_business_id", (q) => q.eq("businessId", args.businessId))
      .collect();
    
    // Get run counts for each workflow
    const workflowsWithStats = await Promise.all(
      workflows.map(async (workflow) => {
        const runs = await ctx.db
          .query("workflowRuns")
          .withIndex("by_workflow_id", (q) => q.eq("workflowId", workflow._id))
          .collect();
        
        const completedRuns = runs.filter(r => r.status === "completed").length;
        const lastRun = runs.sort((a, b) => b.startedAt - a.startedAt)[0];
        
        return {
          ...workflow,
          runCount: runs.length,
          completedRuns,
          lastRunStatus: lastRun?.status || null,
          lastRunAt: lastRun?.startedAt || null
        };
      })
    );
    
    return workflowsWithStats;
  },
});

export const getWorkflow = query({
  args: { workflowId: v.id("workflows") },
  handler: async (ctx, args) => {
    const workflow = await ctx.db.get(args.workflowId);
    if (!workflow) return null;
    
    const steps = await ctx.db
      .query("workflowSteps")
      .withIndex("by_workflow_id", (q) => q.eq("workflowId", args.workflowId))
      .collect();
    
    return { ...workflow, steps: steps.sort((a, b) => a.order - b.order) };
  },
});

export const listWorkflowRuns = query({
  args: { workflowId: v.id("workflows") },
  handler: async (ctx, args) => {
    const runs = await ctx.db
      .query("workflowRuns")
      .withIndex("by_workflow_id", (q) => q.eq("workflowId", args.workflowId))
      .order("desc")
      .collect();
    
    return runs;
  },
});

export const getWorkflowRun = query({
  args: { runId: v.id("workflowRuns") },
  handler: async (ctx, args) => {
    const run = await ctx.db.get(args.runId);
    if (!run) return null;
    
    const runSteps = await ctx.db
      .query("workflowRunSteps")
      .withIndex("by_run_id", (q) => q.eq("runId", args.runId))
      .collect();
    
    return { ...run, steps: runSteps };
  },
});

export const listTemplates = query({
  args: {},
  handler: async (ctx) => {
    return await ctx.db.query("workflowTemplates").collect();
  },
});

// Mutations
export const createWorkflow = mutation({
  args: {
    businessId: v.id("businesses"),
    name: v.string(),
    description: v.string(),
    trigger: v.union(v.literal("manual"), v.literal("schedule"), v.literal("event")),
    triggerConfig: v.object({
      schedule: v.optional(v.string()),
      eventType: v.optional(v.string()),
      conditions: v.optional(v.array(v.object({
        field: v.string(),
        operator: v.string(),
        value: v.any()
      })))
    }),
    approvalPolicy: v.object({
      type: v.union(v.literal("none"), v.literal("single"), v.literal("tiered")),
      approvers: v.array(v.string()),
      tierGates: v.optional(v.array(v.object({
        tier: v.string(),
        required: v.boolean()
      })))
    }),
    associatedAgentIds: v.array(v.id("aiAgents")),
    createdBy: v.id("users")
  },
  handler: async (ctx, args) => {
    return await ctx.db.insert("workflows", {
      ...args,
      isActive: true
    });
  },
});

export const addStep = mutation({
  args: {
    workflowId: v.id("workflows"),
    type: v.union(v.literal("agent"), v.literal("approval"), v.literal("delay")),
    title: v.string(),
    config: v.object({
      delayMinutes: v.optional(v.number()),
      approverRole: v.optional(v.string()),
      agentPrompt: v.optional(v.string())
    }),
    agentId: v.optional(v.id("aiAgents"))
  },
  handler: async (ctx, args) => {
    const existingSteps = await ctx.db
      .query("workflowSteps")
      .withIndex("by_workflow_id", (q) => q.eq("workflowId", args.workflowId))
      .collect();
    
    const nextOrder = existingSteps.length;
    
    return await ctx.db.insert("workflowSteps", {
      workflowId: args.workflowId,
      order: nextOrder,
      type: args.type,
      config: args.config,
      agentId: args.agentId,
      title: args.title
    });
  },
});

export const updateStep = mutation({
  args: {
    stepId: v.id("workflowSteps"),
    title: v.optional(v.string()),
    config: v.optional(v.object({
      delayMinutes: v.optional(v.number()),
      approverRole: v.optional(v.string()),
      agentPrompt: v.optional(v.string())
    })),
    agentId: v.optional(v.id("aiAgents"))
  },
  handler: async (ctx, args) => {
    const { stepId, ...updates } = args;
    const cleanUpdates = Object.fromEntries(
      Object.entries(updates).filter(([_, value]) => value !== undefined)
    );
    
    await ctx.db.patch(stepId, cleanUpdates);
  },
});

export const toggleWorkflow = mutation({
  args: { workflowId: v.id("workflows"), isActive: v.boolean() },
  handler: async (ctx, args) => {
    await ctx.db.patch(args.workflowId, { isActive: args.isActive });
  },
});

export const createFromTemplate = mutation({
  args: {
    businessId: v.id("businesses"),
    templateId: v.id("workflowTemplates"),
    createdBy: v.id("users")
  },
  handler: async (ctx, args) => {
    const template = await ctx.db.get(args.templateId);
    if (!template) throw new Error("Template not found");
    
    // Create workflow
    const workflowId = await ctx.db.insert("workflows", {
      businessId: args.businessId,
      name: template.name,
      description: template.description,
      trigger: "manual",
      triggerConfig: {},
      isActive: true,
      createdBy: args.createdBy,
      approvalPolicy: {
        type: "single",
        approvers: ["manager"]
      },
      associatedAgentIds: []
    });
    
    // Create steps
    for (let i = 0; i < template.steps.length; i++) {
      const step = template.steps[i];
      await ctx.db.insert("workflowSteps", {
        workflowId,
        order: i,
        type: step.type,
        config: step.config,
        title: step.title,
        agentId: undefined // Will be set later when user configures
      });
    }
    
    return workflowId;
  },
});

export const approveRunStep = mutation({
  args: {
    runStepId: v.id("workflowRunSteps"),
    approved: v.boolean(),
    note: v.optional(v.string())
  },
  handler: async (ctx, args) => {
    const runStep = await ctx.db.get(args.runStepId);
    if (!runStep) throw new Error("Run step not found");
    
    await ctx.db.patch(args.runStepId, {
      status: args.approved ? "completed" : "failed",
      finishedAt: Date.now(),
      output: {
        approved: args.approved,
        note: args.note || ""
      }
    });
    
    // Continue workflow execution if approved
    if (args.approved) {
      await ctx.scheduler.runAfter(0, internal.workflows.executeNext, {
        runId: runStep.runId
      });
    }
  },
});

export const seedTemplates = mutation({
  args: {},
  handler: async (ctx) => {
    const templates = [
      {
        name: "E-commerce Launch",
        category: "Marketing",
        description: "Complete product launch workflow with market research, content creation, and campaign execution",
        steps: [
          {
            type: "agent" as const,
            title: "Market Research & Strategy",
            agentType: "strategic_planning",
            config: { agentPrompt: "Analyze market opportunity and create launch strategy" }
          },
          {
            type: "approval" as const,
            title: "Strategy Approval",
            config: { approverRole: "Marketing Manager" }
          },
          {
            type: "agent" as const,
            title: "Create Launch Content",
            agentType: "content_creation",
            config: { agentPrompt: "Generate product descriptions, social posts, and email campaigns" }
          },
          {
            type: "agent" as const,
            title: "Execute Marketing Campaign",
            agentType: "marketing_automation",
            config: { agentPrompt: "Launch multi-channel marketing campaign" }
          },
          {
            type: "delay" as const,
            title: "Campaign Runtime",
            config: { delayMinutes: 1440 } // 24 hours
          },
          {
            type: "agent" as const,
            title: "Analyze Results",
            agentType: "data_analysis",
            config: { agentPrompt: "Generate launch performance report" }
          }
        ],
        recommendedAgents: ["strategic_planning", "content_creation", "marketing_automation", "data_analysis"],
        industryTags: ["e-commerce", "retail", "product-launch"]
      },
      {
        name: "SaaS Case Study Drip",
        category: "Content",
        description: "Automated case study creation and distribution workflow",
        steps: [
          {
            type: "agent" as const,
            title: "Customer Success Research",
            agentType: "customer_support",
            config: { agentPrompt: "Gather customer success metrics and testimonials" }
          },
          {
            type: "agent" as const,
            title: "Create Case Study Content",
            agentType: "content_creation",
            config: { agentPrompt: "Write compelling case study with metrics and quotes" }
          },
          {
            type: "approval" as const,
            title: "Content Review",
            config: { approverRole: "Content Manager" }
          },
          {
            type: "agent" as const,
            title: "Distribute Case Study",
            agentType: "marketing_automation",
            config: { agentPrompt: "Share case study across channels and nurture sequences" }
          }
        ],
        recommendedAgents: ["customer_support", "content_creation", "marketing_automation"],
        industryTags: ["saas", "b2b", "content-marketing"]
      },
      {
        name: "Low Engagement Social Push",
        category: "Social Media",
        description: "Reactive workflow to boost engagement when metrics drop",
        steps: [
          {
            type: "agent" as const,
            title: "Analyze Engagement Drop",
            agentType: "data_analysis",
            config: { agentPrompt: "Identify causes of low engagement and recommend actions" }
          },
          {
            type: "agent" as const,
            title: "Create Engaging Content",
            agentType: "content_creation",
            config: { agentPrompt: "Generate high-engagement social content based on analysis" }
          },
          {
            type: "agent" as const,
            title: "Execute Social Campaign",
            agentType: "marketing_automation",
            config: { agentPrompt: "Launch targeted social media campaign to boost engagement" }
          },
          {
            type: "delay" as const,
            title: "Monitor Period",
            config: { delayMinutes: 480 } // 8 hours
          },
          {
            type: "agent" as const,
            title: "Measure Impact",
            agentType: "data_analysis",
            config: { agentPrompt: "Analyze engagement improvement and ROI" }
          }
        ],
        recommendedAgents: ["data_analysis", "content_creation", "marketing_automation"],
        industryTags: ["social-media", "engagement", "reactive"]
      }
    ];
    
    for (const template of templates) {
      await ctx.db.insert("workflowTemplates", template);
    }
    
    return templates.length;
  },
});

// Actions
export const runWorkflow = action({
  args: {
    workflowId: v.id("workflows"),
    startedBy: v.id("users"),
    dryRun: v.optional(v.boolean())
  },
  handler: async (ctx, args) => {
    const workflow: any = await ctx.runQuery(internal.workflows.getWorkflowInternal, {
      workflowId: args.workflowId
    });
    
    if (!workflow) throw new Error("Workflow not found");
    
    // Create workflow run
    const runId: Id<"workflowRuns"> = await ctx.runMutation(internal.workflows.createWorkflowRun, {
      workflowId: args.workflowId,
      startedBy: args.startedBy,
      dryRun: args.dryRun || false,
      totalSteps: workflow.steps.length
    });
    
    // Start execution
    await ctx.runAction(internal.workflows.executeNext, { runId });
    
    return runId;
  },
});

export const executeNext = internalAction({
  args: { runId: v.id("workflowRuns") },
  handler: async (ctx, args) => {
    const run: any = await ctx.runQuery(internal.workflows.getWorkflowRunInternal, {
      runId: args.runId
    });
    
    if (!run || run.status !== "running") return;
    
    // Find next pending step
    const nextStep = run.steps.find((s: any) => s.status === "pending");
    if (!nextStep) {
      // All steps completed
      await ctx.runMutation(internal.workflows.completeWorkflowRun, {
        runId: args.runId
      });
      return;
    }
    
    // Execute step based on type
    await ctx.runMutation(internal.workflows.startRunStep, {
      runStepId: nextStep._id
    });
    
    const step: any = await ctx.runQuery(internal.workflows.getWorkflowStep, {
      stepId: nextStep.stepId
    });
    
    if (step?.type === "agent") {
      // Simulate agent execution
      const output = {
        result: `Agent ${step.agentId || 'unknown'} executed: ${step.title}`,
        metrics: { confidence: 0.85, executionTime: Math.random() * 1000 },
        timestamp: Date.now()
      };
      
      await ctx.runMutation(internal.workflows.completeRunStep, {
        runStepId: nextStep._id,
        output
      });
      
      // Continue to next step
      await ctx.runAction(internal.workflows.executeNext, { runId: args.runId });
      
    } else if (step?.type === "approval") {
      // Set to awaiting approval
      await ctx.runMutation(internal.workflows.awaitApproval, {
        runStepId: nextStep._id
      });
      
    } else if (step?.type === "delay") {
      // Skip delay in demo
      await ctx.runMutation(internal.workflows.completeRunStep, {
        runStepId: nextStep._id,
        output: { skipped: true, reason: "Delay skipped in demo" }
      });
      
      // Continue to next step
      await ctx.runAction(internal.workflows.executeNext, { runId: args.runId });
    }
  },
});

// Internal functions
export const getWorkflowInternal = internalQuery({
  args: { workflowId: v.id("workflows") },
  handler: async (ctx, args) => {
    const workflow = await ctx.db.get(args.workflowId);
    if (!workflow) return null;
    
    const steps = await ctx.db
      .query("workflowSteps")
      .withIndex("by_workflow_id", (q) => q.eq("workflowId", args.workflowId))
      .collect();
    
    return { ...workflow, steps: steps.sort((a, b) => a.order - b.order) };
  },
});

export const getWorkflowRunInternal = internalQuery({
  args: { runId: v.id("workflowRuns") },
  handler: async (ctx, args) => {
    const run = await ctx.db.get(args.runId);
    if (!run) return null;
    
    const runSteps = await ctx.db
      .query("workflowRunSteps")
      .withIndex("by_run_id", (q) => q.eq("runId", args.runId))
      .collect();
    
    return { ...run, steps: runSteps };
  },
});

export const getWorkflowStep = internalQuery({
  args: { stepId: v.id("workflowSteps") },
  handler: async (ctx, args) => {
    return await ctx.db.get(args.stepId);
  },
});

export const createWorkflowRun = internalMutation({
  args: {
    workflowId: v.id("workflows"),
    startedBy: v.id("users"),
    dryRun: v.boolean(),
    totalSteps: v.number()
  },
  handler: async (ctx, args) => {
    const runId = await ctx.db.insert("workflowRuns", {
      workflowId: args.workflowId,
      status: "running",
      startedBy: args.startedBy,
      startedAt: Date.now(),
      summary: {
        totalSteps: args.totalSteps,
        completedSteps: 0,
        failedSteps: 0,
        outputs: []
      },
      dryRun: args.dryRun
    });
    
    // Create run steps
    const steps = await ctx.db
      .query("workflowSteps")
      .withIndex("by_workflow_id", (q) => q.eq("workflowId", args.workflowId))
      .collect();
    
    for (const step of steps.sort((a, b) => a.order - b.order)) {
      await ctx.db.insert("workflowRunSteps", {
        runId,
        stepId: step._id,
        status: "pending"
      });
    }
    
    return runId;
  },
});

export const startRunStep = internalMutation({
  args: { runStepId: v.id("workflowRunSteps") },
  handler: async (ctx, args) => {
    await ctx.db.patch(args.runStepId, {
      status: "running",
      startedAt: Date.now()
    });
  },
});

export const completeRunStep = internalMutation({
  args: {
    runStepId: v.id("workflowRunSteps"),
    output: v.any()
  },
  handler: async (ctx, args) => {
    await ctx.db.patch(args.runStepId, {
      status: "completed",
      finishedAt: Date.now(),
      output: args.output
    });
  },
});

export const awaitApproval = internalMutation({
  args: { runStepId: v.id("workflowRunSteps") },
  handler: async (ctx, args) => {
    const runStep = await ctx.db.get(args.runStepId);
    if (!runStep) return;
    
    await ctx.db.patch(args.runStepId, {
      status: "awaiting_approval"
    });
    
    // Update run status
    await ctx.db.patch(runStep.runId, {
      status: "awaiting_approval"
    });
  },
});

export const completeWorkflowRun = internalMutation({
  args: { runId: v.id("workflowRuns") },
  handler: async (ctx, args) => {
    const runSteps = await ctx.db
      .query("workflowRunSteps")
      .withIndex("by_run_id", (q) => q.eq("runId", args.runId))
      .collect();
    
    const completedSteps = runSteps.filter(s => s.status === "completed").length;
    const failedSteps = runSteps.filter(s => s.status === "failed").length;
    
    await ctx.db.patch(args.runId, {
      status: "completed",
      finishedAt: Date.now(),
      summary: {
        totalSteps: runSteps.length,
        completedSteps,
        failedSteps,
        outputs: runSteps.map(s => s.output).filter(Boolean)
      }
    });
  },
});
