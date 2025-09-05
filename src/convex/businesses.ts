import { v } from "convex/values";
import { mutation, query } from "./_generated/server";
import { getCurrentUser } from "./users";

export const create = mutation({
  args: {
    name: v.string(),
    tier: v.union(
      v.literal("solopreneur"),
      v.literal("startup"),
      v.literal("sme"),
      v.literal("enterprise")
    ),
    industry: v.string(),
    description: v.optional(v.string()),
    website: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    const user = await getCurrentUser(ctx);
    if (!user) {
      throw new Error("User must be authenticated");
    }

    const businessId = await ctx.db.insert("businesses", {
      name: args.name,
      tier: args.tier,
      industry: args.industry,
      description: args.description,
      website: args.website,
      ownerId: user._id,
      teamMembers: [user._id],
      settings: {
        aiAgentsEnabled: [],
        dataIntegrations: [],
        complianceLevel: "standard",
      },
    });

    return businessId;
  },
});

export const getUserBusinesses = query({
  args: {},
  handler: async (ctx) => {
    const user = await getCurrentUser(ctx);
    if (!user) {
      return [];
    }

    return await ctx.db
      .query("businesses")
      .withIndex("by_owner", (q) => q.eq("ownerId", user._id))
      .collect();
  },
});

export const getById = query({
  args: { id: v.id("businesses") },
  handler: async (ctx, args) => {
    const user = await getCurrentUser(ctx);
    if (!user) {
      throw new Error("User must be authenticated");
    }

    const business = await ctx.db.get(args.id);
    if (!business) {
      return null;
    }

    // Check if user has access to this business
    if (business.ownerId !== user._id && !business.teamMembers.includes(user._id)) {
      throw new Error("Access denied");
    }

    return business;
  },
});

export const update = mutation({
  args: {
    id: v.id("businesses"),
    name: v.optional(v.string()),
    tier: v.optional(v.union(
      v.literal("solopreneur"),
      v.literal("startup"),
      v.literal("sme"),
      v.literal("enterprise")
    )),
    industry: v.optional(v.string()),
    description: v.optional(v.string()),
    website: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    const user = await getCurrentUser(ctx);
    if (!user) {
      throw new Error("User must be authenticated");
    }

    const business = await ctx.db.get(args.id);
    if (!business || business.ownerId !== user._id) {
      throw new Error("Access denied");
    }

    const updates: any = {};
    if (args.name !== undefined) updates.name = args.name;
    if (args.tier !== undefined) updates.tier = args.tier;
    if (args.industry !== undefined) updates.industry = args.industry;
    if (args.description !== undefined) updates.description = args.description;
    if (args.website !== undefined) updates.website = args.website;

    await ctx.db.patch(args.id, updates);
    return args.id;
  },
});
