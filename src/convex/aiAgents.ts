import { v } from "convex/values";
import { mutation, query, action } from "./_generated/server";
import { withErrorHandling } from "./utils";
import { Id } from "./_generated/dataModel";
import { api } from "./_generated/api";

async function getCurrentUser(_ctx: any): Promise<{ _id: Id<"users">; name: string; email: string } | null> {
  // In a real setup you'd fetch from auth; for now return a guest-like user to prevent null errors.
  return { _id: "guest-user" as Id<"users">, name: "Guest", email: "guest@example.com" };
}

export const create = mutation({
  args: {
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
    configuration: v.object({
      model: v.string(),
      parameters: v.record(v.string(), v.any()),
      triggers: v.array(v.string()),
    }),
  },
  handler: withErrorHandling(async (ctx, args) => {
    const user = await getCurrentUser(ctx);
    if (!user) {
      throw new Error("User must be authenticated");
    }

    const business = await ctx.db.get(args.businessId);
    if (!business || (business.ownerId !== user._id && !(business.teamMembers || []).includes(user._id))) {
      throw new Error("Access denied");
    }

    const agentId = await ctx.db.insert("aiAgents", {
      name: args.name,
      type: args.type,
      businessId: args.businessId,
      isActive: true,
      configuration: args.configuration,
      capabilities: [],
      channels: [],
      playbooks: [],
      mmrPolicy: "auto_with_review",
      performance: {
        tasksCompleted: 0,
        successRate: 0,
        lastActive: Date.now(),
      },
    });

    return agentId;
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
    // Make teamMembers check safe if it's undefined
    if (!business || (business.ownerId !== user._id && !(business.teamMembers || []).includes(user._id))) {
      return [];
    }

    return await ctx.db
      .query("aiAgents")
      .withIndex("by_businessId", (q: any) => q.eq("businessId", args.businessId))
      .collect();
  }),
});

export const toggle = mutation({
  args: {
    id: v.id("aiAgents"),
    isActive: v.boolean(),
  },
  handler: withErrorHandling(async (ctx, args) => {
    const user = await getCurrentUser(ctx);
    if (!user) {
      throw new Error("User must be authenticated");
    }

    const agent = await ctx.db.get(args.id);
    if (!agent) {
      throw new Error("Agent not found");
    }

    const business = await ctx.db.get(agent.businessId);
    // Make teamMembers check safe if it's undefined
    if (!business || (business.ownerId !== user._id && !(business.teamMembers || []).includes(user._id))) {
      throw new Error("Access denied");
    }

    await ctx.db.patch(args.id, { isActive: args.isActive });
    return args.id;
  }),
});

