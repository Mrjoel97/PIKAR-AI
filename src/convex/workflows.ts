import { v } from "convex/values";
import { query, mutation, action, internalMutation, internalQuery, internalAction } from "./_generated/server";
import { internal } from "./_generated/api";
import { Id } from "./_generated/dataModel";
// Add standardized error handling wrapper
import { withErrorHandling } from "./utils";
import { paginationOptsValidator } from "convex/server";

// Queries
export const listWorkflows = query({
  args: { 
    businessId: v.id("businesses"),
    templatesOnly: v.optional(v.boolean())
  },
  handler: async (ctx, args) => {
    // Use schema-aligned index name
    return await ctx.db
      .query("workflows")
      .withIndex("by_business", (q) => q.eq("businessId", args.businessId))
      .order("desc")
      .collect();
  },
});

export const getWorkflow = query({
  args: { workflowId: v.id("workflows") },
  handler: withErrorHandling(async (ctx, args) => {
    const workflow = await ctx.db.get(args.workflowId);
    if (!workflow) return null;
    
    const steps = await ctx.db
      .query("workflowSteps")
      .withIndex("by_workflow_id", (q: any) => q.eq("workflowId", args.workflowId))
      .collect();
    
    return { ...workflow, steps: steps.sort((a: any, b: any) => a.order - b.order) };
  }),
});

export const listWorkflowRuns = query({
  args: { workflowId: v.id("workflows") },
  handler: withErrorHandling(async (ctx, args) => {
    const runs = await ctx.db
      .query("workflowRuns")
      .withIndex("by_workflow_id", (q: any) => q.eq("workflowId", args.workflowId))
      .order("desc")
      .collect();
    
    return runs;
  }),
});

export const getWorkflowRun = query({
  args: { runId: v.id("workflowRuns") },
  handler: withErrorHandling(async (ctx, args) => {
    const run = await ctx.db.get(args.runId);
    if (!run) return null;
    
    const runSteps = await ctx.db
      .query("workflowRunSteps")
      .withIndex("by_run_id", (q: any) => q.eq("runId", args.runId))
      .collect();
    
    return { ...run, steps: runSteps };
  }),
});

export const listTemplates = query({
  args: {},
  handler: withErrorHandling(async (ctx) => {
    return await ctx.db.query("workflowTemplates").collect();
  }),
});

// Add: Governance & Compliance visibility queries (Risks, Incidents, Nonconformities, SOPs, Compliance Checks, Audit Logs)
export const listRisks = query({
  args: { businessId: v.id("businesses") },
  handler: withErrorHandling(async (ctx, args) => {
    return await ctx.db
      .query("risks")
      .withIndex("by_businessId_and_status", (q: any) => q.eq("businessId", args.businessId))
      .order("desc")
      .collect();
  }),
});

export const listIncidents = query({
  args: { businessId: v.id("businesses") },
  handler: withErrorHandling(async (ctx, args) => {
    return await ctx.db
      .query("incidents")
      .withIndex("by_businessId_and_status", (q: any) => q.eq("businessId", args.businessId))
      .order("desc")
      .collect();
  }),
});

export const listNonconformities = query({
  args: { businessId: v.id("businesses") },
  handler: withErrorHandling(async (ctx, args) => {
    return await ctx.db
      .query("nonconformities")
      .withIndex("by_businessId_and_status", (q: any) => q.eq("businessId", args.businessId))
      .order("desc")
      .collect();
  }),
});

export const listSops = query({
  args: { businessId: v.id("businesses"), status: v.optional(v.union(v.literal("draft"), v.literal("active"), v.literal("archived"))) },
  handler: withErrorHandling(async (ctx, args) => {
    if (args.status) {
      // Fast path when status is provided
      return await ctx.db
        .query("sops")
        .withIndex("by_businessId_and_status", (q: any) =>
          q.eq("businessId", args.businessId).eq("status", args.status),
        )
        .order("desc")
        .collect();
    }
    // List all SOPs for a business (use processKey index to avoid scans)
    return await ctx.db
      .query("sops")
      .withIndex("by_businessId_and_processKey", (q: any) => q.eq("businessId", args.businessId))
      .order("desc")
      .collect();
  }),
});

export const listComplianceChecks = query({
  args: { businessId: v.id("businesses"), subjectType: v.optional(v.string()) },
  handler: withErrorHandling(async (ctx, args) => {
    if (args.subjectType) {
      return await ctx.db
        .query("compliance_checks")
        .withIndex("by_businessId_and_subject", (q: any) =>
          q.eq("businessId", args.businessId).eq("subjectType", args.subjectType),
        )
        .order("desc")
        .collect();
    }
    // Query by businessId only using the composite index
    return await ctx.db
      .query("compliance_checks")
      .withIndex("by_businessId_and_subject", (q: any) => q.eq("businessId", args.businessId))
      .order("desc")
      .collect();
  }),
});

export const listAuditLogs = query({
  args: { businessId: v.optional(v.id("businesses")), action: v.optional(v.string()) },
  handler: withErrorHandling(async (ctx, args) => {
    if (args.businessId) {
      if (args.action) {
        return await ctx.db
          .query("audit_logs")
          .withIndex("by_businessId_and_action", (q: any) => q.eq("businessId", args.businessId).eq("action", args.action))
          .order("desc")
          .collect();
      }
      return await ctx.db
        .query("audit_logs")
        .withIndex("by_businessId_and_action", (q: any) => q.eq("businessId", args.businessId))
        .order("desc")
        .collect();
    }
    // Fallback: query by action only (uses by_action index) or full list if no filters
    if (args.action) {
      return await ctx.db
        .query("audit_logs")
        .withIndex("by_action", (q: any) => q.eq("action", args.action))
        .order("desc")
        .collect();
    }
    // Note: no global index; avoid scans — return empty to enforce filtered access
    return [];
  }),
});

export const getTemplates = query({
  args: { businessId: v.id("businesses") },
  handler: async (ctx, args) => {
    return await ctx.db
      .query("workflows")
      .withIndex("by_business_and_template", (q) => 
        q.eq("businessId", args.businessId).eq("template", true))
      .order("desc")
      .collect();
  },
});

export const getExecutions = query({
  args: { 
    workflowId: v.id("workflows"),
    paginationOpts: paginationOptsValidator
  },
  handler: async (ctx, args) => {
    return await ctx.db
      .query("workflowExecutions")
      .withIndex("by_workflow", (q) => q.eq("workflowId", args.workflowId))
      .order("desc")
      .paginate(args.paginationOpts);
  },
});

