import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

export default defineSchema({
  users: defineTable({
    name: v.string(),
    email: v.string(),
    image: v.optional(v.string()),
    emailVerificationTime: v.optional(v.number()),
    phone: v.optional(v.string()),
    phoneVerificationTime: v.optional(v.number()),
    isAnonymous: v.optional(v.boolean()),
  }).index("email", ["email"]),

  businesses: defineTable({
    name: v.string(),
    industry: v.string(),
    size: v.string(),
    ownerId: v.id("users"),
    teamMembers: v.array(v.id("users")),
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
  })
    .index("by_owner", ["ownerId"])
    .index("by_team_member", ["teamMembers"]),

  initiatives: defineTable({
    businessId: v.id("businesses"),
    name: v.string(),
    industry: v.string(),
    businessModel: v.string(),
    status: v.union(v.literal("active"), v.literal("paused"), v.literal("completed")),
    currentPhase: v.number(),
    ownerId: v.id("users"),
    onboardingProfile: v.object({
      industry: v.string(),
      businessModel: v.string(),
      goals: v.array(v.string()),
    }),
    featureFlags: v.array(v.string()),
    updatedAt: v.number(),
  })
    .index("by_business", ["businessId"])
    .index("by_owner", ["ownerId"])
    .index("by_business_and_phase", ["businessId", "currentPhase"]),

  diagnostics: defineTable({
    businessId: v.id("businesses"),
    createdBy: v.id("users"),
    phase: v.union(v.literal("discovery"), v.literal("planning")),
    inputs: v.object({
      goals: v.array(v.string()),
      signals: v.record(v.string(), v.any()),
    }),
    outputs: v.object({
      tasks: v.array(v.object({
        title: v.string(),
        frequency: v.union(v.literal("daily"), v.literal("weekly"), v.literal("monthly")),
        description: v.string(),
      })),
      workflows: v.array(v.object({
        name: v.string(),
        agentType: v.union(
          v.literal("content_creation"),
          v.literal("sales_intelligence"),
          v.literal("customer_support"),
          v.literal("marketing_automation"),
          v.literal("operations"),
          v.literal("analytics")
        ),
        templateId: v.string(),
      })),
      kpis: v.object({
        targetROI: v.number(),
        targetCompletionRate: v.number(),
      }),
    }),
    runAt: v.number(),
  }).index("by_business", ["businessId"]),

  aiAgents: defineTable({
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
    config: v.object({
      model: v.string(),
      temperature: v.number(),
      maxTokens: v.number(),
      systemPrompt: v.string(),
      tools: v.array(v.string()),
    }),
    status: v.union(v.literal("active"), v.literal("inactive"), v.literal("training")),
    createdBy: v.id("users"),
    metrics: v.object({
      totalRuns: v.number(),
      successRate: v.number(),
      avgResponseTime: v.number(),
      lastRun: v.optional(v.number()),
    }),
  })
    .index("by_business", ["businessId"])
    .index("by_type", ["type"])
    .index("by_status", ["status"]),

  workflows: defineTable({
    name: v.string(),
    description: v.optional(v.string()),
    businessId: v.id("businesses"),
    trigger: v.object({
      type: v.union(v.literal("manual"), v.literal("schedule"), v.literal("webhook")),
      cron: v.optional(v.string()),
      eventKey: v.optional(v.string()),
    }),
    approval: v.object({
      required: v.boolean(),
      threshold: v.number(),
    }),
    pipeline: v.array(v.any()),
    template: v.boolean(),
    tags: v.array(v.string()),
    createdBy: v.optional(v.id("users")),
    status: v.union(v.literal("draft"), v.literal("active"), v.literal("paused")),
    metrics: v.optional(
      v.object({
        totalRuns: v.number(),
        successRate: v.number(),
        avgExecutionTime: v.number(),
        lastRun: v.optional(v.number()),
      })
    ),
  })
    .index("by_business", ["businessId"])
    .index("by_status", ["status"])
    .index("by_business_and_template", ["businessId", "template"]),

  workflowExecutions: defineTable({
    workflowId: v.id("workflows"),
    status: v.union(v.literal("succeeded"), v.literal("failed"), v.literal("running")),
    mode: v.union(v.literal("manual"), v.literal("schedule"), v.literal("webhook")),
    summary: v.string(),
    metrics: v.object({
      roi: v.number(),
    }),
  }).index("by_workflow", ["workflowId"]),

  workflowRuns: defineTable({
    workflowId: v.id("workflows"),
    startedAt: v.number(),
    finishedAt: v.optional(v.number()),
    status: v.union(v.literal("running"), v.literal("succeeded"), v.literal("failed")),
    triggerType: v.union(v.literal("manual"), v.literal("schedule"), v.literal("webhook")),
  }).index("by_workflow", ["workflowId"]),
});