export const seedEnhancedForBusiness = mutation({
  args: { businessId: v.id("businesses") },
  handler: withErrorHandling(async (ctx, args) => {
    const user = await getCurrentUser(ctx);
    if (!user) {
      throw new Error("User must be authenticated");
    }
    const business = await ctx.db.get(args.businessId);
    if (!business || (business.ownerId !== user._id && !business.teamMembers.includes(user._id))) {
      throw new Error("Access denied");
    }

    const enhancedTypes: Array<
      | "content_creation"
      | "sales_intelligence"
      | "customer_support"
      | "marketing_automation"
      | "operations"
      | "analytics"
      | "strategic_planning"
      | "financial_analysis"
      | "hr_recruitment"
      | "compliance_risk"
      | "operations_optimization"
      | "community_engagement"
      | "productivity"
    > = [
      "strategic_planning",
      "content_creation",
      "customer_support",
      "sales_intelligence",
      "analytics",
      "marketing_automation",
      "financial_analysis",
      "hr_recruitment",
      "compliance_risk",
      "operations_optimization",
      "community_engagement",
      "productivity",
      "operations",
    ];

    const typeDefaults: Record<string, {
      name: string;
      capabilities: string[];
      channels: string[];
      playbooks: string[];
      mmrPolicy: "always_human_review" | "auto_with_review" | "auto";
      active: boolean;
    }> = {
      strategic_planning: {
        name: "Strategic Planning Agent",
        capabilities: ["swot", "pestel", "business_model_canvas", "okr_tracking", "scenario_simulation", "competitor_trend_analysis", "quarterly_roadmap"],
        channels: [],
        playbooks: ["quarterly_planning", "annual_plan_outline"],
        mmrPolicy: "auto_with_review",
        active: true,
      },
      content_creation: {
        name: "Content Creation Agent",
        capabilities: ["seo_optimization", "multi_format", "translation_localization", "voice_video_script", "brand_consistency_check", "repurpose_blog_to_slides", "asset_management"],
        channels: ["social", "email", "blog"],
        playbooks: ["newsletter_template", "social_post_series", "blog_ideation"],
        mmrPolicy: "auto_with_review",
        active: true,
      },
      customer_support: {
        name: "Customer Support Agent",
        capabilities: ["omnichannel_support", "kb_integration", "sentiment_prioritization", "escalation_workflows", "social_to_ticket"],
        channels: ["email", "chat", "social"],
        playbooks: ["frustration_escalation", "kb_auto_suggest"],
        mmrPolicy: "auto_with_review",
        active: true,
      },
      sales_intelligence: {
        name: "Sales Intelligence Agent",
        capabilities: ["crm_integration", "lead_scoring", "pipeline_forecast", "next_best_action", "deal_dashboard", "followup_reminders", "ecommerce_upsell", "contract_generation"],
        channels: ["email"],
        playbooks: ["discovery_followup", "renewal_sequence"],
        mmrPolicy: "auto_with_review",
        active: true,
      },
      analytics: {
        name: "Data Analysis Agent",
        capabilities: ["predictive_models", "auto_visualizations", "anomaly_alerts", "root_cause_analysis", "auto_insights", "custom_connectors_csv_sql", "trend_forecast"],
        channels: [],
        playbooks: ["kpi_weekly_digest", "underperforming_campaign_root_cause"],
        mmrPolicy: "auto_with_review",
        active: true,
      },
      marketing_automation: {
        name: "Marketing Automation Agent",
        capabilities: ["email_drips", "seo_keyword_planning", "personalized_sms", "lead_nurture_events", "cross_channel_ab_test", "budget_optimization", "orchestrated_scheduling", "industry_playbooks"],
        channels: ["email", "social", "sms", "ads"],
        playbooks: ["onboarding_nurture", "winback_campaign", "product_launch"],
        mmrPolicy: "auto_with_review",
        active: true,
      },
      financial_analysis: {
        name: "Financial Analysis Agent",
        capabilities: ["cashflow_modeling", "expense_categorization", "accounting_integration", "scenario_planning", "invoice_billing_reminders", "risk_flags", "fraud_detection"],
        channels: ["email"],
        playbooks: ["monthly_cashflow_review", "overdue_receivables_followup"],
        mmrPolicy: "auto_with_review",
        active: false,
      },
      hr_recruitment: {
        name: "HR & Recruitment Agent",
        capabilities: ["candidate_outreach", "interview_scheduling", "onboarding_tasks", "performance_reviews", "training_suggestions", "certification_tracking", "org_charts_resource_planning"],
        channels: ["email", "calendar"],
        playbooks: ["new_hire_onboarding", "quarterly_review_cycle"],
        mmrPolicy: "auto_with_review",
        active: false,
      },
      compliance_risk: {
        name: "Compliance & Risk Agent",
        capabilities: ["gdpr_hipaa_pci_checklists", "regulatory_updates_monitoring", "cybersecurity_scans", "incident_management", "capa_workflows", "risk_registry"],
        channels: ["email"],
        playbooks: ["security_incident_flow", "quarterly_compliance_audit"],
        mmrPolicy: "always_human_review",
        active: false,
      },
      operations_optimization: {
        name: "Operations Optimization Agent",
        capabilities: ["iot_monitoring", "inventory_dashboards", "maintenance_schedules", "supplier_reorders", "process_mining", "service_scheduling"],
        channels: ["email"],
        playbooks: ["maintenance_calendar", "inventory_replenishment"],
        mmrPolicy: "auto_with_review",
        active: false,
      },
      community_engagement: {
        name: "Community & Engagement Agent",
        capabilities: ["ugc_curation", "review_analysis", "social_proof_generation", "affiliate_program_management", "influencer_outreach"],
        channels: ["social", "email"],
        playbooks: ["advocate_outreach", "ugc_roundup_post"],
        mmrPolicy: "auto_with_review",
        active: true,
      },
      productivity: {
        name: "Productivity Agent",
        capabilities: ["daily_prioritization_snap", "todo_management", "calendar_sync", "handoff_coordination"],
        channels: ["email", "calendar"],
        playbooks: ["daily_brief", "weekly_review"],
        mmrPolicy: "auto",
        active: true,
      },
      operations: {
        name: "Operations Agent",
        capabilities: ["workflow_coordination", "backoffice_tasks"],
        channels: ["email"],
        playbooks: ["ops_daily_checklist"],
        mmrPolicy: "auto_with_review",
        active: false,
      },
    };

    const existing = await ctx.db
      .query("aiAgents")
      .withIndex("by_businessId", (q: any) => q.eq("businessId", args.businessId))
      .collect();
    const existingTypes = new Set(existing.map((a: any) => a.type));

    for (const type of enhancedTypes) {
      if (existingTypes.has(type)) continue;

      const def = typeDefaults[type] ?? {
        name: `${type} Agent`,
        capabilities: [],
        channels: [],
        playbooks: [],
        mmrPolicy: "auto_with_review" as const,
        active: ["content_creation", "sales_intelligence", "analytics", "marketing_automation"].includes(type),
      };

      await ctx.db.insert("aiAgents", {
        name: def.name,
        type,
        businessId: args.businessId,
        isActive: def.active,
        configuration: {
          model: "gpt-4o-mini",
          parameters: { temperature: 0.7 },
          triggers: [],
        },
        capabilities: def.capabilities,
        channels: def.channels,
        playbooks: def.playbooks,
        mmrPolicy: def.mmrPolicy,
        performance: {
          tasksCompleted: 0,
          successRate: 0,
          lastActive: Date.now(),
        },
      });
    }

    return true;
  }),
});