export const suggested = query({
  args: { businessId: v.id("businesses") },
  handler: async (ctx, args) => {
    // Basic rule-based suggestions
    const initiatives = await ctx.db
      .query("initiatives")
      .collect();
    
    const agents = await ctx.db
      .query("aiAgents")
      .collect();

    const suggestions = [];
    
    if (initiatives.length > 0 && agents.length > 0) {
      suggestions.push({
        name: "Content Marketing Pipeline",
        description: "Automated content creation and distribution workflow",
        trigger: { type: "schedule" as const, cron: "0 9 * * 1" },
        pipeline: [
          { kind: "agent" as const, agentId: agents[0]._id, input: "Generate weekly content ideas" },
          { kind: "approval" as const, approverRole: "manager" }
        ],
        tags: ["marketing", "content"]
      });
    }

    if (initiatives.length > 2) {
      suggestions.push({
        name: "Initiative Health Check",
        description: "Weekly review of initiative progress and risks",
        trigger: { type: "schedule" as const, cron: "0 10 * * 5" },
        pipeline: [
          { kind: "branch" as const, condition: { metric: "completion", op: "<" as const, value: 50 }, onTrueNext: 1, onFalseNext: 2 },
          { kind: "approval" as const, approverRole: "lead" }
        ],
        tags: ["management", "review"]
      });
    }

    return suggestions;
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
  handler: withErrorHandling(async (ctx, args) => {
    return await ctx.db.insert("workflows", {
      ...args,
      isActive: true
    });
  }),
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
  handler: withErrorHandling(async (ctx, args) => {
    const existingSteps = await ctx.db
      .query("workflowSteps")
      .withIndex("by_workflow_id", (q: any) => q.eq("workflowId", args.workflowId))
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
  }),
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
  handler: withErrorHandling(async (ctx, args) => {
    const { stepId, ...updates } = args;
    const cleanUpdates = Object.fromEntries(
      Object.entries(updates).filter(([_, value]) => value !== undefined)
    );
    
    await ctx.db.patch(stepId, cleanUpdates);
  }),
});

export const toggleWorkflow = mutation({
  args: { workflowId: v.id("workflows"), isActive: v.boolean() },
  handler: withErrorHandling(async (ctx, args) => {
    await ctx.db.patch(args.workflowId, { isActive: args.isActive });
  }),
});

export const createFromTemplate = mutation({
  args: {
    businessId: v.id("businesses"),
    templateId: v.id("workflowTemplates"),
    createdBy: v.id("users")
  },
  handler: withErrorHandling(async (ctx, args) => {
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
  }),
});

export const approveRunStep = mutation({
  args: {
    runStepId: v.id("workflowRunSteps"),
    approved: v.boolean(),
    note: v.optional(v.string())
  },
  handler: withErrorHandling(async (ctx, args) => {
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
  }),
});

export const seedTemplates = mutation({
  args: {},
  handler: withErrorHandling(async (ctx) => {
    // Load existing templates to avoid duplicates on reseed
    const existing = await ctx.db.query("workflowTemplates").collect();
    const existingNames = new Set(existing.map((t: any) => t.name));

    const templates: Array<{
  name: string;
  category: string;
  description: string;
  steps: Array<{
    type: "agent" | "approval" | "delay";
    title: string;
    agentType?: string;
    config: {
      delayMinutes?: number;
      approverRole?: string;
      agentPrompt?: string;
    };
  }>;
  recommendedAgents: string[];
  industryTags: string[];
}> = [
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
      },

      // New templates for Solopreneurs (20+)
      {
        name: "Personal Brand Builder",
        category: "Branding",
        description: "Establish a consistent personal brand presence across platforms.",
        steps: [
          { type: "agent", title: "Define Positioning Statement", agentType: "strategic_planning", config: { agentPrompt: "Craft a one-sentence positioning with target audience and value" } },
          { type: "agent", title: "Content Pillars & Topics", agentType: "content_creation", config: { agentPrompt: "Generate 5 content pillars and 20 topic ideas" } },
          { type: "approval", title: "Pillars Approval", config: { approverRole: "Founder" } },
          { type: "agent", title: "30-Day Content Calendar", agentType: "marketing_automation", config: { agentPrompt: "Create a content calendar by platform with cadence" } },
        ],
        recommendedAgents: ["strategic_planning", "content_creation", "marketing_automation"],
        industryTags: ["solopreneur", "branding", "creator"],
      },
      {
        name: "Freelance Lead Generation",
        category: "Sales",
        description: "Attract, qualify, and follow up with freelance leads.",
        steps: [
          { type: "agent", title: "Ideal Client Profile", agentType: "strategic_planning", config: { agentPrompt: "Define ICP for service offerings" } },
          { type: "agent", title: "Prospect List Build", agentType: "operations", config: { agentPrompt: "Compile 50 prospects from public sources" } },
          { type: "agent", title: "Cold Outreach Sequence", agentType: "marketing_automation", config: { agentPrompt: "Draft 4-step outreach sequence with personalization tokens" } },
          { type: "delay", title: "Wait Before Follow-up", config: { delayMinutes: 2880 } },
          { type: "agent", title: "Auto Follow-up & Qualification", agentType: "marketing_automation", config: { agentPrompt: "Send follow-up and schedule discovery calls" } },
        ],
        recommendedAgents: ["strategic_planning", "operations", "marketing_automation"],
        industryTags: ["freelance", "services", "b2b"],
      },
      {
        name: "Consulting Discovery to Proposal",
        category: "Consulting",
        description: "Standardize discovery, proposal, and kickoff.",
        steps: [
          { type: "agent", title: "Discovery Call Brief", agentType: "operations", config: { agentPrompt: "Prepare discovery call agenda and intake form" } },
          { type: "agent", title: "Proposal Draft", agentType: "content_creation", config: { agentPrompt: "Create proposal with scope, timeline, pricing tiers" } },
          { type: "approval", title: "Proposal Review", config: { approverRole: "Founder" } },
          { type: "agent", title: "Send Proposal & Automate Follow-up", agentType: "marketing_automation", config: { agentPrompt: "Send proposal and set 3 follow-ups" } },
        ],
        recommendedAgents: ["operations", "content_creation", "marketing_automation"],
        industryTags: ["consulting", "b2b"],
      },
      {
        name: "Online Course Launch",
        category: "Education",
        description: "Plan, pre-sell, and launch a cohort or evergreen course.",
        steps: [
          { type: "agent", title: "Curriculum Outline", agentType: "strategic_planning", config: { agentPrompt: "Create course modules and learning outcomes" } },
          { type: "agent", title: "Sales Page Copy", agentType: "content_creation", config: { agentPrompt: "Draft sales page with objections and FAQs" } },
          { type: "approval", title: "Sales Page Approval", config: { approverRole: "Founder" } },
          { type: "agent", title: "Email Prelaunch Sequence", agentType: "marketing_automation", config: { agentPrompt: "5-email prelaunch + 3 launch emails" } },
          { type: "delay", title: "Open Cart Window", config: { delayMinutes: 4320 } },
          { type: "agent", title: "Launch Report", agentType: "analytics", config: { agentPrompt: "Analyze signups, conversion, and next steps" } },
        ],
        recommendedAgents: ["strategic_planning", "content_creation", "marketing_automation", "analytics"],
        industryTags: ["education", "courses", "solopreneur"],
      },
      {
        name: "Podcast Production Pipeline",
        category: "Content",
        description: "End-to-end podcast planning, recording, and publishing.",
        steps: [
          { type: "agent", title: "Episode Research & Brief", agentType: "operations", config: { agentPrompt: "Create outline with talking points and CTA" } },
          { type: "agent", title: "Show Notes & Titles", agentType: "content_creation", config: { agentPrompt: "Generate show notes, titles, and timestamps" } },
          { type: "approval", title: "Episode Review", config: { approverRole: "Host" } },
          { type: "agent", title: "Distribution & Social Clips", agentType: "marketing_automation", config: { agentPrompt: "Publish to platforms and create 3 social snippets" } },
        ],
        recommendedAgents: ["operations", "content_creation", "marketing_automation"],
        industryTags: ["podcast", "creator"],
      },
      {
        name: "Etsy Shop Optimization",
        category: "E-commerce",
        description: "Optimize listings, SEO, and promotions for an Etsy shop.",
        steps: [
          { type: "agent", title: "Listing SEO Audit", agentType: "analytics", config: { agentPrompt: "Audit titles, tags, and descriptions with keywords" } },
          { type: "agent", title: "Listing Refresh", agentType: "content_creation", config: { agentPrompt: "Rewrite 5 listings for SEO and conversions" } },
          { type: "agent", title: "Promo Campaign", agentType: "marketing_automation", config: { agentPrompt: "Create email and social promo plan" } },
          { type: "delay", title: "Run Promo & Monitor", config: { delayMinutes: 10080 } },
          { type: "agent", title: "Performance Summary", agentType: "analytics", config: { agentPrompt: "Summarize sales impact and next steps" } },
        ],
        recommendedAgents: ["analytics", "content_creation", "marketing_automation"],
        industryTags: ["etsy", "handmade", "e-commerce"],
      },
      {
        name: "Local Service Ads Booster",
        category: "Advertising",
        description: "Spin up hyperlocal ads with conversion tracking.",
        steps: [
          { type: "agent", title: "Offer & ICP Brief", agentType: "strategic_planning", config: { agentPrompt: "Define offer and local ICP" } },
          { type: "agent", title: "Ad Copy & Assets", agentType: "content_creation", config: { agentPrompt: "Draft 3 ad variants with hooks and CTAs" } },
          { type: "approval", title: "Ad Set Approval", config: { approverRole: "Founder" } },
          { type: "agent", title: "Tracking & Launch Checklist", agentType: "operations", config: { agentPrompt: "Set up pixels and launch checklist" } },
          { type: "agent", title: "Weekly Performance Report", agentType: "analytics", config: { agentPrompt: "Report CPC, CTR, CPL with insights" } },
        ],
        recommendedAgents: ["strategic_planning", "content_creation", "operations", "analytics"],
        industryTags: ["local-services", "home-services"],
      },
      {
        name: "Personal Brand Newsletter Engine",
        category: "Email",
        description: "Produce and send a weekly newsletter with repurposing.",
        steps: [
          { type: "agent", title: "Topics Pipeline", agentType: "content_creation", config: { agentPrompt: "Generate 10 newsletter topics from pillars" } },
          { type: "agent", title: "Draft Newsletter", agentType: "content_creation", config: { agentPrompt: "Write newsletter with story and CTA" } },
          { type: "approval", title: "Editorial Review", config: { approverRole: "Founder" } },
          { type: "agent", title: "Send & Repurpose", agentType: "marketing_automation", config: { agentPrompt: "Send newsletter and create 3 social posts" } },
        ],
        recommendedAgents: ["content_creation", "marketing_automation"],
        industryTags: ["newsletter", "creator", "solopreneur"],
      },
      {
        name: "YouTube Channel Growth",
        category: "Content",
        description: "Plan, script, publish, and analyze weekly videos.",
        steps: [
          { type: "agent", title: "Keyword & Angle Research", agentType: "analytics", config: { agentPrompt: "Find 5 keywords and video angles" } },
          { type: "agent", title: "Script & Hook Variations", agentType: "content_creation", config: { agentPrompt: "Write script with 3 hook variations" } },
          { type: "approval", title: "Script Approval", config: { approverRole: "Host" } },
          { type: "agent", title: "Optimize Title/Description/Tags", agentType: "marketing_automation", config: { agentPrompt: "Optimize metadata for CTR and SEO" } },
          { type: "agent", title: "Post-Performance Review", agentType: "analytics", config: { agentPrompt: "Analyze retention and CTR, recommend next topics" } },
        ],
        recommendedAgents: ["analytics", "content_creation", "marketing_automation"],
        industryTags: ["youtube", "creator"],
      },
      {
        name: "SEO Blog Engine",
        category: "Content",
        description: "Generate, review, publish, and interlink SEO articles.",
        steps: [
          { type: "agent", title: "Keyword Cluster Plan", agentType: "analytics", config: { agentPrompt: "Build 1 cluster with 1 pillar and 5 spokes" } },
          { type: "agent", title: "Write Pillar Article", agentType: "content_creation", config: { agentPrompt: "Draft 1500-word pillar article" } },
          { type: "approval", title: "Pillar Review", config: { approverRole: "Founder" } },
          { type: "agent", title: "Write 2 Spoke Articles", agentType: "content_creation", config: { agentPrompt: "Draft 2 spoke posts with internal links" } },
          { type: "agent", title: "Index & Performance Report", agentType: "analytics", config: { agentPrompt: "Track indexing and early rankings" } },
        ],
        recommendedAgents: ["analytics", "content_creation"],
        industryTags: ["seo", "content-marketing"],
      },
      {
        name: "Event Webinar Funnel",
        category: "Events",
        description: "Run a webinar with registrations, reminders, and replays.",
        steps: [
          { type: "agent", title: "Webinar Outline & Deck Notes", agentType: "strategic_planning", config: { agentPrompt: "Outline agenda and slide talking points" } },
          { type: "agent", title: "Registration Page & Emails", agentType: "content_creation", config: { agentPrompt: "Write landing copy and 3 reminder emails" } },
          { type: "approval", title: "Funnel Approval", config: { approverRole: "Founder" } },
          { type: "agent", title: "Post-Event Replay & CTA", agentType: "marketing_automation", config: { agentPrompt: "Send replay and CTA follow-up sequence" } },
        ],
        recommendedAgents: ["strategic_planning", "content_creation", "marketing_automation"],
        industryTags: ["events", "webinar", "b2b"],
      },
      {
        name: "Affiliate Outreach Program",
        category: "Partnerships",
        description: "Set up and scale an affiliate outreach program.",
        steps: [
          { type: "agent", title: "Partner List Build", agentType: "operations", config: { agentPrompt: "Identify 50 potential affiliates" } },
          { type: "agent", title: "Outreach Copy & Assets", agentType: "content_creation", config: { agentPrompt: "Create outreach templates and one-pagers" } },
          { type: "agent", title: "Follow-up Cadence", agentType: "marketing_automation", config: { agentPrompt: "Schedule 3-stage outreach" } },
          { type: "agent", title: "Performance Tracking", agentType: "analytics", config: { agentPrompt: "Track signups, clicks, conversions" } },
        ],
        recommendedAgents: ["operations", "content_creation", "marketing_automation", "analytics"],
        industryTags: ["partnerships", "affiliate"],
      },
      {
        name: "Kickstarter Prelaunch",
        category: "Crowdfunding",
        description: "Build list, validate, and prepare for crowdfunding launch.",
        steps: [
          { type: "agent", title: "Audience & Offer Validation", agentType: "strategic_planning", config: { agentPrompt: "Define audience and prelaunch offer" } },
          { type: "agent", title: "Landing Page & Email Sequence", agentType: "content_creation", config: { agentPrompt: "Create prelaunch page and 4 email sequence" } },
          { type: "agent", title: "Content & PR Plan", agentType: "marketing_automation", config: { agentPrompt: "Develop PR angles and content plan" } },
          { type: "agent", title: "Prelaunch Metrics Report", agentType: "analytics", config: { agentPrompt: "Assess signups and readiness" } },
        ],
        recommendedAgents: ["strategic_planning", "content_creation", "marketing_automation", "analytics"],
        industryTags: ["crowdfunding", "product"],
      },
      {
        name: "Photography Mini-Sessions Booking",
        category: "Local Services",
        description: "Market and book mini-sessions efficiently.",
        steps: [
          { type: "agent", title: "Offer & Package Copy", agentType: "content_creation", config: { agentPrompt: "Create compelling packages and copy" } },
          { type: "agent", title: "Booking Page Setup", agentType: "operations", config: { agentPrompt: "Checklist for booking tools and slots" } },
          { type: "agent", title: "Local Ads + Social Plan", agentType: "marketing_automation", config: { agentPrompt: "Create local ads and 2-week social plan" } },
          { type: "agent", title: "Retargeting & Recap", agentType: "analytics", config: { agentPrompt: "Analyze bookings and retarget" } },
        ],
        recommendedAgents: ["content_creation", "operations", "marketing_automation", "analytics"],
        industryTags: ["photography", "local-services"],
      },
      {
        name: "Restaurant Soft Launch",
        category: "Hospitality",
        description: "Soft open with influencers and early customers.",
        steps: [
          { type: "agent", title: "Menu Highlights & Brand Story", agentType: "content_creation", config: { agentPrompt: "Craft story and 3 signature highlights" } },
          { type: "agent", title: "Influencer Outreach", agentType: "marketing_automation", config: { agentPrompt: "Invite local micro-influencers" } },
          { type: "delay", title: "Soft Launch Window", config: { delayMinutes: 4320 } },
          { type: "agent", title: "Review & UGC Campaign", agentType: "marketing_automation", config: { agentPrompt: "Encourage reviews and UGC posts" } },
          { type: "agent", title: "Week 1 Performance", agentType: "analytics", config: { agentPrompt: "Summarize check sizes and traffic" } },
        ],
        recommendedAgents: ["content_creation", "marketing_automation", "analytics"],
        industryTags: ["restaurant", "hospitality"],
      },
      {
        name: "Real Estate Listing Promotion",
        category: "Real Estate",
        description: "Promote property listings with multi-channel content.",
        steps: [
          { type: "agent", title: "Property Brief & Angles", agentType: "strategic_planning", config: { agentPrompt: "Craft 3 buyer personas and angles" } },
          { type: "agent", title: "Listing Copy & Flyers", agentType: "content_creation", config: { agentPrompt: "Write MLS summary and flyer copy" } },
          { type: "agent", title: "Local Ads & Email Blast", agentType: "marketing_automation", config: { agentPrompt: "Set up local ads and email to list" } },
          { type: "agent", title: "Open House Promotion", agentType: "marketing_automation", config: { agentPrompt: "Promote open house with reminders" } },
        ],
        recommendedAgents: ["strategic_planning", "content_creation", "marketing_automation"],
        industryTags: ["real-estate", "local"],
      },
      {
        name: "Fitness Coaching Funnel",
        category: "Health & Fitness",
        description: "Lead magnet, nurture, and consult booking.",
        steps: [
          { type: "agent", title: "Lead Magnet Outline", agentType: "content_creation", config: { agentPrompt: "Create 7-day challenge outline" } },
          { type: "agent", title: "Landing Page & Emails", agentType: "content_creation", config: { agentPrompt: "Write landing copy and 5-email nurture" } },
          { type: "agent", title: "Booking Automation", agentType: "marketing_automation", config: { agentPrompt: "Automate consult scheduling" } },
          { type: "agent", title: "Funnel Performance", agentType: "analytics", config: { agentPrompt: "Report opt-ins and bookings" } },
        ],
        recommendedAgents: ["content_creation", "marketing_automation", "analytics"],
        industryTags: ["fitness", "coaching"],
      },
      {
        name: "Handmade Product Launch",
        category: "E-commerce",
        description: "Launch a handmade product with story-driven content.",
        steps: [
          { type: "agent", title: "Brand Story & Product Page", agentType: "content_creation", config: { agentPrompt: "Write product story and page copy" } },
          { type: "agent", title: "IG/TikTok Teaser Plan", agentType: "marketing_automation", config: { agentPrompt: "Create 7-day teaser content plan" } },
          { type: "delay", title: "Prelaunch Window", config: { delayMinutes: 2880 } },
          { type: "agent", title: "Launch Announcements", agentType: "marketing_automation", config: { agentPrompt: "Announce across channels with CTA" } },
          { type: "agent", title: "Sales Recap", agentType: "analytics", config: { agentPrompt: "Analyze launch sales and feedback" } },
        ],
        recommendedAgents: ["content_creation", "marketing_automation", "analytics"],
        industryTags: ["handmade", "etsy", "shopify"],
      },
      {
        name: "Coaching Program Enrollment",
        category: "Coaching",
        description: "Enroll clients into a coaching program.",
        steps: [
          { type: "agent", title: "Program Promise & Outcomes", agentType: "strategic_planning", config: { agentPrompt: "Clarify outcomes and proof points" } },
          { type: "agent", title: "Sales Page & Social Proof", agentType: "content_creation", config: { agentPrompt: "Draft sales page and testimonial posts" } },
          { type: "agent", title: "DM/Email Enrollment Campaign", agentType: "marketing_automation", config: { agentPrompt: "Create 5-message DM and email flow" } },
          { type: "agent", title: "Enrollment Metrics", agentType: "analytics", config: { agentPrompt: "Track applications and enrollments" } },
        ],
        recommendedAgents: ["strategic_planning", "content_creation", "marketing_automation", "analytics"],
        industryTags: ["coaching", "education"],
      },
      {
        name: "Personal Finance Advisor Funnel",
        category: "Finance",
        description: "Lead gen and nurturing for solo advisors.",
        steps: [
          { type: "agent", title: "ICP & Compliance Checklist", agentType: "operations", config: { agentPrompt: "Create ICP and compliance notes" } },
          { type: "agent", title: "Lead Magnet & Emails", agentType: "content_creation", config: { agentPrompt: "Write budgeting guide and 4-email sequence" } },
          { type: "agent", title: "Local SEO & GMB Updates", agentType: "operations", config: { agentPrompt: "Checklist for GMB and local citations" } },
          { type: "agent", title: "Lead Flow Report", agentType: "analytics", config: { agentPrompt: "Report leads and booked calls" } },
        ],
        recommendedAgents: ["operations", "content_creation", "analytics"],
        industryTags: ["finance", "advisory", "local"],
      },
      {
        name: "Therapist Intake & Retention",
        category: "Healthcare",
        description: "Automate intake, reminders, and retention content.",
        steps: [
          { type: "agent", title: "Intake Form & Policies", agentType: "operations", config: { agentPrompt: "Draft intake and consent docs" } },
          { type: "agent", title: "Reminder & Follow-up Flow", agentType: "marketing_automation", config: { agentPrompt: "Create reminders and post-session follow-ups" } },
          { type: "agent", title: "Educational Content Plan", agentType: "content_creation", config: { agentPrompt: "Plan weekly blogs for patient education" } },
          { type: "agent", title: "Monthly Retention Report", agentType: "analytics", config: { agentPrompt: "Track attendance and retention" } },
        ],
        recommendedAgents: ["operations", "marketing_automation", "content_creation", "analytics"],
        industryTags: ["healthcare", "therapy", "local"],
      },
      {
        name: "Legal Services Consultation Funnel",
        category: "Legal",
        description: "Qualify, schedule, and follow-up for legal consults.",
        steps: [
          { type: "agent", title: "Qualification Questions", agentType: "operations", config: { agentPrompt: "Draft intake and qualification flow" } },
          { type: "agent", title: "Service Pages & FAQs", agentType: "content_creation", config: { agentPrompt: "Write practice area pages and FAQs" } },
          { type: "agent", title: "Local Ads & Retargeting", agentType: "marketing_automation", config: { agentPrompt: "Launch local ads with retargeting" } },
          { type: "agent", title: "Lead Quality Report", agentType: "analytics", config: { agentPrompt: "Summarize lead quality and cost" } },
        ],
        recommendedAgents: ["operations", "content_creation", "marketing_automation", "analytics"],
        industryTags: ["legal", "services", "local"],
      },
      {
        name: "Nonprofit Micro-Campaign",
        category: "Nonprofit",
        description: "Run a focused 2-week donation or awareness campaign.",
        steps: [
          { type: "agent", title: "Campaign Narrative", agentType: "content_creation", config: { agentPrompt: "Craft campaign story and CTA" } },
          { type: "agent", title: "Email & Social Plan", agentType: "marketing_automation", config: { agentPrompt: "Plan 2-week cadence across channels" } },
          { type: "delay", title: "Run Campaign", config: { delayMinutes: 20160 } },
          { type: "agent", title: "Impact Report", agentType: "analytics", config: { agentPrompt: "Report donations and engagement" } },
        ],
        recommendedAgents: ["content_creation", "marketing_automation", "analytics"],
        industryTags: ["nonprofit", "awareness", "donations"],
      },
      {
        name: "Digital Product Funnel",
        category: "E-commerce",
        description: "Landing page, email nurture, and upsell for a digital product.",
        steps: [
          { type: "agent", title: "Offer Positioning", agentType: "strategic_planning", config: { agentPrompt: "Clarify transformation and bonuses" } },
          { type: "agent", title: "Landing & Incentives", agentType: "content_creation", config: { agentPrompt: "Write landing page and referral incentive" } },
          { type: "agent", title: "Weekly Updates & Surveys", agentType: "marketing_automation", config: { agentPrompt: "Send updates and micro-surveys" } },
          { type: "agent", title: "Waitlist Growth Report", agentType: "analytics", config: { agentPrompt: "Track signups and referral K-factor" } },
        ],
        recommendedAgents: ["strategic_planning", "content_creation", "marketing_automation", "analytics"],
        industryTags: ["digital-products", "gumroad", "shopify"],
      },
      {
        name: "Creator Sponsorship Outreach",
        category: "Creator Economy",
        description: "Find, pitch, and close sponsorships.",
        steps: [
          { type: "agent", title: "Media Kit Draft", agentType: "content_creation", config: { agentPrompt: "Create media kit overview and stats" } },
          { type: "agent", title: "Prospect List & Pitch", agentType: "operations", config: { agentPrompt: "Build 30-brand list and pitch templates" } },
          { type: "agent", title: "Follow-ups & Negotiation Aids", agentType: "marketing_automation", config: { agentPrompt: "Automate follow-ups and negotiation checklists" } },
          { type: "agent", title: "Deals Pipeline Report", agentType: "analytics", config: { agentPrompt: "Summarize responses and deals won" } },
        ],
        recommendedAgents: ["content_creation", "operations", "marketing_automation", "analytics"],
        industryTags: ["creator", "sponsorships"],
      },
      {
        name: "UX/UI Freelancer Portfolio Refresh",
        category: "Design",
        description: "Revamp portfolio and outreach to land projects.",
        steps: [
          { type: "agent", title: "Case Study Outlines", agentType: "content_creation", config: { agentPrompt: "Outline 3 case studies with outcomes" } },
          { type: "agent", title: "Portfolio Copy & Structure", agentType: "content_creation", config: { agentPrompt: "Rewrite homepage and services pages" } },
          { type: "agent", title: "Prospect Outreach", agentType: "marketing_automation", config: { agentPrompt: "Create 4-step outreach with personalization" } },
          { type: "agent", title: "Pipeline Report", agentType: "analytics", config: { agentPrompt: "Track replies and calls booked" } },
        ],
        recommendedAgents: ["content_creation", "marketing_automation", "analytics"],
        industryTags: ["design", "freelance", "portfolio"],
      },
      {
        name: "Dropshipping Validation Sprint",
        category: "E-commerce",
        description: "Validate a product with fast content and ads.",
        steps: [
          { type: "agent", title: "Product Angles & Hooks", agentType: "strategic_planning", config: { agentPrompt: "Define 3 angles and hooks" } },
          { type: "agent", title: "Creative Variations", agentType: "content_creation", config: { agentPrompt: "Draft 5 ad creative scripts" } },
          { type: "agent", title: "Quick Landing & Tracking", agentType: "operations", config: { agentPrompt: "Checklist for landing and pixel setup" } },
          { type: "agent", title: "48h Test Analysis", agentType: "analytics", config: { agentPrompt: "Report CPC/CTR/CPA and next steps" } },
        ],
        recommendedAgents: ["strategic_planning", "content_creation", "operations", "analytics"],
        industryTags: ["dropshipping", "validation"],
      },
      {
        name: "LinkedIn Authority Builder",
        category: "Social",
        description: "Daily posting with DM nurture and content repurposing.",
        steps: [
          { type: "agent", title: "30 Post Ideas", agentType: "content_creation", config: { agentPrompt: "Generate 30 posts with hooks and CTAs" } },
          { type: "agent", title: "Posting Schedule", agentType: "marketing_automation", config: { agentPrompt: "Create daily posting schedule" } },
          { type: "agent", title: "DM Nurture Cadence", agentType: "marketing_automation", config: { agentPrompt: "Draft 3-step DM flow to call booking" } },
          { type: "agent", title: "Engagement Report", agentType: "analytics", config: { agentPrompt: "Summarize reach and replies" } },
        ],
        recommendedAgents: ["content_creation", "marketing_automation", "analytics"],
        industryTags: ["linkedin", "b2b", "authority"],
      },
      {
        name: "Influencer UGC Pipeline",
        category: "UGC",
        description: "Collect and publish user-generated content.",
        steps: [
          { type: "agent", title: "UGC Guidelines & Brief", agentType: "operations", config: { agentPrompt: "Create UGC brief and consent checklist" } },
          { type: "agent", title: "Call for UGC Posts", agentType: "marketing_automation", config: { agentPrompt: "Draft posts and email requests for UGC" } },
          { type: "agent", title: "Curation & Scheduling", agentType: "marketing_automation", config: { agentPrompt: "Curate and schedule UGC posts" } },
          { type: "agent", title: "Impact Report", agentType: "analytics", config: { agentPrompt: "Analyze engagement from UGC" } },
        ],
        recommendedAgents: ["operations", "marketing_automation", "analytics"],
        industryTags: ["ugc", "social"],
      },
      {
        name: "Micro-SaaS Waitlist Growth",
        category: "SaaS",
        description: "Drive signups for early access with feedback loops.",
        steps: [
          { type: "agent", title: "Positioning & ICP Doc", agentType: "strategic_planning", config: { agentPrompt: "Draft positioning and ICP jobs-to-be-done" } },
          { type: "agent", title: "Landing & Incentives", agentType: "content_creation", config: { agentPrompt: "Write landing page and referral incentive" } },
          { type: "agent", title: "Weekly Updates & Surveys", agentType: "marketing_automation", config: { agentPrompt: "Send updates and micro-surveys" } },
          { type: "agent", title: "Waitlist Growth Report", agentType: "analytics", config: { agentPrompt: "Track signups and referral K-factor" } },
        ],
        recommendedAgents: ["strategic_planning", "content_creation", "marketing_automation", "analytics"],
        industryTags: ["saas", "waitlist"],
      },
      {
        name: "CAPA Remediation",
        category: "Compliance",
        description: "Corrective and Preventive Action workflow for incidents and nonconformities.",
        steps: [
          { type: "approval" as const, title: "Triage & Assignment", config: { approverRole: "Compliance Lead" } },
          { type: "agent" as const, title: "Root Cause Analysis", agentType: "operations", config: { agentPrompt: "Analyze incident and identify root cause(s)" } },
          { type: "agent" as const, title: "Action Plan Draft", agentType: "content_creation", config: { agentPrompt: "Draft corrective and preventive action plan" } },
          { type: "approval" as const, title: "Plan Approval", config: { approverRole: "Compliance Lead" } },
          { type: "delay" as const, title: "Implementation Window", config: { delayMinutes: 1440 } },
          { type: "agent" as const, title: "Effectiveness Review", agentType: "analytics", config: { agentPrompt: "Assess action effectiveness and residual risk" } },
        ],
        recommendedAgents: ["operations", "content_creation", "analytics"],
        industryTags: ["compliance", "quality"],
      },
    ];

    let inserted = 0;
    for (const template of templates) {
      if (!existingNames.has(template.name)) {
        await ctx.db.insert("workflowTemplates", template);
        inserted++;
      }
    }

    return inserted;
  }),
});

