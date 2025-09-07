import { v } from "convex/values";
import { mutation, query } from "./_generated/server";
import { getCurrentUser } from "./users";
import { withErrorHandling } from "./utils";

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
  handler: withErrorHandling(async (ctx, args) => {
    const user = await getCurrentUser(ctx);
    if (!user) {
      throw new Error("User must be authenticated");
    }

    const business = await ctx.db.get(args.businessId);
    if (!business || (business.ownerId !== user._id && !(business.teamMembers ?? []).includes(user._id))) {
      throw new Error("Access denied");
    }

    const initiativeId = await ctx.db.insert("initiatives", {
      title: args.title,
      description: args.description,
      businessId: args.businessId,
      createdBy: user._id,
      // Keep backward-compatible; "draft" is now allowed by schema
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
      // Initialize Phase 0 fields empty; can be updated via onboarding mutation
      currentPhase: 0,
      onboardingProfile: {
        goals: [],
        connectors: [],
      },
    });

    return initiativeId;
  }),
});

export const getByBusiness = query({
  args: { businessId: v.id("businesses") },
  handler: withErrorHandling(async (ctx, args) => {
    const user = await getCurrentUser(ctx);
    if (!user) {
      return [];
    }

    const business = await ctx.db.get(args.businessId);
    if (!business || (business.ownerId !== user._id && !(business.teamMembers ?? []).includes(user._id))) {
      return [];
    }

    // Fix: use correct index name from schema
    return await ctx.db
      .query("initiatives")
      .withIndex("by_businessId", (q: any) => q.eq("businessId", args.businessId))
      .collect();
  }),
});

// Get onboarding profile for an initiative
export const getOnboardingProfile = query({
  args: { initiativeId: v.id("initiatives") },
  handler: withErrorHandling(async (ctx, args) => {
    const user = await getCurrentUser(ctx);
    if (!user) return null;

    const initiative = await ctx.db.get(args.initiativeId);
    if (!initiative) return null;

    const business = await ctx.db.get(initiative.businessId);
    if (!business || (business.ownerId !== user._id && !(business.teamMembers ?? []).includes(user._id))) {
      return null;
    }

    const { industry, businessModel, currentPhase, onboardingProfile } = initiative;
    return {
      industry: industry ?? null,
      businessModel: businessModel ?? null,
      currentPhase: currentPhase ?? 0,
      onboardingProfile: onboardingProfile ?? { goals: [], connectors: [] },
    };
  }),
});

// Upsert onboarding profile and optionally confirm Phase 0
export const upsertOnboardingProfile = mutation({
  args: {
    initiativeId: v.id("initiatives"),
    industry: v.optional(v.string()),
    businessModel: v.optional(v.string()),
    goals: v.optional(v.array(v.string())),
    connectors: v.optional(
      v.array(
        v.object({
          type: v.string(),
          provider: v.string(),
          status: v.union(v.literal("connected"), v.literal("pending"), v.literal("error")),
        })
      )
    ),
    confirm: v.optional(v.boolean()),
    skipReason: v.optional(v.string()),
  },
  handler: withErrorHandling(async (ctx, args) => {
    const user = await getCurrentUser(ctx);
    if (!user) throw new Error("User must be authenticated");

    const initiative = await ctx.db.get(args.initiativeId);
    if (!initiative) throw new Error("Initiative not found");

    const business = await ctx.db.get(initiative.businessId);
    if (!business || (business.ownerId !== user._id && !(business.teamMembers ?? []).includes(user._id))) {
      throw new Error("Access denied");
    }

    const nextProfile = {
      goals: args.goals ?? initiative.onboardingProfile?.goals ?? [],
      connectors: args.connectors ?? initiative.onboardingProfile?.connectors ?? [],
      confirmedAt:
        args.confirm ? Date.now() : initiative.onboardingProfile?.confirmedAt,
      skipReason: args.skipReason ?? initiative.onboardingProfile?.skipReason,
    };

    // Phase movement rule: if confirm=true and at least one connector connected OR skipReason provided -> move to phase 1
    let nextPhase = initiative.currentPhase ?? 0;
    if (args.confirm) {
      const hasConnector =
        (nextProfile.connectors ?? []).some(
          (c: { status: "connected" | "pending" | "error" }) => c.status === "connected"
        ) || !!nextProfile.skipReason;
      if (hasConnector) {
        nextPhase = Math.max(1, nextPhase);
      }
    }

    await ctx.db.patch(args.initiativeId, {
      industry: args.industry ?? initiative.industry,
      businessModel: args.businessModel ?? initiative.businessModel,
      onboardingProfile: nextProfile,
      currentPhase: nextPhase,
      // If we were in "draft", formalize as "planning" after confirmation, else leave unchanged
      status:
        args.confirm && initiative.status === "draft" ? ("planning" as const) : initiative.status,
    });

    return { initiativeId: args.initiativeId, currentPhase: nextPhase };
  }),
});

