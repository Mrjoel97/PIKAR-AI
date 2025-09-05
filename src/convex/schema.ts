import { authTables } from "@convex-dev/auth/server";
import { defineSchema, defineTable } from "convex/server";
import { Infer, v } from "convex/values";

// default user roles. can add / remove based on the project as needed
export const ROLES = {
  ADMIN: "admin",
  USER: "user",
  MEMBER: "member",
} as const;

export const roleValidator = v.union(
  v.literal(ROLES.ADMIN),
  v.literal(ROLES.USER),
  v.literal(ROLES.MEMBER),
);
export type Role = Infer<typeof roleValidator>;

// Business tiers for Pikar AI
export const BUSINESS_TIERS = {
  SOLOPRENEUR: "solopreneur",
  STARTUP: "startup", 
  SME: "sme",
  ENTERPRISE: "enterprise",
} as const;

export const businessTierValidator = v.union(
  v.literal(BUSINESS_TIERS.SOLOPRENEUR),
  v.literal(BUSINESS_TIERS.STARTUP),
  v.literal(BUSINESS_TIERS.SME),
  v.literal(BUSINESS_TIERS.ENTERPRISE),
);
export type BusinessTier = Infer<typeof businessTierValidator>;

// AI Agent types
export const AI_AGENT_TYPES = {
  CONTENT_CREATION: "content_creation",
  SALES_INTELLIGENCE: "sales_intelligence", 
  CUSTOMER_SUPPORT: "customer_support",
  MARKETING_AUTOMATION: "marketing_automation",
  OPERATIONS: "operations",
  ANALYTICS: "analytics",
  // Additions:
  STRATEGIC_PLANNING: "strategic_planning",
  FINANCIAL_ANALYSIS: "financial_analysis",
  HR_RECRUITMENT: "hr_recruitment",
  COMPLIANCE_RISK: "compliance_risk",
  OPERATIONS_OPTIMIZATION: "operations_optimization",
  COMMUNITY_ENGAGEMENT: "community_engagement",
  PRODUCTIVITY: "productivity",
} as const;

export const aiAgentTypeValidator = v.union(
  v.literal(AI_AGENT_TYPES.CONTENT_CREATION),
  v.literal(AI_AGENT_TYPES.SALES_INTELLIGENCE),
  v.literal(AI_AGENT_TYPES.CUSTOMER_SUPPORT),
  v.literal(AI_AGENT_TYPES.MARKETING_AUTOMATION),
  v.literal(AI_AGENT_TYPES.OPERATIONS),
  v.literal(AI_AGENT_TYPES.ANALYTICS),
  // Additions:
  v.literal(AI_AGENT_TYPES.STRATEGIC_PLANNING),
  v.literal(AI_AGENT_TYPES.FINANCIAL_ANALYSIS),
  v.literal(AI_AGENT_TYPES.HR_RECRUITMENT),
  v.literal(AI_AGENT_TYPES.COMPLIANCE_RISK),
  v.literal(AI_AGENT_TYPES.OPERATIONS_OPTIMIZATION),
  v.literal(AI_AGENT_TYPES.COMMUNITY_ENGAGEMENT),
  v.literal(AI_AGENT_TYPES.PRODUCTIVITY),
);
export type AIAgentType = Infer<typeof aiAgentTypeValidator>;