// Actions
export const runWorkflow = action({
  args: {
    workflowId: v.id("workflows"),
    startedBy: v.id("users"),
    dryRun: v.optional(v.boolean())
  },
  handler: withErrorHandling(async (ctx, args) => {
    const workflow: any = await ctx.runQuery(internal.workflows.getWorkflowInternal, {
      workflowId: args.workflowId
    });
    
    if (!workflow) throw new Error("Workflow not found");
    
    // Create workflow run
    const runId: Id<"workflowRuns"> = await ctx.runMutation(internal.workflows.createWorkflowRun, {
      workflowId: args.workflowId,
      startedBy: args.startedBy ?? undefined,
      dryRun: args.dryRun || false,
      totalSteps: workflow.steps.length
    });
    
    // Start execution
    await ctx.runAction(internal.workflows.executeNext, { runId });
    
    return runId;
  }),
});

export const executeNext = internalAction({
  args: { runId: v.id("workflowRuns") },
  handler: withErrorHandling(async (ctx, args) => {
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
  }),
});

// Add: simulateWorkflow action (runtime params + compliance preview)
export const simulateWorkflow = action({
  args: {
    workflowId: v.id("workflows"),
    params: v.optional(v.record(v.string(), v.any())),
  },
  handler: withErrorHandling(async (ctx, args) => {
    const workflow: any = await ctx.runQuery(internal.workflows.getWorkflowInternal, {
      workflowId: args.workflowId,
    });
    if (!workflow) throw new Error("Workflow not found");

    const params = args.params || {};
    // Build simulated steps with expected outputs
    const simulatedSteps = workflow.steps.map((s: any) => {
      const base = {
        stepId: s._id,
        type: s.type,
        title: s.title,
      };
      if (s.type === "agent") {
        return {
          ...base,
          expectedOutput: {
            preview: `Would execute agent ${s.agentId || "unassigned"}: ${s.title}`,
            paramsUsed: params,
          },
        };
      }
      if (s.type === "approval") {
        return {
          ...base,
          expectedOutput: {
            preview: `Would await approval (${s?.config?.approverRole || "approver"})`,
          },
        };
      }
      if (s.type === "delay") {
        return {
          ...base,
          expectedOutput: {
            preview: `Would wait for ${s?.config?.delayMinutes ?? 0} minute(s)`,
          },
        };
      }
      return { ...base, expectedOutput: { preview: "Unknown step type" } };
    });

    // Simple regulatory cues based on step titles/keywords
    const textBlob = [workflow.name, workflow.description, ...workflow.steps.map((s: any) => s.title)].join(" ").toLowerCase();
    const complianceChecks: Array<{ domain: "healthcare" | "finance"; note: string }> = [];
    if (textBlob.includes("patient") || textBlob.includes("hipaa") || textBlob.includes("therapy") || textBlob.includes("healthcare")) {
      complianceChecks.push({
        domain: "healthcare",
        note: "HIPAA compliance: Verify PHI handling, consent, and access controls before executing publishing steps.",
      });
    }
    if (textBlob.includes("finance") || textBlob.includes("financial") || textBlob.includes("audit") || textBlob.includes("report")) {
      complianceChecks.push({
        domain: "finance",
        note: "Finance compliance: Ensure audit trail generation and approvals before releasing financial outputs.",
      });
    }

    return {
      workflowId: args.workflowId,
      steps: simulatedSteps,
      complianceChecks,
      summary: {
        totalSteps: simulatedSteps.length,
        agentSteps: simulatedSteps.filter((s: any) => s.type === "agent").length,
        approvalSteps: simulatedSteps.filter((s: any) => s.type === "approval").length,
        delaySteps: simulatedSteps.filter((s: any) => s.type === "delay").length,
      },
    };
  }),
});

