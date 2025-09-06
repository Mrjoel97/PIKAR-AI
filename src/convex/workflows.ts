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
    // Load existing templates to avoid duplicates on reseed
    const existing = await ctx.db.query("workflowTemplates").collect();
    const existingNames = new Set(existing.map((t) => t.name));

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
          { type: "agent", title: "Sales Page & Checkout Copy", agentType: "content_creation", config: { agentPrompt: "Write sales and checkout copy" } },
          { type: "agent", title: "Nurture Sequence & Upsell", agentType: "marketing_automation", config: { agentPrompt: "4-email nurture with 1-click upsell" } },
          { type: "agent", title: "Conversion Report", agentType: "analytics", config: { agentPrompt: "Report CR and AOV with insights" } },
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
    ];

    let inserted = 0;
    for (const template of templates) {
      if (!existingNames.has(template.name)) {
        await ctx.db.insert("workflowTemplates", template);
        inserted++;
      }
    }

    return inserted;
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