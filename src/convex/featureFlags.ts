import { v } from "convex/values";
import { mutation, query } from "./_generated/server";
import { Doc, Id } from "./_generated/dataModel";

// Query to get feature flags for a business
export const getFeatureFlags = query({
  args: { businessId: v.optional(v.id("businesses")) },
  handler: async (ctx, args) => {
    const identity = await ctx.auth.getUserIdentity();
    if (!identity) {
      throw new Error("Not authenticated");
    }

    // Get global flags (no businessId) and business-specific flags
    const globalFlags = await ctx.db
      .query("featureFlags")
      .filter((q) => q.eq(q.field("businessId"), undefined))
      .collect();

    const businessFlags = args.businessId
      ? await ctx.db
          .query("featureFlags")
          .withIndex("by_business", (q) => q.eq("businessId", args.businessId))
          .collect()
      : [];

    return [...globalFlags, ...businessFlags];
  },
});

// Query to check if a specific feature is enabled
export const isFeatureEnabled = query({
  args: { 
    flagName: v.string(),
    businessId: v.optional(v.id("businesses")),
    userTier: v.optional(v.string()),
    businessTier: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    const identity = await ctx.auth.getUserIdentity();
    if (!identity) {
      return false;
    }

    // Check business-specific flag first, then global
    const businessFlag = args.businessId
      ? await ctx.db
          .query("featureFlags")
          .withIndex("by_business_and_flag", (q) => 
            q.eq("businessId", args.businessId).eq("flagName", args.flagName)
          )
          .first()
      : null;

    const globalFlag = await ctx.db
      .query("featureFlags")
      .withIndex("by_flag_name", (q) => q.eq("flagName", args.flagName))
      .filter((q) => q.eq(q.field("businessId"), undefined))
      .first();

    const flag = businessFlag || globalFlag;
    
    if (!flag || !flag.isEnabled) {
      return false;
    }

    // Check rollout percentage
    if (flag.rolloutPercentage < 100) {
      // Simple hash-based rollout using user identity
      const hash = identity.subject.split('').reduce((a, b) => {
        a = ((a << 5) - a) + b.charCodeAt(0);
        return a & a;
      }, 0);
      const percentage = Math.abs(hash) % 100;
      if (percentage >= flag.rolloutPercentage) {
        return false;
      }
    }

    // Check conditions
    if (flag.conditions) {
      if (flag.conditions.userTier && args.userTier) {
        if (!flag.conditions.userTier.includes(args.userTier)) {
          return false;
        }
      }
      if (flag.conditions.businessTier && args.businessTier) {
        if (!flag.conditions.businessTier.includes(args.businessTier)) {
          return false;
        }
      }
    }

    return true;
  },
});

// Mutation to create or update a feature flag
export const upsertFeatureFlag = mutation({
  args: {
    businessId: v.optional(v.id("businesses")),
    flagName: v.string(),
    isEnabled: v.boolean(),
    rolloutPercentage: v.number(),
    conditions: v.optional(v.object({
      userTier: v.optional(v.array(v.string())),
      businessTier: v.optional(v.array(v.string())),
    })),
  },
  handler: async (ctx, args) => {
    const identity = await ctx.auth.getUserIdentity();
    if (!identity) {
      throw new Error("Not authenticated");
    }

    // Check if user has permission to manage feature flags
    // This would typically check for admin role
    const user = await ctx.db
      .query("users")
      .filter((q) => q.eq(q.field("email"), identity.email))
      .first();

    if (!user) {
      throw new Error("User not found");
    }

    const now = Date.now();

    // Check if flag already exists
    const existingFlag = args.businessId
      ? await ctx.db
          .query("featureFlags")
          .withIndex("by_business_and_flag", (q) => 
            q.eq("businessId", args.businessId).eq("flagName", args.flagName)
          )
          .first()
      : await ctx.db
          .query("featureFlags")
          .withIndex("by_flag_name", (q) => q.eq("flagName", args.flagName))
          .filter((q) => q.eq(q.field("businessId"), undefined))
          .first();

    if (existingFlag) {
      // Update existing flag
      await ctx.db.patch(existingFlag._id, {
        isEnabled: args.isEnabled,
        rolloutPercentage: args.rolloutPercentage,
        conditions: args.conditions,
        updatedAt: now,
      });
      return existingFlag._id;
    } else {
      // Create new flag
      return await ctx.db.insert("featureFlags", {
        businessId: args.businessId,
        flagName: args.flagName,
        isEnabled: args.isEnabled,
        rolloutPercentage: args.rolloutPercentage,
        conditions: args.conditions,
        createdAt: now,
        updatedAt: now,
      });
    }
  },
});

// Mutation to toggle a feature flag
export const toggleFeatureFlag = mutation({
  args: { flagId: v.id("featureFlags") },
  handler: async (ctx, args) => {
    const identity = await ctx.auth.getUserIdentity();
    if (!identity) {
      throw new Error("Not authenticated");
    }

    const flag = await ctx.db.get(args.flagId);
    if (!flag) {
      throw new Error("Feature flag not found");
    }

    await ctx.db.patch(args.flagId, {
      isEnabled: !flag.isEnabled,
      updatedAt: Date.now(),
    });

    return !flag.isEnabled;
  },
});

// Query to get feature flag usage analytics
export const getFeatureFlagAnalytics = query({
  args: { businessId: v.optional(v.id("businesses")) },
  handler: async (ctx, args) => {
    const identity = await ctx.auth.getUserIdentity();
    if (!identity) {
      throw new Error("Not authenticated");
    }

    const flags = await ctx.db
      .query("featureFlags")
      .filter((q) => 
        args.businessId 
          ? q.eq(q.field("businessId"), args.businessId)
          : q.eq(q.field("businessId"), undefined)
      )
      .collect();

    // Get telemetry events for feature flag usage
    const flagUsageEvents = await ctx.db
      .query("telemetryEvents")
      .withIndex("by_event_name", (q) => q.eq("eventName", "feature_flag_check"))
      .filter((q) => 
        args.businessId 
          ? q.eq(q.field("businessId"), args.businessId)
          : q.neq(q.field("businessId"), undefined)
      )
      .collect();

    return {
      flags,
      totalFlags: flags.length,
      enabledFlags: flags.filter(f => f.isEnabled).length,
      usageEvents: flagUsageEvents.length,
    };
  },
});