// Add: createBlueprintFromWorkflow mutation
export const createBlueprintFromWorkflow = mutation({
  args: {
    workflowId: v.id("workflows"),
    name: v.optional(v.string()),
    description: v.optional(v.string()),
    category: v.optional(v.string()),
  },
  handler: withErrorHandling(async (ctx, args) => {
    const wf = await ctx.db.get(args.workflowId);
    if (!wf) throw new Error("Workflow not found");

    const steps = await ctx.db
      .query("workflowSteps")
      .withIndex("by_workflow_id", (q: any) => q.eq("workflowId", args.workflowId))
      .collect();

    // Map to template-compatible shape
    const templateSteps = steps
      .sort((a: any, b: any) => a.order - b.order)
      .map((s: any) => ({
        type: s.type as "agent" | "approval" | "delay",
        title: s.title || (s.type === "delay" ? "Delay" : s.type),
        config: {
          delayMinutes: s?.config?.delayMinutes,
          approverRole: s?.config?.approverRole,
          agentPrompt: s?.config?.agentPrompt,
        },
      }));

    const templateId = await ctx.db.insert("workflowTemplates", {
      name: args.name ?? `${wf.name} (Blueprint)`,
      category: args.category ?? "Custom",
      description: args.description ?? (typeof wf.description === "string" ? wf.description : "Custom workflow blueprint"),
      steps: templateSteps,
      recommendedAgents: [],
      industryTags: [],
    });

    return templateId;
  }),
});

