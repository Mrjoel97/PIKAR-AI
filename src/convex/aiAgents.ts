import { v } from "convex/values";
import { mutation, query } from "./_generated/server";
import { getCurrentUser } from "./users";

export const create = mutation({
  args: {
    name: v.string(),
    type: v.union(
      v.literal("content_creation"),
      v.literal("sales_intelligence"),
      v.literal("customer_support"),
      v.literal("marketing_automation"),
      v.literal("operations"),
      v.literal("analytics")
    ),
    businessId: v.id("businesses"),
    configuration: v.object({
      model: v.string(),
      parameters: v.record(v.string(), v.any()),
      triggers: v.array(v.string()),
    }),
  },
  handler: async (ctx, args) => {
    const user = await getCurrentUser(ctx);
    if (!user) {
      throw new Error("User must be authenticated");
    }

    // Verify user has access to the business
    const business = await ctx.db.get(args.businessId);
    if (!business || (business.ownerId !== user._id && !business.teamMembers.includes(user._id))) {
      throw new Error("Access denied");
    }

    const agentId = await ctx.db.insert("aiAgents", {
      name: args.name,
      type: args.type,
      businessId: args.businessId,
      isActive: true,
      configuration: args.configuration,
      performance: {
        tasksCompleted: 0,
        successRate: 0,
        lastActive: Date.now(),
      },
    });

    return agentId;
  },
});

export const getByBusiness = query({
  args: { businessId: v.id("businesses") },
  handler: async (ctx, args) => {
    const user = await getCurrentUser(ctx);
    if (!user) {
      return [];
    }

    // Verify user has access to the business
    const business = await ctx.db.get(args.businessId);
    if (!business || (business.ownerId !== user._id && !business.teamMembers.includes(user._id))) {
      return [];
    }

    return await ctx.db
      .query("aiAgents")
      .withIndex("by_business", (q) => q.eq("businessId", args.businessId))
      .collect();
  },
});

export const toggle = mutation({
  args: {
    id: v.id("aiAgents"),
    isActive: v.boolean(),
  },
  handler: async (ctx, args) => {
    const user = await getCurrentUser(ctx);
    if (!user) {
      throw new Error("User must be authenticated");
    }

    const agent = await ctx.db.get(args.id);
    if (!agent) {
      throw new Error("Agent not found");
    }

    // Verify user has access to the business
    const business = await ctx.db.get(agent.businessId);
    if (!business || (business.ownerId !== user._id && !business.teamMembers.includes(user._id))) {
      throw new Error("Access denied");
    }

    await ctx.db.patch(args.id, { isActive: args.isActive });
    return args.id;
  },
});

export const seedEnhancedForBusiness = mutation({
  args: { businessId: v.id("businesses") },
  handler: async (ctx, args) => {
    const user = await getCurrentUser(ctx);
    if (!user) {
      throw new Error("User must be authenticated");
    }
    const business = await ctx.db.get(args.businessId);
    if (!business || (business.ownerId !== user._id && !business.teamMembers.includes(user._id))) {
      throw new Error("Access denied");
    }

    // Define the list of enhanced agent types to ensure coverage across domains
    const enhancedTypes: Array<
      | "content_creation"
      | "sales_intelligence"
      | "customer_support"
      | "marketing_automation"
      | "operations"
      | "analytics"
      | "strategic_planning"
      | "financial_analysis"
      | "hr_recruitment"
      | "compliance_risk"
      | "operations_optimization"
      | "community_engagement"
      | "productivity"
    > = [
      "strategic_planning",
      "content_creation",
      "customer_support",
      "sales_intelligence",
      "analytics",
      "marketing_automation",
      "financial_analysis",
      "hr_recruitment",
      "compliance_risk",
      "operations_optimization",
      "community_engagement",
      "productivity",
      "operations",
    ];

    // Collect existing agents for the business
    const existing = await ctx.db
      .query("aiAgents")
      .withIndex("by_business", (q) => q.eq("businessId", args.businessId))
      .collect();
    const existingTypes = new Set(existing.map((a) => a.type));

    // Seed missing agents with reasonable defaults
    for (const type of enhancedTypes) {
      if (existingTypes.has(type)) continue;

      const defaultName: Record<string, string> = {
        strategic_planning: "Strategic Planning Agent",
        content_creation: "Content Creation Agent",
        customer_support: "Customer Support Agent",
        sales_intelligence: "Sales Intelligence Agent",
        analytics: "Data Analysis Agent",
        marketing_automation: "Marketing Automation Agent",
        financial_analysis: "Financial Analysis Agent",
        hr_recruitment: "HR & Recruitment Agent",
        compliance_risk: "Compliance & Risk Agent",
        operations_optimization: "Operations Optimization Agent",
        community_engagement: "Community & Engagement Agent",
        productivity: "Productivity Agent",
        operations: "Operations Agent",
      };

      await ctx.db.insert("aiAgents", {
        name: defaultName[type] ?? `${type} Agent`,
        type,
        businessId: args.businessId,
        isActive: ["content_creation", "sales_intelligence", "analytics", "marketing_automation"].includes(type),
        configuration: {
          model: "gpt-4o-mini",
          parameters: { temperature: 0.7 },
          triggers: [],
        },
        performance: {
          tasksCompleted: 0,
          successRate: 0,
          lastActive: Date.now(),
        },
      });
    }

    return true;
  },
});

export const updateConfig = mutation({
  args: {
    id: v.id("aiAgents"),
    configuration: v.object({
      model: v.string(),
      parameters: v.record(v.string(), v.any()),
      triggers: v.array(v.string()),
    }),
    isActive: v.optional(v.boolean()),
  },
  handler: async (ctx, args) => {
    const user = await getCurrentUser(ctx);
    if (!user) {
      throw new Error("User must be authenticated");
    }
    const agent = await ctx.db.get(args.id);
    if (!agent) {
      throw new Error("Agent not found");
    }
    const business = await ctx.db.get(agent.businessId);
    if (!business || (business.ownerId !== user._id && !business.teamMembers.includes(user._id))) {
      throw new Error("Access denied");
    }

    const updates: any = { configuration: args.configuration };
    if (typeof args.isActive === "boolean") {
      updates.isActive = args.isActive;
    }
    await ctx.db.patch(args.id, updates);
    return args.id;
  },
});