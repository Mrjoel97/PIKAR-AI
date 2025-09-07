import { v } from "convex/values";
import { mutation, query } from "./_generated/server";
import { Id } from "./_generated/dataModel";

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
    inputs: v.object({
      goals: v.array(v.string()),
      phase: v.union(v.literal("discovery"), v.literal("planning")),
    }),
  },
  handler: async (ctx, args) => {
    const identity = await ctx.auth.getUserIdentity();
    if (!identity) {
      throw new Error("Not authenticated");
    }

    const user = await ctx.db
      .query("users")
      .withIndex("email", (q) => q.eq("email", identity.email!))
      .first();
    
    if (!user) {
      throw new Error("User not found");
    }

    const business = await ctx.db.get(args.businessId);
    if (!business) {
      throw new Error("Business not found");
    }

    // RBAC: Check if user is owner or team member
    if (business.ownerId !== user._id && !business.teamMembers.includes(user._id)) {
      throw new Error("Not authorized to run diagnostics for this business");
    }

    // Generate sample diagnostic outputs based on goals and phase
    const tasks = args.inputs.goals.map((goal, index) => ({
      title: `Analyze ${goal.toLowerCase()}`,
      frequency: (["daily", "weekly", "monthly"] as const)[index % 3],
      description: `Regular analysis and optimization of ${goal.toLowerCase()} metrics and performance indicators.`,
    }));

    const workflows = [
      {
        name: "Content Creation Workflow",
        agentType: "content_creation" as const,
        templateId: "content-template-1",
      },
      {
        name: "Sales Intelligence Workflow", 
        agentType: "sales_intelligence" as const,
        templateId: "sales-template-1",
      },
      {
        name: "Analytics Workflow",
        agentType: "analytics" as const,
        templateId: "analytics-template-1",
      },
    ];

    const kpis = {
      targetROI: 150 + Math.floor(Math.random() * 100), // 150-250%
      targetCompletionRate: 85 + Math.floor(Math.random() * 15), // 85-100%
    };

    const diagnosticId = await ctx.db.insert("diagnostics", {
      businessId: args.businessId,
      createdBy: user._id,
      phase: args.inputs.phase,
      inputs: {
        goals: args.inputs.goals,
        signals: {}, // Empty for now, can be populated with real data later
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
  args: {
    businessId: v.id("businesses"),
  },
  handler: async (ctx, args) => {
    const identity = await ctx.auth.getUserIdentity();
    if (!identity) {
      throw new Error("Not authenticated");
    }

    const user = await ctx.db
      .query("users")
      .withIndex("email", (q) => q.eq("email", identity.email!))
      .first();
    
    if (!user) {
      throw new Error("User not found");
    }

    const business = await ctx.db.get(args.businessId);
    if (!business) {
      throw new Error("Business not found");
    }

    // RBAC: Check if user is owner or team member
    if (business.ownerId !== user._id && !business.teamMembers.includes(user._id)) {
      throw new Error("Not authorized to access diagnostics for this business");
    }

    return await ctx.db
      .query("diagnostics")
      .withIndex("by_business", (q) => q.eq("businessId", args.businessId))
      .order("desc")
      .first();
  },
});

export const getAll = query({
  args: {
    businessId: v.id("businesses"),
  },
  handler: async (ctx, args) => {
    const identity = await ctx.auth.getUserIdentity();
    if (!identity) {
      throw new Error("Not authenticated");
    }

    const user = await ctx.db
      .query("users")
      .withIndex("email", (q) => q.eq("email", identity.email!))
      .first();
    
    if (!user) {
      throw new Error("User not found");
    }

    const business = await ctx.db.get(args.businessId);
    if (!business) {
      throw new Error("Business not found");
    }

    // RBAC: Check if user is owner or team member
    if (business.ownerId !== user._id && !business.teamMembers.includes(user._id)) {
      throw new Error("Not authorized to access diagnostics for this business");
    }

    return await ctx.db
      .query("diagnostics")
      .withIndex("by_business", (q) => q.eq("businessId", args.businessId))
      .order("desc")
      .collect();
  },
});