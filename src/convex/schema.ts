import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

export default defineSchema({
  users: defineTable({
    email: v.optional(v.string()),
    name: v.optional(v.string()),
    role: v.optional(v.union(v.literal("admin"), v.literal("creator"), v.literal("user"))),
    businessId: v.optional(v.id("businesses")),
    // Additional optional fields used by guest flows and onboarding
    isAnonymous: v.optional(v.boolean()),
    onboardingCompleted: v.optional(v.boolean()),
    companyName: v.optional(v.string()),
    industry: v.optional(v.string()),
    businessTier: v.optional(
      v.union(
        v.literal("solopreneur"),
        v.literal("startup"),
        v.literal("sme"),
        v.literal("enterprise"),
      )
    ),
  }).index("by_email", ["email"]),

  businesses: defineTable({
    name: v.string(),
    tier: v.union(
      v.literal("solopreneur"),
      v.literal("startup"), 
      v.literal("sme"),
      v.literal("enterprise")
    ),
    ownerId: v.id("users"),
    description: v.optional(v.string()),
    teamMembers: v.optional(v.array(v.id("users"))),
    industry: v.optional(v.string()),
    website: v.optional(v.string()),
    settings: v.optional(v.object({
      aiAgentsEnabled: v.array(v.string()),
      complianceLevel: v.string(),
      dataIntegrations: v.array(v.string()),
    })),
  }).index("by_ownerId", ["ownerId"]),

  initiatives: defineTable({
    title: v.string(),
    description: v.string(),
    status: v.union(
      v.literal("planning"),
      v.literal("active"),
      v.literal("completed"),
      v.literal("paused")
    ),
    priority: v.union(v.literal("low"), v.literal("medium"), v.literal("high")),
    businessId: v.id("businesses"),
    createdBy: v.id("users"),
    dueDate: v.optional(v.number()),
    // Allow existing initiative docs with extended fields
    aiAgents: v.optional(v.array(v.id("aiAgents"))),
    metrics: v.optional(v.object({
      completionRate: v.optional(v.number()),
      currentROI: v.optional(v.number()),
      targetROI: v.optional(v.number()),
    })),
    timeline: v.optional(v.object({
      startDate: v.optional(v.number()),
      endDate: v.optional(v.number()),
      milestones: v.optional(v.array(v.any())),
    })),
  }).index("by_businessId", ["businessId"])
    .index("by_createdBy", ["createdBy"]),

  workflows: defineTable({
    name: v.string(),
    description: v.string(),
    category: v.string(),
    businessId: v.id("businesses"),
    createdBy: v.id("users"),
    isTemplate: v.boolean(),
    steps: v.array(v.object({
      id: v.string(),
      title: v.string(),
      description: v.string(),
      type: v.string(),
    })),
  }).index("by_businessId", ["businessId"])
    .index("by_createdBy", ["createdBy"])
    .index("by_isTemplate", ["isTemplate"]),

  aiAgents: defineTable({
    name: v.string(),
    type: v.string(),
    businessId: v.id("businesses"),
    isActive: v.boolean(),
    configuration: v.object({
      model: v.string(),
      parameters: v.record(v.string(), v.any()),
      triggers: v.array(v.string()),
    }),
    capabilities: v.array(v.string()),
    channels: v.array(v.string()),
    playbooks: v.array(v.string()),
    mmrPolicy: v.union(
      v.literal("always_human_review"),
      v.literal("auto_with_review"),
      v.literal("auto")
    ),
    performance: v.object({
      tasksCompleted: v.number(),
      successRate: v.number(),
      lastActive: v.number(),
    }),
  }).index("by_businessId", ["businessId"]),

  diagnostics: defineTable({
    type: v.optional(v.string()),
    message: v.optional(v.string()),
    level: v.optional(v.union(v.literal("info"), v.literal("warning"), v.literal("error"))),

    businessId: v.optional(v.id("businesses")),
    userId: v.optional(v.id("users")),
    createdBy: v.optional(v.id("users")),
    inputs: v.optional(v.any()),
    outputs: v.optional(v.any()),
    phase: v.optional(v.string()),
    runAt: v.optional(v.number()),
    metadata: v.optional(v.object({})),
  }).index("by_businessId", ["businessId"])
    .index("by_userId", ["userId"])
    .index("by_type", ["type"]),

  // New tables for Custom Agent Framework
  agent_templates: defineTable({
    name: v.string(),
    description: v.string(),
    tags: v.array(v.string()),
    configPreview: v.object({}),
    createdBy: v.id("users"),
    tier: v.optional(v.union(
      v.literal("solopreneur"),
      v.literal("startup"),
      v.literal("sme"),
      v.literal("enterprise")
    )),
  }).index("by_createdBy", ["createdBy"])
    .index("by_tier", ["tier"]),

  custom_agents: defineTable({
    name: v.string(),
    description: v.string(),
    tags: v.array(v.string()),
    currentVersionId: v.optional(v.id("custom_agent_versions")),
    createdBy: v.id("users"),
    businessId: v.id("businesses"),
    visibility: v.union(v.literal("private"), v.literal("team"), v.literal("market")),
    requiresApproval: v.boolean(),
    riskLevel: v.union(v.literal("low"), v.literal("medium"), v.literal("high")),
  }).index("by_createdBy", ["createdBy"])
    .index("by_businessId", ["businessId"])
    .index("by_visibility", ["visibility"]),

  custom_agent_versions: defineTable({
    agentId: v.id("custom_agents"),
    version: v.string(),
    changelog: v.string(),
    config: v.object({}),
    createdBy: v.id("users"),
  }).index("by_agentId", ["agentId"])
    .index("by_createdBy", ["createdBy"]),

  agent_marketplace: defineTable({
    agentId: v.id("custom_agents"),
    status: v.union(v.literal("pending"), v.literal("approved"), v.literal("rejected")),
    submittedBy: v.id("users"),
    industryTags: v.array(v.string()),
    usageTags: v.array(v.string()),
    vettedBy: v.optional(v.id("users")),
    notes: v.optional(v.string()),
  }).index("by_agentId", ["agentId"])
    .index("by_status", ["status"])
    .index("by_submittedBy", ["submittedBy"]),

  agent_stats: defineTable({
    agentId: v.id("custom_agents"),
    runs: v.number(),
    successes: v.number(),
    lastRunAt: v.optional(v.number()),
  }).index("by_agentId", ["agentId"]),

  agent_ratings: defineTable({
    agentId: v.id("custom_agents"),
    userId: v.id("users"),
    rating: v.union(v.literal(1), v.literal(2), v.literal(3), v.literal(4), v.literal(5)),
    comment: v.optional(v.string()),
  }).index("by_agentId", ["agentId"])
    .index("by_userId_and_agentId", ["userId", "agentId"]),

  approvals: defineTable({
    subjectType: v.union(v.literal("agent"), v.literal("action")),
    subjectId: v.string(),
    requestedBy: v.id("users"),
    approvers: v.array(v.id("users")),
    status: v.union(v.literal("pending"), v.literal("approved"), v.literal("rejected")),
    reason: v.optional(v.string()),
    reviewedBy: v.optional(v.id("users")),
    reviewedAt: v.optional(v.number()),
  }).index("by_status", ["status"])
    .index("by_requestedBy", ["requestedBy"])
    .index("by_subjectType", ["subjectType"]),

  workflowTemplates: defineTable({
    name: v.string(),
    category: v.string(),
    description: v.string(),
    steps: v.array(v.object({
      type: v.union(v.literal("agent"), v.literal("approval"), v.literal("delay")),
      title: v.string(),
      agentType: v.optional(v.string()),
      config: v.object({
        delayMinutes: v.optional(v.number()),
        approverRole: v.optional(v.string()),
        agentPrompt: v.optional(v.string()),
      }),
    })),
    recommendedAgents: v.array(v.string()),
    industryTags: v.array(v.string()),
  }),

  workflowSteps: defineTable({
    workflowId: v.id("workflows"),
    order: v.number(),
    type: v.union(v.literal("agent"), v.literal("approval"), v.literal("delay")),
    config: v.object({
      delayMinutes: v.optional(v.number()),
      approverRole: v.optional(v.string()),
      agentPrompt: v.optional(v.string()),
    }),
    agentId: v.optional(v.id("aiAgents")),
    title: v.string(),
  }).index("by_workflow_id", ["workflowId"]),

  workflowRuns: defineTable({
    workflowId: v.id("workflows"),
    status: v.union(
      v.literal("running"),
      v.literal("awaiting_approval"),
      v.literal("completed")
    ),
    startedBy: v.id("users"),
    startedAt: v.number(),
    finishedAt: v.optional(v.number()),
    summary: v.object({
      totalSteps: v.number(),
      completedSteps: v.number(),
      failedSteps: v.number(),
      outputs: v.array(v.any()),
    }),
    dryRun: v.optional(v.boolean()),
  }).index("by_workflow_id", ["workflowId"]),

  workflowRunSteps: defineTable({
    runId: v.id("workflowRuns"),
    stepId: v.id("workflowSteps"),
    status: v.union(
      v.literal("pending"),
      v.literal("running"),
      v.literal("awaiting_approval"),
      v.literal("completed"),
      v.literal("failed")
    ),
    startedAt: v.optional(v.number()),
    finishedAt: v.optional(v.number()),
    output: v.optional(v.any()),
  }).index("by_run_id", ["runId"]),
});