const schema = defineSchema(
  {
    // default auth tables using convex auth.
    ...authTables, // do not remove or modify

    // the users table is the default users table that is brought in by the authTables
    users: defineTable({
      name: v.optional(v.string()), // name of the user. do not remove
      image: v.optional(v.string()), // image of the user. do not remove
      email: v.optional(v.string()), // email of the user. do not remove
      emailVerificationTime: v.optional(v.number()), // email verification time. do not remove
      isAnonymous: v.optional(v.boolean()), // is the user anonymous. do not remove

      role: v.optional(roleValidator), // role of the user. do not remove
      
      // Pikar AI specific fields
      businessTier: v.optional(businessTierValidator),
      companyName: v.optional(v.string()),
      industry: v.optional(v.string()),
      onboardingCompleted: v.optional(v.boolean()),
      preferences: v.optional(v.object({
        notifications: v.boolean(),
        aiSuggestions: v.boolean(),
        dataSharing: v.boolean(),
      })),
    }).index("email", ["email"]), // index for the email. do not remove or modify

    // Business profiles for organizations
    businesses: defineTable({
      name: v.string(),
      tier: businessTierValidator,
      industry: v.string(),
      description: v.optional(v.string()),
      website: v.optional(v.string()),
      ownerId: v.id("users"),
      teamMembers: v.array(v.id("users")),
      settings: v.object({
        aiAgentsEnabled: v.array(aiAgentTypeValidator),
        dataIntegrations: v.array(v.string()),
        complianceLevel: v.string(),
      }),
    }).index("by_owner", ["ownerId"]),

    // AI Agents and their configurations
    aiAgents: defineTable({
      name: v.string(),
      type: aiAgentTypeValidator,
      businessId: v.id("businesses"),
      isActive: v.boolean(),
      configuration: v.object({
        model: v.string(),
        parameters: v.record(v.string(), v.any()),
        triggers: v.array(v.string()),
      }),
      // ADD: Enhanced agent metadata for capabilities & orchestration
      capabilities: v.array(v.string()), // eg: ["okr_tracking", "seo_optimization"]
      channels: v.array(v.string()), // eg: ["email", "chat", "social", "sms"]
      playbooks: v.array(v.string()), // eg: ["newsletter_campaign", "ab_test_multi_channel"]
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
    }).index("by_business", ["businessId"])
      .index("by_type", ["type"]),

    // Initiatives and workflows
    initiatives: defineTable({
      title: v.string(),
      description: v.string(),
      businessId: v.id("businesses"),
      createdBy: v.id("users"),
      status: v.union(
        v.literal("draft"),
        v.literal("active"), 
        v.literal("paused"),
        v.literal("completed")
      ),
      priority: v.union(
        v.literal("low"),
        v.literal("medium"),
        v.literal("high"),
        v.literal("urgent")
      ),
      aiAgents: v.array(v.id("aiAgents")),
      metrics: v.object({
        targetROI: v.number(),
        currentROI: v.number(),
        completionRate: v.number(),
      }),
      timeline: v.object({
        startDate: v.number(),
        endDate: v.number(),
        milestones: v.array(v.object({
          name: v.string(),
          date: v.number(),
          completed: v.boolean(),
        })),
      }),
    }).index("by_business", ["businessId"])
      .index("by_status", ["status"]),

    // Tasks generated and managed by AI agents
    tasks: defineTable({
      title: v.string(),
      description: v.string(),
      initiativeId: v.optional(v.id("initiatives")),
      aiAgentId: v.id("aiAgents"),
      assignedTo: v.optional(v.id("users")),
      status: v.union(
        v.literal("pending"),
        v.literal("in_progress"),
        v.literal("completed"),
        v.literal("failed")
      ),
      priority: v.union(
        v.literal("low"),
        v.literal("medium"),
        v.literal("high"),
        v.literal("urgent")
      ),
      dueDate: v.optional(v.number()),
      result: v.optional(v.object({
        output: v.any(),
        metrics: v.record(v.string(), v.number()),
        feedback: v.optional(v.string()),
      })),
    }).index("by_initiative", ["initiativeId"])
      .index("by_agent", ["aiAgentId"])
      .index("by_assignee", ["assignedTo"])
      .index("by_status", ["status"]),

    // Analytics and insights
    analytics: defineTable({
      businessId: v.id("businesses"),
      type: v.union(
        v.literal("performance"),
        v.literal("roi"),
        v.literal("usage"),
        v.literal("prediction")
      ),
      period: v.object({
        start: v.number(),
        end: v.number(),
      }),
      data: v.record(v.string(), v.any()),
      insights: v.array(v.object({
        title: v.string(),
        description: v.string(),
        confidence: v.number(),
        actionable: v.boolean(),
      })),
    }).index("by_business", ["businessId"])
      .index("by_type", ["type"]),

    // Data integrations and sources
    integrations: defineTable({
      name: v.string(),
      type: v.string(), // "crm", "email", "social", "analytics", etc.
      businessId: v.id("businesses"),
      isActive: v.boolean(),
      credentials: v.object({
        encrypted: v.string(),
        lastSync: v.optional(v.number()),
      }),
      dataMapping: v.record(v.string(), v.string()),
      syncStatus: v.object({
        lastSync: v.number(),
        recordsProcessed: v.number(),
        errors: v.array(v.string()),
      }),
    }).index("by_business", ["businessId"])
      .index("by_type", ["type"]),

    // Business diagnostics (recommendations & KPI targets)
    diagnostics: defineTable({
      businessId: v.id("businesses"),
      createdBy: v.id("users"),
      phase: v.union(v.literal("discovery"), v.literal("planning")),
      inputs: v.object({
        goals: v.array(v.string()),
        signals: v.record(v.string(), v.any()),
      }),
      outputs: v.object({
        tasks: v.array(
          v.object({
            title: v.string(),
            frequency: v.union(
              v.literal("daily"),
              v.literal("weekly"),
              v.literal("monthly")
            ),
            description: v.string(),
          })
        ),
        workflows: v.array(
          v.object({
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
          })
        ),
        kpis: v.object({
          targetROI: v.number(),
          targetCompletionRate: v.number(),
        }),
      }),
      runAt: v.number(),
    }).index("by_business", ["businessId"]),
  },
  {
    schemaValidation: false,
  },
);

export default schema;