export const updateConfig = mutation({
  args: {
    id: v.id("aiAgents"),
    configuration: v.object({
      model: v.string(),
      parameters: v.record(v.string(), v.any()),
      triggers: v.array(v.string()),
    }),
    isActive: v.optional(v.boolean()),
  },
  handler: withErrorHandling(async (ctx, args) => {
    const user = await getCurrentUser(ctx);
    if (!user) {
      throw new Error("User must be authenticated");
    }
    const agent = await ctx.db.get(args.id);
    if (!agent) {
      throw new Error("Agent not found");
    }
    const business = await ctx.db.get(agent.businessId);
    if (!business || (business.ownerId !== user._id && !business.teamMembers.includes(user._id))) {
      throw new Error("Access denied");
    }

    const updates: any = { configuration: args.configuration };
    if (typeof args.isActive === "boolean") {
      updates.isActive = args.isActive;
    }
    await ctx.db.patch(args.id, updates);
    return args.id;
  }),
});

export const listTemplates = query({
  args: {
    tags: v.optional(v.array(v.string())),
    tier: v.optional(v.string()),
  },
  handler: withErrorHandling(async (ctx, args) => {
    let q = ctx.db.query("agent_templates");
    if (args.tier) {
      q = q.withIndex("by_tier", (q2: any) => q2.eq("tier", args.tier as any));
    }
    const templates = await q.collect();
    if (args.tags && args.tags.length > 0) {
      return templates.filter((template: any) =>
        args.tags!.some((tag: string) => template.tags.includes(tag))
      );
    }
    return templates;
  }),
});

export const getTemplate = query({
  args: { id: v.id("agent_templates") },
  handler: withErrorHandling(async (ctx, args) => {
    return await ctx.db.get(args.id);
  }),
});

export const createFromTemplate = mutation({
  args: {
    templateId: v.id("agent_templates"),
    name: v.string(),
    tags: v.optional(v.array(v.string())),
    businessId: v.id("businesses"),
    userId: v.id("users"),
  },
  handler: withErrorHandling(async (ctx, args) => {
    const template = await ctx.db.get(args.templateId);
    if (!template) throw new Error("Template not found");

    const agentId = await ctx.db.insert("custom_agents", {
      name: args.name,
      description: template.description,
      tags: args.tags || template.tags,
      createdBy: args.userId,
      businessId: args.businessId,
      visibility: "private",
      requiresApproval: false,
      riskLevel: "low",
    });

    const versionId = await ctx.db.insert("custom_agent_versions", {
      agentId,
      version: "1.0.0",
      changelog: "Created from template",
      config: template.configPreview,
      createdBy: args.userId,
    });

    await ctx.db.patch(agentId, { currentVersionId: versionId });

    await ctx.db.insert("agent_stats", {
      agentId,
      runs: 0,
      successes: 0,
    });

    return agentId;
  }),
});