// Internal functions
export const getWorkflowInternal = internalQuery({
  args: { workflowId: v.id("workflows") },
  handler: withErrorHandling(async (ctx, args) => {
    const workflow = await ctx.db.get(args.workflowId);
    if (!workflow) return null;
    
    const steps = await ctx.db
      .query("workflowSteps")
      .withIndex("by_workflow_id", (q: any) => q.eq("workflowId", args.workflowId))
      .collect();
    
    return { ...workflow, steps: steps.sort((a: any, b: any) => a.order - b.order) };
  }),
});

export const getWorkflowRunInternal = internalQuery({
  args: { runId: v.id("workflowRuns") },
  handler: withErrorHandling(async (ctx, args) => {
    const run = await ctx.db.get(args.runId);
    if (!run) return null;
    
    const runSteps = await ctx.db
      .query("workflowRunSteps")
      .withIndex("by_run_id", (q: any) => q.eq("runId", args.runId))
      .collect();
    
    return { ...run, steps: runSteps };
  }),
});

export const getWorkflowStep = internalQuery({
  args: { stepId: v.id("workflowSteps") },
  handler: withErrorHandling(async (ctx, args) => {
    return await ctx.db.get(args.stepId);
  }),
});

export const createWorkflowRun = internalMutation({
  args: {
    workflowId: v.id("workflows"),
    startedBy: v.id("users"),
    dryRun: v.boolean(),
    totalSteps: v.number()
  },
  handler: withErrorHandling(async (ctx, args) => {
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
      .withIndex("by_workflow_id", (q: any) => q.eq("workflowId", args.workflowId))
      .collect();
    
    for (const step of steps.sort((a: any, b: any) => a.order - b.order)) {
      await ctx.db.insert("workflowRunSteps", {
        runId,
        stepId: step._id,
        status: "pending"
      });
    }
    
    return runId;
  }),
});

