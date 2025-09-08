import { v } from "convex/values";
import { mutation, query, internalMutation } from "./_generated/server";
import { Doc, Id } from "./_generated/dataModel";

// Mutation to track a telemetry event
export const trackEvent = mutation({
  args: {
    businessId: v.id("businesses"),
    eventName: v.string(),
    eventData: v.any(),
    sessionId: v.optional(v.string()),
    userAgent: v.optional(v.string()),
    ipAddress: v.optional(v.string()),
    source: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    const identity = await ctx.auth.getUserIdentity();
    if (!identity) {
      throw new Error("Not authenticated");
    }

    const user = await ctx.db
      .query("users")
      .filter((q) => q.eq(q.field("email"), identity.email))
      .first();

    if (!user) {
      throw new Error("User not found");
    }

    return await ctx.db.insert("telemetryEvents", {
      businessId: args.businessId,
      userId: user._id,
      eventName: args.eventName,
      eventData: args.eventData,
      timestamp: Date.now(),
      sessionId: args.sessionId,
      userAgent: args.userAgent,
      ipAddress: args.ipAddress,
      source: args.source,
    });
  },
});

// Query to get telemetry events for analytics
export const getEvents = query({
  args: {
    businessId: v.id("businesses"),
    eventName: v.optional(v.string()),
    startTime: v.optional(v.number()),
    endTime: v.optional(v.number()),
    limit: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    const identity = await ctx.auth.getUserIdentity();
    if (!identity) {
      throw new Error("Not authenticated");
    }

    let query = ctx.db
      .query("telemetryEvents")
      .withIndex("by_business", (q) => q.eq("businessId", args.businessId))
      .order("desc");

    // Fix: assert eventName type within the narrowing block
    if (args.eventName) {
      query = ctx.db
        .query("telemetryEvents")
        .withIndex("by_business_and_event", (q) =>
          q.eq("businessId", args.businessId).eq("eventName", args.eventName as string)
        )
        .order("desc");
    }

    let events = args.limit ? await query.take(args.limit) : await query.collect();

    // Filter by time range if provided
    if (args.startTime || args.endTime) {
      events = events.filter(event => {
        if (args.startTime && event.timestamp < args.startTime) return false;
        if (args.endTime && event.timestamp > args.endTime) return false;
        return true;
      });
    }

    return events;
  },
});

// Query to get event analytics/aggregations
export const getEventAnalytics = query({
  args: {
    businessId: v.id("businesses"),
    eventNames: v.optional(v.array(v.string())),
    startTime: v.optional(v.number()),
    endTime: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    const identity = await ctx.auth.getUserIdentity();
    if (!identity) {
      throw new Error("Not authenticated");
    }

    const events = await ctx.db
      .query("telemetryEvents")
      .withIndex("by_business", (q) => q.eq("businessId", args.businessId))
      .collect();

    // Filter by time range and event names
    const filteredEvents = events.filter(event => {
      if (args.startTime && event.timestamp < args.startTime) return false;
      if (args.endTime && event.timestamp > args.endTime) return false;
      if (args.eventNames && !args.eventNames.includes(event.eventName)) return false;
      return true;
    });

    // Aggregate by event name
    const eventCounts: Record<string, number> = {};
    const uniqueUsers = new Set<string>();
    const uniqueSessions = new Set<string>();

    filteredEvents.forEach(event => {
      eventCounts[event.eventName] = (eventCounts[event.eventName] || 0) + 1;
      if (event.userId) uniqueUsers.add(event.userId);
      if (event.sessionId) uniqueSessions.add(event.sessionId);
    });

    return {
      totalEvents: filteredEvents.length,
      eventCounts,
      uniqueUsers: uniqueUsers.size,
      uniqueSessions: uniqueSessions.size,
      timeRange: {
        start: args.startTime,
        end: args.endTime,
      },
    };
  },
});

// Internal mutation for system events
export const trackSystemEvent = internalMutation({
  args: {
    businessId: v.id("businesses"),
    userId: v.optional(v.id("users")),
    eventName: v.string(),
    eventData: v.any(),
    source: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    return await ctx.db.insert("telemetryEvents", {
      businessId: args.businessId,
      userId: args.userId,
      eventName: args.eventName,
      eventData: args.eventData,
      timestamp: Date.now(),
      source: args.source || "system",
    });
  },
});

// Mutation to track user journey events
export const trackUserJourney = mutation({
  args: {
    businessId: v.id("businesses"),
    journeyStep: v.string(),
    stepData: v.any(),
    sessionId: v.string(),
  },
  handler: async (ctx, args) => {
    const identity = await ctx.auth.getUserIdentity();
    if (!identity) {
      throw new Error("Not authenticated");
    }

    const user = await ctx.db
      .query("users")
      .filter((q) => q.eq(q.field("email"), identity.email))
      .first();

    if (!user) {
      throw new Error("User not found");
    }

    return await ctx.db.insert("telemetryEvents", {
      businessId: args.businessId,
      userId: user._id,
      eventName: "user_journey_step",
      eventData: {
        step: args.journeyStep,
        data: args.stepData,
      },
      timestamp: Date.now(),
      sessionId: args.sessionId,
      source: "user_journey",
    });
  },
});

// Query to get user journey analytics
export const getUserJourneyAnalytics = query({
  args: {
    businessId: v.id("businesses"),
    startTime: v.optional(v.number()),
    endTime: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    const identity = await ctx.auth.getUserIdentity();
    if (!identity) {
      throw new Error("Not authenticated");
    }

    const journeyEvents = await ctx.db
      .query("telemetryEvents")
      .withIndex("by_business_and_event", (q) => 
        q.eq("businessId", args.businessId).eq("eventName", "user_journey_step")
      )
      .collect();

    // Filter by time range
    const filteredEvents = journeyEvents.filter(event => {
      if (args.startTime && event.timestamp < args.startTime) return false;
      if (args.endTime && event.timestamp > args.endTime) return false;
      return true;
    });

    // Aggregate journey steps
    const stepCounts: Record<string, number> = {};
    const userJourneys: Record<string, string[]> = {};

    filteredEvents.forEach(event => {
      const step = event.eventData?.step;
      if (step) {
        stepCounts[step] = (stepCounts[step] || 0) + 1;
        
        if (event.sessionId) {
          if (!userJourneys[event.sessionId]) {
            userJourneys[event.sessionId] = [];
          }
          userJourneys[event.sessionId].push(step);
        }
      }
    });

    return {
      stepCounts,
      totalSessions: Object.keys(userJourneys).length,
      averageStepsPerSession: Object.values(userJourneys).reduce((sum, steps) => sum + steps.length, 0) / Object.keys(userJourneys).length || 0,
    };
  },
});

// Mutation to track onboarding progress
export const trackOnboardingProgress = mutation({
  args: {
    businessId: v.id("businesses"),
    step: v.string(),
    completed: v.boolean(),
    timeSpent: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    const identity = await ctx.auth.getUserIdentity();
    if (!identity) {
      throw new Error("Not authenticated");
    }

    const user = await ctx.db
      .query("users")
      .filter((q) => q.eq(q.field("email"), identity.email))
      .first();

    if (!user) {
      throw new Error("User not found");
    }

    return await ctx.db.insert("telemetryEvents", {
      businessId: args.businessId,
      userId: user._id,
      eventName: "onboarding_progress",
      eventData: {
        step: args.step,
        completed: args.completed,
        timeSpent: args.timeSpent,
      },
      timestamp: Date.now(),
      source: "onboarding",
    });
  },
});