export const createCustomAgent = mutation({
  args: {
    name: v.string(),
    description: v.string(),
    tags: v.array(v.string()),
    config: v.object({}),
    businessId: v.id("businesses"),
    userId: v.id("users"),
    visibility: v.optional(v.string()),
    riskLevel: v.optional(v.string()),
  },
  handler: withErrorHandling(async (ctx, args) => {
    const agentId = await ctx.db.insert("custom_agents", {
      name: args.name,
      description: args.description,
      tags: args.tags,
      createdBy: args.userId,
      businessId: args.businessId,
      visibility: (args.visibility as any) || "private",
      requiresApproval: false,
      riskLevel: (args.riskLevel as any) || "low",
    });

    const versionId = await ctx.db.insert("custom_agent_versions", {
      agentId,
      version: "1.0.0",
      changelog: "Initial version",
      config: args.config,
      createdBy: args.userId,
    });

    await ctx.db.patch(agentId, { currentVersionId: versionId });

    await ctx.db.insert("agent_stats", {
      agentId,
      runs: 0,
      successes: 0,
    });

    return agentId;
  }),
});

export const listCustomAgents = query({
  args: {
    userId: v.optional(v.id("users")),
    businessId: v.optional(v.id("businesses")),
    visibility: v.optional(v.string()),
  },
  handler: withErrorHandling(async (ctx, args) => {
    let q = ctx.db.query("custom_agents");
    if (args.userId) {
      q = q.withIndex("by_createdBy", (q2: any) => q2.eq("createdBy", args.userId!));
    } else if (args.businessId) {
      q = q.withIndex("by_businessId", (q2: any) => q2.eq("businessId", args.businessId!));
    } else if (args.visibility) {
      q = q.withIndex("by_visibility", (q2: any) => q2.eq("visibility", args.visibility as any));
    }

    const agents = await q.collect();

    const withStats = await Promise.all(
      agents.map(async (agent: any) => {
        const stats = await ctx.db
          .query("agent_stats")
          .withIndex("by_agentId", (q2: any) => q2.eq("agentId", agent._id))
          .unique();

        const currentVersion = agent.currentVersionId ? await ctx.db.get(agent.currentVersionId) : null;

        return {
          ...agent,
          stats: stats || { runs: 0, successes: 0, lastRunAt: undefined },
          currentVersion,
        };
      })
    );

    return withStats;
  }),
});

export const getCustomAgent = query({
  args: { id: v.id("custom_agents") },
  handler: withErrorHandling(async (ctx, args) => {
    const agent = await ctx.db.get(args.id);
    if (!agent) return null;

    const stats = await ctx.db
      .query("agent_stats")
      .withIndex("by_agentId", (q2: any) => q2.eq("agentId", args.id))
      .unique();

    const currentVersion = agent.currentVersionId ? await ctx.db.get(agent.currentVersionId) : null;

    return {
      ...agent,
      stats: stats || { runs: 0, successes: 0, lastRunAt: undefined },
      currentVersion,
    };
  }),
});

export const updateCustomAgentMeta = mutation({
  args: {
    id: v.id("custom_agents"),
    name: v.optional(v.string()),
    description: v.optional(v.string()),
    tags: v.optional(v.array(v.string())),
    visibility: v.optional(v.string()),
    riskLevel: v.optional(v.string()),
  },
  handler: withErrorHandling(async (ctx, args) => {
    const { id, ...rest } = args;
    const updates = Object.fromEntries(
      Object.entries(rest).filter(([, v]) => v !== undefined)
    );
    await ctx.db.patch(id, updates as any);
  }),
});

