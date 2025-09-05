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