export const startRunStep = internalMutation({
  args: { runStepId: v.id("workflowRunSteps") },
  handler: withErrorHandling(async (ctx, args) => {
    await ctx.db.patch(args.runStepId, {
      status: "running",
      startedAt: Date.now()
    });
  }),
});

export const completeRunStep = internalMutation({
  args: {
    runStepId: v.id("workflowRunSteps"),
    output: v.any()
  },
  handler: withErrorHandling(async (ctx, args) => {
    await ctx.db.patch(args.runStepId, {
      status: "completed",
      finishedAt: Date.now(),
      output: args.output
    });
  }),
});

export const awaitApproval = internalMutation({
  args: { runStepId: v.id("workflowRunSteps") },
  handler: withErrorHandling(async (ctx, args) => {
    const runStep = await ctx.db.get(args.runStepId);
    if (!runStep) return;
    
    await ctx.db.patch(args.runStepId, {
      status: "awaiting_approval"
    });
    
    // Update run status
    await ctx.db.patch(runStep.runId, {
      status: "awaiting_approval"
    });
  }),
});

export const completeWorkflowRun = internalMutation({
  args: { runId: v.id("workflowRuns") },
  handler: withErrorHandling(async (ctx, args) => {
    const runSteps = await ctx.db
      .query("workflowRunSteps")
      .withIndex("by_run_id", (q: any) => q.eq("runId", args.runId))
      .collect();

    const completedSteps = runSteps.filter((s: any) => s.status === "completed").length;
    const failedSteps = runSteps.filter((s: any) => s.status === "failed").length;

    await ctx.db.patch(args.runId, {
      status: "completed",
      finishedAt: Date.now(),
      summary: {
        totalSteps: runSteps.length,
        completedSteps,
        failedSteps,
        outputs: runSteps.map((s: any) => s.output).filter(Boolean),
      },
    });

    // Collaboration follow-up: record a diagnostics entry if there were failures
    if (failedSteps > 0) {
      const runDoc = await ctx.db.get(args.runId);
      if (runDoc) {
        await ctx.db.insert("diagnostics", {
          type: "collaboration",
          level: "warning",
          message: `Workflow run ${String(args.runId)} completed with ${failedSteps} failed step(s). Recommend assigning a review task.`,
          businessId: (runDoc as any).businessId, // may be absent; optional fields allowed
          userId: (runDoc as any).startedBy,
          metadata: {
            runId: args.runId,
            workflowId: (runDoc as any).workflowId,
          },
          createdBy: (runDoc as any).startedBy,
          phase: "post_run",
          inputs: null,
          outputs: null,
          runAt: Date.now(),
        } as any);
      }
    }
  }),
});