export const createVersion = mutation({
  args: {
    agentId: v.id("custom_agents"),
    changelog: v.string(),
    config: v.object({}),
    userId: v.id("users"),
  },
  handler: withErrorHandling(async (ctx, args) => {
    const agent = await ctx.db.get(args.agentId);
    if (!agent) throw new Error("Agent not found");

    const versions = await ctx.db
      .query("custom_agent_versions")
      .withIndex("by_agentId", (q2: any) => q2.eq("agentId", args.agentId))
      .collect();

    const nextVersion = `1.${versions.length}.0`;

    const versionId = await ctx.db.insert("custom_agent_versions", {
      agentId: args.agentId,
      version: nextVersion,
      changelog: args.changelog,
      config: args.config,
      createdBy: args.userId,
    });

    await ctx.db.patch(args.agentId, { currentVersionId: versionId });
    return versionId;
  }),
});

export const getVersions = query({
  args: { agentId: v.id("custom_agents") },
  handler: withErrorHandling(async (ctx, args) => {
    return await ctx.db
      .query("custom_agent_versions")
      .withIndex("by_agentId", (q2: any) => q2.eq("agentId", args.agentId))
      .collect();
  }),
});

export const getAgentStats = query({
  args: { agentId: v.id("custom_agents") },
  handler: withErrorHandling(async (ctx, args) => {
    return await ctx.db
      .query("agent_stats")
      .withIndex("by_agentId", (q2: any) => q2.eq("agentId", args.agentId))
      .unique();
  }),
});

export const addRating = mutation({
  args: {
    agentId: v.id("custom_agents"),
    userId: v.id("users"),
    rating: v.number(),
    comment: v.optional(v.string()),
  },
  handler: withErrorHandling(async (ctx, args) => {
    const existing = await ctx.db
      .query("agent_ratings")
      .withIndex("by_userId_and_agentId", (q2: any) =>
        q2.eq("userId", args.userId).eq("agentId", args.agentId)
      )
      .unique();

    if (existing) {
      await ctx.db.patch(existing._id, {
        rating: args.rating as any,
        comment: args.comment,
      });
      return existing._id;
    } else {
      return await ctx.db.insert("agent_ratings", {
        agentId: args.agentId,
        userId: args.userId,
        rating: args.rating as any,
        comment: args.comment,
      });
    }
  }),
});

export const listRatings = query({
  args: { agentId: v.id("custom_agents") },
  handler: withErrorHandling(async (ctx, args) => {
    const ratings = await ctx.db
      .query("agent_ratings")
      .withIndex("by_agentId", (q2: any) => q2.eq("agentId", args.agentId))
      .collect();

    return await Promise.all(
      ratings.map(async (rating: any) => {
        const user = await ctx.db.get(rating.userId);
        return {
          ...rating,
          user: user ? { name: user.name, email: user.email } : null,
        };
      })
    );
  }),
});

export const seedAgentFramework = action({
  args: {},
  handler: withErrorHandling(async (ctx) => {
    const existingTemplates = await ctx.runQuery(api.aiAgents.listTemplates, {});
    if (existingTemplates.length > 0) {
      return { message: "Already seeded" };
    }

    let sampleUser = await ctx.runQuery(api.users.currentUser, {});
    if (!sampleUser) {
      sampleUser = { _id: "sample-user" as Id<"users">, name: "Sample User", email: "sample@example.com" } as any;
    }

    const templates = [
      {
        name: "Twitter Account Manager",
        description: "Automates Twitter posting and engagement tracking",
        tags: ["social-media", "automation", "twitter"],
        tier: "solopreneur" as const,
        configPreview: {
          inputs: ["content", "schedule"],
          hooks: ["post_tweet", "track_engagement"],
          outputs: ["engagement_metrics"],
        },
      },
      {
        name: "Inventory Notifier",
        description: "Monitors inventory levels and sends alerts",
        tags: ["inventory", "alerts", "monitoring"],
        tier: "startup" as const,
        configPreview: {
          inputs: ["inventory_data", "thresholds"],
          hooks: ["check_levels", "send_alert"],
          outputs: ["alert_status"],
        },
      },
      {
        name: "Customer Support Bot",
        description: "Handles basic customer inquiries automatically",
        tags: ["customer-service", "automation", "chat"],
        tier: "sme" as const,
        configPreview: {
          inputs: ["customer_message", "knowledge_base"],
          hooks: ["analyze_intent", "generate_response"],
          outputs: ["response", "escalation_flag"],
        },
      },
    ];

    for (const template of templates) {
      await ctx.runMutation(api.aiAgents.createTemplate, {
        ...template,
        createdBy: sampleUser._id,
      });
    }

    return { message: "Seeded successfully" };
  }),
});

