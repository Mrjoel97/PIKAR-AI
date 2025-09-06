import { v } from "convex/values";
import { mutation, query } from "./_generated/server";
import { getCurrentUser } from "./users";
import { withErrorHandling } from "./utils";

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
    if (!business || (business.ownerId !== user._id && !business.teamMembers.includes(user._id))) {
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
    if (!business || (business.ownerId !== user._id && !business.teamMembers.includes(user._id))) {
      return [];
    }

    return await ctx.db
      .query("aiAgents")
      .withIndex("by_business", (q: any) => q.eq("businessId", args.businessId))
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
    if (!business || (business.ownerId !== user._id && !business.teamMembers.includes(user._id))) {
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
      .withIndex("by_business", (q: any) => q.eq("businessId", args.businessId))
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