import { v } from "convex/values";
import { mutation, query } from "./_generated/server";
import { Id } from "./_generated/dataModel";

export const upsertForBusiness = mutation({
  args: {
    businessId: v.id("businesses"),
    name: v.optional(v.string()),
    industry: v.optional(v.string()), 
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

    const business = await ctx.db.get(args.businessId);
    if (!business) {
      throw new Error("Business not found");
    }

    // RBAC: Check if user is owner or team member
    if (business.ownerId !== user._id && !business.teamMembers.includes(user._id)) {
      throw new Error("Not authorized to access this business");
    }

    // Check if initiative already exists for this business
    const existing = await ctx.db
      .query("initiatives")
      .withIndex("by_business", (q) => q.eq("businessId", args.businessId))
      .unique();

    if (existing) {
      return existing;
    }

    // Create new initiative with defaults
    const initiativeId = await ctx.db.insert("initiatives", {
      businessId: args.businessId,
      name: args.name || `${business.name} Initiative`,
      industry: args.industry || business.industry || "software",
      businessModel: args.businessModel || business.businessModel || "saas",
      status: "active",
      currentPhase: 0,
      ownerId: business.ownerId,
      onboardingProfile: {
        industry: args.industry || business.industry || "software",
        businessModel: args.businessModel || business.businessModel || "saas",
        goals: [],
      },
      featureFlags: ["journey.phase0_onboarding", "journey.phase1_discovery_ai"],
      updatedAt: Date.now(),
    });

    return await ctx.db.get(initiativeId);
  },
});

export const updateOnboarding = mutation({
  args: {
    initiativeId: v.id("initiatives"),
    profile: v.object({
      industry: v.string(),
      businessModel: v.string(),
      goals: v.array(v.string()),
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
      .unique();
    
    if (!user) {
      throw new Error("User not found");
    }

    const initiative = await ctx.db.get(args.initiativeId);
    if (!initiative) {
      throw new Error("Initiative not found");
    }

    const business = await ctx.db.get(initiative.businessId);
    if (!business) {
      throw new Error("Business not found");
    }

    // RBAC: Check if user is owner or team member
    if (business.ownerId !== user._id && !business.teamMembers.includes(user._id)) {
      throw new Error("Not authorized to update this initiative");
    }

    await ctx.db.patch(args.initiativeId, {
      onboardingProfile: args.profile,
      industry: args.profile.industry,
      businessModel: args.profile.businessModel,
      updatedAt: Date.now(),
    });

    return await ctx.db.get(args.initiativeId);
  },
});

export const advancePhase = mutation({
  args: {
    initiativeId: v.id("initiatives"),
    toPhase: v.number(),
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

    const initiative = await ctx.db.get(args.initiativeId);
    if (!initiative) {
      throw new Error("Initiative not found");
    }

    const business = await ctx.db.get(initiative.businessId);
    if (!business) {
      throw new Error("Business not found");
    }

    // RBAC: Check if user is owner or team member
    if (business.ownerId !== user._id && !business.teamMembers.includes(user._id)) {
      throw new Error("Not authorized to update this initiative");
    }

    // Validate phase advancement (can only advance by 1 or stay same)
    if (args.toPhase > initiative.currentPhase + 1 || args.toPhase < initiative.currentPhase) {
      throw new Error("Invalid phase transition");
    }

    await ctx.db.patch(args.initiativeId, {
      currentPhase: args.toPhase,
      updatedAt: Date.now(),
    });

    return await ctx.db.get(args.initiativeId);
  },
});

export const getByBusiness = query({
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
      .unique();
    
    if (!user) {
      throw new Error("User not found");
    }

    const business = await ctx.db.get(args.businessId);
    if (!business) {
      throw new Error("Business not found");
    }

    // RBAC: Check if user is owner or team member
    if (business.ownerId !== user._id && !business.teamMembers.includes(user._id)) {
      throw new Error("Not authorized to access this business");
    }

    return await ctx.db
      .query("initiatives")
      .withIndex("by_business", (q) => q.eq("businessId", args.businessId))
      .unique();
  },
});

export const runPhase0Diagnostics = mutation({
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
      .unique();

    if (!user) {
      throw new Error("User not found");
    }

    // Ensure initiative exists WITHOUT calling same-file mutation through api.*
    let initiative = await ctx.db
      .query("initiatives")
      .withIndex("by_business", (q) => q.eq("businessId", args.businessId))
      .unique();

    if (!initiative) {
      const business = await ctx.db.get(args.businessId);
      if (!business) {
        throw new Error("Business not found");
      }

      const initiativeId = await ctx.db.insert("initiatives", {
        businessId: args.businessId,
        name: `${business.name} Initiative`,
        industry: (business.industry as string) || "software",
        businessModel: (business.businessModel as string) || "saas",
        status: "active",
        currentPhase: 0,
        ownerId: business.ownerId,
        onboardingProfile: {
          industry: (business.industry as string) || "software",
          businessModel: (business.businessModel as string) || "saas",
          goals: [],
        },
        featureFlags: ["journey.phase0_onboarding", "journey.phase1_discovery_ai"],
        updatedAt: Date.now(),
      });
      initiative = await ctx.db.get(initiativeId);
    }

    if (!initiative) {
      throw new Error("Failed to create or get initiative");
    }

    // Create a diagnostics record directly to avoid circular api references
    const diagnosticId = await ctx.db.insert("diagnostics", {
      businessId: args.businessId,
      createdBy: user._id,
      phase: "discovery",
      inputs: {
        goals: initiative.onboardingProfile.goals,
        signals: {},
      },
      outputs: {
        tasks: [],
        workflows: [],
        kpis: {
          targetROI: 0,
          targetCompletionRate: 0,
        },
      },
      runAt: Date.now(),
    });

    return diagnosticId;
  },
});