// Internal helpers for Quality & Compliance

export const logAudit = internalMutation({
  args: {
    businessId: v.optional(v.id("businesses")),
    actorId: v.optional(v.id("users")),
    action: v.string(),
    subjectType: v.string(),
    subjectId: v.string(),
    metadata: v.optional(v.any()),
    ip: v.optional(v.string()),
  },
  handler: withErrorHandling(async (ctx, args) => {
    await ctx.db.insert("audit_logs", {
      businessId: args.businessId,
      actorId: args.actorId,
      action: args.action,
      subjectType: args.subjectType,
      subjectId: args.subjectId,
      metadata: args.metadata,
      ip: args.ip,
      at: Date.now(),
    });
  }),
});

export const addComplianceCheck = internalMutation({
  args: {
    businessId: v.id("businesses"),
    subjectType: v.string(),
    subjectId: v.string(),
    result: v.object({
      flags: v.array(v.string()),
      score: v.number(),
      details: v.optional(v.any()),
    }),
    status: v.union(v.literal("pass"), v.literal("warn"), v.literal("fail")),
    checkedBy: v.optional(v.id("users")),
  },
  handler: withErrorHandling(async (ctx, args) => {
    await ctx.db.insert("compliance_checks", {
      businessId: args.businessId,
      subjectType: args.subjectType,
      subjectId: args.subjectId,
      result: args.result,
      status: args.status,
      checkedAt: Date.now(),
      checkedBy: args.checkedBy,
    });
  }),
});

export const createCapaForIncident = internalMutation({
  args: {
    incidentId: v.id("incidents"),
    businessId: v.id("businesses"),
    createdBy: v.id("users"),
  },
  handler: withErrorHandling(async (ctx, args) => {
    // Ensure CAPA template exists
    const templates = await ctx.db.query("workflowTemplates").collect();
    let capa = templates.find((t: any) => t.name === "CAPA Remediation");
    if (!capa) {
      const templateId = await ctx.db.insert("workflowTemplates", {
        name: "CAPA Remediation",
        category: "Compliance",
        description: "Corrective and Preventive Action workflow for incidents and nonconformities.",
        steps: [
          { type: "approval", title: "Triage & Assignment", config: { approverRole: "Compliance Lead" } },
          { type: "agent", title: "Root Cause Analysis", config: { agentPrompt: "Analyze incident and identify root cause(s)" } },
          { type: "agent", title: "Action Plan Draft", config: { agentPrompt: "Draft corrective and preventive action plan" } },
          { type: "approval", title: "Plan Approval", config: { approverRole: "Compliance Lead" } },
          { type: "delay", title: "Implementation Window", config: { delayMinutes: 1440 } },
          { type: "agent", title: "Effectiveness Review", config: { agentPrompt: "Assess action effectiveness and residual risk" } },
        ],
        recommendedAgents: ["operations", "content_creation", "analytics"],
        industryTags: ["compliance", "quality"],
      });
      capa = await ctx.db.get(templateId);
    }

    // Mirror createFromTemplate to create a workflow
    const workflowId = await ctx.db.insert("workflows", {
      businessId: args.businessId,
      name: "CAPA for Incident",
      description: "Automated Corrective and Preventive Action workflow",
      trigger: "manual",
      triggerConfig: {},
      isActive: true,
      createdBy: args.createdBy,
      approvalPolicy: {
        type: "single",
        approvers: ["Compliance Lead"],
      },
      associatedAgentIds: [],
    } as any);

    // Create steps from template
    for (let i = 0; i < (capa as any).steps.length; i++) {
      const step = (capa as any).steps[i];
      await ctx.db.insert("workflowSteps", {
        workflowId,
        order: i,
        type: step.type,
        config: step.config,
        title: step.title,
        agentId: undefined,
      });
    }

    // Link workflow back to incident
    await ctx.db.patch(args.incidentId, {
      correctiveWorkflowId: workflowId,
      status: "investigating",
    } as any);

    await ctx.db.insert("diagnostics", {
      type: "compliance",
      level: "info",
      message: "CAPA workflow created for incident",
      businessId: args.businessId,
      userId: args.createdBy,
      metadata: { incidentId: args.incidentId, workflowId },
      createdBy: args.createdBy,
      phase: "incident",
      runAt: Date.now(),
    } as any);

    await ctx.db.insert("audit_logs", {
      businessId: args.businessId,
      actorId: args.createdBy,
      action: "incident.capa_created",
      subjectType: "incident",
      subjectId: String(args.incidentId),
      metadata: { workflowId },
      at: Date.now(),
    });

    return workflowId;
  }),
});

// Public mutations/actions for QMS & Compliance

export const reportIncident = mutation({
  args: {
    businessId: v.id("businesses"),
    reportedBy: v.id("users"),
    type: v.string(),
    description: v.string(),
    severity: v.union(v.literal("low"), v.literal("medium"), v.literal("high"), v.literal("critical")),
    linkedRiskId: v.optional(v.id("risks")),
  },
  handler: withErrorHandling(async (ctx, args) => {
    const incidentId = await ctx.db.insert("incidents", {
      businessId: args.businessId,
      type: args.type,
      description: args.description,
      severity: args.severity,
      status: "open",
      reportedBy: args.reportedBy,
      linkedRiskId: args.linkedRiskId,
      correctiveWorkflowId: undefined,
      createdAt: Date.now(),
    });

    await ctx.scheduler.runAfter(0, internal.workflows.createCapaForIncident, {
      incidentId,
      businessId: args.businessId,
      createdBy: args.reportedBy,
    });

    await ctx.scheduler.runAfter(0, internal.workflows.logAudit, {
      businessId: args.businessId,
      actorId: args.reportedBy,
      action: "incident.reported",
      subjectType: "incident",
      subjectId: String(incidentId),
      metadata: { severity: args.severity, type: args.type },
    });

    return incidentId;
  }),
});

export const logNonconformity = mutation({
  args: {
    businessId: v.id("businesses"),
    createdBy: v.id("users"),
    description: v.string(),
    severity: v.union(v.literal("low"), v.literal("medium"), v.literal("high"), v.literal("critical")),
    source: v.optional(v.string()),
    relatedWorkflowRunId: v.optional(v.id("workflowRuns")),
    autoCapa: v.optional(v.boolean()),
  },
  handler: withErrorHandling(async (ctx, args) => {
    const id = await ctx.db.insert("nonconformities", {
      businessId: args.businessId,
      description: args.description,
      severity: args.severity,
      status: "open",
      source: args.source,
      relatedWorkflowRunId: args.relatedWorkflowRunId,
      correctiveWorkflowId: undefined,
      createdBy: args.createdBy,
      createdAt: Date.now(),
    });

    if (args.autoCapa) {
      const wfId = await ctx.runMutation(internal.workflows.createCapaForIncident, {
        // Reuse incident-based CAPA for consistency; create a temporary incident to track
        incidentId: await ctx.db.insert("incidents", {
          businessId: args.businessId,
          type: "nonconformity",
          description: args.description,
          severity: args.severity,
          status: "open",
          reportedBy: args.createdBy,
          createdAt: Date.now(),
        } as any),
        businessId: args.businessId,
        createdBy: args.createdBy,
      });
      await ctx.db.patch(id, { correctiveWorkflowId: wfId } as any);
    }

    await ctx.scheduler.runAfter(0, internal.workflows.logAudit, {
      businessId: args.businessId,
      actorId: args.createdBy,
      action: "qms.nonconformity_logged",
      subjectType: "nonconformity",
      subjectId: String(id),
      metadata: { severity: args.severity },
    });

    return id;
  }),
});

