import { v } from "convex/values";
import { query, mutation } from "./_generated/server";
import type { Id } from "./_generated/dataModel";

export const getUserBusinesses = query({
  args: {},
  handler: async (ctx) => {
    const identity = await ctx.auth.getUserIdentity();
    if (!identity?.email) return [];

    const user = await ctx.db
      .query("users")
      .withIndex("email", (q) => q.eq("email", identity.email!))
      .unique();

    if (!user) return [];

    const owned = await ctx.db
      .query("businesses")
      .withIndex("by_owner", (q) => q.eq("ownerId", user._id))
      .collect();

    const member = await ctx.db
      .query("businesses")
      .withIndex("by_team_member", (q: any) => q.eq("teamMembers", user._id))
      .collect();

    // Deduplicate by _id
    const seen: Record<string, boolean> = {};
    const all = [...owned, ...member].filter((b) => {
      if (seen[b._id as any]) return false;
      seen[b._id as any] = true;
      return true;
    });

    return all;
  },
});

export const create = mutation({
  args: {
    name: v.string(),
    industry: v.string(),
    size: v.string(),
    description: v.optional(v.string()),
    website: v.optional(v.string()),
    location: v.optional(v.string()),
    foundedYear: v.optional(v.number()),
    revenue: v.optional(v.string()),
    goals: v.array(v.string()),
    challenges: v.array(v.string()),
    currentSolutions: v.array(v.string()),
    targetMarket: v.optional(v.string()),
    businessModel: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    const identity = await ctx.auth.getUserIdentity();
    if (!identity) {
      throw new Error("Not authenticated");
    }

    const user = await ctx.db
      .query("users")
      .withIndex("email", (q) => q.eq("email", identity.email!))
      .unique();
    
    if (!user) {
      throw new Error("User not found");
    }

    const businessId = await ctx.db.insert("businesses", {
      ...args,
      ownerId: user._id,
      teamMembers: [],
    });

    return businessId;
  },
});

export const getByOwner = query({
  args: {},
  handler: async (ctx) => {
    const identity = await ctx.auth.getUserIdentity();
    if (!identity) {
      throw new Error("Not authenticated");
    }

    const user = await ctx.db
      .query("users")
      .withIndex("email", (q) => q.eq("email", identity.email!))
      .unique();
    
    if (!user) {
      throw new Error("User not found");
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
    const identity = await ctx.auth.getUserIdentity();
    if (!identity) {
      throw new Error("Not authenticated");
    }

    const user = await ctx.db
      .query("users")
      .withIndex("email", (q) => q.eq("email", identity.email!))
      .unique();
    
    if (!user) {
      throw new Error("User not found");
    }

    const business = await ctx.db.get(args.id);
    if (!business) {
      return null;
    }

    // Check if user has access (owner or team member)
    if (business.ownerId !== user._id && !business.teamMembers.includes(user._id)) {
      throw new Error("Not authorized to access this business");
    }

    return business;
  },
});

export const update = mutation({
  args: {
    id: v.id("businesses"),
    name: v.optional(v.string()),
    industry: v.optional(v.string()),
    size: v.optional(v.string()),
    description: v.optional(v.string()),
    website: v.optional(v.string()),
    location: v.optional(v.string()),
    foundedYear: v.optional(v.number()),
    revenue: v.optional(v.string()),
    goals: v.optional(v.array(v.string())),
    challenges: v.optional(v.array(v.string())),
    currentSolutions: v.optional(v.array(v.string())),
    targetMarket: v.optional(v.string()),
    businessModel: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    const identity = await ctx.auth.getUserIdentity();
    if (!identity) {
      throw new Error("Not authenticated");
    }

    const user = await ctx.db
      .query("users")
      .withIndex("email", (q) => q.eq("email", identity.email!))
      .unique();
    
    if (!user) {
      throw new Error("User not found");
    }

    const business = await ctx.db.get(args.id);
    if (!business) {
      throw new Error("Business not found");
    }

    // Only owner can update business details
    if (business.ownerId !== user._id) {
      throw new Error("Not authorized to update this business");
    }

    const { id, ...updates } = args;
    await ctx.db.patch(id, updates);
    
    return await ctx.db.get(id);
  },
});

export const addTeamMember = mutation({
  args: {
    businessId: v.id("businesses"),
    userId: v.id("users"),
  },
  handler: async (ctx, args) => {
    const identity = await ctx.auth.getUserIdentity();
    if (!identity) {
      throw new Error("Not authenticated");
    }

    const user = await ctx.db
      .query("users")
      .withIndex("email", (q) => q.eq("email", identity.email!))
      .unique();
    
    if (!user) {
      throw new Error("User not found");
    }

    const business = await ctx.db.get(args.businessId);
    if (!business) {
      throw new Error("Business not found");
    }

    // Only owner can add team members
    if (business.ownerId !== user._id) {
      throw new Error("Not authorized to add team members");
    }

    // Check if user is already a team member
    if (business.teamMembers.includes(args.userId)) {
      throw new Error("User is already a team member");
    }

    await ctx.db.patch(args.businessId, {
      teamMembers: [...business.teamMembers, args.userId],
    });

    return await ctx.db.get(args.businessId);
  },
});

export const removeTeamMember = mutation({
  args: {
    businessId: v.id("businesses"),
    userId: v.id("users"),
  },
  handler: async (ctx, args) => {
    const identity = await ctx.auth.getUserIdentity();
    if (!identity) {
      throw new Error("Not authenticated");
    }

    const user = await ctx.db
      .query("users")
      .withIndex("email", (q) => q.eq("email", identity.email!))
      .unique();
    
    if (!user) {
      throw new Error("User not found");
    }

    const business = await ctx.db.get(args.businessId);
    if (!business) {
      throw new Error("Business not found");
    }

    // Only owner can remove team members
    if (business.ownerId !== user._id) {
      throw new Error("Not authorized to remove team members");
    }

    await ctx.db.patch(args.businessId, {
      teamMembers: business.teamMembers.filter((id: Id<"users">) => id !== args.userId),
    });

    return await ctx.db.get(args.businessId);
  },
});

// Helper query to get current user's business
export const currentUserBusiness = query({
  args: {},
  handler: async (ctx) => {
    const identity = await ctx.auth.getUserIdentity();
    if (!identity) {
      throw new Error("Not authenticated");
    }

    const user = await ctx.db
      .query("users")
      .withIndex("email", (q) => q.eq("email", identity.email!))
      .unique();
    
    if (!user) {
      throw new Error("User not found");
    }

    // First try to find business owned by user
    let business = await ctx.db
      .query("businesses")
      .withIndex("by_owner", (q) => q.eq("ownerId", user._id))
      .first();

    // If not found, try to find business where user is team member
    if (!business) {
      const businesses = await ctx.db
        .query("businesses")
        // TS types expect the array type here; Convex supports membership using eq on array index.
        // Safe cast to satisfy TS while preserving correct behavior.
        .withIndex("by_team_member", (q) => q.eq("teamMembers", user._id as any))
        .first();
      business = businesses;
    }

    return business;
  },
});