export const seedForEmail = mutation({
  args: {
    email: v.string(),
  },
  handler: async (ctx, args) => {
    // Find user by email
    const user = await ctx.db
      .query("users")
      .withIndex("email", (q) => q.eq("email", args.email))
      .unique();

    if (!user) {
      throw new Error("User not found");
    }

    // Find or create business for user
    let business = await ctx.db
      .query("businesses")
      .withIndex("by_owner", (q) => q.eq("ownerId", user._id))
      .first();

    if (!business) {
      const businessId = await ctx.db.insert("businesses", {
        name: "Sample Business",
        industry: "software",
        size: "1-10",
        ownerId: user._id,
        teamMembers: [],
        description: "A sample business for testing",
        businessModel: "saas",
        goals: ["Increase revenue", "Improve efficiency"],
        challenges: ["Market competition", "Resource constraints"],
        currentSolutions: ["Manual processes"],
      });
      business = await ctx.db.get(businessId);
    }

    if (!business) {
      throw new Error("Failed to create business");
    }

    // Ensure initiative exists (direct, no api.* to same file)
    let initiative = await ctx.db
      .query("initiatives")
      .withIndex("by_business", (q) => q.eq("businessId", business._id))
      .unique();

    if (!initiative) {
      const initiativeId = await ctx.db.insert("initiatives", {
        businessId: business._id,
        name: "Growth Initiative",
        industry: "software",
        businessModel: "saas",
        status: "active",
        currentPhase: 0,
        ownerId: business.ownerId,
        onboardingProfile: {
          industry: "software",
          businessModel: "saas",
          goals: [],
        },
        featureFlags: ["journey.phase0_onboarding", "journey.phase1_discovery_ai"],
        updatedAt: Date.now(),
      });
      initiative = await ctx.db.get(initiativeId);
    }

    // Run diagnostics directly
    const diagnosticId = await ctx.db.insert("diagnostics", {
      businessId: business._id,
      createdBy: user._id,
      phase: "discovery",
      inputs: {
        goals: initiative?.onboardingProfile.goals ?? [],
        signals: {},
      },
      outputs: {
        tasks: [],
        workflows: [],
        kpis: {
          targetROI: 0,
          targetCompletionRate: 0,
        },
      },
      runAt: Date.now(),
    });

    // Advance to phase 1
    if (initiative) {
      await ctx.db.patch(initiative._id, { currentPhase: 1, updatedAt: Date.now() });
    }

    return {
      businessId: business._id,
      initiativeId: initiative?._id,
      diagnosticId,
    };
  },
});

// Command to run: npx convex run initiatives:seedForEmail '{"email":"joel.feruzi@gmail.com"}'