export const upsertRisk = mutation({
  args: {
    riskId: v.optional(v.id("risks")),
    businessId: v.id("businesses"),
    title: v.string(),
    category: v.string(),
    score: v.number(),
    likelihood: v.union(v.literal("low"), v.literal("medium"), v.literal("high")),
    impact: v.union(v.literal("low"), v.literal("medium"), v.literal("high")),
    status: v.union(v.literal("open"), v.literal("mitigating"), v.literal("accepted"), v.literal("closed")),
    ownerId: v.id("users"),
  },
  handler: withErrorHandling(async (ctx, args) => {
    if (args.riskId) {
      await ctx.db.patch(args.riskId, {
        title: args.title,
        category: args.category,
        score: args.score,
        likelihood: args.likelihood,
        impact: args.impact,
        status: args.status,
        ownerId: args.ownerId,
        updatedAt: Date.now(),
      });
      return args.riskId;
    }
    return await ctx.db.insert("risks", {
      businessId: args.businessId,
      title: args.title,
      category: args.category,
      score: args.score,
      likelihood: args.likelihood,
      impact: args.impact,
      status: args.status,
      ownerId: args.ownerId,
      updatedAt: Date.now(),
    });
  }),
});

// Automated Compliance Checks (simple content scanner)
export const checkMarketingCompliance = action({
  args: {
    businessId: v.id("businesses"),
    subjectType: v.string(),
    subjectId: v.string(),
    content: v.string(),
    checkedBy: v.optional(v.id("users")),
  },
  handler: withErrorHandling(async (ctx, args) => {
    const text = args.content.toLowerCase();
    const flags: Array<string> = [];

    // GDPR / email compliance heuristics
    if (!(text.includes("unsubscribe") || text.includes("opt-out") || text.includes("opt out"))) {
      flags.push("missing_unsubscribe_or_opt_out");
    }
    if (text.includes("fda approved") || text.includes("fda-approved")) {
      flags.push("regulated_claim_fda");
    }
    if (text.includes("hipaa") || text.includes("patient")) {
      flags.push("potential_phi_reference");
    }

    const score = Math.max(0, 100 - flags.length * 25);
    const status: "pass" | "warn" | "fail" =
      flags.length === 0 ? "pass" : flags.length <= 2 ? "warn" : "fail";

    await ctx.runMutation(internal.workflows.addComplianceCheck, {
      businessId: args.businessId,
      subjectType: args.subjectType,
      subjectId: args.subjectId,
      result: { flags, score, details: { length: args.content.length } },
      status,
      checkedBy: args.checkedBy,
    });

    await ctx.runMutation(internal.workflows.logAudit, {
      businessId: args.businessId,
      actorId: args.checkedBy,
      action: "compliance.scan",
      subjectType: args.subjectType,
      subjectId: args.subjectId,
      metadata: { status, flags },
    });

    return { status, score, flags };
  }),
});

export const upsertSop = mutation({
  args: {
    businessId: v.id("businesses"),
    processKey: v.string(),
    title: v.string(),
    version: v.string(),
    url: v.optional(v.string()),
    status: v.union(v.literal("draft"), v.literal("active"), v.literal("archived")),
    requiresReview: v.boolean(),
    updatedBy: v.id("users"),
  },
  handler: withErrorHandling(async (ctx, args) => {
    // Try to find existing SOP by business + processKey (latest by updatedAt)
    const existing = await ctx.db
      .query("sops")
      .withIndex("by_businessId_and_processKey", (q: any) => q.eq("businessId", args.businessId).eq("processKey", args.processKey))
      .order("desc")
      .collect();

    if (existing.length > 0) {
      // Replace latest with new fields (versioned via version string)
      await ctx.db.patch(existing[0]._id, {
        title: args.title,
        version: args.version,
        url: args.url,
        status: args.status,
        requiresReview: args.requiresReview,
        updatedBy: args.updatedBy,
        updatedAt: Date.now(),
      });
      return existing[0]._id;
    }

    return await ctx.db.insert("sops", {
      businessId: args.businessId,
      processKey: args.processKey,
      title: args.title,
      version: args.version,
      url: args.url,
      status: args.status,
      requiresReview: args.requiresReview,
      updatedBy: args.updatedBy,
      updatedAt: Date.now(),
    });
  }),
});

// Neutralize upsertWorkflow to avoid patching unknown fields on the workflows table
export const upsertWorkflow = mutation({
  args: {
    id: v.optional(v.id("workflows")),
    businessId: v.id("businesses"),
    name: v.string(),
    description: v.optional(v.string()),
    trigger: v.object({
      type: v.union(v.literal("manual"), v.literal("schedule"), v.literal("webhook")),
      cron: v.optional(v.string()),
      eventKey: v.optional(v.string())
    }),
    approval: v.object({
      required: v.boolean(),
      threshold: v.number()
    }),
    pipeline: v.array(v.object({
      kind: v.union(v.literal("agent"), v.literal("branch"), v.literal("approval")),
      agentId: v.optional(v.id("aiAgents")),
      input: v.optional(v.string()),
      condition: v.optional(v.object({
        metric: v.string(),
        op: v.union(v.literal("<"), v.literal(">"), v.literal("<="), v.literal(">="), v.literal("==")),
        value: v.number()
      })),
      onTrueNext: v.optional(v.number()),
      onFalseNext: v.optional(v.number()),
      approverRole: v.optional(v.string())
    })),
    template: v.boolean(),
    tags: v.array(v.string())
  },
  handler: async () => {
    // Temporarily disabled to avoid schema mismatches.
    throw new Error("upsertWorkflow is temporarily disabled.");
  },
});

export const copyFromTemplate = mutation({
  args: {
    templateId: v.id("workflows"),
    name: v.optional(v.string())
  },
  handler: async () => {
    // Temporarily disabled to avoid schema mismatches.
    throw new Error("copyFromTemplate is temporarily disabled.");
  },
});

// Keep internal.workflows.run available for http webhook usage, but simplify internals
export const run: any = action({
  args: {
    workflowId: v.id("workflows"),
  },
  handler: async (ctx, args) => {
    // Use the first internal getWorkflowInternal (with workflowId) to prevent name collisions
    const workflow: any = await ctx.runQuery(internal.workflows.getWorkflowInternal, { workflowId: args.workflowId });
    if (!workflow) throw new Error("Workflow not found");

    const executionId = await ctx.runMutation(internal.workflows.createExecution, {
      workflowId: args.workflowId,
      mode: "manual",
    });

    const logs: Array<{ t: number; level: "info" | "warn" | "error"; msg: string }> = [];
    logs.push({ t: Date.now(), level: "info", msg: "Execution started" });
    // Minimal no-op execution to avoid referencing unknown fields on workflow
    logs.push({ t: Date.now(), level: "info", msg: "Execution completed" });

    await ctx.runMutation(internal.workflows.updateExecution, {
      id: executionId,
      status: "succeeded",
      summary: "Execution completed",
      metrics: { roi: 0 },
    });

    return executionId;
  },
});

export const createExecution = internalMutation({
  args: {
    workflowId: v.id("workflows"),
    mode: v.union(v.literal("manual"), v.literal("schedule"), v.literal("webhook")),
  },
  handler: async (ctx, args) => {
    return await ctx.db.insert("workflowExecutions", {
      workflowId: args.workflowId,
      status: "running",
      mode: args.mode,
      summary: "",
      metrics: { roi: 0 },
    });
  },
});

export const updateExecution = internalMutation({
  args: {
    id: v.id("workflowExecutions"),
    status: v.union(v.literal("running"), v.literal("succeeded"), v.literal("failed")),
    summary: v.string(),
    metrics: v.object({
      roi: v.number(),
    }),
  },
  handler: async (ctx, args) => {
    await ctx.db.patch(args.id, {
      status: args.status,
      summary: args.summary,
      metrics: args.metrics,
    });
  },
});

export const getWorkflowsByWebhook = internalQuery({
  args: { eventKey: v.string() },
  handler: async () => {
    // Return empty list to avoid referencing non-schema fields like trigger/eventKey
    return [] as any[];
  },
});