export const createTemplate = mutation({
  args: {
    name: v.string(),
    description: v.string(),
    tags: v.array(v.string()),
    tier: v.string(),
    configPreview: v.object({}),
    createdBy: v.id("users"),
  },
  handler: withErrorHandling(async (ctx, args) => {
    return await ctx.db.insert("agent_templates", {
      name: args.name,
      description: args.description,
      tags: args.tags,
      tier: args.tier as any,
      configPreview: args.configPreview,
      createdBy: args.createdBy,
    });
  }),
});

export const listMarketplaceAgents = query({
  args: {
    status: v.union(v.literal("pending"), v.literal("approved"), v.literal("rejected")),
  },
  handler: withErrorHandling(async (ctx, args) => {
    const marketplace = await ctx.db
      .query("agent_marketplace")
      .withIndex("by_status", (q: any) => q.eq("status", args.status))
      .collect();

    const enriched = await Promise.all(
      marketplace.map(async (item: any) => {
        const agent = await ctx.db.get(item.agentId);

        const stats =
          (await ctx.db
            .query("agent_stats")
            .withIndex("by_agentId", (q2: any) => q2.eq("agentId", item.agentId))
            .unique()) || { runs: 0, successes: 0 };

        const ratings = await ctx.db
          .query("agent_ratings")
          .withIndex("by_agentId", (q2: any) => q2.eq("agentId", item.agentId))
          .collect();

        const ratingsCount = ratings.length;
        const avgRating =
          ratingsCount > 0
            ? ratings.reduce((sum: number, r: any) => sum + (r.rating || 0), 0) / ratingsCount
            : 0;

        return {
          ...item,
          agent,
          stats,
          avgRating,
          ratingsCount,
        };
      })
    );

    return enriched;
  }),
});

export const addToWorkspace = mutation({
  args: {
    marketplaceAgentId: v.id("custom_agents"),
    businessId: v.id("businesses"),
    userId: v.id("users"),
  },
  handler: withErrorHandling(async (ctx, args) => {
    const originalAgent = await ctx.db.get(args.marketplaceAgentId);
    if (!originalAgent) {
      throw new Error("Marketplace agent not found");
    }

    const originalVersion = originalAgent.currentVersionId
      ? await ctx.db.get(originalAgent.currentVersionId)
      : null;

    // Clone as a new agent into the user's business
    const newAgentId = await ctx.db.insert("custom_agents", {
      name: originalAgent.name,
      description: originalAgent.description,
      tags: originalAgent.tags || [],
      createdBy: args.userId,
      businessId: args.businessId,
      visibility: "private",
      requiresApproval: false,
      riskLevel: originalAgent.riskLevel || ("low" as const),
    });

    const newVersionId = await ctx.db.insert("custom_agent_versions", {
      agentId: newAgentId,
      version: (originalVersion?.version as string) || "1.0.0",
      changelog: "Imported from marketplace",
      config: originalVersion?.config || {},
      createdBy: args.userId,
    });

    await ctx.db.patch(newAgentId, { currentVersionId: newVersionId });

    await ctx.db.insert("agent_stats", {
      agentId: newAgentId,
      runs: 0,
      successes: 0,
    });

    return newAgentId;
  }),
});

export const rollbackToVersion = mutation({
  args: {
    agentId: v.id("custom_agents"),
    versionId: v.id("custom_agent_versions"),
  },
  handler: withErrorHandling(async (ctx, args) => {
    const version = await ctx.db.get(args.versionId);
    if (!version) {
      throw new Error("Version not found");
    }
    if (version.agentId !== args.agentId) {
      throw new Error("Version does not belong to the specified agent");
    }

    await ctx.db.patch(args.agentId, { currentVersionId: args.versionId });
    return args.versionId;
  }),
});