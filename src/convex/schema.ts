import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

export default defineSchema({
  users: defineTable({
    // Make legacy fields compatible and optional
    name: v.optional(v.string()),
    email: v.optional(v.string()),
    image: v.optional(v.string()),
    emailVerificationTime: v.optional(v.number()),
    phone: v.optional(v.string()),
    phoneVerificationTime: v.optional(v.number()),
    isAnonymous: v.optional(v.boolean()),
    // Accept legacy/seeded fields
    companyName: v.optional(v.string()),
    industry: v.optional(v.string()),
    businessTier: v.optional(v.string()),
    onboardingCompleted: v.optional(v.boolean()),
    // Add optional businessId to satisfy consumers that reference it
    businessId: v.optional(v.id("businesses")),
  }).index("email", ["email"]), // Add trailing comma to separate table entries
  // Remove duplicate email index to avoid conflict
  // Removed: .index("by_email", ["email"]),

  businesses: defineTable({
    name: v.string(),
    industry: v.string(),
    size: v.optional(v.string()),
    ownerId: v.id("users"),
    teamMembers: v.array(v.id("users")),
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
    // Allow legacy/seeded fields
    tier: v.optional(v.string()),
    settings: v.optional(
      v.object({
        aiAgentsEnabled: v.array(v.string()),
        complianceLevel: v.string(),
        dataIntegrations: v.array(v.string()),
      })
    ),
  })
    .index("by_owner", ["ownerId"])
    // Keep a single team member index
    .index("by_team_member", ["teamMembers"]),

  initiatives: defineTable({
    businessId: v.id("businesses"),
    // Make previously required fields optional to support legacy data
    name: v.optional(v.string()),
    industry: v.optional(v.string()),
    businessModel: v.optional(v.string()),
    status: v.union(v.literal("active"), v.literal("paused"), v.literal("completed")),
    currentPhase: v.optional(v.number()),
    ownerId: v.optional(v.id("users")),
    onboardingProfile: v.optional(
      v.object({
        industry: v.string(),
        businessModel: v.string(),
        goals: v.array(v.string()),
      })
    ),
    featureFlags: v.optional(v.array(v.string())),
    updatedAt: v.optional(v.number()),

    // Allow legacy/seeded fields present in existing data
    title: v.optional(v.string()),
    description: v.optional(v.string()),
    createdBy: v.optional(v.id("users")),
    timeline: v.optional(v.any()),
    metrics: v.optional(v.any()),
    priority: v.optional(v.string()),
    aiAgents: v.optional(v.array(v.any())),
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
    type: v.string(),
    businessId: v.id("businesses"),
    description: v.optional(v.string()),
    config: v.optional(
      v.object({
        model: v.string(),
        temperature: v.number(),
        maxTokens: v.number(),
        systemPrompt: v.string(),
        tools: v.array(v.string()),
      })
    ),
    configuration: v.optional(
      v.object({
        model: v.string(),
        parameters: v.object({
          temperature: v.number(),
        }),
        triggers: v.array(v.string()),
      })
    ),
    capabilities: v.optional(v.array(v.string())),
    channels: v.optional(v.array(v.string())),
    isActive: v.optional(v.boolean()),
    mmrPolicy: v.optional(v.string()),
    playbooks: v.optional(v.array(v.string())),
    performance: v.optional(
      v.object({
        lastActive: v.optional(v.number()),
        successRate: v.number(),
        tasksCompleted: v.number(),
      })
    ),
    status: v.optional(
      v.union(v.literal("active"), v.literal("inactive"), v.literal("training"))
    ),
    createdBy: v.optional(v.id("users")),
    metrics: v.optional(
      v.object({
        totalRuns: v.number(),
        successRate: v.number(),
        avgResponseTime: v.number(),
        lastRun: v.optional(v.number()),
      })
    ),
  })
    .index("by_business", ["businessId"])
    .index("by_type", ["type"])
    .index("by_status", ["status"]),
    // Removed duplicate:
    // .index("by_businessId", ["businessId"]),

  workflows: defineTable({
    name: v.string(),
    description: v.optional(v.string()),
    businessId: v.id("businesses"),
    // Structured fields (optional for backward compatibility)
    region: v.optional(v.string()),
    unit: v.optional(v.string()),
    channel: v.optional(v.union(
      v.literal("email"),
      v.literal("social"),
      v.literal("paid"),
      v.literal("referral")
    )),
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
    .index("by_business_and_template", ["businessId", "template"])
    .index("by_business_region", ["businessId", "region"])
    .index("by_business_unit", ["businessId", "unit"])
    .index("by_business_channel", ["businessId", "channel"]),
    // Removed duplicate:
    // .index("by_businessId", ["businessId"]),

  workflowExecutions: defineTable({
    workflowId: v.id("workflows"),
    // Denormalized fields for efficient analytics and filtering
    businessId: v.optional(v.id("businesses")),
    region: v.optional(v.string()),
    unit: v.optional(v.string()),
    channel: v.optional(v.union(
      v.literal("email"),
      v.literal("social"),
      v.literal("paid"),
      v.literal("referral")
    )),
    status: v.union(v.literal("succeeded"), v.literal("failed"), v.literal("running")),
    mode: v.union(v.literal("manual"), v.literal("schedule"), v.literal("webhook")),
    summary: v.string(),
    metrics: v.object({
      roi: v.number(),
    }),
  })
    .index("by_workflow", ["workflowId"])
    .index("by_business", ["businessId"])
    .index("by_business_region", ["businessId", "region"])
    .index("by_business_unit", ["businessId", "unit"])
    .index("by_business_channel", ["businessId", "channel"]),

  // Feature Flag System
  featureFlags: defineTable({
    businessId: v.optional(v.id("businesses")),
    flagName: v.string(),
    isEnabled: v.boolean(),
    rolloutPercentage: v.number(),
    conditions: v.optional(v.object({
      userTier: v.optional(v.array(v.string())),
      businessTier: v.optional(v.array(v.string())),
    })),
    createdAt: v.number(),
    updatedAt: v.number(),
  })
    .index("by_flag_name", ["flagName"])
    .index("by_business", ["businessId"])
    .index("by_business_and_flag", ["businessId", "flagName"]),

  // Workflow Assignment Extensions
  workflowSteps: defineTable({
    workflowId: v.id("workflows"),
    businessId: v.id("businesses"),
    stepNumber: v.number(),
    name: v.string(),
    description: v.optional(v.string()),
    type: v.string(),
    config: v.any(),
    // New assignment fields
    assigneeId: v.optional(v.id("users")),
    dueDate: v.optional(v.number()),
    assignedAt: v.optional(v.number()),
    assignedBy: v.optional(v.id("users")),
    status: v.union(v.literal("pending"), v.literal("in_progress"), v.literal("completed"), v.literal("blocked")),
    completedAt: v.optional(v.number()),
    completedBy: v.optional(v.id("users")),
  })
    .index("by_workflow", ["workflowId"])
    .index("by_business", ["businessId"])
    .index("by_assignee", ["assigneeId"])
    .index("by_due_date", ["dueDate"])
    .index("by_status", ["status"]),

  // Approval Queue System
  approvalQueue: defineTable({
    businessId: v.id("businesses"),
    workflowId: v.id("workflows"),
    stepId: v.id("workflowSteps"),
    assigneeId: v.id("users"),
    requestedBy: v.id("users"),
    status: v.union(v.literal("pending"), v.literal("approved"), v.literal("rejected")),
    priority: v.union(v.literal("low"), v.literal("medium"), v.literal("high"), v.literal("urgent")),
    createdAt: v.number(),
    slaDeadline: v.optional(v.number()),
    approvedAt: v.optional(v.number()),
    approvedBy: v.optional(v.id("users")),
    rejectedAt: v.optional(v.number()),
    rejectedBy: v.optional(v.id("users")),
    rejectionReason: v.optional(v.string()),
    comments: v.optional(v.string()),
  })
    .index("by_business", ["businessId"])
    .index("by_assignee", ["assigneeId"])
    .index("by_status", ["status"])
    .index("by_workflow", ["workflowId"])
    .index("by_sla_deadline", ["slaDeadline"]),

  // Notification System
  notifications: defineTable({
    businessId: v.id("businesses"),
    userId: v.id("users"),
    type: v.union(
      v.literal("assignment"),
      v.literal("approval"),
      v.literal("sla_warning"),
      v.literal("integration_error"),
      v.literal("workflow_completion"),
      v.literal("system_alert")
    ),
    title: v.string(),
    message: v.string(),
    data: v.optional(v.any()),
    isRead: v.boolean(),
    priority: v.union(v.literal("low"), v.literal("medium"), v.literal("high")),
    createdAt: v.number(),
    readAt: v.optional(v.number()),
    expiresAt: v.optional(v.number()),
  })
    .index("by_user", ["userId"])
    .index("by_business", ["businessId"])
    .index("by_user_and_read", ["userId", "isRead"])
    .index("by_created_at", ["createdAt"])
    .index("by_expires_at", ["expiresAt"]),

  // Notification Preferences
  notificationPreferences: defineTable({
    userId: v.id("users"),
    businessId: v.id("businesses"),
    emailEnabled: v.boolean(),
    pushEnabled: v.boolean(),
    smsEnabled: v.boolean(),
    preferences: v.object({
      assignments: v.boolean(),
      approvals: v.boolean(),
      slaWarnings: v.boolean(),
      integrationErrors: v.boolean(),
      workflowCompletions: v.boolean(),
      systemAlerts: v.boolean(),
    }),
    rateLimits: v.object({
      maxPerHour: v.number(),
      maxPerDay: v.number(),
    }),
    updatedAt: v.number(),
  })
    .index("by_user", ["userId"])
    .index("by_business", ["businessId"]),

  // Telemetry Events
  telemetryEvents: defineTable({
    businessId: v.id("businesses"),
    userId: v.optional(v.id("users")),
    eventName: v.string(),
    eventData: v.any(),
    timestamp: v.number(),
    sessionId: v.optional(v.string()),
    userAgent: v.optional(v.string()),
    ipAddress: v.optional(v.string()),
    source: v.optional(v.string()),
  })
    .index("by_business", ["businessId"])
    .index("by_user", ["userId"])
    .index("by_event_name", ["eventName"])
    .index("by_timestamp", ["timestamp"])
    .index("by_business_and_event", ["businessId", "eventName"]),

  // Marketing Suite Tables
  emailCampaigns: defineTable({
    businessId: v.id("businesses"),
    name: v.string(),
    content: v.object({
      blocks: v.array(v.any()),
      html: v.string(),
      subject: v.string(),
      preheader: v.optional(v.string()),
    }),
    scheduledAt: v.optional(v.number()),
    status: v.union(v.literal("draft"), v.literal("scheduled"), v.literal("sending"), v.literal("sent"), v.literal("cancelled")),
    createdBy: v.id("users"),
    createdAt: v.number(),
    updatedAt: v.number(),
    metrics: v.optional(v.object({
      sent: v.number(),
      delivered: v.number(),
      opened: v.number(),
      clicked: v.number(),
      bounced: v.number(),
      unsubscribed: v.number(),
    })),
    recipients: v.optional(v.array(v.string())),
    testRecipients: v.optional(v.array(v.string())),
  })
    .index("by_business", ["businessId"])
    .index("by_status", ["status"])
    .index("by_created_by", ["createdBy"])
    .index("by_scheduled_at", ["scheduledAt"]),

  seoSuggestions: defineTable({
    businessId: v.id("businesses"),
    contentId: v.string(),
    contentType: v.string(),
    suggestions: v.object({
      title: v.array(v.string()),
      meta: v.array(v.string()),
      h1: v.array(v.string()),
      readability: v.object({
        score: v.number(),
        suggestions: v.array(v.string()),
      }),
    }),
    createdAt: v.number(),
    updatedAt: v.number(),
    clickedSuggestions: v.optional(v.array(v.string())),
  })
    .index("by_business", ["businessId"])
    .index("by_content_id", ["contentId"])
    .index("by_business_and_content", ["businessId", "contentId"]),

  // Analytics Platform Tables
  dashboards: defineTable({
    businessId: v.id("businesses"),
    name: v.string(),
    description: v.optional(v.string()),
    layout: v.array(v.object({
      cardType: v.string(),
      config: v.any(),
      position: v.object({ 
        x: v.number(), 
        y: v.number(),
        width: v.number(),
        height: v.number(),
      }),
    })),
    createdBy: v.id("users"),
    createdAt: v.number(),
    updatedAt: v.number(),
    isPublic: v.boolean(),
    sharedWith: v.optional(v.array(v.id("users"))),
  })
    .index("by_business", ["businessId"])
    .index("by_created_by", ["createdBy"])
    .index("by_public", ["isPublic"]),

  exportJobs: defineTable({
    businessId: v.id("businesses"),
    type: v.union(v.literal("csv"), v.literal("pdf")),
    config: v.any(),
    status: v.union(v.literal("queued"), v.literal("processing"), v.literal("completed"), v.literal("failed")),
    createdBy: v.id("users"),
    createdAt: v.number(),
    startedAt: v.optional(v.number()),
    completedAt: v.optional(v.number()),
    downloadUrl: v.optional(v.string()),
    errorMessage: v.optional(v.string()),
    fileSize: v.optional(v.number()),
    expiresAt: v.optional(v.number()),
  })
    .index("by_business", ["businessId"])
    .index("by_status", ["status"])
    .index("by_created_by", ["createdBy"])
    .index("by_created_at", ["createdAt"]),

  scheduledReports: defineTable({
    businessId: v.id("businesses"),
    name: v.string(),
    dashboardId: v.id("dashboards"),
    schedule: v.string(), // cron expression
    recipients: v.array(v.string()),
    format: v.union(v.literal("pdf"), v.literal("csv")),
    isActive: v.boolean(),
    createdBy: v.id("users"),
    createdAt: v.number(),
    updatedAt: v.number(),
    lastRun: v.optional(v.number()),
    nextRun: v.optional(v.number()),
  })
    .index("by_business", ["businessId"])
    .index("by_dashboard", ["dashboardId"])
    .index("by_next_run", ["nextRun"])
    .index("by_active", ["isActive"]),

  // Compliance QMS Tables
  capaItems: defineTable({
    businessId: v.id("businesses"),
    incidentId: v.optional(v.string()),
    nonconformityId: v.optional(v.string()),
    title: v.string(),
    description: v.string(),
    severity: v.union(v.literal("low"), v.literal("medium"), v.literal("high"), v.literal("critical")),
    status: v.union(v.literal("open"), v.literal("in_progress"), v.literal("verification"), v.literal("closed")),
    assigneeId: v.id("users"),
    createdBy: v.id("users"),
    createdAt: v.number(),
    updatedAt: v.number(),
    slaDeadline: v.number(),
    verificationRequired: v.boolean(),
    verifiedBy: v.optional(v.id("users")),
    verifiedAt: v.optional(v.number()),
    closedAt: v.optional(v.number()),
    rootCause: v.optional(v.string()),
    correctiveAction: v.optional(v.string()),
    preventiveAction: v.optional(v.string()),
  })
    .index("by_business", ["businessId"])
    .index("by_assignee", ["assigneeId"])
    .index("by_status", ["status"])
    .index("by_severity", ["severity"])
    .index("by_sla_deadline", ["slaDeadline"]),

  riskRegister: defineTable({
    businessId: v.id("businesses"),
    title: v.string(),
    description: v.string(),
    category: v.string(),
    probability: v.number(), // 1-5 scale
    impact: v.number(), // 1-5 scale
    riskScore: v.number(), // calculated
    mitigation: v.string(),
    ownerId: v.id("users"),
    createdBy: v.id("users"),
    createdAt: v.number(),
    updatedAt: v.number(),
    status: v.union(v.literal("identified"), v.literal("assessed"), v.literal("mitigated"), v.literal("closed")),
    reviewDate: v.optional(v.number()),
    mitigationDeadline: v.optional(v.number()),
  })
    .index("by_business", ["businessId"])
    .index("by_owner", ["ownerId"])
    .index("by_status", ["status"])
    .index("by_risk_score", ["riskScore"])
    .index("by_review_date", ["reviewDate"]),

  // Integrations Hub Tables
  integrations: defineTable({
    businessId: v.id("businesses"),
    provider: v.string(),
    name: v.string(),
    type: v.union(v.literal("oauth"), v.literal("api_key"), v.literal("webhook")),
    config: v.object({
      clientId: v.optional(v.string()),
      encryptedTokens: v.optional(v.string()),
      webhookUrl: v.optional(v.string()),
      apiEndpoint: v.optional(v.string()),
      scopes: v.optional(v.array(v.string())),
    }),
    status: v.union(v.literal("connected"), v.literal("disconnected"), v.literal("error"), v.literal("pending")),
    lastHealthCheck: v.optional(v.number()),
    healthStatus: v.optional(v.string()),
    connectedAt: v.number(),
    connectedBy: v.id("users"),
    lastError: v.optional(v.string()),
    errorCount: v.optional(v.number()),
  })
    .index("by_business", ["businessId"])
    .index("by_provider", ["provider"])
    .index("by_status", ["status"])
    .index("by_health_check", ["lastHealthCheck"]),

  ssoConfig: defineTable({
    businessId: v.id("businesses"),
    provider: v.string(),
    isEnabled: v.boolean(),
    config: v.object({
      entityId: v.optional(v.string()),
      ssoUrl: v.optional(v.string()),
      certificate: v.optional(v.string()),
      attributeMapping: v.optional(v.any()),
    }),
    status: v.union(v.literal("placeholder"), v.literal("configured"), v.literal("active")),
    createdBy: v.id("users"),
    createdAt: v.number(),
    updatedAt: v.number(),
  })
    .index("by_business", ["businessId"])
    .index("by_provider", ["provider"])
    .index("by_status", ["status"]),

  // Enhanced Onboarding Tables
  onboardingProgress: defineTable({
    businessId: v.id("businesses"),
    userId: v.id("users"),
    currentStep: v.number(),
    totalSteps: v.number(),
    completedSteps: v.array(v.string()),
    startedAt: v.number(),
    lastActiveAt: v.number(),
    completedAt: v.optional(v.number()),
    profile: v.object({
      industry: v.string(),
      tier: v.string(),
      goals: v.array(v.string()),
      selectedTemplates: v.array(v.string()),
      connectedIntegrations: v.array(v.string()),
      complianceRequirements: v.optional(v.array(v.string())),
    }),
    sessionData: v.optional(v.any()),
  })
    .index("by_business", ["businessId"])
    .index("by_user", ["userId"])
    .index("by_completion_status", ["completedAt"]),

  contextualTips: defineTable({
    businessId: v.id("businesses"),
    userId: v.id("users"),
    tipId: v.string(),
    context: v.string(), // page/feature context
    shown: v.boolean(),
    dismissed: v.boolean(),
    clicked: v.boolean(),
    shownAt: v.optional(v.number()),
    dismissedAt: v.optional(v.number()),
    clickedAt: v.optional(v.number()),
  })
    .index("by_user", ["userId"])
    .index("by_business", ["businessId"])
    .index("by_context", ["context"])
    .index("by_tip_id", ["tipId"]),

  // Add authAccounts table required by @convex-dev/auth
  authAccounts: defineTable({
    userId: v.id("users"),
    provider: v.string(), // e.g., "google"
    providerAccountId: v.string(),
    // Make type optional to accommodate anonymous provider docs
    type: v.optional(v.string()),
    access_token: v.optional(v.string()),
    refresh_token: v.optional(v.string()),
    expires_at: v.optional(v.number()),
    token_type: v.optional(v.string()),
    scope: v.optional(v.string()),
    id_token: v.optional(v.string()),
    session_state: v.optional(v.string()),
  })
    // IMPORTANT: index name must match the library's expectation
    .index("providerAndAccountId", ["provider", "providerAccountId"])
    .index("by_userId", ["userId"]),
});