// Move to a specific phase (admin/manager)
export const movePhase = mutation({
  args: {
    initiativeId: v.id("initiatives"),
    toPhase: v.number(), // 0..6
  },
  handler: withErrorHandling(async (ctx, args) => {
    const user = await getCurrentUser(ctx);
    if (!user) throw new Error("User must be authenticated");

    const initiative = await ctx.db.get(args.initiativeId);
    if (!initiative) throw new Error("Initiative not found");

    const business = await ctx.db.get(initiative.businessId);
    if (!business) throw new Error("Business not found");

    // Simple role gating: owner or team member allowed (extend later with RBAC)
    if (business.ownerId !== user._id && !(business.teamMembers ?? []).includes(user._id)) {
      throw new Error("Access denied");
    }

    const bounded = Math.max(0, Math.min(6, args.toPhase));
    await ctx.db.patch(args.initiativeId, { currentPhase: bounded });
    return { initiativeId: args.initiativeId, currentPhase: bounded };
  }),
});

// Seed minimal Phase 0 test data for the current user
export const seedPhase0TestData = mutation({
  args: {},
  handler: withErrorHandling(async (ctx) => {
    const user = await getCurrentUser(ctx);
    if (!user) throw new Error("User must be authenticated");

    // Find or create a business for this user
    const existing = await ctx.db
      .query("businesses")
      .withIndex("by_ownerId", (q: any) => q.eq("ownerId", user._id))
      .collect();

    const businessId =
      existing[0]?._id ??
      (await ctx.db.insert("businesses", {
        name: "Demo Startup",
        tier: "startup",
        ownerId: user._id,
        description: "Auto-created for Phase 0 demo",
        teamMembers: [],
        industry: "Technology",
        website: "https://example.com",
        settings: {
          aiAgentsEnabled: [],
          complianceLevel: "standard",
          dataIntegrations: [],
        },
      }));

    const initiativeId = await ctx.db.insert("initiatives", {
      title: "Phase 0 Onboarding",
      description: "Personalize journey and connect core integrations.",
      businessId,
      createdBy: user._id,
      status: "draft",
      priority: "medium",
      metrics: {
        completionRate: 0,
        currentROI: 0,
        targetROI: 0,
      },
      timeline: {
        startDate: Date.now(),
        endDate: Date.now() + 7 * 24 * 60 * 60 * 1000,
        milestones: [],
      },
      currentPhase: 0,
      industry: "Technology",
      businessModel: "SaaS",
      onboardingProfile: {
        goals: ["Launch first campaign", "Validate ICP"],
        connectors: [
          { type: "social", provider: "twitter", status: "pending" },
          { type: "email", provider: "gmail", status: "pending" },
        ],
        confirmedAt: undefined,
        skipReason: undefined,
      },
      aiAgents: [],
    });

    return { businessId, initiativeId };
  }),
});