import { v } from "convex/values";
import { mutation, query } from "./_generated/server";
import { getCurrentUser } from "./users";

export const create = mutation({
  args: {
    title: v.string(),
    description: v.string(),
    businessId: v.id("businesses"),
    priority: v.union(
      v.literal("low"),
      v.literal("medium"),
      v.literal("high"),
      v.literal("urgent")
    ),
    targetROI: v.number(),
    startDate: v.number(),
    endDate: v.number(),
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

    const initiativeId = await ctx.db.insert("initiatives", {
      title: args.title,
      description: args.description,
      businessId: args.businessId,
      createdBy: user._id,
      status: "draft",
      priority: args.priority,
      aiAgents: [],
      metrics: {
        targetROI: args.targetROI,
        currentROI: 0,
        completionRate: 0,
      },
      timeline: {
        startDate: args.startDate,
        endDate: args.endDate,
        milestones: [],
      },
    });

    return initiativeId;
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
      .query("initiatives")
      .withIndex("by_business", (q) => q.eq("businessId", args.businessId))
      .collect();
  },
});

export const updateStatus = mutation({
  args: {
    id: v.id("initiatives"),
    status: v.union(
      v.literal("draft"),
      v.literal("active"),
      v.literal("paused"),
      v.literal("completed")
    ),
  },
  handler: async (ctx, args) => {
    const user = await getCurrentUser(ctx);
    if (!user) {
      throw new Error("User must be authenticated");
    }

    const initiative = await ctx.db.get(args.id);
    if (!initiative) {
      throw new Error("Initiative not found");
    }

    // Verify user has access to the business
    const business = await ctx.db.get(initiative.businessId);
    if (!business || (business.ownerId !== user._id && !business.teamMembers.includes(user._id))) {
      throw new Error("Access denied");
    }

    await ctx.db.patch(args.id, { status: args.status });
    return args.id;
  },
});
