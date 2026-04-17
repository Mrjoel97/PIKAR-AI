export interface Env {
  FALLBACK_BACKEND_ORIGIN: string;
  ALLOWED_ORIGINS?: string;
  INTERNAL_PROXY_TOKEN?: string;
  SUPABASE_URL?: string;
  SUPABASE_ANON_KEY?: string;
  SUPABASE_SERVICE_ROLE_KEY?: string;
  LINKEDIN_CLIENT_SECRET?: string;
  LINKEDIN_WEBHOOK_SECRET?: string;
  [key: string]: string | undefined;
}

const DEFAULT_SESSION_CONFIG = {
  max_concurrent_streams: 4,
  memory_eviction_minutes: 30,
  max_active_sessions_in_memory: 20,
} as const;

const BUILT_IN_TOOLS_INFO = [
  {
    id: "tavily",
    name: "Web Search (Tavily)",
    description: "AI-powered web search - automatically used for research tasks.",
  },
  {
    id: "firecrawl",
    name: "Web Scraping (Firecrawl)",
    description: "Content extraction from webpages - automatically used for deep research.",
  },
] as const;

const CONFIGURABLE_TOOLS_INFO = [
  {
    id: "stitch",
    name: "Landing Page Builder (Stitch)",
    description: "Generate professional landing pages with AI. Creates HTML and React components.",
    envVar: "STITCH_API_KEY",
    docsUrl: "https://stitch.withgoogle.com/docs",
  },
  {
    id: "stripe",
    name: "Payments (Stripe)",
    description: "Accept payments, create checkout sessions, and manage subscriptions for landing pages.",
    envVar: "STRIPE_API_KEY",
    docsUrl: "https://stripe.com/docs",
  },
  {
    id: "canva",
    name: "Media Creation (Canva)",
    description: "Create professional graphics, social media posts, and visual content with AI.",
    envVar: "CANVA_API_KEY",
    docsUrl: "https://www.canva.dev/docs",
  },
  {
    id: "resend",
    name: "Email Service (Resend)",
    description: "Send transactional emails and notifications to users and customers.",
    envVar: "RESEND_API_KEY",
    docsUrl: "https://resend.com/docs",
  },
  {
    id: "hubspot",
    name: "CRM Integration (HubSpot)",
    description: "Sync contacts, track deals, and manage customer relationships.",
    envVar: "HUBSPOT_API_KEY",
    docsUrl: "https://developers.hubspot.com/docs",
  },
] as const;

const SOCIAL_PLATFORMS_INFO = [
  {
    platform: "twitter",
    display_name: "Twitter / X",
    icon: "twitter",
    config_keys: ["TWITTER_CLIENT_ID", "TWITTER_CLIENT_SECRET"],
  },
  {
    platform: "linkedin",
    display_name: "LinkedIn",
    icon: "linkedin",
    config_keys: ["LINKEDIN_CLIENT_ID", "LINKEDIN_CLIENT_SECRET"],
  },
  {
    platform: "facebook",
    display_name: "Facebook",
    icon: "facebook",
    config_keys: ["FACEBOOK_APP_ID", "FACEBOOK_APP_SECRET"],
  },
  {
    platform: "instagram",
    display_name: "Instagram",
    icon: "instagram",
    config_keys: ["FACEBOOK_APP_ID", "FACEBOOK_APP_SECRET"],
  },
  {
    platform: "youtube",
    display_name: "YouTube",
    icon: "youtube",
    config_keys: ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"],
  },
  {
    platform: "tiktok",
    display_name: "TikTok",
    icon: "tiktok",
    config_keys: ["TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET"],
  },
] as const;

const INBOUND_PROVIDER_SECRETS: Record<string, string> = {
  stripe: "STRIPE_WEBHOOK_SECRET",
  hubspot: "HUBSPOT_WEBHOOK_SECRET",
  resend: "RESEND_WEBHOOK_SECRET",
  github: "GITHUB_WEBHOOK_SECRET",
  slack: "SLACK_WEBHOOK_SECRET",
  shopify: "SHOPIFY_WEBHOOK_SECRET",
};

const INBOUND_SIGNATURE_HEADERS: Record<string, string> = {
  stripe: "Stripe-Signature",
  hubspot: "X-HubSpot-Signature-v3",
  github: "X-Hub-Signature-256",
  slack: "X-Slack-Signature",
  shopify: "X-Shopify-Hmac-SHA256",
};

const OUTBOUND_WEBHOOK_EVENT_CATALOG: OutboundWebhookEventCatalogItem[] = [
  {
    event_type: "task.created",
    description: "A new task has been created.",
    schema: {
      type: "object",
      properties: {
        task_id: { type: "string", format: "uuid" },
        title: { type: "string" },
        status: { type: "string" },
        created_by: { type: "string", format: "uuid" },
        created_at: { type: "string", format: "date-time" },
      },
      required: ["task_id", "title", "status", "created_by", "created_at"],
    },
  },
  {
    event_type: "task.updated",
    description: "An existing task has been updated.",
    schema: {
      type: "object",
      properties: {
        task_id: { type: "string", format: "uuid" },
        title: { type: "string" },
        status: { type: "string" },
        updated_by: { type: "string", format: "uuid" },
        updated_at: { type: "string", format: "date-time" },
        changes: {
          type: "object",
          description: "Key-value map of changed fields with old/new values.",
        },
      },
      required: ["task_id", "status", "updated_at"],
    },
  },
  {
    event_type: "workflow.started",
    description: "A workflow execution has started.",
    schema: {
      type: "object",
      properties: {
        execution_id: { type: "string", format: "uuid" },
        template_id: { type: "string", format: "uuid" },
        template_name: { type: "string" },
        started_by: { type: "string", format: "uuid" },
        started_at: { type: "string", format: "date-time" },
      },
      required: ["execution_id", "template_id", "started_at"],
    },
  },
  {
    event_type: "workflow.completed",
    description: "A workflow execution has completed.",
    schema: {
      type: "object",
      properties: {
        execution_id: { type: "string", format: "uuid" },
        template_id: { type: "string", format: "uuid" },
        template_name: { type: "string" },
        status: {
          type: "string",
          enum: ["completed", "failed", "cancelled"],
        },
        completed_at: { type: "string", format: "date-time" },
        duration_seconds: { type: "number" },
      },
      required: ["execution_id", "template_id", "status", "completed_at"],
    },
  },
  {
    event_type: "approval.pending",
    description: "A new approval request is awaiting a decision.",
    schema: {
      type: "object",
      properties: {
        approval_id: { type: "string", format: "uuid" },
        request_type: { type: "string" },
        title: { type: "string" },
        requested_by: { type: "string", format: "uuid" },
        created_at: { type: "string", format: "date-time" },
      },
      required: ["approval_id", "request_type", "title", "created_at"],
    },
  },
  {
    event_type: "approval.decided",
    description: "An approval request has been decided (approved or rejected).",
    schema: {
      type: "object",
      properties: {
        approval_id: { type: "string", format: "uuid" },
        decision: { type: "string", enum: ["approved", "rejected"] },
        decided_by: { type: "string", format: "uuid" },
        decided_at: { type: "string", format: "date-time" },
        reason: { type: "string" },
      },
      required: ["approval_id", "decision", "decided_at"],
    },
  },
  {
    event_type: "initiative.phase_changed",
    description: "An initiative has moved to a new phase.",
    schema: {
      type: "object",
      properties: {
        initiative_id: { type: "string", format: "uuid" },
        initiative_name: { type: "string" },
        previous_phase: { type: "string" },
        new_phase: { type: "string" },
        changed_at: { type: "string", format: "date-time" },
      },
      required: ["initiative_id", "previous_phase", "new_phase", "changed_at"],
    },
  },
  {
    event_type: "contact.synced",
    description: "A contact has been synced from an external CRM.",
    schema: {
      type: "object",
      properties: {
        contact_id: { type: "string", format: "uuid" },
        provider: { type: "string" },
        external_id: { type: "string" },
        email: { type: "string", format: "email" },
        name: { type: "string" },
        synced_at: { type: "string", format: "date-time" },
      },
      required: ["contact_id", "provider", "synced_at"],
    },
  },
  {
    event_type: "invoice.created",
    description: "A new invoice has been created.",
    schema: {
      type: "object",
      properties: {
        invoice_id: { type: "string", format: "uuid" },
        amount: { type: "number" },
        currency: { type: "string" },
        customer_id: { type: "string" },
        due_date: { type: "string", format: "date" },
        created_at: { type: "string", format: "date-time" },
      },
      required: ["invoice_id", "amount", "currency", "created_at"],
    },
  },
] as const;

const OUTBOUND_WEBHOOK_EVENT_TYPES = new Set(
  OUTBOUND_WEBHOOK_EVENT_CATALOG.map((entry) => entry.event_type),
);

type SuggestionCategory =
  | "quick_start"
  | "persona_specific"
  | "time_aware"
  | "activity_followup";

type SuggestionItem = {
  text: string;
  category: SuggestionCategory;
};

type IntegrationAuthType = "oauth2" | "api_key";
type IntegrationCategory =
  | "crm_sales"
  | "finance_commerce"
  | "productivity"
  | "analytics"
  | "communication";

type IntegrationProvider = {
  key: string;
  name: string;
  auth_type: IntegrationAuthType;
  category: IntegrationCategory;
  icon_url: string;
  scopes: string[];
};

type IntegrationProviderConfig = IntegrationProvider & {
  auth_url: string;
  token_url: string;
  client_id_env: string;
  client_secret_env: string;
};

type OAuthStatePayload = {
  user_id: string;
  provider: string;
  shop?: string;
  nonce: string;
  exp: number;
};

type PersonaTier = "solopreneur" | "startup" | "sme" | "enterprise";

type WorkspaceRecord = {
  id: string;
  name: string;
  slug?: string | null;
  owner_id: string;
  created_at?: string;
  updated_at?: string;
};

type WorkspaceMemberRecord = {
  id: string;
  user_id: string;
  role: string;
  joined_at: string;
  email?: string | null;
  full_name?: string | null;
};

type WorkspaceInviteRecord = {
  id: string;
  workspace_id: string;
  token: string;
  role: string;
  created_by: string;
  invited_email?: string | null;
  expires_at: string;
  accepted_by?: string | null;
  accepted_at?: string | null;
  is_active: boolean;
  created_at?: string;
};

type DataDeletionRequestRecord = {
  id: string;
  status: string;
  platform: string;
  requested_at: string;
  completed_at?: string | null;
  confirmation_code?: string | null;
};

type OnboardingStatusResponse = {
  is_completed: boolean;
  current_step: number;
  total_steps: number;
  business_context_completed: boolean;
  preferences_completed: boolean;
  agent_setup_completed: boolean;
  persona: string | null;
  agent_name: string | null;
};

type BusinessContextPayload = {
  company_name: string;
  industry: string;
  description: string;
  goals: string[];
  team_size: string | null;
  role: string | null;
  website: string | null;
};

type UserPreferencesPayload = {
  tone: string;
  verbosity: string;
  communication_style: string;
  notification_frequency: string;
};

type AgentSetupPayload = {
  agent_name: string;
  focus_areas: string[] | null;
};

type OnboardingChecklistItem = {
  id: string;
  icon: string;
  title: string;
  description: string;
  completed: boolean;
};

type OnboardingExtractContextPayload = {
  messages: string[];
};

type SupportTicketPriority = "low" | "normal" | "high" | "urgent";
type SupportTicketStatus = "new" | "open" | "in_progress" | "waiting" | "resolved" | "closed";

type SupportTicketRecord = {
  id: string;
  user_id: string;
  subject: string;
  description: string;
  customer_email: string;
  priority: SupportTicketPriority;
  status: SupportTicketStatus;
  assigned_to: string | null;
  resolution: string | null;
  created_at: string;
  updated_at: string;
};

type CommunityPostRecord = {
  id: string;
  user_id: string;
  author_name: string;
  title: string;
  body: string;
  category: string;
  tags: string[];
  upvotes: number;
  reply_count: number;
  is_pinned: boolean;
  created_at: string;
  updated_at: string;
};

type CommunityCommentRecord = {
  id: string;
  post_id: string;
  user_id: string;
  author_name: string;
  body: string;
  upvotes: number;
  created_at: string;
};

type LandingPageRecord = {
  id: string;
  user_id: string;
  title: string;
  slug: string;
  html_content: string;
  published: boolean;
  published_at: string | null;
  created_at: string;
  updated_at: string;
  metadata: Record<string, unknown>;
  submission_count: number;
};

type ApprovalStatus = "PENDING" | "APPROVED" | "REJECTED" | "EXPIRED";

type ApprovalRequestRecord = {
  id: string;
  action_type: string;
  payload: Record<string, unknown>;
  status: ApprovalStatus;
  created_at: string;
  expires_at: string;
  responded_at: string | null;
  token?: string | null;
  user_id?: string | null;
};

type OutboundWebhookEndpointRecord = {
  id: string;
  user_id: string;
  url: string;
  events: string[];
  active: boolean;
  consecutive_failures: number;
  disabled_at: string | null;
  created_at: string;
  updated_at: string | null;
  description: string | null;
  secret: string | null;
};

type OutboundWebhookDeliveryRecord = {
  id: string;
  endpoint_id: string;
  event_type: string;
  status: string;
  attempts: number;
  response_code: number | null;
  created_at: string;
};

type OutboundWebhookEventCatalogItem = {
  event_type: string;
  description: string;
  schema: Record<string, unknown>;
};

type FinanceInvoiceRecord = {
  id: string;
  user_id: string;
  invoice_number: string | null;
  client_name: string | null;
  client_email: string | null;
  amount: number;
  currency: string;
  status: string;
  due_date: string | null;
  paid_at: string | null;
  created_at: string;
  updated_at: string;
};

type FinanceAssumptionRecord = {
  id: string;
  assumption_type: string;
  key: string;
  label: string;
  value: unknown;
  is_active: boolean;
  created_at: string;
};

type SalesConnectedAccountResponse = {
  id: string;
  user_id: string;
  platform: string;
  account_name: string | null;
  account_id: string | null;
  status: string;
  connected_at: string | null;
  last_synced_at: string | null;
};

type SalesCampaignResponse = {
  id: string;
  name: string;
  type: string | null;
  target_audience: string | null;
  status: string;
  schedule: Record<string, unknown>;
  metrics: Record<string, unknown> | null;
  created_at: string;
};

type SalesPageAnalyticsResponse = {
  id: string;
  page_url: string | null;
  platform: string | null;
  views: number;
  clicks: number | null;
  conversions: number | null;
  engagement_rate: number | null;
  created_at: string;
};

type ContentBundleResponse = {
  id: string;
  user_id: string;
  title: string;
  bundle_type: string | null;
  status: string;
  description: string | null;
  target_date: string | null;
  published_at: string | null;
  created_at: string;
  updated_at: string;
};

type ContentDeliverableResponse = {
  id: string;
  bundle_id: string;
  title: string;
  type: string | null;
  status: string;
  platform: string | null;
  content_url: string | null;
  created_at: string;
};

const DEFAULT_ONBOARDING_PREFERENCES: UserPreferencesPayload = {
  tone: "professional",
  verbosity: "concise",
  communication_style: "direct",
  notification_frequency: "daily",
};

const PERSONA_ONBOARDING_CHECKLISTS: Record<PersonaTier, OnboardingChecklistItem[]> = {
  solopreneur: [
    { id: "revenue_strategy", icon: "💰", title: "Map your revenue strategy", description: "Identify your best income opportunities", completed: false },
    { id: "brain_dump", icon: "🧠", title: "Do a brain dump", description: "Get all your ideas organized", completed: false },
    { id: "weekly_plan", icon: "📋", title: "Plan your week", description: "Create a focused 7-day action plan", completed: false },
    { id: "first_workflow", icon: "⚡", title: "Run your first workflow", description: "Automate a repetitive task", completed: false },
    { id: "content_piece", icon: "✍️", title: "Create your first content piece", description: "Generate a blog post or social update", completed: false },
  ],
  startup: [
    { id: "growth_experiment", icon: "🚀", title: "Design a growth experiment", description: "Test a hypothesis to accelerate growth", completed: false },
    { id: "pitch_review", icon: "🎯", title: "Review your pitch", description: "Sharpen your value proposition", completed: false },
    { id: "burn_rate", icon: "📊", title: "Check your burn rate", description: "Understand your runway", completed: false },
    { id: "team_update", icon: "👥", title: "Write a team update", description: "Align your team on priorities", completed: false },
    { id: "first_workflow", icon: "⚡", title: "Run your first workflow", description: "Automate a repeatable process", completed: false },
  ],
  sme: [
    { id: "dept_health", icon: "🏥", title: "Run a department health check", description: "See how each team is performing", completed: false },
    { id: "process_audit", icon: "⚙️", title: "Audit your processes", description: "Find bottlenecks and optimize", completed: false },
    { id: "compliance_review", icon: "🛡️", title: "Run a compliance review", description: "Ensure nothing falls through cracks", completed: false },
    { id: "kpi_dashboard", icon: "📊", title: "Set up KPI tracking", description: "Define and monitor key metrics", completed: false },
    { id: "first_workflow", icon: "⚡", title: "Run your first workflow", description: "Automate a department process", completed: false },
  ],
  enterprise: [
    { id: "stakeholder_briefing", icon: "📋", title: "Prepare a stakeholder briefing", description: "Strategic update for leadership", completed: false },
    { id: "risk_assessment", icon: "⚠️", title: "Run a risk assessment", description: "Identify and prioritize risks", completed: false },
    { id: "portfolio_review", icon: "📈", title: "Review initiative portfolio", description: "Evaluate portfolio health", completed: false },
    { id: "approval_workflow", icon: "✅", title: "Set up an approval workflow", description: "Configure governance controls", completed: false },
    { id: "first_workflow", icon: "⚡", title: "Run your first workflow", description: "Automate an enterprise process", completed: false },
  ],
};

const SUPPORT_TICKET_PRIORITIES = ["low", "normal", "high", "urgent"] as const;
const SUPPORT_TICKET_STATUSES = [
  "new",
  "open",
  "in_progress",
  "waiting",
  "resolved",
  "closed",
] as const;

const ACCOUNT_DELETE_SUCCESS_MESSAGE =
  "Your account and all associated data have been permanently deleted. Compliance audit records that must be retained have been anonymized — your identity has been removed.";
const EXPORT_BUCKET_NAME = "generated-documents";
const EXPORT_SIGNED_URL_EXPIRY_SECONDS = 24 * 60 * 60;
const EXPORT_JSON_CONTENT_TYPE = "application/json; charset=utf-8";
const REDACTED_VALUE = "[REDACTED]";
const SENSITIVE_KEYWORDS = [
  "token",
  "secret",
  "api_key",
  "apikey",
  "password",
  "private_key",
  "authorization",
  "credential",
] as const;

const PERSONA_SUGGESTIONS: Record<string, string[]> = {
  solopreneur: [
    "Review yesterday's revenue",
    "Check my business revenue",
    "Create a content calendar for this week",
    "Start a brain dump session",
    "Show available workflows",
    "Brainstorm a new product idea",
    "Generate a marketing campaign",
    "Analyze my social media performance",
    "Draft a sales outreach email",
    "Review my task pipeline",
    "Find growth opportunities",
    "Optimize my pricing strategy",
  ],
  startup: [
    "Check product-market fit signals",
    "Review experiment velocity this sprint",
    "Analyze growth metrics dashboard",
    "Prepare fundraising pitch materials",
    "Review burn rate and runway",
    "Identify top churn risk customers",
    "Draft investor update email",
    "Brainstorm feature prioritization",
    "Analyze competitor landscape",
    "Review hiring pipeline status",
    "Plan next sprint objectives",
    "Check activation funnel metrics",
  ],
  sme: [
    "Review department performance reports",
    "Check compliance status across teams",
    "Generate monthly business report",
    "Optimize cross-department workflows",
    "Review employee satisfaction trends",
    "Audit process efficiency metrics",
    "Plan resource allocation for Q2",
    "Check vendor contract renewals",
    "Review customer satisfaction scores",
    "Analyze operational bottlenecks",
    "Draft team communication update",
    "Review project milestone progress",
  ],
  enterprise: [
    "Check portfolio health dashboard",
    "Review governance compliance status",
    "Analyze enterprise risk indicators",
    "Coordinate cross-functional initiatives",
    "Review executive briefing summary",
    "Audit security posture metrics",
    "Plan strategic quarterly objectives",
    "Check regulatory change impacts",
    "Review M&A pipeline status",
    "Analyze workforce planning data",
    "Draft board presentation materials",
    "Review global operations dashboard",
  ],
};

const TIME_BUCKET_SUGGESTIONS: Record<string, string[]> = {
  morning: [
    "Review yesterday's metrics",
    "Plan today's priorities",
    "Check overnight notifications",
    "Review pending approvals",
    "Start the day with a brain dump",
    "Check your calendar for today",
    "Review urgent action items",
  ],
  afternoon: [
    "Summarize progress so far today",
    "Draft a follow-up on pending items",
    "Review team updates",
    "Analyze today's performance data",
    "Create a workflow for a recurring task",
    "Check on running experiments",
    "Prepare materials for tomorrow",
  ],
  evening: [
    "Plan tomorrow's top priorities",
    "Review today's accomplishments",
    "Draft end-of-day status update",
    "Brainstorm ideas for next week",
    "Review weekly goals progress",
    "Prepare for tomorrow's meetings",
    "Reflect on key learnings today",
  ],
};

const ACTIVITY_FOLLOWUP_MAP: Record<string, string[]> = {
  "workflow:content_creation": [
    "Review your latest content draft",
    "Schedule content for publishing",
    "Analyze content performance metrics",
  ],
  "workflow:marketing_campaign": [
    "Check campaign performance results",
    "Adjust campaign targeting parameters",
    "Review campaign budget allocation",
  ],
  "workflow:financial_review": [
    "Review updated financial projections",
    "Check expense anomalies flagged",
    "Compare actuals vs budget",
  ],
  "workflow:strategic_planning": [
    "Review strategic initiative progress",
    "Update milestone timelines",
    "Check strategic goal alignment",
  ],
  "workflow:compliance_check": [
    "Review compliance findings report",
    "Address flagged compliance items",
    "Schedule follow-up compliance audit",
  ],
  "workflow:sales_pipeline": [
    "Review pipeline conversion rates",
    "Follow up on stalled deals",
    "Prepare proposal for top prospect",
  ],
};

const QUICK_START_SUGGESTIONS: SuggestionItem[] = [
  { text: "Review my business", category: "quick_start" },
  { text: "Create a strategic plan", category: "quick_start" },
  { text: "Start a brain dump session", category: "quick_start" },
  { text: "Show available workflows", category: "quick_start" },
];

const INTEGRATION_PROVIDERS: IntegrationProvider[] = [
  {
    key: "hubspot",
    name: "HubSpot",
    auth_type: "oauth2",
    category: "crm_sales",
    icon_url: "https://cdn.pikar.ai/icons/hubspot.svg",
    scopes: [
      "crm.objects.contacts.read",
      "crm.objects.contacts.write",
      "crm.objects.deals.read",
      "crm.objects.deals.write",
      "crm.objects.companies.read",
    ],
  },
  {
    key: "stripe",
    name: "Stripe",
    auth_type: "oauth2",
    category: "finance_commerce",
    icon_url: "https://cdn.pikar.ai/icons/stripe.svg",
    scopes: ["read_write"],
  },
  {
    key: "shopify",
    name: "Shopify",
    auth_type: "oauth2",
    category: "finance_commerce",
    icon_url: "https://cdn.pikar.ai/icons/shopify.svg",
    scopes: [
      "read_products",
      "read_orders",
      "read_customers",
      "read_analytics",
    ],
  },
  {
    key: "linear",
    name: "Linear",
    auth_type: "oauth2",
    category: "productivity",
    icon_url: "https://cdn.pikar.ai/icons/linear.svg",
    scopes: ["read", "write", "issues:create", "comments:create"],
  },
  {
    key: "asana",
    name: "Asana",
    auth_type: "oauth2",
    category: "productivity",
    icon_url: "https://cdn.pikar.ai/icons/asana.svg",
    scopes: ["default"],
  },
  {
    key: "slack",
    name: "Slack",
    auth_type: "oauth2",
    category: "communication",
    icon_url: "https://cdn.pikar.ai/icons/slack.svg",
    scopes: [
      "channels:read",
      "chat:write",
      "chat:write.public",
      "users:read",
      "files:read",
    ],
  },
  {
    key: "teams",
    name: "Microsoft Teams",
    auth_type: "api_key",
    category: "communication",
    icon_url: "https://cdn.pikar.ai/icons/teams.svg",
    scopes: [],
  },
  {
    key: "postgresql",
    name: "PostgreSQL",
    auth_type: "api_key",
    category: "analytics",
    icon_url: "https://cdn.pikar.ai/icons/postgresql.svg",
    scopes: [],
  },
  {
    key: "bigquery",
    name: "BigQuery",
    auth_type: "oauth2",
    category: "analytics",
    icon_url: "https://cdn.pikar.ai/icons/bigquery.svg",
    scopes: [
      "https://www.googleapis.com/auth/bigquery.readonly",
      "https://www.googleapis.com/auth/cloud-platform.read-only",
    ],
  },
  {
    key: "google_ads",
    name: "Google Ads",
    auth_type: "oauth2",
    category: "analytics",
    icon_url: "https://cdn.pikar.ai/icons/google-ads.svg",
    scopes: ["https://www.googleapis.com/auth/adwords"],
  },
  {
    key: "meta_ads",
    name: "Meta Ads",
    auth_type: "oauth2",
    category: "analytics",
    icon_url: "https://cdn.pikar.ai/icons/meta-ads.svg",
    scopes: ["ads_management", "ads_read", "business_management"],
  },
];

const INTEGRATION_PROVIDER_CONFIGS: Record<string, IntegrationProviderConfig> = {
  hubspot: {
    key: "hubspot",
    name: "HubSpot",
    auth_type: "oauth2",
    category: "crm_sales",
    icon_url: "https://cdn.pikar.ai/icons/hubspot.svg",
    scopes: [
      "crm.objects.contacts.read",
      "crm.objects.contacts.write",
      "crm.objects.deals.read",
      "crm.objects.deals.write",
      "crm.objects.companies.read",
    ],
    auth_url: "https://app.hubspot.com/oauth/authorize",
    token_url: "https://api.hubapi.com/oauth/v1/token",
    client_id_env: "HUBSPOT_CLIENT_ID",
    client_secret_env: "HUBSPOT_CLIENT_SECRET",
  },
  stripe: {
    key: "stripe",
    name: "Stripe",
    auth_type: "oauth2",
    category: "finance_commerce",
    icon_url: "https://cdn.pikar.ai/icons/stripe.svg",
    scopes: ["read_write"],
    auth_url: "https://connect.stripe.com/oauth/authorize",
    token_url: "https://connect.stripe.com/oauth/token",
    client_id_env: "STRIPE_CLIENT_ID",
    client_secret_env: "STRIPE_CLIENT_SECRET",
  },
  shopify: {
    key: "shopify",
    name: "Shopify",
    auth_type: "oauth2",
    category: "finance_commerce",
    icon_url: "https://cdn.pikar.ai/icons/shopify.svg",
    scopes: [
      "read_products",
      "read_orders",
      "read_customers",
      "read_analytics",
    ],
    auth_url: "https://{shop}.myshopify.com/admin/oauth/authorize",
    token_url: "https://{shop}.myshopify.com/admin/oauth/access_token",
    client_id_env: "SHOPIFY_CLIENT_ID",
    client_secret_env: "SHOPIFY_CLIENT_SECRET",
  },
  linear: {
    key: "linear",
    name: "Linear",
    auth_type: "oauth2",
    category: "productivity",
    icon_url: "https://cdn.pikar.ai/icons/linear.svg",
    scopes: ["read", "write", "issues:create", "comments:create"],
    auth_url: "https://linear.app/oauth/authorize",
    token_url: "https://api.linear.app/oauth/token",
    client_id_env: "LINEAR_CLIENT_ID",
    client_secret_env: "LINEAR_CLIENT_SECRET",
  },
  asana: {
    key: "asana",
    name: "Asana",
    auth_type: "oauth2",
    category: "productivity",
    icon_url: "https://cdn.pikar.ai/icons/asana.svg",
    scopes: ["default"],
    auth_url: "https://app.asana.com/-/oauth_authorize",
    token_url: "https://app.asana.com/-/oauth_token",
    client_id_env: "ASANA_CLIENT_ID",
    client_secret_env: "ASANA_CLIENT_SECRET",
  },
  slack: {
    key: "slack",
    name: "Slack",
    auth_type: "oauth2",
    category: "communication",
    icon_url: "https://cdn.pikar.ai/icons/slack.svg",
    scopes: [
      "channels:read",
      "chat:write",
      "chat:write.public",
      "users:read",
      "files:read",
    ],
    auth_url: "https://slack.com/oauth/v2/authorize",
    token_url: "https://slack.com/api/oauth.v2.access",
    client_id_env: "SLACK_CLIENT_ID",
    client_secret_env: "SLACK_CLIENT_SECRET",
  },
  bigquery: {
    key: "bigquery",
    name: "BigQuery",
    auth_type: "oauth2",
    category: "analytics",
    icon_url: "https://cdn.pikar.ai/icons/bigquery.svg",
    scopes: [
      "https://www.googleapis.com/auth/bigquery.readonly",
      "https://www.googleapis.com/auth/cloud-platform.read-only",
    ],
    auth_url: "https://accounts.google.com/o/oauth2/v2/auth",
    token_url: "https://oauth2.googleapis.com/token",
    client_id_env: "BIGQUERY_CLIENT_ID",
    client_secret_env: "BIGQUERY_CLIENT_SECRET",
  },
  google_ads: {
    key: "google_ads",
    name: "Google Ads",
    auth_type: "oauth2",
    category: "analytics",
    icon_url: "https://cdn.pikar.ai/icons/google-ads.svg",
    scopes: ["https://www.googleapis.com/auth/adwords"],
    auth_url: "https://accounts.google.com/o/oauth2/v2/auth",
    token_url: "https://oauth2.googleapis.com/token",
    client_id_env: "GOOGLE_ADS_CLIENT_ID",
    client_secret_env: "GOOGLE_ADS_CLIENT_SECRET",
  },
  meta_ads: {
    key: "meta_ads",
    name: "Meta Ads",
    auth_type: "oauth2",
    category: "analytics",
    icon_url: "https://cdn.pikar.ai/icons/meta-ads.svg",
    scopes: ["ads_management", "ads_read", "business_management"],
    auth_url: "https://www.facebook.com/v19.0/dialog/oauth",
    token_url: "https://graph.facebook.com/v19.0/oauth/access_token",
    client_id_env: "META_ADS_CLIENT_ID",
    client_secret_env: "META_ADS_CLIENT_SECRET",
  },
};

const TIER_ORDER: PersonaTier[] = ["solopreneur", "startup", "sme", "enterprise"];

function hasConfigValue(value: string | undefined): boolean {
  return Boolean(value?.trim());
}

function buildBuiltInToolStatus(env: Env) {
  return BUILT_IN_TOOLS_INFO.map((tool) => {
    const configured =
      tool.id === "tavily"
        ? hasConfigValue(env.TAVILY_API_KEY)
        : hasConfigValue(env.FIRECRAWL_API_KEY);

    return {
      id: tool.id,
      name: tool.name,
      description: tool.description,
      is_built_in: true,
      configured,
      status: configured
        ? "Configured server-side and ready for automatic use"
        : "Bundled in the app, but inactive until its API key is configured",
    };
  });
}

function buildConfigurableToolStatus(env: Env) {
  return CONFIGURABLE_TOOLS_INFO.map((tool) => ({
    id: tool.id,
    name: tool.name,
    description: tool.description,
    configured: hasConfigValue(env[tool.envVar]),
    env_var: tool.envVar,
    docs_url: tool.docsUrl,
    is_built_in: false,
  }));
}

function buildSchedulerReadiness(env: Env) {
  const schedulerSecretConfigured = hasConfigValue(env.SCHEDULER_SECRET);

  return {
    configuration_ready: schedulerSecretConfigured,
    worker_schedule_tick_enabled: true,
    secure_endpoints_enabled: true,
    deployment_required: true,
    status: schedulerSecretConfigured
      ? "App is ready to be deployed for scheduled jobs"
      : "Scheduled jobs need one more configuration step",
    message: schedulerSecretConfigured
      ? "Scheduler authentication is configured and the worker can execute saved report schedules. You still need always-on API and worker services plus an external scheduler for unattended runs."
      : "Add SCHEDULER_SECRET in the server environment to secure scheduled endpoints. The worker-side schedule tick is already wired, but unattended runs still require always-on deployment.",
  };
}

function buildMcpStatusResponse(env: Env) {
  return {
    built_in_tools: buildBuiltInToolStatus(env),
    configurable_tools: buildConfigurableToolStatus(env),
    scheduler_readiness: buildSchedulerReadiness(env),
  };
}

function buildErrorResponse(
  request: Request,
  env: Env,
  status: number,
  body: Record<string, unknown>,
  route: "blocked" | "native" = "native",
): Response {
  const response = Response.json(body, { status });
  const corsHeaders = buildCorsHeaders(request, env);
  corsHeaders.forEach((value, key) => response.headers.set(key, value));
  response.headers.set("x-pikar-public-route", route);
  return response;
}

function isTrustedEdgeRequest(request: Request, env: Env): boolean {
  const expected = env.INTERNAL_PROXY_TOKEN?.trim();
  if (!expected) {
    return false;
  }

  return request.headers.get("x-pikar-edge-token") === expected;
}

function normalizeOrigin(origin: string | undefined, label: string): string {
  const value = origin?.trim();
  if (!value) {
    throw new Error(`${label} is required.`);
  }

  try {
    const url = new URL(value);
    return url.origin;
  } catch {
    throw new Error(`${label} must be a valid absolute URL.`);
  }
}

function buildCorsHeaders(request: Request, env: Env): Headers {
  const headers = new Headers();
  const allowList = (env.ALLOWED_ORIGINS ?? "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);

  const origin = request.headers.get("Origin");
  if (!origin) {
    return headers;
  }

  if (allowList.length === 0 || allowList.includes(origin)) {
    headers.set("Access-Control-Allow-Origin", origin);
    headers.set("Access-Control-Allow-Credentials", "true");
    headers.set("Vary", "Origin");
  }

  return headers;
}

function handlePreflight(request: Request, env: Env): Response {
  const headers = buildCorsHeaders(request, env);
  headers.set("Access-Control-Allow-Methods", "GET,HEAD,POST,PUT,PATCH,DELETE,OPTIONS");
  headers.set(
    "Access-Control-Allow-Headers",
    request.headers.get("Access-Control-Request-Headers") ?? "authorization,content-type",
  );
  headers.set("Access-Control-Max-Age", "86400");

  return new Response(null, { status: 204, headers });
}

function buildLiveResponse() {
  return {
    status: "ok",
    version: "1",
    service: "live",
    latency_ms: 0,
    details: {
      served_by: "cloudflare-public-api",
      layer: "public-origin",
    },
    checked_at: new Date().toISOString(),
  };
}

function buildStartupResponse(env: Env) {
  const fallbackOrigin = normalizeOrigin(
    env.FALLBACK_BACKEND_ORIGIN,
    "FALLBACK_BACKEND_ORIGIN",
  );

  return {
    status: "ready",
    checks: {
      cloudflare_public_api: "ok",
      fallback_origin: fallbackOrigin,
    },
  };
}

function jsonWithCors(data: unknown, request: Request, env: Env): Response {
  const response = Response.json(data);
  const corsHeaders = buildCorsHeaders(request, env);
  corsHeaders.forEach((value, key) => response.headers.set(key, value));
  response.headers.set("x-pikar-public-route", "native");
  return response;
}

function jsonWithCorsStatus(data: unknown, request: Request, env: Env, status: number): Response {
  const response = Response.json(data, { status });
  const corsHeaders = buildCorsHeaders(request, env);
  corsHeaders.forEach((value, key) => response.headers.set(key, value));
  response.headers.set("x-pikar-public-route", "native");
  return response;
}

function noContentWithCors(request: Request, env: Env): Response {
  const headers = buildCorsHeaders(request, env);
  headers.set("x-pikar-public-route", "native");
  return new Response(null, { status: 204, headers });
}

function requireEdgeAccess(request: Request, env: Env): Response | null {
  if (isTrustedEdgeRequest(request, env)) {
    return null;
  }

  return buildErrorResponse(
    request,
    env,
    403,
    {
      ok: false,
      error: "This route is only available through the main API entrypoint.",
    },
    "blocked",
  );
}

function getSupabaseRequestContext(request: Request, env: Env) {
  const supabaseUrl = normalizeOrigin(env.SUPABASE_URL, "SUPABASE_URL");
  const anonKey = env.SUPABASE_ANON_KEY?.trim();
  if (!anonKey) {
    throw new Error("SUPABASE_ANON_KEY is required.");
  }

  const authorization = request.headers.get("authorization")?.trim();
  if (!authorization?.startsWith("Bearer ")) {
    return null;
  }

  return {
    supabaseUrl,
    headers: {
      apikey: anonKey,
      Authorization: authorization,
      Accept: "application/json",
    },
  };
}

async function fetchSupabaseRows<T>(request: Request, env: Env, path: string): Promise<T> {
  const context = getSupabaseRequestContext(request, env);
  if (!context) {
    throw new Response(
      JSON.stringify({ detail: "Invalid authentication credentials" }),
      {
        status: 401,
        headers: { "content-type": "application/json" },
      },
    );
  }

  const response = await fetch(`${context.supabaseUrl}${path}`, {
    method: "GET",
    headers: context.headers,
  });

  if (response.status === 401 || response.status === 403) {
    throw new Response(
      JSON.stringify({ detail: "Invalid authentication credentials" }),
      {
        status: 401,
        headers: { "content-type": "application/json" },
      },
    );
  }

  if (!response.ok) {
    throw new Error(`Supabase request failed with ${response.status}.`);
  }

  return (await response.json()) as T;
}

async function fetchSupabaseUser(
  request: Request,
  env: Env,
): Promise<{
  id?: string | null;
  email?: string | null;
  identities?: Array<{
    provider?: string | null;
    identity_data?: {
      email?: string | null;
    } | null;
  }> | null;
}> {
  const context = getSupabaseRequestContext(request, env);
  if (!context) {
    throw new Response(
      JSON.stringify({ detail: "Invalid authentication credentials" }),
      {
        status: 401,
        headers: { "content-type": "application/json" },
      },
    );
  }

  const response = await fetch(`${context.supabaseUrl}/auth/v1/user`, {
    method: "GET",
    headers: context.headers,
  });

  if (response.status === 401 || response.status === 403) {
    throw new Response(
      JSON.stringify({ detail: "Invalid authentication credentials" }),
      {
        status: 401,
        headers: { "content-type": "application/json" },
      },
    );
  }

  if (!response.ok) {
    throw new Error(`Supabase auth user request failed with ${response.status}.`);
  }

  return (await response.json()) as {
    id?: string | null;
    email?: string | null;
    identities?: Array<{
      provider?: string | null;
      identity_data?: {
        email?: string | null;
      } | null;
    }> | null;
  };
}

async function requireAuthenticatedUserId(request: Request, env: Env): Promise<string> {
  const user = await fetchSupabaseUser(request, env);
  if (!user.id) {
    throw new Response(
      JSON.stringify({ detail: "Invalid authentication credentials" }),
      {
        status: 401,
        headers: { "content-type": "application/json" },
      },
    );
  }

  return user.id;
}

function getSupabaseAdminContext(env: Env) {
  const supabaseUrl = normalizeOrigin(env.SUPABASE_URL, "SUPABASE_URL");
  const serviceRoleKey = env.SUPABASE_SERVICE_ROLE_KEY?.trim();
  if (!serviceRoleKey) {
    throw new Error("SUPABASE_SERVICE_ROLE_KEY is required.");
  }

  return {
    supabaseUrl,
    headers: {
      apikey: serviceRoleKey,
      Authorization: `Bearer ${serviceRoleKey}`,
      Accept: "application/json",
      "Content-Type": "application/json",
    },
  };
}

async function fetchSupabaseAdminRows<T>(env: Env, path: string): Promise<T> {
  const context = getSupabaseAdminContext(env);
  const response = await fetch(`${context.supabaseUrl}${path}`, {
    method: "GET",
    headers: context.headers,
  });

  if (!response.ok) {
    throw new Error(`Supabase admin request failed with ${response.status}.`);
  }

  return (await response.json()) as T;
}

async function insertSupabaseAdminRow<T>(
  env: Env,
  path: string,
  payload: Record<string, unknown>,
): Promise<T> {
  const context = getSupabaseAdminContext(env);
  const headers = new Headers(context.headers);
  headers.set("Prefer", "return=representation");

  const response = await fetch(`${context.supabaseUrl}${path}`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Supabase admin insert failed with ${response.status}.`);
  }

  return (await response.json()) as T;
}

async function deleteSupabaseAdminRows<T>(env: Env, path: string): Promise<T> {
  const context = getSupabaseAdminContext(env);
  const headers = new Headers(context.headers);
  headers.set("Prefer", "return=representation");

  const response = await fetch(`${context.supabaseUrl}${path}`, {
    method: "DELETE",
    headers,
  });

  if (!response.ok) {
    throw new Error(`Supabase admin delete failed with ${response.status}.`);
  }

  return (await response.json()) as T;
}

async function updateSupabaseAdminRows<T>(
  env: Env,
  path: string,
  payload: Record<string, unknown>,
): Promise<T> {
  const context = getSupabaseAdminContext(env);
  const headers = new Headers(context.headers);
  headers.set("Prefer", "return=representation");

  const response = await fetch(`${context.supabaseUrl}${path}`, {
    method: "PATCH",
    headers,
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Supabase admin update failed with ${response.status}.`);
  }

  return (await response.json()) as T;
}

async function upsertSupabaseAdminMergeRow<T>(
  env: Env,
  path: string,
  payload: Record<string, unknown>,
): Promise<T> {
  const context = getSupabaseAdminContext(env);
  const headers = new Headers(context.headers);
  headers.set("Prefer", "resolution=merge-duplicates,return=representation");

  const response = await fetch(`${context.supabaseUrl}${path}`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Supabase admin upsert failed with ${response.status}.`);
  }

  return (await response.json()) as T;
}

async function upsertSupabaseAdminRow<T>(
  env: Env,
  path: string,
  payload: Record<string, unknown>,
): Promise<T> {
  const context = getSupabaseAdminContext(env);
  const headers = new Headers(context.headers);
  headers.set("Prefer", "resolution=ignore-duplicates,return=representation");

  const response = await fetch(`${context.supabaseUrl}${path}`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Supabase admin upsert failed with ${response.status}.`);
  }

  return (await response.json()) as T;
}

async function invokeSupabaseAdminRpc<T>(
  env: Env,
  rpcName: string,
  payload: Record<string, unknown>,
): Promise<T | null> {
  const context = getSupabaseAdminContext(env);
  const response = await fetch(`${context.supabaseUrl}/rest/v1/rpc/${rpcName}`, {
    method: "POST",
    headers: context.headers,
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Supabase admin rpc '${rpcName}' failed with ${response.status}.`);
  }

  if (response.status === 204) {
    return null;
  }

  const text = await response.text();
  if (!text) {
    return null;
  }

  return JSON.parse(text) as T;
}

async function fetchSupabaseAdminAuthUser(
  env: Env,
  userId: string,
): Promise<Record<string, unknown> | null> {
  const context = getSupabaseAdminContext(env);
  const response = await fetch(`${context.supabaseUrl}/auth/v1/admin/users/${encodeURIComponent(userId)}`, {
    method: "GET",
    headers: context.headers,
  });

  if (!response.ok) {
    throw new Error(`Supabase admin auth user request failed with ${response.status}.`);
  }

  const parsed = asRecord(await response.json());
  return asRecord(parsed?.user ?? null);
}

async function uploadSupabaseStorageObject(
  env: Env,
  bucket: string,
  objectPath: string,
  bytes: Uint8Array,
  contentType: string,
): Promise<void> {
  const context = getSupabaseAdminContext(env);
  const headers = new Headers({
    apikey: context.headers.apikey,
    Authorization: context.headers.Authorization,
    "Content-Type": contentType,
    "x-upsert": "true",
  });

  const response = await fetch(
    `${context.supabaseUrl}/storage/v1/object/${bucket}/${objectPath}`,
    {
      method: "POST",
      headers,
      body: bytes,
    },
  );

  if (!response.ok) {
    throw new Error(`Supabase storage upload failed with ${response.status}.`);
  }
}

async function createSupabaseStorageSignedUrl(
  env: Env,
  bucket: string,
  objectPath: string,
  expiresIn: number,
): Promise<string> {
  const context = getSupabaseAdminContext(env);
  const response = await fetch(
    `${context.supabaseUrl}/storage/v1/object/sign/${bucket}/${objectPath}`,
    {
      method: "POST",
      headers: context.headers,
      body: JSON.stringify({ expiresIn }),
    },
  );

  if (!response.ok) {
    throw new Error(`Supabase storage signed URL creation failed with ${response.status}.`);
  }

  const payload = asRecord(await response.json());
  const rawSignedUrl = typeof payload?.signedURL === "string"
    ? payload.signedURL
    : typeof payload?.signedUrl === "string"
      ? payload.signedUrl
      : "";
  if (!rawSignedUrl) {
    throw new Error("Supabase storage signed URL response was missing signedURL.");
  }

  if (/^https?:\/\//i.test(rawSignedUrl)) {
    return rawSignedUrl;
  }

  const origin = new URL(context.supabaseUrl).origin;
  if (rawSignedUrl.startsWith("/storage/v1/")) {
    return `${origin}${rawSignedUrl}`;
  }

  if (rawSignedUrl.startsWith("/object/")) {
    return `${origin}/storage/v1${rawSignedUrl}`;
  }

  return `${origin}/storage/v1/${rawSignedUrl.replace(/^\/+/, "")}`;
}

function randomBase64Url(byteLength: number): string {
  const bytes = crypto.getRandomValues(new Uint8Array(byteLength));
  return btoa(String.fromCharCode(...bytes))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/g, "");
}

function normalizeInviteRole(value: unknown): "editor" | "viewer" | null {
  if (typeof value !== "string") {
    return null;
  }

  const normalized = value.trim().toLowerCase();
  if (normalized === "editor" || normalized === "viewer") {
    return normalized;
  }

  return null;
}

function normalizeOptionalEmail(value: unknown): string | null {
  if (typeof value !== "string") {
    return null;
  }

  const normalized = value.trim().toLowerCase();
  if (!normalized || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalized)) {
    return null;
  }

  return normalized;
}

function normalizeOptionalText(value: unknown): string | null {
  if (typeof value !== "string") {
    return null;
  }

  const normalized = value.trim();
  return normalized ? normalized : null;
}

function requireTextField(
  payload: Record<string, unknown>,
  field: string,
  request: Request,
  env: Env,
): string {
  const value = normalizeOptionalText(payload[field]);
  if (!value) {
    throw buildErrorResponse(request, env, 400, {
      detail: `${field} is required`,
    });
  }

  return value;
}

function normalizeStringArrayField(
  payload: Record<string, unknown>,
  field: string,
  request: Request,
  env: Env,
): string[] {
  const value = payload[field];
  if (!Array.isArray(value)) {
    throw buildErrorResponse(request, env, 400, {
      detail: `${field} must be an array of strings`,
    });
  }

  const normalized = value
    .map((item) => (typeof item === "string" ? item.trim() : ""))
    .filter(Boolean);
  if (normalized.length !== value.length) {
    throw buildErrorResponse(request, env, 400, {
      detail: `${field} must be an array of strings`,
    });
  }

  return normalized;
}

function normalizeOptionalStringArray(value: unknown): string[] | null {
  if (value === null || value === undefined) {
    return null;
  }

  if (!Array.isArray(value)) {
    return null;
  }

  const normalized = value
    .map((item) => (typeof item === "string" ? item.trim() : ""))
    .filter(Boolean);
  return normalized.length === value.length ? normalized : null;
}

function hasNonEmptyJsonValue(value: unknown): boolean {
  if (Array.isArray(value)) {
    return value.length > 0;
  }

  const record = asRecord(value);
  if (!record) {
    return false;
  }

  return Object.keys(record).length > 0;
}

function determineOnboardingPersona(context: BusinessContextPayload): PersonaTier {
  const size = (context.team_size ?? "").toLowerCase();
  const role = (context.role ?? "").toLowerCase();
  const industry = context.industry.toLowerCase();

  if (size === "solo") {
    return "solopreneur";
  }
  if (size === "enterprise") {
    return "enterprise";
  }
  if (size === "sme-small" || size === "sme-large") {
    return "sme";
  }
  if (size === "startup") {
    return "startup";
  }

  if (size.includes("200+") || size.includes("enterprise") || size.includes("500+")) {
    return "enterprise";
  }
  if (
    industry.includes("corporate") &&
    (role.includes("vp") || role.includes("chief") || role.includes("head"))
  ) {
    return "enterprise";
  }

  if (size.includes("51-200")) {
    return "sme";
  }
  if (size.includes("11-50") && industry.includes("manufacturing")) {
    return "sme";
  }

  if (
    size === "1" ||
    size === "just me" ||
    size === "freelancer" ||
    size === "solopreneur"
  ) {
    return "solopreneur";
  }
  if (role.includes("freelance") || role.includes("consultant")) {
    return "solopreneur";
  }

  return "startup";
}

async function ensureOnboardingSeedRows(env: Env, userId: string): Promise<void> {
  const now = new Date().toISOString();

  await upsertSupabaseAdminRow<Array<Record<string, unknown>>>(
    env,
    "/rest/v1/users_profile?on_conflict=user_id&select=user_id",
    {
      user_id: userId,
      storage_bucket_id: "user-content",
      storage_path_prefix: `${userId}/`,
      created_at: now,
      updated_at: now,
    },
  );

  await upsertSupabaseAdminRow<Array<Record<string, unknown>>>(
    env,
    "/rest/v1/user_executive_agents?on_conflict=user_id&select=user_id",
    {
      user_id: userId,
      onboarding_completed: false,
      created_at: now,
      updated_at: now,
    },
  );
}

async function fetchOnboardingProfileRow(env: Env, userId: string): Promise<Record<string, unknown>> {
  const params = new URLSearchParams({
    select: "user_id,persona,business_context,preferences",
    user_id: `eq.${userId}`,
    limit: "1",
  });
  const rows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/users_profile?${params.toString()}`,
  );
  return asRecord(rows[0]) ?? {};
}

async function fetchOnboardingAgentRow(env: Env, userId: string): Promise<Record<string, unknown>> {
  const params = new URLSearchParams({
    select: "user_id,agent_name,onboarding_completed,configuration,persona",
    user_id: `eq.${userId}`,
    limit: "1",
  });
  const rows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/user_executive_agents?${params.toString()}`,
  );
  return asRecord(rows[0]) ?? {};
}

function parseBusinessContextPayload(
  payload: Record<string, unknown>,
  request: Request,
  env: Env,
): BusinessContextPayload {
  return {
    company_name: requireTextField(payload, "company_name", request, env),
    industry: requireTextField(payload, "industry", request, env),
    description: requireTextField(payload, "description", request, env),
    goals: normalizeStringArrayField(payload, "goals", request, env),
    team_size: normalizeOptionalText(payload.team_size),
    role: normalizeOptionalText(payload.role),
    website: normalizeOptionalText(payload.website),
  };
}

function parseUserPreferencesPayload(
  payload: Record<string, unknown>,
  request: Request,
  env: Env,
): UserPreferencesPayload {
  const normalizeOrThrow = (field: keyof UserPreferencesPayload, fallback: string) => {
    const value = payload[field];
    if (value === undefined || value === null) {
      return fallback;
    }

    const normalized = normalizeOptionalText(value);
    if (!normalized) {
      throw buildErrorResponse(request, env, 400, {
        detail: `${field} must be a non-empty string`,
      });
    }

    return normalized;
  };

  return {
    tone: normalizeOrThrow("tone", DEFAULT_ONBOARDING_PREFERENCES.tone),
    verbosity: normalizeOrThrow("verbosity", DEFAULT_ONBOARDING_PREFERENCES.verbosity),
    communication_style: normalizeOrThrow(
      "communication_style",
      DEFAULT_ONBOARDING_PREFERENCES.communication_style,
    ),
    notification_frequency: normalizeOrThrow(
      "notification_frequency",
      DEFAULT_ONBOARDING_PREFERENCES.notification_frequency,
    ),
  };
}

function parseAgentSetupPayload(
  payload: Record<string, unknown>,
  request: Request,
  env: Env,
): AgentSetupPayload {
  const agentName = requireTextField(payload, "agent_name", request, env);
  const focusAreas = normalizeOptionalStringArray(payload.focus_areas);
  if (payload.focus_areas !== undefined && payload.focus_areas !== null && !focusAreas) {
    throw buildErrorResponse(request, env, 400, {
      detail: "focus_areas must be an array of strings",
    });
  }

  return {
    agent_name: agentName,
    focus_areas: focusAreas,
  };
}

function parseOnboardingExtractContextPayload(
  payload: Record<string, unknown>,
  request: Request,
  env: Env,
): OnboardingExtractContextPayload {
  const rawMessages = payload.messages;
  if (!Array.isArray(rawMessages)) {
    throw buildErrorResponse(request, env, 422, {
      detail: "messages must be an array of strings",
    });
  }

  if (rawMessages.length > 50) {
    throw buildErrorResponse(request, env, 422, {
      detail: "messages must contain at most 50 entries",
    });
  }

  const sanitizedMessages = rawMessages.map((message, index) => {
    if (typeof message !== "string") {
      throw buildErrorResponse(request, env, 422, {
        detail: "messages must be an array of strings",
      });
    }

    if (message.length > 10000) {
      throw buildErrorResponse(request, env, 422, {
        detail: `Message ${index} exceeds 10000 character limit`,
      });
    }

    return message.replace(/```/g, "'''");
  });

  return { messages: sanitizedMessages };
}

function normalizeSupportTicketPriority(value: unknown): SupportTicketPriority | null {
  if (typeof value !== "string") {
    return null;
  }

  const normalized = value.trim().toLowerCase();
  return SUPPORT_TICKET_PRIORITIES.includes(normalized as SupportTicketPriority)
    ? (normalized as SupportTicketPriority)
    : null;
}

function normalizeSupportTicketStatus(value: unknown): SupportTicketStatus | null {
  if (typeof value !== "string") {
    return null;
  }

  const normalized = value.trim().toLowerCase();
  return SUPPORT_TICKET_STATUSES.includes(normalized as SupportTicketStatus)
    ? (normalized as SupportTicketStatus)
    : null;
}

function normalizeSupportTicketRecord(record: Record<string, unknown>): SupportTicketRecord {
  const createdAt =
    typeof record.created_at === "string" ? record.created_at : new Date().toISOString();
  const updatedAt = typeof record.updated_at === "string" ? record.updated_at : createdAt;

  return {
    id: typeof record.id === "string" ? record.id : "",
    user_id: typeof record.user_id === "string" ? record.user_id : "",
    subject: typeof record.subject === "string" ? record.subject : "",
    description: typeof record.description === "string" ? record.description : "",
    customer_email: typeof record.customer_email === "string" ? record.customer_email : "",
    priority: normalizeSupportTicketPriority(record.priority) ?? "normal",
    status: normalizeSupportTicketStatus(record.status) ?? "new",
    assigned_to: typeof record.assigned_to === "string" ? record.assigned_to : null,
    resolution: typeof record.resolution === "string" ? record.resolution : null,
    created_at: createdAt,
    updated_at: updatedAt,
  };
}

function parseCreateSupportTicketPayload(
  payload: Record<string, unknown>,
  request: Request,
  env: Env,
) {
  const subject = requireTextField(payload, "subject", request, env);
  const description = requireTextField(payload, "description", request, env);
  const customerEmail = normalizeOptionalEmail(payload.customer_email);
  if (!customerEmail) {
    throw buildErrorResponse(request, env, 400, {
      detail: "customer_email is required",
    });
  }

  return {
    subject,
    description,
    customer_email: customerEmail,
    priority: normalizeSupportTicketPriority(payload.priority) ?? "normal",
  };
}

function parseUpdateSupportTicketPayload(
  payload: Record<string, unknown>,
  request: Request,
  env: Env,
): Record<string, unknown> {
  const update: Record<string, unknown> = {};

  if (payload.status !== undefined) {
    const status = normalizeSupportTicketStatus(payload.status);
    if (!status) {
      throw buildErrorResponse(request, env, 400, {
        detail: "status must be one of new, open, in_progress, waiting, resolved, closed",
      });
    }
    update.status = status;
  }

  if (payload.priority !== undefined) {
    const priority = normalizeSupportTicketPriority(payload.priority);
    if (!priority) {
      throw buildErrorResponse(request, env, 400, {
        detail: "priority must be one of low, normal, high, urgent",
      });
    }
    update.priority = priority;
  }

  if (payload.assigned_to !== undefined) {
    const assignedTo = normalizeOptionalText(payload.assigned_to);
    if (payload.assigned_to !== null && !assignedTo) {
      throw buildErrorResponse(request, env, 400, {
        detail: "assigned_to must be a non-empty string or null",
      });
    }
    if (assignedTo) {
      update.assigned_to = assignedTo;
    }
  }

  if (payload.resolution !== undefined) {
    const resolution = normalizeOptionalText(payload.resolution);
    if (payload.resolution !== null && !resolution) {
      throw buildErrorResponse(request, env, 400, {
        detail: "resolution must be a non-empty string or null",
      });
    }
    if (resolution) {
      update.resolution = resolution;
    }
  }

  if (Object.keys(update).length === 0) {
    throw buildErrorResponse(request, env, 400, {
      detail: "At least one updatable field is required",
    });
  }

  return update;
}

function normalizeStringArrayValues(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.filter((item): item is string => typeof item === "string");
}

function normalizeCommunityPostRecord(record: Record<string, unknown>): CommunityPostRecord {
  return {
    id: typeof record.id === "string" ? record.id : "",
    user_id: typeof record.user_id === "string" ? record.user_id : "",
    author_name: typeof record.author_name === "string" ? record.author_name : "Anonymous",
    title: typeof record.title === "string" ? record.title : "",
    body: typeof record.body === "string" ? record.body : "",
    category: typeof record.category === "string" ? record.category : "general",
    tags: normalizeStringArrayValues(record.tags),
    upvotes: typeof record.upvotes === "number" ? record.upvotes : 0,
    reply_count: typeof record.reply_count === "number" ? record.reply_count : 0,
    is_pinned: record.is_pinned === true,
    created_at: typeof record.created_at === "string" ? record.created_at : new Date().toISOString(),
    updated_at:
      typeof record.updated_at === "string"
        ? record.updated_at
        : typeof record.created_at === "string"
          ? record.created_at
          : new Date().toISOString(),
  };
}

function normalizeCommunityCommentRecord(record: Record<string, unknown>): CommunityCommentRecord {
  return {
    id: typeof record.id === "string" ? record.id : "",
    post_id: typeof record.post_id === "string" ? record.post_id : "",
    user_id: typeof record.user_id === "string" ? record.user_id : "",
    author_name: typeof record.author_name === "string" ? record.author_name : "Anonymous",
    body: typeof record.body === "string" ? record.body : "",
    upvotes: typeof record.upvotes === "number" ? record.upvotes : 0,
    created_at: typeof record.created_at === "string" ? record.created_at : new Date().toISOString(),
  };
}

async function resolveCommunityAuthorName(env: Env, userId: string): Promise<string> {
  const rows = await fetchSupabaseAdminRows<Array<{ full_name?: string | null }>>(
    env,
    `/rest/v1/users_profile?user_id=eq.${userId}&select=full_name&limit=1`,
  );

  const fullName = rows[0]?.full_name;
  return typeof fullName === "string" && fullName.trim() ? fullName.trim() : "Anonymous";
}

function parseCreateCommunityPostPayload(
  payload: Record<string, unknown>,
  request: Request,
  env: Env,
): {
  title: string;
  body: string;
  category: string;
  tags: string[];
} {
  const title = requireTextField(payload, "title", request, env);
  if (title.length > 200) {
    throw buildErrorResponse(request, env, 400, {
      detail: "title must be 200 characters or fewer",
    });
  }

  const body = requireTextField(payload, "body", request, env);
  if (body.length > 10000) {
    throw buildErrorResponse(request, env, 400, {
      detail: "body must be 10000 characters or fewer",
    });
  }

  const category = normalizeOptionalText(payload.category) ?? "general";
  if (category.length > 50) {
    throw buildErrorResponse(request, env, 400, {
      detail: "category must be 50 characters or fewer",
    });
  }

  const rawTags = payload.tags;
  if (rawTags !== undefined && rawTags !== null && !Array.isArray(rawTags)) {
    throw buildErrorResponse(request, env, 400, {
      detail: "tags must be an array of strings",
    });
  }

  const tags = (rawTags ?? []).map((tag) => (typeof tag === "string" ? tag.trim() : ""));
  if (tags.some((tag) => !tag || tag.length > 50)) {
    throw buildErrorResponse(request, env, 400, {
      detail: "Each tag must be between 1 and 50 characters",
    });
  }
  if (tags.length > 10) {
    throw buildErrorResponse(request, env, 400, {
      detail: "tags must contain at most 10 entries",
    });
  }

  return {
    title,
    body,
    category,
    tags,
  };
}

function parseCreateCommunityCommentPayload(
  payload: Record<string, unknown>,
  request: Request,
  env: Env,
): { body: string } {
  const body = requireTextField(payload, "body", request, env);
  if (body.length > 5000) {
    throw buildErrorResponse(request, env, 400, {
      detail: "body must be 5000 characters or fewer",
    });
  }

  return { body };
}

function normalizeLandingPageRecord(record: Record<string, unknown>): LandingPageRecord {
  const metadata = asRecord(record.metadata) ?? {};
  const submissionCount =
    typeof record.submission_count === "number"
      ? record.submission_count
      : typeof record.submission_count === "string"
        ? Number.parseInt(record.submission_count, 10) || 0
        : 0;
  return {
    id: typeof record.id === "string" ? record.id : "",
    user_id: typeof record.user_id === "string" ? record.user_id : "",
    title: typeof record.title === "string" ? record.title : "",
    slug: typeof record.slug === "string" ? record.slug : "",
    html_content: typeof record.html_content === "string" ? record.html_content : "",
    published: record.published === true,
    published_at: typeof record.published_at === "string" ? record.published_at : null,
    created_at: typeof record.created_at === "string" ? record.created_at : new Date().toISOString(),
    updated_at:
      typeof record.updated_at === "string"
        ? record.updated_at
        : typeof record.created_at === "string"
          ? record.created_at
          : new Date().toISOString(),
    metadata,
    submission_count: submissionCount,
  };
}

function normalizeOutboundWebhookEndpointRecord(
  record: Record<string, unknown>,
): OutboundWebhookEndpointRecord {
  const rawEvents = Array.isArray(record.events) ? record.events : [];
  return {
    id: typeof record.id === "string" ? record.id : "",
    user_id: typeof record.user_id === "string" ? record.user_id : "",
    url: typeof record.url === "string" ? record.url : "",
    events: rawEvents.filter((value): value is string => typeof value === "string"),
    active: typeof record.active === "boolean" ? record.active : true,
    consecutive_failures:
      typeof record.consecutive_failures === "number" ? record.consecutive_failures : 0,
    disabled_at: typeof record.disabled_at === "string" ? record.disabled_at : null,
    created_at: typeof record.created_at === "string" ? record.created_at : new Date().toISOString(),
    updated_at: typeof record.updated_at === "string" ? record.updated_at : null,
    description: typeof record.description === "string" ? record.description : null,
    secret: typeof record.secret === "string" ? record.secret : null,
  };
}

function normalizeOutboundWebhookDeliveryRecord(
  record: Record<string, unknown>,
): OutboundWebhookDeliveryRecord {
  return {
    id: typeof record.id === "string" ? record.id : "",
    endpoint_id: typeof record.endpoint_id === "string" ? record.endpoint_id : "",
    event_type: typeof record.event_type === "string" ? record.event_type : "",
    status: typeof record.status === "string" ? record.status : "pending",
    attempts: typeof record.attempts === "number" ? record.attempts : 0,
    response_code: typeof record.response_code === "number" ? record.response_code : null,
    created_at:
      typeof record.created_at === "string" ? record.created_at : new Date().toISOString(),
  };
}

function normalizeFinanceInvoiceRecord(record: Record<string, unknown>): FinanceInvoiceRecord {
  const metadata = asRecord(record.metadata) ?? {};
  const rawAmount = metadata.total_amount ?? metadata.amount ?? 0;
  const amount =
    typeof rawAmount === "number"
      ? rawAmount
      : typeof rawAmount === "string"
        ? Number.parseFloat(rawAmount) || 0
        : 0;

  return {
    id: typeof record.id === "string" ? record.id : "",
    user_id: typeof record.user_id === "string" ? record.user_id : "",
    invoice_number: typeof record.invoice_number === "string" ? record.invoice_number : null,
    client_name:
      typeof metadata.customer_name === "string"
        ? metadata.customer_name
        : typeof metadata.client_name === "string"
          ? metadata.client_name
          : null,
    client_email:
      typeof metadata.customer_email === "string"
        ? metadata.customer_email
        : typeof metadata.client_email === "string"
          ? metadata.client_email
          : null,
    amount,
    currency: typeof metadata.currency === "string" ? metadata.currency : "USD",
    status: typeof record.status === "string" ? record.status : "draft",
    due_date: typeof record.due_date === "string" ? record.due_date : null,
    paid_at: typeof metadata.paid_at === "string" ? metadata.paid_at : null,
    created_at: typeof record.created_at === "string" ? record.created_at : new Date().toISOString(),
    updated_at:
      typeof record.updated_at === "string"
        ? record.updated_at
        : typeof record.created_at === "string"
          ? record.created_at
          : new Date().toISOString(),
  };
}

function normalizeFinanceAssumptionRecord(record: Record<string, unknown>): FinanceAssumptionRecord {
  return {
    id: typeof record.id === "string" ? record.id : "",
    assumption_type: typeof record.assumption_type === "string" ? record.assumption_type : "",
    key: typeof record.assumption_key === "string" ? record.assumption_key : "",
    label: typeof record.label === "string" ? record.label : "",
    value: record.value ?? null,
    is_active: record.is_active === true,
    created_at: typeof record.created_at === "string" ? record.created_at : new Date().toISOString(),
  };
}

function normalizeSalesConnectedAccountRecord(
  record: Record<string, unknown>,
): SalesConnectedAccountResponse {
  const metadata = asRecord(record.metadata) ?? {};

  return {
    id: typeof record.id === "string" ? record.id : "",
    user_id: typeof record.user_id === "string" ? record.user_id : "",
    platform: typeof record.platform === "string" ? record.platform : "",
    account_name:
      typeof metadata.account_name === "string"
        ? metadata.account_name
        : typeof record.platform_username === "string"
          ? record.platform_username
          : null,
    account_id:
      typeof metadata.account_id === "string"
        ? metadata.account_id
        : typeof record.platform_user_id === "string"
          ? record.platform_user_id
          : null,
    status: typeof record.status === "string" ? record.status : "active",
    connected_at: typeof record.connected_at === "string" ? record.connected_at : null,
    last_synced_at:
      typeof metadata.last_synced_at === "string"
        ? metadata.last_synced_at
        : typeof record.last_used_at === "string"
          ? record.last_used_at
          : typeof record.connected_at === "string"
            ? record.connected_at
            : null,
  };
}

function normalizeSalesCampaignRecord(record: Record<string, unknown>): SalesCampaignResponse {
  const metrics = asRecord(record.metrics);
  const schedule: Record<string, unknown> = {};
  if (typeof record.schedule_start === "string") {
    schedule.start = record.schedule_start;
  }
  if (typeof record.schedule_end === "string") {
    schedule.end = record.schedule_end;
  }

  return {
    id: typeof record.id === "string" ? record.id : "",
    name: typeof record.name === "string" ? record.name : "",
    type: typeof record.campaign_type === "string" ? record.campaign_type : null,
    target_audience: typeof record.target_audience === "string" ? record.target_audience : null,
    status: typeof record.status === "string" ? record.status : "draft",
    schedule,
    metrics,
    created_at: typeof record.created_at === "string" ? record.created_at : new Date().toISOString(),
  };
}

function inferAnalyticsPlatform(record: Record<string, unknown>): string | null {
  const utmSource = typeof record.utm_source === "string" ? record.utm_source.trim().toLowerCase() : "";
  if (utmSource) {
    return utmSource;
  }

  const referrer = typeof record.referrer === "string" ? record.referrer.trim().toLowerCase() : "";
  if (!referrer) {
    return null;
  }

  const platformMatchers: Array<[string, RegExp]> = [
    ["linkedin", /linkedin/],
    ["twitter", /twitter|x\\.com/],
    ["facebook", /facebook/],
    ["instagram", /instagram/],
    ["youtube", /youtube/],
    ["tiktok", /tiktok/],
  ];

  for (const [platform, pattern] of platformMatchers) {
    if (pattern.test(referrer)) {
      return platform;
    }
  }

  return null;
}

function normalizeSalesPageAnalyticsRecords(
  records: Array<Record<string, unknown>>,
): SalesPageAnalyticsResponse[] {
  const aggregates = new Map<
    string,
    {
      id: string;
      page_url: string | null;
      platform: string | null;
      views: number;
      clicks: number;
      conversions: number;
      created_at: string;
    }
  >();

  for (const record of records) {
    const pageUrl = typeof record.page_url === "string" ? record.page_url : null;
    const platform = inferAnalyticsPlatform(record);
    const key = `${pageUrl ?? ""}::${platform ?? ""}`;
    const createdAt =
      typeof record.created_at === "string" ? record.created_at : new Date(0).toISOString();
    const eventType =
      typeof record.event_type === "string" ? record.event_type.trim().toLowerCase() : "pageview";

    const current =
      aggregates.get(key) ?? {
        id: typeof record.id === "string" ? record.id : crypto.randomUUID(),
        page_url: pageUrl,
        platform,
        views: 0,
        clicks: 0,
        conversions: 0,
        created_at: createdAt,
      };

    if (createdAt > current.created_at) {
      current.created_at = createdAt;
    }

    if (eventType === "pageview") {
      current.views += 1;
    } else if (eventType === "click" || eventType === "cta_click") {
      current.clicks += 1;
    } else if (eventType === "form_submit" || eventType === "conversion" || eventType === "purchase") {
      current.conversions += 1;
    } else {
      current.views += 1;
    }

    aggregates.set(key, current);
  }

  return Array.from(aggregates.values())
    .sort((left, right) => right.created_at.localeCompare(left.created_at))
    .map((aggregate) => {
      const denominator = aggregate.views > 0 ? aggregate.views : aggregate.clicks + aggregate.conversions;
      const engagementRate =
        denominator > 0 ? ((aggregate.clicks + aggregate.conversions) / denominator) * 100 : 0;

      return {
        id: aggregate.id,
        page_url: aggregate.page_url,
        platform: aggregate.platform,
        views: aggregate.views,
        clicks: aggregate.clicks,
        conversions: aggregate.conversions,
        engagement_rate: Number(engagementRate.toFixed(2)),
        created_at: aggregate.created_at,
      };
    });
}

function normalizeContentBundleRecord(record: Record<string, unknown>): ContentBundleResponse {
  const metadata = asRecord(record.metadata) ?? {};

  return {
    id: typeof record.id === "string" ? record.id : "",
    user_id: typeof record.user_id === "string" ? record.user_id : "",
    title: typeof record.title === "string" ? record.title : "",
    bundle_type: typeof record.bundle_type === "string" ? record.bundle_type : null,
    status: typeof record.status === "string" ? record.status : "draft",
    description:
      typeof metadata.description === "string"
        ? metadata.description
        : typeof record.prompt === "string"
          ? record.prompt
          : null,
    target_date:
      typeof metadata.target_date === "string"
        ? metadata.target_date
        : typeof metadata.scheduled_for === "string"
          ? metadata.scheduled_for
          : null,
    published_at:
      typeof metadata.published_at === "string"
        ? metadata.published_at
        : typeof metadata.last_published_at === "string"
          ? metadata.last_published_at
          : null,
    created_at: typeof record.created_at === "string" ? record.created_at : new Date().toISOString(),
    updated_at:
      typeof record.updated_at === "string"
        ? record.updated_at
        : typeof record.created_at === "string"
          ? record.created_at
          : new Date().toISOString(),
  };
}

function normalizeContentDeliverableRecord(
  record: Record<string, unknown>,
): ContentDeliverableResponse {
  const metadata = asRecord(record.metadata) ?? {};

  return {
    id: typeof record.id === "string" ? record.id : "",
    bundle_id: typeof record.bundle_id === "string" ? record.bundle_id : "",
    title: typeof record.title === "string" ? record.title : "",
    type: typeof record.asset_type === "string" ? record.asset_type : null,
    status:
      typeof metadata.status === "string"
        ? metadata.status
        : typeof record.variant_label === "string"
          ? record.variant_label
          : "ready",
    platform:
      typeof record.platform_profile === "string"
        ? record.platform_profile
        : typeof metadata.platform_profile === "string"
          ? metadata.platform_profile
          : typeof metadata.platform === "string"
            ? metadata.platform
            : null,
    content_url:
      typeof record.file_url === "string"
        ? record.file_url
        : typeof record.editable_url === "string"
          ? record.editable_url
          : null,
    created_at: typeof record.created_at === "string" ? record.created_at : new Date().toISOString(),
  };
}

function buildLandingPageUrl(request: Request, env: Env, slug: string): string {
  return new URL(`/landing/${slug}`, resolvePublicAppOrigin(request, env)).toString();
}

function slugifyLandingPageTitle(title: string): string {
  const normalized = title.toLowerCase().replace(/\s+/g, "-");
  return normalized.replace(/[^a-z0-9-]/g, "").replace(/-+/g, "-").replace(/^-|-$/g, "") || "page";
}

function injectLandingPageSeo(title: string, htmlContent: string): string {
  if (htmlContent.includes('<meta name="description"') || !htmlContent.includes("<head>")) {
    return htmlContent;
  }

  const seoTags =
    `<meta name="description" content="${title}">\n` +
    `<meta property="og:title" content="${title}">\n` +
    '<meta property="og:type" content="website">\n';
  return htmlContent.replace("<head>", `<head>\n${seoTags}`);
}

function parsePageImportPayload(
  payload: Record<string, unknown>,
  request: Request,
  env: Env,
): { title: string; html_content: string; source: string } {
  const title = requireTextField(payload, "title", request, env);
  const htmlContent = requireTextField(payload, "html_content", request, env);
  const source = normalizeOptionalText(payload.source) ?? "import";
  return {
    title,
    html_content: htmlContent,
    source,
  };
}

function parsePageUpdatePayload(
  payload: Record<string, unknown>,
  request: Request,
  env: Env,
): Record<string, unknown> {
  const update: Record<string, unknown> = {};

  if (payload.title !== undefined) {
    update.title = requireTextField(payload, "title", request, env);
  }

  if (payload.html_content !== undefined) {
    if (typeof payload.html_content !== "string") {
      throw buildErrorResponse(request, env, 400, {
        detail: "html_content must be a string",
      });
    }
    update.html_content = payload.html_content;
  }

  if (payload.slug !== undefined) {
    update.slug = requireTextField(payload, "slug", request, env);
  }

  if (payload.metadata !== undefined) {
    if (payload.metadata !== null && !asRecord(payload.metadata)) {
      throw buildErrorResponse(request, env, 400, {
        detail: "metadata must be an object or null",
      });
    }
    update.metadata = payload.metadata;
  }

  if (Object.keys(update).length === 0) {
    throw buildErrorResponse(request, env, 400, {
      detail: "No fields to update",
    });
  }

  return update;
}

function isSupabaseStatusError(error: unknown, status: number): boolean {
  return error instanceof Error && error.message.includes(` ${status}.`);
}

function isApprovalStatus(value: string | null | undefined): value is ApprovalStatus {
  return value === "PENDING" || value === "APPROVED" || value === "REJECTED" || value === "EXPIRED";
}

function normalizeApprovalRequestRecord(record: Record<string, unknown>): ApprovalRequestRecord {
  const payload = asRecord(record.payload) ?? {};
  const rawStatus = typeof record.status === "string" ? record.status : "PENDING";
  return {
    id: typeof record.id === "string" ? record.id : "",
    action_type: typeof record.action_type === "string" ? record.action_type : "",
    payload,
    status: isApprovalStatus(rawStatus) ? rawStatus : "PENDING",
    created_at: typeof record.created_at === "string" ? record.created_at : new Date().toISOString(),
    expires_at: typeof record.expires_at === "string" ? record.expires_at : new Date().toISOString(),
    responded_at: typeof record.responded_at === "string" ? record.responded_at : null,
    token: typeof record.token === "string" ? record.token : null,
    user_id: typeof record.user_id === "string" ? record.user_id : null,
  };
}

async function hashApprovalToken(token: string): Promise<string> {
  return sha256Hex(new TextEncoder().encode(token));
}

function generateApprovalToken(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(32));
  return toBase64Url(bytes);
}

function extractApprovalRequesterUserId(row: ApprovalRequestRecord): string | null {
  if (row.user_id) {
    return row.user_id;
  }

  for (const key of ["requester_user_id", "user_id"] as const) {
    const value = row.payload[key];
    if (typeof value === "string" && value.trim()) {
      return value;
    }
  }

  return null;
}

async function fetchApprovalRowByTokenHash(
  env: Env,
  tokenHash: string,
): Promise<ApprovalRequestRecord | null> {
  const rows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/approval_requests?token=eq.${encodeURIComponent(tokenHash)}&select=id,action_type,payload,status,created_at,expires_at,responded_at,user_id&limit=1`,
  );
  const row = asRecord(rows[0]) ?? null;
  return row ? normalizeApprovalRequestRecord(row) : null;
}

async function fetchApprovalRowById(
  env: Env,
  approvalId: string,
): Promise<ApprovalRequestRecord | null> {
  const rows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/approval_requests?id=eq.${encodeURIComponent(approvalId)}&select=id,action_type,payload,status,created_at,expires_at,responded_at,user_id&limit=1`,
  );
  const row = asRecord(rows[0]) ?? null;
  return row ? normalizeApprovalRequestRecord(row) : null;
}

async function fetchUserApprovalRows(
  env: Env,
  userId: string,
  options: {
    statusEq?: ApprovalStatus;
    statusNeq?: ApprovalStatus;
    limit?: number;
    offset?: number;
  },
): Promise<ApprovalRequestRecord[]> {
  const params = new URLSearchParams({
    select: "id,action_type,payload,status,created_at,expires_at,responded_at,user_id",
    order: "created_at.desc",
  });
  if (options.statusEq) {
    params.set("status", `eq.${options.statusEq}`);
  }
  if (options.statusNeq) {
    params.set("status", `neq.${options.statusNeq}`);
  }
  if (options.limit !== undefined) {
    params.set("limit", String(options.limit));
  }
  if (options.offset !== undefined) {
    params.set("offset", String(options.offset));
  }

  let rows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/approval_requests?user_id=eq.${userId}&${params.toString()}`,
  );
  let normalized = rows.map((row) => normalizeApprovalRequestRecord(row));
  if (normalized.length > 0) {
    return normalized.filter((row) => extractApprovalRequesterUserId(row) === userId);
  }

  const fallbackLimit =
    options.limit !== undefined
      ? Math.max(options.limit + (options.offset ?? 0), 100)
      : 100;
  const fallbackParams = new URLSearchParams(params);
  fallbackParams.set("limit", String(fallbackLimit));
  fallbackParams.delete("offset");
  rows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/approval_requests?${fallbackParams.toString()}`,
  );
  normalized = rows
    .map((row) => normalizeApprovalRequestRecord(row))
    .filter((row) => extractApprovalRequesterUserId(row) === userId);
  if (options.offset || options.limit !== undefined) {
    return normalized.slice(options.offset ?? 0, (options.offset ?? 0) + (options.limit ?? normalized.length));
  }
  return normalized;
}

function serializePendingApproval(row: ApprovalRequestRecord) {
  const token = typeof row.payload.public_token === "string" ? row.payload.public_token : null;
  return {
    id: row.id,
    action_type: row.action_type,
    created_at: row.created_at,
    token,
  };
}

function approvalRowBelongsToUser(row: ApprovalRequestRecord, userId: string): boolean {
  return extractApprovalRequesterUserId(row) === userId;
}

function getAdApprovalCardData(row: ApprovalRequestRecord): Record<string, unknown> {
  const cardData = asRecord(row.payload.card_data);
  return cardData ?? row.payload;
}

function getRequesterIp(request: Request): string | null {
  return (
    request.headers.get("cf-connecting-ip")?.trim() ||
    request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ||
    null
  );
}

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function requirePageId(pageId: string, request: Request, env: Env, detail = "Page not found"): string {
  if (!UUID_RE.test(pageId)) {
    throw buildErrorResponse(request, env, 404, { detail });
  }
  return pageId;
}

const DELETION_CONFIRMATION_CODE_RE = /^[A-Za-z0-9_-]{20,30}$/;

function resolvePublicAppOrigin(request: Request, env: Env): string {
  const allowList = (env.ALLOWED_ORIGINS ?? "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  const isAllowed = (origin: string) => allowList.length === 0 || allowList.includes(origin);

  const requestOrigin = request.headers.get("origin")?.trim();
  if (requestOrigin && isAllowed(requestOrigin)) {
    return requestOrigin;
  }

  const referer = request.headers.get("referer")?.trim();
  if (referer) {
    try {
      const refererOrigin = new URL(referer).origin;
      if (isAllowed(refererOrigin)) {
        return refererOrigin;
      }
    } catch {
      // Ignore malformed referer headers.
    }
  }

  if (allowList.length > 0) {
    return allowList[0];
  }

  return new URL(request.url).origin;
}

function constantTimeEqual(left: string, right: string): boolean {
  if (left.length !== right.length) {
    return false;
  }

  let diff = 0;
  for (let index = 0; index < left.length; index += 1) {
    diff |= left.charCodeAt(index) ^ right.charCodeAt(index);
  }

  return diff === 0;
}

function getPrimaryAppOrigin(env: Env): string {
  const allowList = (env.ALLOWED_ORIGINS ?? "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  return allowList[0] ?? "https://pikar-ai.com";
}

function sortJsonKeysDeep(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map((item) => sortJsonKeysDeep(item));
  }

  const record = asRecord(value);
  if (!record) {
    return value;
  }

  return Object.fromEntries(
    Object.entries(record)
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([key, item]) => [key, sortJsonKeysDeep(item)]),
  );
}

function isSensitiveKey(key: string): boolean {
  const normalized = key.toLowerCase();
  return SENSITIVE_KEYWORDS.some((keyword) => normalized.includes(keyword));
}

function redactSensitiveData(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map((item) => redactSensitiveData(item));
  }

  const record = asRecord(value);
  if (!record) {
    return value;
  }

  const configKey = typeof record.config_key === "string" ? record.config_key.toLowerCase() : "";
  const isSensitiveConfig =
    Boolean(record.is_sensitive) || (configKey.length > 0 && isSensitiveKey(configKey));

  const redactedEntries = Object.entries(record).map(([key, item]) => {
    const normalizedKey = key.toLowerCase();

    if (normalizedKey === "config_value" && isSensitiveConfig) {
      return [key, REDACTED_VALUE];
    }

    if (normalizedKey === "sync_cursor") {
      return [key, item ? REDACTED_VALUE : {}];
    }

    if (isSensitiveKey(normalizedKey)) {
      return [key, REDACTED_VALUE];
    }

    return [key, redactSensitiveData(item)];
  });

  return Object.fromEntries(redactedEntries);
}

async function signHmacSha256Hex(secret: string, payload: Uint8Array): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );

  const signature = await crypto.subtle.sign("HMAC", key, payload);
  return Array.from(new Uint8Array(signature))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

async function signHmacSha256Base64(secret: string, payload: Uint8Array): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );

  const signature = await crypto.subtle.sign("HMAC", key, payload);
  return btoa(String.fromCharCode(...new Uint8Array(signature)));
}

async function signRawHmacSha256Base64(keyBytes: Uint8Array, payload: Uint8Array): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw",
    keyBytes,
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );

  const signature = await crypto.subtle.sign("HMAC", key, payload);
  return btoa(String.fromCharCode(...new Uint8Array(signature)));
}

async function sha256Hex(payload: Uint8Array): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", payload);
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }

  return value as Record<string, unknown>;
}

function normalizePersonaTier(value: string | null | undefined): PersonaTier | null {
  if (!value) {
    return null;
  }

  const normalized = value.trim().toLowerCase();
  if (normalized === "solopreneur" || normalized === "startup" || normalized === "sme" || normalized === "enterprise") {
    return normalized;
  }

  return null;
}

function getRequestPersonaOverride(request: Request): PersonaTier | null {
  const headerPersona = normalizePersonaTier(request.headers.get("x-pikar-persona"));
  if (headerPersona) {
    return headerPersona;
  }

  const cookieHeader = request.headers.get("cookie") ?? "";
  const cookieMatch = cookieHeader.match(/(?:^|;\s*)x-pikar-persona=([^;]+)/);
  if (!cookieMatch) {
    return null;
  }

  try {
    return normalizePersonaTier(decodeURIComponent(cookieMatch[1]));
  } catch {
    return normalizePersonaTier(cookieMatch[1]);
  }
}

function isFeatureAllowedForTier(featureKey: "teams" | "sales", tier: PersonaTier): boolean {
  const minTierByFeature: Record<"teams" | "sales", PersonaTier> = {
    teams: "startup",
    sales: "solopreneur",
  };

  return TIER_ORDER.indexOf(tier) >= TIER_ORDER.indexOf(minTierByFeature[featureKey]);
}

function buildFeatureGatePayload(featureKey: "teams" | "sales", currentTier: PersonaTier) {
  const featureMeta: Record<"teams" | "sales", { label: string; requiredTier: PersonaTier }> = {
    teams: {
      label: "Team Workspace",
      requiredTier: "startup",
    },
    sales: {
      label: "Sales Pipeline & CRM",
      requiredTier: "solopreneur",
    },
  };
  const meta = featureMeta[featureKey];

  return {
    detail: {
      error: "feature_gated",
      message: `${meta.label} requires ${meta.requiredTier} tier or higher. Your current tier is ${currentTier}.`,
      feature: featureKey,
      current_tier: currentTier,
      required_tier: meta.requiredTier,
      upgrade_url: "/dashboard/billing",
    },
  };
}

function buildWorkspaceSlug(userId: string): string {
  const base = `workspace-${userId.slice(0, 8).toLowerCase()}`.replace(/[^a-z0-9-]/g, "");
  const suffix = Array.from(crypto.getRandomValues(new Uint8Array(4)))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("")
    .slice(0, 6);
  return `${base}-${suffix}`;
}

function shuffleInPlace<T>(items: T[]): T[] {
  for (let index = items.length - 1; index > 0; index -= 1) {
    const swapIndex = Math.floor(Math.random() * (index + 1));
    [items[index], items[swapIndex]] = [items[swapIndex], items[index]];
  }

  return items;
}

function getSuggestionTimeBucket(hour: number): "morning" | "afternoon" | "evening" {
  if (hour >= 6 && hour < 12) {
    return "morning";
  }
  if (hour >= 12 && hour < 17) {
    return "afternoon";
  }
  return "evening";
}

function buildSuggestionsResponse(url: URL): SuggestionItem[] {
  const persona = url.searchParams.get("persona")?.trim();
  if (!persona) {
    throw new Response(
      JSON.stringify({ detail: "Query parameter 'persona' is required" }),
      {
        status: 400,
        headers: { "content-type": "application/json" },
      },
    );
  }

  const hourParam = url.searchParams.get("hour");
  const hour = hourParam === null ? new Date().getUTCHours() : Number(hourParam);
  if (!Number.isInteger(hour) || hour < 0 || hour > 23) {
    throw new Response(
      JSON.stringify({ detail: "Query parameter 'hour' must be an integer between 0 and 23" }),
      {
        status: 400,
        headers: { "content-type": "application/json" },
      },
    );
  }

  const recentActivity = (url.searchParams.get("recent_activity") ?? "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);

  const weightedPool: Array<{ text: string; category: SuggestionCategory }> = [];
  const personaPool = PERSONA_SUGGESTIONS[persona] ?? PERSONA_SUGGESTIONS.solopreneur;
  for (const text of personaPool) {
    weightedPool.push(
      { text, category: "persona_specific" },
      { text, category: "persona_specific" },
      { text, category: "persona_specific" },
    );
  }

  const bucket = getSuggestionTimeBucket(hour);
  for (const text of TIME_BUCKET_SUGGESTIONS[bucket]) {
    weightedPool.push(
      { text, category: "time_aware" },
      { text, category: "time_aware" },
    );
  }

  const seen = new Set<string>();
  const result: SuggestionItem[] = [];

  const activityItems: SuggestionItem[] = [];
  for (const activityKey of recentActivity) {
    for (const text of ACTIVITY_FOLLOWUP_MAP[activityKey] ?? []) {
      if (seen.has(text)) {
        continue;
      }
      seen.add(text);
      activityItems.push({ text, category: "activity_followup" });
    }
  }

  if (activityItems.length > 0) {
    shuffleInPlace(activityItems);
    result.push(activityItems[0]);
  }

  shuffleInPlace(weightedPool);
  const mainUnique: SuggestionItem[] = [];
  for (const item of weightedPool) {
    if (seen.has(item.text)) {
      continue;
    }
    seen.add(item.text);
    mainUnique.push(item);
  }

  const remainingSlots = Math.max(6, 4) - result.length;
  result.push(...mainUnique.slice(0, remainingSlots));
  shuffleInPlace(result);

  if (result.length < 4) {
    for (const fallback of QUICK_START_SUGGESTIONS) {
      if (seen.has(fallback.text) || result.length >= 4) {
        continue;
      }
      seen.add(fallback.text);
      result.push(fallback);
    }
  }

  return result;
}

function stableJsonStringify(value: unknown): string {
  if (value === null || typeof value !== "object") {
    return JSON.stringify(value);
  }

  if (Array.isArray(value)) {
    return `[${value.map((item) => stableJsonStringify(item)).join(",")}]`;
  }

  const entries = Object.entries(value as Record<string, unknown>)
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([key, item]) => `${JSON.stringify(key)}:${stableJsonStringify(item)}`);

  return `{${entries.join(",")}}`;
}

function extractLinkedInEventType(payload: Record<string, unknown>): string {
  const eventType = payload.eventType;
  if (typeof eventType === "string" && eventType.trim()) {
    return eventType;
  }

  const fallback = payload.type;
  if (typeof fallback === "string" && fallback.trim()) {
    return fallback;
  }

  return "unknown";
}

function extractLinkedInOrganizationId(payload: Record<string, unknown>): string | null {
  const data = asRecord(payload.data);
  const nestedOrganization = data?.organization;
  if (typeof nestedOrganization === "string" && nestedOrganization.trim()) {
    return nestedOrganization;
  }

  const organizationId = payload.organizationId;
  if (typeof organizationId === "string" && organizationId.trim()) {
    return organizationId;
  }

  return null;
}

function extractLinkedInActorUrn(payload: Record<string, unknown>): string | null {
  const data = asRecord(payload.data);
  const nestedActor = data?.actor;
  if (typeof nestedActor === "string" && nestedActor.trim()) {
    return nestedActor;
  }

  const actor = payload.actor;
  if (typeof actor === "string" && actor.trim()) {
    return actor;
  }

  return null;
}

async function resolveLinkedInUserId(
  env: Env,
  actorUrn: string | null,
): Promise<string | null> {
  if (!actorUrn) {
    return null;
  }

  const params = new URLSearchParams({
    select: "user_id",
    platform: "eq.linkedin",
    platform_user_id: `eq.${actorUrn}`,
    status: "eq.active",
    limit: "1",
  });

  const rows = await fetchSupabaseAdminRows<Array<{ user_id?: string | null }>>(
    env,
    `/rest/v1/connected_accounts?${params.toString()}`,
  );

  return rows[0]?.user_id ?? null;
}

async function storeLinkedInWebhookEvent(
  env: Env,
  payload: Record<string, unknown>,
): Promise<{ id?: string | null }> {
  const actorUrn = extractLinkedInActorUrn(payload);
  const userId = await resolveLinkedInUserId(env, actorUrn);

  const rows = await insertSupabaseAdminRow<Array<{ id?: string | null }>>(
    env,
    "/rest/v1/social_webhook_events?select=id",
    {
      platform: "linkedin",
      event_type: extractLinkedInEventType(payload),
      payload,
      linkedin_org_id: extractLinkedInOrganizationId(payload),
      user_id: userId,
      status: "pending",
      received_at: new Date().toISOString(),
    },
  );

  return rows[0] ?? {};
}

function getInboundSecretEnvVar(provider: string, env: Env): string | null {
  const mapped = INBOUND_PROVIDER_SECRETS[provider];
  if (mapped) {
    return mapped;
  }

  const dynamic = `${provider.toUpperCase().replace(/[^A-Z0-9]+/g, "_")}_WEBHOOK_SECRET`;
  if (hasConfigValue(env[dynamic])) {
    return dynamic;
  }

  return null;
}

function verifyInboundSignature(
  body: Uint8Array,
  signatureHeader: string,
  expectedHex: string,
): boolean {
  void body;
  if (!signatureHeader) {
    return false;
  }

  const normalized = signatureHeader.startsWith("sha256=")
    ? signatureHeader.slice(7)
    : signatureHeader;

  return constantTimeEqual(normalized, expectedHex);
}

function decodeBase64(value: string): Uint8Array {
  const binary = atob(value);
  return Uint8Array.from(binary, (char) => char.charCodeAt(0));
}

function toBase64Url(bytes: Uint8Array): string {
  const base64 = btoa(String.fromCharCode(...bytes));
  return base64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

function fromBase64Url(value: string): Uint8Array {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
  const padding = normalized.length % 4 === 0 ? "" : "=".repeat(4 - (normalized.length % 4));
  return decodeBase64(`${normalized}${padding}`);
}

function canonicalRequestUrl(request: Request): string {
  const url = new URL(request.url);
  const proto = request.headers.get("x-forwarded-proto")?.trim() || url.protocol.replace(":", "");
  const host = request.headers.get("x-forwarded-host")?.trim() || url.host;
  return `${proto}://${host}${url.pathname}${url.search}`;
}

function canonicalRequestOrigin(request: Request): string {
  const url = new URL(canonicalRequestUrl(request));
  return url.origin;
}

function isFreshUnixTimestamp(
  value: string,
  toleranceSeconds: number,
  multiplier: number,
): boolean {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return false;
  }

  const now = Date.now() / 1000;
  const timestamp = numeric / multiplier;
  return Math.abs(now - timestamp) <= toleranceSeconds;
}

async function verifyHubSpotWebhook(
  request: Request,
  env: Env,
  rawBody: Uint8Array,
): Promise<boolean> {
  const secret = env.HUBSPOT_CLIENT_SECRET?.trim() || env.HUBSPOT_WEBHOOK_SECRET?.trim();
  if (!secret) {
    return false;
  }

  const timestamp = request.headers.get("X-HubSpot-Request-Timestamp")?.trim() ?? "";
  const signature = request.headers.get("X-HubSpot-Signature-v3")?.trim() ?? "";
  if (!timestamp || !signature || !isFreshUnixTimestamp(timestamp, 300, 1000)) {
    return false;
  }

  const source = `${request.method}${canonicalRequestUrl(request)}${new TextDecoder().decode(rawBody)}${timestamp}`;
  const expected = await signHmacSha256Base64(secret, new TextEncoder().encode(source));
  return constantTimeEqual(expected, signature);
}

async function verifyResendWebhook(request: Request, env: Env, rawBody: Uint8Array): Promise<boolean> {
  const secret = env.RESEND_WEBHOOK_SECRET?.trim();
  if (!secret) {
    return false;
  }

  const svixId = request.headers.get("svix-id")?.trim() ?? "";
  const svixTimestamp = request.headers.get("svix-timestamp")?.trim() ?? "";
  const svixSignature = request.headers.get("svix-signature")?.trim() ?? "";
  if (!svixId || !svixTimestamp || !svixSignature || !isFreshUnixTimestamp(svixTimestamp, 300, 1)) {
    return false;
  }

  const encodedSecret = secret.startsWith("whsec_") ? secret.slice("whsec_".length) : secret;
  const signedContent = new TextEncoder().encode(`${svixId}.${svixTimestamp}.`);
  const payload = new Uint8Array(signedContent.length + rawBody.length);
  payload.set(signedContent);
  payload.set(rawBody, signedContent.length);
  const expected = await signRawHmacSha256Base64(decodeBase64(encodedSecret), payload);

  return svixSignature
    .split(/\s+/)
    .map((value) => value.replace(/^v1,/, ""))
    .some((candidate) => constantTimeEqual(expected, candidate));
}

async function verifyShopifyWebhook(
  request: Request,
  env: Env,
  rawBody: Uint8Array,
): Promise<boolean> {
  const secret = env.SHOPIFY_WEBHOOK_SECRET?.trim();
  if (!secret) {
    return false;
  }

  const provided = request.headers.get("X-Shopify-Hmac-SHA256")?.trim() ?? "";
  if (!provided) {
    return false;
  }

  const expected = await signHmacSha256Base64(secret, rawBody);
  return constantTimeEqual(expected, provided);
}

async function verifyStripeWebhook(
  request: Request,
  env: Env,
  rawBody: Uint8Array,
): Promise<boolean> {
  const secret = env.STRIPE_WEBHOOK_SECRET?.trim();
  if (!secret) {
    return false;
  }

  const header = request.headers.get("Stripe-Signature")?.trim() ?? "";
  if (!header) {
    return false;
  }

  let timestamp = "";
  const signatures: string[] = [];
  for (const part of header.split(",")) {
    const [key, value] = part.split("=", 2);
    if (!key || !value) {
      continue;
    }

    if (key === "t") {
      timestamp = value;
    } else if (key === "v1") {
      signatures.push(value);
    }
  }

  if (!timestamp || signatures.length === 0 || !isFreshUnixTimestamp(timestamp, 300, 1)) {
    return false;
  }

  const signedPayload = new TextEncoder().encode(
    `${timestamp}.${new TextDecoder().decode(rawBody)}`,
  );
  const expected = await signHmacSha256Hex(secret, signedPayload);
  return signatures.some((candidate) => constantTimeEqual(expected, candidate));
}

async function extractInboundEventId(payload: Record<string, unknown>): Promise<string> {
  const eventId = payload.id;
  if (
    typeof eventId === "string" ||
    typeof eventId === "number" ||
    typeof eventId === "bigint"
  ) {
    return String(eventId);
  }

  const serialized = stableJsonStringify(payload);
  return (await sha256Hex(new TextEncoder().encode(serialized))).slice(0, 32);
}

function extractInboundEventType(payload: Record<string, unknown>): string {
  const type = payload.type;
  if (typeof type === "string" && type.trim()) {
    return type;
  }

  const fallback = payload.event;
  if (typeof fallback === "string" && fallback.trim()) {
    return fallback;
  }

  return "unknown";
}

async function storeGenericInboundWebhook(
  env: Env,
  provider: string,
  payload: Record<string, unknown>,
): Promise<{ status: "received" | "duplicate"; event_id: string }> {
  const eventId = await extractInboundEventId(payload);
  const eventType = extractInboundEventType(payload);
  const rows = await upsertSupabaseAdminRow<Array<{ id?: string | null }>>(
    env,
    "/rest/v1/webhook_events?on_conflict=provider,event_id&select=id",
    {
      provider,
      event_id: eventId,
      event_type: eventType,
      payload,
      status: "pending",
    },
  );

  const rowId = rows[0]?.id;
  if (!rowId) {
    return {
      status: "duplicate",
      event_id: eventId,
    };
  }

  await insertSupabaseAdminRow<Array<{ id?: string | null }>>(
    env,
    "/rest/v1/ai_jobs?select=id",
    {
      job_type: "webhook_inbound_process",
      priority: 8,
      input_data: {
        webhook_event_id: rowId,
        provider,
        event_type: eventType,
      },
    },
  );

  return {
    status: "received",
    event_id: eventId,
  };
}

async function buildUserConfigsResponse(request: Request, env: Env) {
  const rows = await fetchSupabaseRows<Array<Record<string, unknown>>>(
    request,
    env,
    "/rest/v1/user_configurations?select=config_key,config_value,updated_at",
  );

  return { configs: rows };
}

async function buildSessionConfigResponse(request: Request, env: Env) {
  try {
    const rows = await fetchSupabaseRows<Array<{ config_value?: string | null }>>(
      request,
      env,
      "/rest/v1/user_configurations?select=config_value&config_key=eq.sessions&limit=1",
    );

    if (!rows.length || !rows[0]?.config_value) {
      return DEFAULT_SESSION_CONFIG;
    }

    const parsed = JSON.parse(rows[0].config_value) as Record<string, unknown>;
    return {
      ...DEFAULT_SESSION_CONFIG,
      ...parsed,
    };
  } catch (error) {
    if (error instanceof Response) {
      throw error;
    }

    return DEFAULT_SESSION_CONFIG;
  }
}

async function buildSocialStatusResponse(request: Request, env: Env) {
  const rows = await fetchSupabaseRows<
    Array<{
      platform: string;
      platform_username?: string | null;
      status?: string | null;
      connected_at?: string | null;
    }>
  >(
    request,
    env,
    "/rest/v1/connected_accounts?select=platform,platform_username,status,connected_at",
  );

  const connectionMap = new Map(rows.map((row) => [row.platform, row]));

  return {
    platforms: SOCIAL_PLATFORMS_INFO.map((platform) => {
      const connection = connectionMap.get(platform.platform);

      return {
        platform: platform.platform,
        display_name: platform.display_name,
        icon: platform.icon,
        connected: connection?.status === "active",
        username: connection?.platform_username ?? null,
        connected_at: connection?.connected_at ?? null,
        requires_config: platform.config_keys.some((key) => !hasConfigValue(env[key])),
        config_keys: [...platform.config_keys],
      };
    }),
  };
}

async function buildGoogleWorkspaceStatusResponse(request: Request, env: Env) {
  const user = await fetchSupabaseUser(request, env);
  const identities = user.identities ?? [];
  const googleIdentity = identities.find((identity) => identity.provider === "google");

  if (!googleIdentity) {
    return {
      connected: false,
      provider: null,
      message: "Sign in with Google to enable Google Workspace features",
    };
  }

  return {
    connected: true,
    email: user.email ?? googleIdentity.identity_data?.email ?? "",
    provider: "google",
    features: [
      "Google Docs - Create and edit documents",
      "Google Sheets - Create spreadsheets and track data",
      "Google Forms - Create surveys and feedback forms",
      "Google Calendar - Schedule events and meetings",
      "Gmail - Send emails on your behalf",
    ],
    message: "Google Workspace is connected and ready to use",
  };
}

async function buildConfigurationSettingsResponse(request: Request, env: Env) {
  const user = await fetchSupabaseUser(request, env);
  if (!user.id) {
    throw new Response(
      JSON.stringify({ detail: "Invalid authentication credentials" }),
      {
        status: 401,
        headers: { "content-type": "application/json" },
      },
    );
  }

  const params = new URLSearchParams({
    select: "config_value",
    user_id: `eq.${user.id}`,
    config_key: "eq.settings",
    limit: "1",
  });
  const rows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/user_configurations?${params.toString()}`,
  );
  let settings: Record<string, unknown> = {};
  const rawValue = rows[0]?.config_value;
  if (typeof rawValue === "string") {
    try {
      settings = asRecord(JSON.parse(rawValue)) ?? {};
    } catch {
      settings = {};
    }
  }

  const identityEmail =
    user.identities?.find((identity) => typeof identity?.identity_data?.email === "string")
      ?.identity_data?.email ?? null;

  const parseNumber = (value: unknown) => {
    if (typeof value === "number" && Number.isFinite(value)) {
      return value;
    }
    if (typeof value === "string" && value.trim()) {
      const parsed = Number(value);
      return Number.isFinite(parsed) ? parsed : null;
    }
    return null;
  };

  return {
    full_name: typeof settings.full_name === "string" ? settings.full_name : "",
    email: user.email ?? identityEmail ?? "",
    notifications_enabled: settings.notifications_enabled === true,
    revenue_target: parseNumber(settings.revenue_target),
    burn_rate: parseNumber(settings.burn_rate),
    department_count: parseNumber(settings.department_count),
    audit_logs_enabled: settings.audit_logs_enabled === true,
  };
}

async function buildConfigurationSettingsUpdateResponse(request: Request, env: Env) {
  const user = await fetchSupabaseUser(request, env);
  if (!user.id) {
    throw new Response(
      JSON.stringify({ detail: "Invalid authentication credentials" }),
      {
        status: 401,
        headers: { "content-type": "application/json" },
      },
    );
  }

  let payload: Record<string, unknown>;
  try {
    payload = (await request.json()) as Record<string, unknown>;
  } catch {
    throw buildErrorResponse(request, env, 400, {
      detail: "Request body must be valid JSON.",
    });
  }

  const existingParams = new URLSearchParams({
    select: "config_value",
    user_id: `eq.${user.id}`,
    config_key: "eq.settings",
    limit: "1",
  });
  const existingRows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/user_configurations?${existingParams.toString()}`,
  );
  let existingSettings: Record<string, unknown> = {};
  const existingValue = existingRows[0]?.config_value;
  if (typeof existingValue === "string") {
    try {
      existingSettings = asRecord(JSON.parse(existingValue)) ?? {};
    } catch {
      existingSettings = {};
    }
  }

  const parseOptionalNumber = (field: string) => {
    const value = payload[field];
    if (value === undefined) {
      const existing = existingSettings[field];
      if (typeof existing === "number" && Number.isFinite(existing)) {
        return existing;
      }
      if (typeof existing === "string" && existing.trim()) {
        const parsedExisting = Number(existing);
        return Number.isFinite(parsedExisting) ? parsedExisting : null;
      }
      return null;
    }
    if (value === null || value === "") {
      return null;
    }
    if (typeof value === "number" && Number.isFinite(value)) {
      return value;
    }
    if (typeof value === "string" && value.trim()) {
      const parsed = Number(value);
      if (Number.isFinite(parsed)) {
        return parsed;
      }
    }
    throw buildErrorResponse(request, env, 400, {
      detail: `${field} must be a number when provided`,
    });
  };

  const fullName = payload.full_name;
  if (fullName !== undefined && typeof fullName !== "string") {
    throw buildErrorResponse(request, env, 400, {
      detail: "full_name must be a string",
    });
  }
  const notificationsEnabled = payload.notifications_enabled;
  if (notificationsEnabled !== undefined && typeof notificationsEnabled !== "boolean") {
    throw buildErrorResponse(request, env, 400, {
      detail: "notifications_enabled must be a boolean",
    });
  }
  const auditLogsEnabled = payload.audit_logs_enabled;
  if (auditLogsEnabled !== undefined && typeof auditLogsEnabled !== "boolean") {
    throw buildErrorResponse(request, env, 400, {
      detail: "audit_logs_enabled must be a boolean",
    });
  }

  const settings = {
    full_name:
      typeof fullName === "string"
        ? fullName
        : typeof existingSettings.full_name === "string"
          ? existingSettings.full_name
          : "",
    notifications_enabled:
      typeof notificationsEnabled === "boolean"
        ? notificationsEnabled
        : existingSettings.notifications_enabled === true,
    revenue_target: parseOptionalNumber("revenue_target"),
    burn_rate: parseOptionalNumber("burn_rate"),
    department_count: parseOptionalNumber("department_count"),
    audit_logs_enabled:
      typeof auditLogsEnabled === "boolean"
        ? auditLogsEnabled
        : existingSettings.audit_logs_enabled === true,
  };

  await upsertSupabaseAdminMergeRow<Array<Record<string, unknown>>>(
    env,
    "/rest/v1/user_configurations?on_conflict=user_id,config_key&select=id",
    {
      user_id: user.id,
      config_key: "settings",
      config_value: JSON.stringify(settings),
      is_sensitive: false,
      updated_at: new Date().toISOString(),
    },
  );

  return {
    ...settings,
    email: user.email ?? "",
  };
}

async function buildFinanceInvoicesResponse(request: Request, env: Env, url: URL) {
  const userId = await requireAuthenticatedUserId(request, env);
  const limit = parseIntegerQueryParam(url, "limit", 50, 1, 200);
  const rows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/invoices?user_id=eq.${userId}&select=*&order=created_at.desc&limit=${limit}`,
  );
  return rows.map((row) => normalizeFinanceInvoiceRecord(row));
}

async function buildFinanceAssumptionsResponse(request: Request, env: Env) {
  const userId = await requireAuthenticatedUserId(request, env);
  const rows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/finance_assumptions_ledger?user_id=eq.${userId}&is_active=eq.true&select=*&order=created_at.desc`,
  );
  return rows.map((row) => normalizeFinanceAssumptionRecord(row));
}

async function buildFinanceRevenueTimeSeriesResponse(request: Request, env: Env, url: URL) {
  const userId = await requireAuthenticatedUserId(request, env);
  const months = parseIntegerQueryParam(url, "months", 6, 1, 24);
  const since = new Date(Date.now() - months * 30 * 24 * 60 * 60 * 1000).toISOString();
  const rows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/payment_transactions?user_id=eq.${userId}&status=eq.succeeded&created_at=gte.${encodeURIComponent(since)}&select=amount,created_at&order=created_at.asc`,
  );

  const byMonth: Record<string, number> = {};
  for (const row of rows) {
    const createdAt = typeof row.created_at === "string" ? row.created_at : null;
    if (!createdAt) {
      continue;
    }
    const date = new Date(createdAt);
    if (Number.isNaN(date.getTime())) {
      continue;
    }
    const key = `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, "0")}`;
    const rawAmount = row.amount;
    const amount =
      typeof rawAmount === "number"
        ? rawAmount
        : typeof rawAmount === "string"
          ? Number.parseFloat(rawAmount) || 0
          : 0;
    byMonth[key] = (byMonth[key] ?? 0) + amount;
  }

  return Object.entries(byMonth)
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([month, total]) => ({ month, total }));
}

async function buildSalesContactsResponse(request: Request, env: Env, url: URL) {
  const userId = await requireAuthenticatedUserId(request, env);
  const featureDenied = await requireFeatureAccess(request, env, "sales", userId);
  if (featureDenied) {
    throw featureDenied;
  }

  const limit = parseIntegerQueryParam(url, "limit", 200, 1, 500);
  const stage = url.searchParams.get("stage");
  let path = `/rest/v1/contacts?user_id=eq.${userId}&select=*&order=updated_at.desc&limit=${limit}`;
  if (stage && stage !== "all") {
    path += `&lifecycle_stage=eq.${encodeURIComponent(stage)}`;
  }

  return fetchSupabaseAdminRows<Array<Record<string, unknown>>>(env, path);
}

async function buildSalesContactActivitiesResponse(request: Request, env: Env, url: URL) {
  const userId = await requireAuthenticatedUserId(request, env);
  const featureDenied = await requireFeatureAccess(request, env, "sales", userId);
  if (featureDenied) {
    throw featureDenied;
  }

  const limit = parseIntegerQueryParam(url, "limit", 10, 1, 100);
  return fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/contact_activities?user_id=eq.${userId}&select=*&order=created_at.desc&limit=${limit}`,
  );
}

async function buildSalesConnectedAccountsResponse(request: Request, env: Env) {
  const userId = await requireAuthenticatedUserId(request, env);
  const featureDenied = await requireFeatureAccess(request, env, "sales", userId);
  if (featureDenied) {
    throw featureDenied;
  }

  const rows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/connected_accounts?user_id=eq.${userId}&select=id,user_id,platform,platform_user_id,platform_username,status,connected_at,last_used_at,metadata&order=connected_at.desc`,
  );
  return rows.map((row) => normalizeSalesConnectedAccountRecord(row));
}

async function buildSalesCampaignsResponse(request: Request, env: Env, url: URL) {
  const userId = await requireAuthenticatedUserId(request, env);
  const featureDenied = await requireFeatureAccess(request, env, "sales", userId);
  if (featureDenied) {
    throw featureDenied;
  }

  const limit = parseIntegerQueryParam(url, "limit", 50, 1, 200);
  const rows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/campaigns?user_id=eq.${userId}&select=id,name,campaign_type,target_audience,status,schedule_start,schedule_end,metrics,created_at&order=created_at.desc&limit=${limit}`,
  );
  return rows.map((row) => normalizeSalesCampaignRecord(row));
}

async function buildSalesPageAnalyticsResponse(request: Request, env: Env, url: URL) {
  const userId = await requireAuthenticatedUserId(request, env);
  const featureDenied = await requireFeatureAccess(request, env, "sales", userId);
  if (featureDenied) {
    throw featureDenied;
  }

  const limit = parseIntegerQueryParam(url, "limit", 50, 1, 200);
  const rows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/page_analytics?user_id=eq.${userId}&select=id,page_url,event_type,utm_source,referrer,created_at&order=created_at.desc&limit=${limit}`,
  );
  return normalizeSalesPageAnalyticsRecords(rows);
}

async function buildContentBundlesResponse(request: Request, env: Env, url: URL) {
  const userId = await requireAuthenticatedUserId(request, env);
  const scopedUserIds = await getWorkspaceScopedUserIds(env, userId);
  const limit = parseIntegerQueryParam(url, "limit", 100, 1, 500);
  const userFilter =
    scopedUserIds.length > 1 ? `in.(${scopedUserIds.join(",")})` : `eq.${userId}`;

  const rows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/content_bundles?user_id=${encodeURIComponent(userFilter)}&select=*&order=created_at.desc&limit=${limit}`,
  );
  return rows.map((row) => normalizeContentBundleRecord(row));
}

async function buildContentDeliverablesResponse(request: Request, env: Env, url: URL) {
  const userId = await requireAuthenticatedUserId(request, env);
  const bundleIdsRaw = url.searchParams.get("bundle_ids");
  if (!bundleIdsRaw) {
    return [];
  }

  const bundleIds = bundleIdsRaw
    .split(",")
    .map((value) => value.trim())
    .filter((value) => value.length > 0);
  if (!bundleIds.length) {
    return [];
  }

  const scopedUserIds = await getWorkspaceScopedUserIds(env, userId);
  const userFilter =
    scopedUserIds.length > 1 ? `in.(${scopedUserIds.join(",")})` : `eq.${userId}`;
  const bundleFilter = `in.(${bundleIds.join(",")})`;

  const rows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/content_bundle_deliverables?user_id=${encodeURIComponent(userFilter)}&bundle_id=${encodeURIComponent(bundleFilter)}&select=*&order=created_at.desc`,
  );
  return rows.map((row) => normalizeContentDeliverableRecord(row));
}

async function buildContentCampaignsResponse(request: Request, env: Env, url: URL) {
  const userId = await requireAuthenticatedUserId(request, env);
  const scopedUserIds = await getWorkspaceScopedUserIds(env, userId);
  const limit = parseIntegerQueryParam(url, "limit", 50, 1, 200);
  const userFilter =
    scopedUserIds.length > 1 ? `in.(${scopedUserIds.join(",")})` : `eq.${userId}`;

  const rows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/campaigns?user_id=${encodeURIComponent(userFilter)}&select=id,name,campaign_type,target_audience,status,schedule_start,schedule_end,metrics,created_at&order=created_at.desc&limit=${limit}`,
  );
  return rows.map((row) => normalizeSalesCampaignRecord(row));
}

async function resolveEffectivePersonaTier(
  request: Request,
  env: Env,
  userId: string,
): Promise<PersonaTier> {
  const requestPersona = getRequestPersonaOverride(request);
  if (requestPersona) {
    return requestPersona;
  }

  const subscriptionParams = new URLSearchParams({
    select: "tier",
    user_id: `eq.${userId}`,
    is_active: "eq.true",
    limit: "1",
  });
  const subscriptions = await fetchSupabaseAdminRows<Array<{ tier?: string | null }>>(
    env,
    `/rest/v1/subscriptions?${subscriptionParams.toString()}`,
  );
  const subscriptionTier = normalizePersonaTier(subscriptions[0]?.tier ?? null);
  if (subscriptionTier) {
    return subscriptionTier;
  }

  const profileParams = new URLSearchParams({
    select: "persona",
    user_id: `eq.${userId}`,
    limit: "1",
  });
  const profileRows = await fetchSupabaseAdminRows<Array<{ persona?: string | null }>>(
    env,
    `/rest/v1/user_executive_agents?${profileParams.toString()}`,
  );
  const profileTier = normalizePersonaTier(profileRows[0]?.persona ?? null);
  if (profileTier) {
    return profileTier;
  }

  return "solopreneur";
}

async function requireFeatureAccess(
  request: Request,
  env: Env,
  featureKey: "teams" | "sales",
  userId: string,
): Promise<Response | null> {
  const tier = await resolveEffectivePersonaTier(request, env, userId);
  if (isFeatureAllowedForTier(featureKey, tier)) {
    return null;
  }

  return buildErrorResponse(request, env, 403, buildFeatureGatePayload(featureKey, tier));
}

async function getWorkspaceMembershipForUser(
  env: Env,
  userId: string,
): Promise<{ workspace_id: string; role?: string | null } | null> {
  const params = new URLSearchParams({
    select: "workspace_id,role",
    user_id: `eq.${userId}`,
    limit: "1",
  });
  const rows = await fetchSupabaseAdminRows<Array<{ workspace_id?: string; role?: string | null }>>(
    env,
    `/rest/v1/workspace_members?${params.toString()}`,
  );

  const row = rows[0];
  if (!row?.workspace_id) {
    return null;
  }

  return {
    workspace_id: row.workspace_id,
    role: row.role ?? null,
  };
}

async function getWorkspaceById(env: Env, workspaceId: string): Promise<WorkspaceRecord | null> {
  const params = new URLSearchParams({
    select: "id,name,slug,owner_id,created_at,updated_at",
    id: `eq.${workspaceId}`,
    limit: "1",
  });
  const rows = await fetchSupabaseAdminRows<Array<WorkspaceRecord>>(
    env,
    `/rest/v1/workspaces?${params.toString()}`,
  );

  return rows[0] ?? null;
}

async function createWorkspaceForUser(env: Env, userId: string): Promise<WorkspaceRecord> {
  const createdRows = await insertSupabaseAdminRow<Array<WorkspaceRecord>>(
    env,
    "/rest/v1/workspaces?select=id,name,slug,owner_id,created_at,updated_at",
    {
      owner_id: userId,
      name: "My Workspace",
      slug: buildWorkspaceSlug(userId),
    },
  );

  const workspace = createdRows[0];
  if (!workspace?.id) {
    throw new Error("Workspace creation did not return a workspace id.");
  }

  await insertSupabaseAdminRow<Array<Record<string, unknown>>>(
    env,
    "/rest/v1/workspace_members?select=id,user_id,workspace_id,role,joined_at",
    {
      workspace_id: workspace.id,
      user_id: userId,
      role: "admin",
    },
  );

  return workspace;
}

async function getOrCreateWorkspaceForUser(
  env: Env,
  userId: string,
): Promise<{ workspace: WorkspaceRecord; role: string }> {
  const membership = await getWorkspaceMembershipForUser(env, userId);
  if (membership?.workspace_id) {
    const workspace = await getWorkspaceById(env, membership.workspace_id);
    if (workspace) {
      return {
        workspace,
        role: membership.role ?? "admin",
      };
    }
  }

  const workspace = await createWorkspaceForUser(env, userId);
  return {
    workspace,
    role: "admin",
  };
}

async function getWorkspaceMembersForWorkspace(
  env: Env,
  workspaceId: string,
): Promise<WorkspaceMemberRecord[]> {
  const params = new URLSearchParams({
    select: "id,user_id,role,joined_at",
    workspace_id: `eq.${workspaceId}`,
    order: "joined_at.asc",
  });
  const members = await fetchSupabaseAdminRows<Array<WorkspaceMemberRecord>>(
    env,
    `/rest/v1/workspace_members?${params.toString()}`,
  );
  if (!members.length) {
    return [];
  }

  const userIds = members
    .map((member) => member.user_id)
    .filter((value): value is string => typeof value === "string" && value.length > 0);
  const profileMap = new Map<string, { full_name?: string | null; email?: string | null }>();

  if (userIds.length > 0) {
    const profileParams = new URLSearchParams({
      select: "user_id,full_name,email",
      user_id: `in.(${userIds.join(",")})`,
    });

    try {
      const profiles = await fetchSupabaseAdminRows<
        Array<{ user_id?: string; full_name?: string | null; email?: string | null }>
      >(env, `/rest/v1/user_profiles?${profileParams.toString()}`);
      for (const profile of profiles) {
        if (!profile.user_id) {
          continue;
        }

        profileMap.set(profile.user_id, {
          full_name: profile.full_name ?? null,
          email: profile.email ?? null,
        });
      }
    } catch {
      // Keep member rows usable even when optional profile enrichment is missing.
    }
  }

  return members.map((member) => {
    const profile = profileMap.get(member.user_id);
    return {
      ...member,
      email: profile?.email ?? null,
      full_name: profile?.full_name ?? null,
    };
  });
}

async function getWorkspaceScopedUserIds(env: Env, userId: string): Promise<string[]> {
  const membership = await getWorkspaceMembershipForUser(env, userId);
  if (!membership?.workspace_id) {
    return [userId];
  }

  const members = await getWorkspaceMembersForWorkspace(env, membership.workspace_id);
  if (!members.length) {
    return [userId];
  }

  const scopedUserIds = members
    .map((member) => member.user_id)
    .filter((value): value is string => typeof value === "string" && value.length > 0);

  if (!scopedUserIds.includes(userId)) {
    scopedUserIds.push(userId);
  }

  return scopedUserIds;
}

async function buildTeamWorkspaceResponse(request: Request, env: Env) {
  const userId = await requireAuthenticatedUserId(request, env);
  const featureDenied = await requireFeatureAccess(request, env, "teams", userId);
  if (featureDenied) {
    throw featureDenied;
  }

  const { workspace, role } = await getOrCreateWorkspaceForUser(env, userId);
  const members = await getWorkspaceMembersForWorkspace(env, workspace.id);

  return {
    id: workspace.id,
    name: workspace.name,
    slug: workspace.slug ?? null,
    owner_id: workspace.owner_id,
    role,
    member_count: members.length,
  };
}

async function buildTeamMembersResponse(request: Request, env: Env) {
  const userId = await requireAuthenticatedUserId(request, env);
  const featureDenied = await requireFeatureAccess(request, env, "teams", userId);
  if (featureDenied) {
    throw featureDenied;
  }

  const membership = await getWorkspaceMembershipForUser(env, userId);
  if (!membership?.workspace_id) {
    return [];
  }

  const members = await getWorkspaceMembersForWorkspace(env, membership.workspace_id);
  return members.map((member) => ({
    id: member.id,
    user_id: member.user_id,
    email: member.email ?? "",
    display_name: member.full_name ?? null,
    role: member.role,
    joined_at: member.joined_at,
  }));
}

function buildWorkspaceRoleDeniedResponse(
  request: Request,
  env: Env,
  currentRole: string | null | undefined,
  allowedRoles: string[],
): Response {
  const requiredDisplay = allowedRoles.join(" or ");
  return buildErrorResponse(request, env, 403, {
    detail: {
      error: "insufficient_role",
      message: `This action requires ${requiredDisplay} role. Your role is ${currentRole ?? "none"}. Contact your workspace admin.`,
      current_role: currentRole ?? null,
      required_roles: allowedRoles,
    },
  });
}

async function getWorkspaceRoleForUser(
  env: Env,
  workspaceId: string,
  userId: string,
): Promise<string | null> {
  const params = new URLSearchParams({
    select: "role",
    workspace_id: `eq.${workspaceId}`,
    user_id: `eq.${userId}`,
    limit: "1",
  });
  const rows = await fetchSupabaseAdminRows<Array<{ role?: string | null }>>(
    env,
    `/rest/v1/workspace_members?${params.toString()}`,
  );
  return rows[0]?.role ?? null;
}

async function countSupabaseAdminRows(env: Env, path: string): Promise<number> {
  const context = getSupabaseAdminContext(env);
  const headers = new Headers(context.headers);
  headers.set("Prefer", "count=exact");

  const response = await fetch(`${context.supabaseUrl}${path}`, {
    method: "HEAD",
    headers,
  });

  if (response.ok) {
    const contentRange = response.headers.get("content-range");
    const match = contentRange ? /\/(\d+)$/.exec(contentRange) : null;
    if (match) {
      return Number(match[1]);
    }
  }

  const rows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(env, path);
  return rows.length;
}

async function countSupabaseAdminRowsSafe(env: Env, path: string): Promise<number> {
  try {
    return await countSupabaseAdminRows(env, path);
  } catch (error) {
    if (error instanceof Error && /\b404\b/.test(error.message)) {
      return 0;
    }
    throw error;
  }
}

async function getWorkspaceInviteByToken(
  env: Env,
  token: string,
): Promise<WorkspaceInviteRecord | null> {
  const params = new URLSearchParams({
    select:
      "id,workspace_id,token,role,created_by,invited_email,expires_at,accepted_by,accepted_at,is_active,created_at",
    token: `eq.${token}`,
    limit: "1",
  });
  const rows = await fetchSupabaseAdminRows<Array<WorkspaceInviteRecord>>(
    env,
    `/rest/v1/workspace_invites?${params.toString()}`,
  );
  return rows[0] ?? null;
}

function getInviteInactiveMessage(invite: WorkspaceInviteRecord): string | null {
  if (invite.accepted_by) {
    return "This invite link has already been accepted.";
  }

  if (!invite.is_active) {
    return "This invite link has been revoked.";
  }

  const expiresAt = Date.parse(invite.expires_at);
  if (Number.isFinite(expiresAt) && Date.now() > expiresAt) {
    return "This invite link has expired.";
  }

  return null;
}

function getInvitePublicErrorStatus(message: string): number {
  const normalized = message.toLowerCase();
  if (normalized.includes("not found")) {
    return 404;
  }
  if (
    normalized.includes("revoked") ||
    normalized.includes("accepted") ||
    normalized.includes("expired")
  ) {
    return 410;
  }
  return 400;
}

async function buildTeamInviteCreateResponse(request: Request, env: Env) {
  const userId = await requireAuthenticatedUserId(request, env);
  const featureDenied = await requireFeatureAccess(request, env, "teams", userId);
  if (featureDenied) {
    throw featureDenied;
  }

  let payload: Record<string, unknown>;
  try {
    payload = (await request.json()) as Record<string, unknown>;
  } catch {
    throw buildErrorResponse(request, env, 400, {
      detail: "Request body must be valid JSON.",
    });
  }

  const role = normalizeInviteRole(payload.role);
  if (!role) {
    const providedRole = typeof payload.role === "string" ? payload.role : String(payload.role ?? "");
    throw buildErrorResponse(request, env, 400, {
      detail: `Invalid invite role '${providedRole}'. Must be 'editor' or 'viewer'.`,
    });
  }

  const expiresHoursRaw = payload.expires_hours ?? 168;
  const expiresHours =
    typeof expiresHoursRaw === "number" ? expiresHoursRaw : Number(expiresHoursRaw);
  if (!Number.isInteger(expiresHours) || expiresHours < 1 || expiresHours > 720) {
    throw buildErrorResponse(request, env, 400, {
      detail: "expires_hours must be an integer between 1 and 720.",
    });
  }

  const membership = await getWorkspaceMembershipForUser(env, userId);
  if (!membership?.workspace_id) {
    throw buildErrorResponse(request, env, 404, { detail: "No workspace found" });
  }

  if (membership.role !== "admin") {
    throw buildWorkspaceRoleDeniedResponse(request, env, membership.role, ["admin"]);
  }

  const inviteRows = await insertSupabaseAdminRow<Array<WorkspaceInviteRecord>>(
    env,
    "/rest/v1/workspace_invites?select=id,workspace_id,token,role,created_by,invited_email,expires_at,is_active,created_at",
    {
      workspace_id: membership.workspace_id,
      token: randomBase64Url(32),
      role,
      created_by: userId,
      expires_at: new Date(Date.now() + expiresHours * 60 * 60 * 1000).toISOString(),
      is_active: true,
      invited_email: normalizeOptionalEmail(payload.invited_email),
    },
  );

  const invite = inviteRows[0];
  if (!invite?.id || !invite.token) {
    throw new Error("Invite creation did not return the expected payload.");
  }

  const appOrigin = resolvePublicAppOrigin(request, env).replace(/\/+$/g, "");

  return {
    id: invite.id,
    token: invite.token,
    role: invite.role,
    expires_at: invite.expires_at,
    share_url: `${appOrigin}/invite/${encodeURIComponent(invite.token)}`,
  };
}

async function buildTeamInviteAcceptResponse(request: Request, env: Env) {
  const userId = await requireAuthenticatedUserId(request, env);
  const featureDenied = await requireFeatureAccess(request, env, "teams", userId);
  if (featureDenied) {
    throw featureDenied;
  }

  let payload: Record<string, unknown>;
  try {
    payload = (await request.json()) as Record<string, unknown>;
  } catch {
    throw buildErrorResponse(request, env, 400, {
      detail: "Request body must be valid JSON.",
    });
  }

  const token = typeof payload.token === "string" ? payload.token.trim() : "";
  if (!token) {
    throw buildErrorResponse(request, env, 400, { detail: "token is required" });
  }

  const invite = await getWorkspaceInviteByToken(env, token);
  if (!invite) {
    throw buildErrorResponse(request, env, 400, {
      detail: "Invite token not found or has already been used.",
    });
  }

  const inactiveMessage = getInviteInactiveMessage(invite);
  if (inactiveMessage) {
    throw buildErrorResponse(request, env, 400, { detail: inactiveMessage });
  }

  const existingRole = await getWorkspaceRoleForUser(env, invite.workspace_id, userId);
  if (existingRole) {
    throw buildErrorResponse(request, env, 400, {
      detail: `User is already a member of this workspace with role '${existingRole}'.`,
    });
  }

  const membershipRows = await insertSupabaseAdminRow<
    Array<{ id?: string; workspace_id?: string; user_id?: string; role?: string; joined_at?: string }>
  >(
    env,
    "/rest/v1/workspace_members?select=id,workspace_id,user_id,role,joined_at",
    {
      workspace_id: invite.workspace_id,
      user_id: userId,
      role: invite.role,
    },
  );
  const membership = membershipRows[0];
  if (!membership?.id || !membership.workspace_id) {
    throw new Error("Invite acceptance did not return a workspace membership.");
  }

  await updateSupabaseAdminRows<Array<WorkspaceInviteRecord>>(
    env,
    `/rest/v1/workspace_invites?id=eq.${invite.id}`,
    {
      accepted_by: userId,
      accepted_at: new Date().toISOString(),
      is_active: false,
    },
  );

  try {
    await insertSupabaseAdminRow<Array<Record<string, unknown>>>(
      env,
      "/rest/v1/governance_audit_log?select=id",
      {
        user_id: userId,
        action_type: "member.joined",
        resource_type: "workspace_member",
        resource_id: membership.id,
        details: {
          workspace_id: membership.workspace_id,
        },
      },
    );
  } catch {
    // Preserve backend behavior where audit logging must not block acceptance.
  }

  return {
    success: true,
    membership,
  };
}

async function buildTeamInviteDetailsResponse(request: Request, env: Env, url: URL) {
  const token = url.searchParams.get("token")?.trim() ?? "";
  if (!token) {
    throw buildErrorResponse(request, env, 400, { detail: "Invite token is required." });
  }

  const invite = await getWorkspaceInviteByToken(env, token);
  if (!invite) {
    const message = "Invite token not found or has already been used.";
    throw buildErrorResponse(request, env, getInvitePublicErrorStatus(message), {
      detail: message,
    });
  }

  const inactiveMessage = getInviteInactiveMessage(invite);
  if (inactiveMessage) {
    throw buildErrorResponse(request, env, getInvitePublicErrorStatus(inactiveMessage), {
      detail: inactiveMessage,
    });
  }

  const workspace = await getWorkspaceById(env, invite.workspace_id);
  if (!workspace) {
    throw buildErrorResponse(request, env, 404, { detail: "Workspace not found." });
  }

  let inviterName: string | null = null;
  const inviterParams = new URLSearchParams({
    select: "user_id,full_name,email",
    user_id: `eq.${invite.created_by}`,
    limit: "1",
  });
  try {
    const profiles = await fetchSupabaseAdminRows<
      Array<{ user_id?: string; full_name?: string | null; email?: string | null }>
    >(env, `/rest/v1/user_profiles?${inviterParams.toString()}`);
    const profile = profiles[0];
    inviterName =
      profile?.full_name?.trim() ||
      profile?.email?.split("@")[0]?.trim() ||
      null;
  } catch {
    inviterName = null;
  }

  return {
    id: invite.id,
    workspaceName: workspace.name,
    role: invite.role,
    invitedEmail: invite.invited_email ?? null,
    inviterName,
    expiresAt: invite.expires_at,
    isActive: true,
  };
}

async function getWorkspaceMemberIds(env: Env, workspaceId: string): Promise<string[]> {
  const members = await getWorkspaceMembersForWorkspace(env, workspaceId);
  return members
    .map((member) => member.user_id)
    .filter((value, index, array) => value && array.indexOf(value) === index);
}

async function buildTeamAnalyticsResponse(request: Request, env: Env) {
  const userId = await requireAuthenticatedUserId(request, env);
  const featureDenied = await requireFeatureAccess(request, env, "teams", userId);
  if (featureDenied) {
    throw featureDenied;
  }

  const membership = await getWorkspaceMembershipForUser(env, userId);
  if (!membership?.workspace_id) {
    throw buildErrorResponse(request, env, 404, { detail: "No workspace found" });
  }

  const workspace = await getWorkspaceById(env, membership.workspace_id);
  if (!workspace) {
    throw buildErrorResponse(request, env, 404, { detail: "No workspace found" });
  }

  const memberIds = await getWorkspaceMemberIds(env, membership.workspace_id);
  if (memberIds.length === 0) {
    return {
      kpis: {
        total_initiatives: 0,
        total_workflows: 0,
        total_tasks: 0,
        total_approvals: 0,
        active_workflows: 0,
        member_count: 0,
      },
      member_breakdown: membership.role === "admin" || workspace.owner_id === userId ? [] : null,
    };
  }

  const buildUserInParams = (select: string) => {
    const params = new URLSearchParams({ select });
    params.set("user_id", `in.(${memberIds.join(",")})`);
    return params;
  };

  const initiativesParams = buildUserInParams("id");
  const workflowsParams = buildUserInParams("id");
  const tasksParams = buildUserInParams("id");
  const approvalsParams = buildUserInParams("id");
  approvalsParams.set("status", "eq.PENDING");
  const activeWorkflowsParams = buildUserInParams("id");
  activeWorkflowsParams.set("status", "in.(pending,running,waiting_approval)");

  const [totalInitiatives, totalWorkflows, totalTasks, totalApprovals, activeWorkflows] =
    await Promise.all([
      countSupabaseAdminRowsSafe(env, `/rest/v1/initiatives?${initiativesParams.toString()}`),
      countSupabaseAdminRowsSafe(
        env,
        `/rest/v1/workflow_executions?${workflowsParams.toString()}`,
      ),
      countSupabaseAdminRowsSafe(env, `/rest/v1/tasks?${tasksParams.toString()}`),
      countSupabaseAdminRowsSafe(env, `/rest/v1/approval_requests?${approvalsParams.toString()}`),
      countSupabaseAdminRowsSafe(
        env,
        `/rest/v1/workflow_executions?${activeWorkflowsParams.toString()}`,
      ),
    ]);

  let memberBreakdown: Array<Record<string, unknown>> | null = null;
  if (membership.role === "admin" || workspace.owner_id === userId) {
    const members = await getWorkspaceMembersForWorkspace(env, membership.workspace_id);
    memberBreakdown = await Promise.all(
      members.map(async (member) => {
        const initiatives = await countSupabaseAdminRowsSafe(
          env,
          `/rest/v1/initiatives?${new URLSearchParams({
            select: "id",
            user_id: `eq.${member.user_id}`,
          }).toString()}`,
        );
        const workflows = await countSupabaseAdminRowsSafe(
          env,
          `/rest/v1/workflow_executions?${new URLSearchParams({
            select: "id",
            user_id: `eq.${member.user_id}`,
          }).toString()}`,
        );
        const tasks = await countSupabaseAdminRowsSafe(
          env,
          `/rest/v1/tasks?${new URLSearchParams({
            select: "id",
            user_id: `eq.${member.user_id}`,
          }).toString()}`,
        );
        const approvals = await countSupabaseAdminRowsSafe(
          env,
          `/rest/v1/approval_requests?${new URLSearchParams({
            select: "id",
            user_id: `eq.${member.user_id}`,
            status: "eq.PENDING",
          }).toString()}`,
        );

        return {
          user_id: member.user_id,
          display_name: member.full_name ?? null,
          email: member.email ?? null,
          initiatives,
          workflows,
          tasks,
          approvals,
        };
      }),
    );
  }

  return {
    kpis: {
      total_initiatives: totalInitiatives,
      total_workflows: totalWorkflows,
      total_tasks: totalTasks,
      total_approvals: totalApprovals,
      active_workflows: activeWorkflows,
      member_count: memberIds.length,
    },
    member_breakdown: memberBreakdown,
  };
}

async function buildTeamSharedInitiativesResponse(request: Request, env: Env, url: URL) {
  const userId = await requireAuthenticatedUserId(request, env);
  const featureDenied = await requireFeatureAccess(request, env, "teams", userId);
  if (featureDenied) {
    throw featureDenied;
  }

  const membership = await getWorkspaceMembershipForUser(env, userId);
  if (!membership?.workspace_id) {
    throw buildErrorResponse(request, env, 404, { detail: "No workspace found" });
  }

  const limit = parseIntegerQueryParam(url, "limit", 50, 1, 200);
  const memberIds = await getWorkspaceMemberIds(env, membership.workspace_id);
  if (memberIds.length === 0) {
    return [];
  }

  const params = new URLSearchParams({
    select: "*",
    order: "updated_at.desc",
    limit: String(limit),
  });
  params.set("user_id", `in.(${memberIds.join(",")})`);

  return fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/initiatives?${params.toString()}`,
  );
}

async function buildTeamSharedWorkflowsResponse(request: Request, env: Env, url: URL) {
  const userId = await requireAuthenticatedUserId(request, env);
  const featureDenied = await requireFeatureAccess(request, env, "teams", userId);
  if (featureDenied) {
    throw featureDenied;
  }

  const membership = await getWorkspaceMembershipForUser(env, userId);
  if (!membership?.workspace_id) {
    throw buildErrorResponse(request, env, 404, { detail: "No workspace found" });
  }

  const limit = parseIntegerQueryParam(url, "limit", 50, 1, 200);
  const memberIds = await getWorkspaceMemberIds(env, membership.workspace_id);
  if (memberIds.length === 0) {
    return [];
  }

  const params = new URLSearchParams({
    select: "*",
    order: "created_at.desc",
    limit: String(limit),
  });
  params.set("user_id", `in.(${memberIds.join(",")})`);

  return fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/workflow_executions?${params.toString()}`,
  );
}

async function buildTeamActivityResponse(request: Request, env: Env, url: URL) {
  const userId = await requireAuthenticatedUserId(request, env);
  const featureDenied = await requireFeatureAccess(request, env, "teams", userId);
  if (featureDenied) {
    throw featureDenied;
  }

  const membership = await getWorkspaceMembershipForUser(env, userId);
  if (!membership?.workspace_id) {
    throw buildErrorResponse(request, env, 404, { detail: "No workspace found" });
  }

  const limit = parseIntegerQueryParam(url, "limit", 100, 1, 500);
  const memberIds = await getWorkspaceMemberIds(env, membership.workspace_id);
  if (memberIds.length === 0) {
    return [];
  }

  const params = new URLSearchParams({
    select: "*",
    order: "created_at.desc",
    limit: String(limit),
  });
  params.set("user_id", `in.(${memberIds.join(",")})`);

  const rows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/governance_audit_log?${params.toString()}`,
  );

  const groups = new Map<string, Array<Record<string, unknown>>>();
  for (const row of rows) {
    const resourceType = typeof row.resource_type === "string" ? row.resource_type : "";
    const resourceId =
      typeof row.resource_id === "string" && row.resource_id.length > 0 ? row.resource_id : null;
    const groupKey = `${resourceType}::${resourceId ?? ""}`;
    const group = groups.get(groupKey) ?? [];
    group.push(row);
    groups.set(groupKey, group);
  }

  const clusters = Array.from(groups.values()).map((events) => {
    const firstEvent = events[0] ?? {};
    const details =
      firstEvent.details && typeof firstEvent.details === "object"
        ? (firstEvent.details as Record<string, unknown>)
        : {};

    return {
      resource_type:
        typeof firstEvent.resource_type === "string" ? firstEvent.resource_type : "",
      resource_id:
        typeof firstEvent.resource_id === "string" ? firstEvent.resource_id : null,
      resource_name:
        typeof details.resource_name === "string" ? details.resource_name : null,
      events,
    };
  });

  clusters.sort((left, right) => {
    const leftTs =
      typeof left.events[0]?.created_at === "string" ? left.events[0].created_at : "";
    const rightTs =
      typeof right.events[0]?.created_at === "string" ? right.events[0].created_at : "";
    return rightTs.localeCompare(leftTs);
  });

  return clusters;
}

async function buildAccountDeletionStatusResponse(
  request: Request,
  env: Env,
  confirmationCode: string,
) {
  if (!DELETION_CONFIRMATION_CODE_RE.test(confirmationCode)) {
    throw buildErrorResponse(request, env, 404, { detail: "Deletion request not found" });
  }

  const params = new URLSearchParams({
    select: "id,status,platform,requested_at,completed_at",
    confirmation_code: `eq.${confirmationCode}`,
    limit: "1",
  });
  const rows = await fetchSupabaseAdminRows<Array<DataDeletionRequestRecord>>(
    env,
    `/rest/v1/data_deletion_requests?${params.toString()}`,
  );

  const row = rows[0];
  if (!row?.id) {
    throw buildErrorResponse(request, env, 404, { detail: "Deletion request not found" });
  }

  return {
    id: String(row.id),
    status: row.status,
    platform: row.platform,
    requested_at: String(row.requested_at),
    completed_at: row.completed_at ? String(row.completed_at) : null,
  };
}

async function buildAccountDeleteResponse(request: Request, env: Env) {
  const userId = await requireAuthenticatedUserId(request, env);
  const confirmationCode = randomBase64Url(16);

  await insertSupabaseAdminRow<Array<Record<string, unknown>>>(
    env,
    "/rest/v1/data_deletion_requests?select=id",
    {
      user_id: userId,
      platform: "self",
      status: "pending",
      confirmation_code: confirmationCode,
    },
  );

  try {
    await invokeSupabaseAdminRpc(env, "delete_user_account", { p_user_id: userId });
  } catch (error) {
    await updateSupabaseAdminRows<Array<Record<string, unknown>>>(
      env,
      `/rest/v1/data_deletion_requests?confirmation_code=eq.${confirmationCode}`,
      {
        status: "failed",
        error_detail: "Database deletion failed",
      },
    );

    throw buildErrorResponse(request, env, 500, {
      detail:
        "Account deletion failed. Please contact privacy@pikar-ai.com for assistance.",
    });
  }

  return {
    success: true,
    message: ACCOUNT_DELETE_SUCCESS_MESSAGE,
  };
}

async function verifyFacebookSignedRequest(
  signedRequest: string,
  appSecret: string,
): Promise<Record<string, unknown>> {
  const [encodedSignature, payloadRaw] = signedRequest.split(".", 2);
  if (!encodedSignature || !payloadRaw) {
    throw new Error("Malformed signed_request");
  }

  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(appSecret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const signature = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(payloadRaw));
  const expectedSignature = toBase64Url(new Uint8Array(signature));
  if (!constantTimeEqual(expectedSignature, encodedSignature)) {
    throw new Error("Invalid signature");
  }

  let payload: unknown;
  try {
    payload = JSON.parse(new TextDecoder().decode(fromBase64Url(payloadRaw)));
  } catch {
    throw new Error("Invalid payload encoding");
  }

  const record = asRecord(payload);
  if (!record) {
    throw new Error("Invalid payload encoding");
  }

  return record;
}

async function buildFacebookDeletionCallbackResponse(request: Request, env: Env) {
  const appSecret = env.FACEBOOK_APP_SECRET?.trim();
  if (!appSecret) {
    throw buildErrorResponse(request, env, 500, {
      detail: "Server configuration error",
    });
  }

  let formData: FormData;
  try {
    formData = await request.formData();
  } catch {
    throw buildErrorResponse(request, env, 400, {
      detail: "Missing signed_request",
    });
  }
  const signedRequest = formData.get("signed_request");
  if (typeof signedRequest !== "string" || !signedRequest.trim()) {
    throw buildErrorResponse(request, env, 400, {
      detail: "Missing signed_request",
    });
  }

  let payload: Record<string, unknown>;
  try {
    payload = await verifyFacebookSignedRequest(signedRequest.trim(), appSecret);
  } catch (error) {
    throw buildErrorResponse(request, env, 400, {
      detail: error instanceof Error ? error.message : "Invalid signed_request",
    });
  }

  const facebookUserId =
    typeof payload.user_id === "string" || typeof payload.user_id === "number"
      ? String(payload.user_id)
      : "";
  if (!facebookUserId) {
    throw buildErrorResponse(request, env, 400, {
      detail: "Missing user_id in signed request",
    });
  }

  const existingParams = new URLSearchParams({
    select: "confirmation_code",
    facebook_user_id: `eq.${facebookUserId}`,
    platform: "eq.facebook",
    status: "in.(pending,completed)",
    limit: "1",
  });
  const existingRows = await fetchSupabaseAdminRows<Array<DataDeletionRequestRecord>>(
    env,
    `/rest/v1/data_deletion_requests?${existingParams.toString()}`,
  );
  const existingCode = existingRows[0]?.confirmation_code?.trim();
  const appOrigin = getPrimaryAppOrigin(env).replace(/\/+$/g, "");
  if (existingCode) {
    return {
      url: `${appOrigin}/data-deletion/status?id=${encodeURIComponent(existingCode)}`,
      confirmation_code: existingCode,
    };
  }

  const accountParams = new URLSearchParams({
    select: "user_id",
    platform: "eq.facebook",
    platform_user_id: `eq.${facebookUserId}`,
    limit: "1",
  });
  const accountRows = await fetchSupabaseAdminRows<Array<{ user_id?: string | null }>>(
    env,
    `/rest/v1/connected_accounts?${accountParams.toString()}`,
  );
  const linkedUserId = accountRows[0]?.user_id ?? null;
  const confirmationCode = randomBase64Url(16);

  await insertSupabaseAdminRow<Array<Record<string, unknown>>>(
    env,
    "/rest/v1/data_deletion_requests?select=id",
    {
      user_id: linkedUserId,
      platform: "facebook",
      facebook_user_id: facebookUserId,
      status: "pending",
      confirmation_code: confirmationCode,
    },
  );

  if (linkedUserId) {
    try {
      await invokeSupabaseAdminRpc(env, "delete_user_account", { p_user_id: linkedUserId });
    } catch {
      await updateSupabaseAdminRows<Array<Record<string, unknown>>>(
        env,
        `/rest/v1/data_deletion_requests?confirmation_code=eq.${confirmationCode}`,
        {
          status: "failed",
          error_detail: "Database deletion failed",
        },
      );
    }
  } else {
    await updateSupabaseAdminRows<Array<Record<string, unknown>>>(
      env,
      `/rest/v1/data_deletion_requests?confirmation_code=eq.${confirmationCode}`,
      {
        status: "completed",
        completed_at: new Date().toISOString(),
      },
    );
  }

  return {
    url: `${appOrigin}/data-deletion/status?id=${encodeURIComponent(confirmationCode)}`,
    confirmation_code: confirmationCode,
  };
}

async function queryExportRows(
  env: Env,
  tableName: string,
  options: {
    userColumn?: string;
    userValue: string;
    orderBy?: string;
    desc?: boolean;
  },
): Promise<Array<Record<string, unknown>>> {
  const params = new URLSearchParams({ select: "*" });
  params.set(options.userColumn ?? "user_id", `eq.${options.userValue}`);
  if (options.orderBy) {
    params.set("order", `${options.orderBy}.${options.desc ? "desc" : "asc"}`);
  }

  const rows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/${tableName}?${params.toString()}`,
  );
  return rows.map((row) => (asRecord(redactSensitiveData(row)) ?? {}));
}

async function queryExportInRows(
  env: Env,
  tableName: string,
  column: string,
  values: unknown[],
  options: {
    orderBy?: string;
    desc?: boolean;
  } = {},
): Promise<Array<Record<string, unknown>>> {
  const scopedValues = values
    .map((value) => (value === null || value === undefined ? null : String(value)))
    .filter((value): value is string => Boolean(value));
  if (scopedValues.length === 0) {
    return [];
  }

  const params = new URLSearchParams({ select: "*" });
  params.set(column, `in.(${scopedValues.join(",")})`);
  if (options.orderBy) {
    params.set("order", `${options.orderBy}.${options.desc ? "desc" : "asc"}`);
  }

  const rows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/${tableName}?${params.toString()}`,
  );
  return rows.map((row) => (asRecord(redactSensitiveData(row)) ?? {}));
}

async function queryExportDepartmentTasks(
  env: Env,
  userId: string,
): Promise<Array<Record<string, unknown>>> {
  const params = new URLSearchParams({
    select: "*",
    order: "created_at.desc",
  });
  params.set("or", `(created_by.eq.${userId},assigned_to.eq.${userId})`);

  const rows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/department_tasks?${params.toString()}`,
  );
  return rows.map((row) => (asRecord(redactSensitiveData(row)) ?? {}));
}

async function safeBuildExportSection<T>(
  warnings: string[],
  section: string,
  loader: () => Promise<T>,
  fallback: T,
): Promise<T> {
  try {
    return await loader();
  } catch (error) {
    warnings.push(`${section}: unavailable during export`);
    return fallback;
  }
}

async function buildPersonalDataExportPayload(
  request: Request,
  env: Env,
  userId: string,
): Promise<Record<string, unknown>> {
  const authUser = await fetchSupabaseUser(request, env);
  const warnings: string[] = [];
  const generatedAt = new Date().toISOString();

  const authUserSection = await safeBuildExportSection(
    warnings,
    "auth_user",
    async () => {
      const adminUser = await fetchSupabaseAdminAuthUser(env, userId);
      if (!adminUser) {
        return null;
      }

      const identities = Array.isArray(adminUser.identities)
        ? adminUser.identities
            .map((identity) => asRecord(identity))
            .map((identity) => identity?.provider)
            .filter((provider): provider is string => typeof provider === "string")
        : Array.isArray(authUser.identities)
          ? authUser.identities
              .map((identity) => identity?.provider)
              .filter((provider): provider is string => typeof provider === "string")
          : [];

      return redactSensitiveData({
        id: adminUser.id ?? userId,
        email: adminUser.email ?? authUser.email ?? null,
        phone: adminUser.phone ?? null,
        role: adminUser.role ?? null,
        created_at: adminUser.created_at ?? null,
        last_sign_in_at: adminUser.last_sign_in_at ?? null,
        app_metadata: asRecord(adminUser.app_metadata) ?? {},
        user_metadata: asRecord(adminUser.user_metadata) ?? {},
        providers: identities,
      });
    },
    null,
  );

  const account = {
    auth_user: authUserSection,
    profile: await safeBuildExportSection(
      warnings,
      "users_profile",
      async () => (await queryExportRows(env, "users_profile", { userValue: userId }))[0] ?? null,
      null,
    ),
    legacy_agent_config: await safeBuildExportSection(
      warnings,
      "user_executive_agents",
      async () =>
        (await queryExportRows(env, "user_executive_agents", { userValue: userId }))[0] ?? null,
      null,
    ),
  };

  const workflowExecutions = await safeBuildExportSection(
    warnings,
    "workflow_executions",
    async () =>
      queryExportRows(env, "workflow_executions", {
        userValue: userId,
        orderBy: "created_at",
        desc: true,
      }),
    [] as Array<Record<string, unknown>>,
  );

  const payload = {
    account,
    privacy: {
      data_deletion_requests: await safeBuildExportSection(
        warnings,
        "data_deletion_requests",
        async () =>
          queryExportRows(env, "data_deletion_requests", {
            userValue: userId,
            orderBy: "requested_at",
            desc: true,
          }),
        [] as Array<Record<string, unknown>>,
      ),
    },
    conversations: {
      sessions: await safeBuildExportSection(
        warnings,
        "sessions",
        async () =>
          queryExportRows(env, "sessions", {
            userValue: userId,
            orderBy: "updated_at",
            desc: true,
          }),
        [] as Array<Record<string, unknown>>,
      ),
      session_events: await safeBuildExportSection(
        warnings,
        "session_events",
        async () =>
          queryExportRows(env, "session_events", {
            userValue: userId,
            orderBy: "created_at",
          }),
        [] as Array<Record<string, unknown>>,
      ),
    },
    initiatives: await safeBuildExportSection(
      warnings,
      "initiatives",
      async () =>
        queryExportRows(env, "initiatives", {
          userValue: userId,
          orderBy: "created_at",
          desc: true,
        }),
      [] as Array<Record<string, unknown>>,
    ),
    workflows: {
      workflow_executions: workflowExecutions,
      workflow_steps: await safeBuildExportSection(
        warnings,
        "workflow_steps",
        async () =>
          queryExportInRows(
            env,
            "workflow_steps",
            "execution_id",
            workflowExecutions.map((row) => row.id),
            { orderBy: "created_at" },
          ),
        [] as Array<Record<string, unknown>>,
      ),
    },
    content: {
      campaigns: await safeBuildExportSection(
        warnings,
        "campaigns",
        async () =>
          queryExportRows(env, "campaigns", {
            userValue: userId,
            orderBy: "created_at",
            desc: true,
          }),
        [] as Array<Record<string, unknown>>,
      ),
      content_bundles: await safeBuildExportSection(
        warnings,
        "content_bundles",
        async () =>
          queryExportRows(env, "content_bundles", {
            userValue: userId,
            orderBy: "created_at",
            desc: true,
          }),
        [] as Array<Record<string, unknown>>,
      ),
      vault_documents: await safeBuildExportSection(
        warnings,
        "vault_documents",
        async () =>
          queryExportRows(env, "vault_documents", {
            userValue: userId,
            orderBy: "created_at",
            desc: true,
          }),
        [] as Array<Record<string, unknown>>,
      ),
      agent_google_docs: await safeBuildExportSection(
        warnings,
        "agent_google_docs",
        async () =>
          queryExportRows(env, "agent_google_docs", {
            userValue: userId,
            orderBy: "created_at",
            desc: true,
          }),
        [] as Array<Record<string, unknown>>,
      ),
    },
    sales: {
      contacts: await safeBuildExportSection(
        warnings,
        "contacts",
        async () =>
          queryExportRows(env, "contacts", {
            userValue: userId,
            orderBy: "created_at",
            desc: true,
          }),
        [] as Array<Record<string, unknown>>,
      ),
      contact_activities: await safeBuildExportSection(
        warnings,
        "contact_activities",
        async () =>
          queryExportRows(env, "contact_activities", {
            userValue: userId,
            orderBy: "created_at",
            desc: true,
          }),
        [] as Array<Record<string, unknown>>,
      ),
    },
    finance: {
      financial_records: await safeBuildExportSection(
        warnings,
        "financial_records",
        async () =>
          queryExportRows(env, "financial_records", {
            userValue: userId,
            orderBy: "created_at",
            desc: true,
          }),
        [] as Array<Record<string, unknown>>,
      ),
    },
    operations: {
      department_tasks: await safeBuildExportSection(
        warnings,
        "department_tasks",
        async () => queryExportDepartmentTasks(env, userId),
        [] as Array<Record<string, unknown>>,
      ),
    },
    support: {
      support_tickets: await safeBuildExportSection(
        warnings,
        "support_tickets",
        async () =>
          queryExportRows(env, "support_tickets", {
            userValue: userId,
            orderBy: "created_at",
            desc: true,
          }),
        [] as Array<Record<string, unknown>>,
      ),
    },
    people: {
      recruitment_jobs: await safeBuildExportSection(
        warnings,
        "recruitment_jobs",
        async () =>
          queryExportRows(env, "recruitment_jobs", {
            userValue: userId,
            orderBy: "created_at",
            desc: true,
          }),
        [] as Array<Record<string, unknown>>,
      ),
      recruitment_candidates: await safeBuildExportSection(
        warnings,
        "recruitment_candidates",
        async () =>
          queryExportRows(env, "recruitment_candidates", {
            userValue: userId,
            orderBy: "created_at",
            desc: true,
          }),
        [] as Array<Record<string, unknown>>,
      ),
    },
    compliance: {
      compliance_audits: await safeBuildExportSection(
        warnings,
        "compliance_audits",
        async () =>
          queryExportRows(env, "compliance_audits", {
            userValue: userId,
            orderBy: "created_at",
            desc: true,
          }),
        [] as Array<Record<string, unknown>>,
      ),
      compliance_risks: await safeBuildExportSection(
        warnings,
        "compliance_risks",
        async () =>
          queryExportRows(env, "compliance_risks", {
            userValue: userId,
            orderBy: "created_at",
            desc: true,
          }),
        [] as Array<Record<string, unknown>>,
      ),
    },
    integrations: {
      connected_accounts: await safeBuildExportSection(
        warnings,
        "connected_accounts",
        async () =>
          queryExportRows(env, "connected_accounts", {
            userValue: userId,
            orderBy: "connected_at",
            desc: true,
          }),
        [] as Array<Record<string, unknown>>,
      ),
      integration_credentials: await safeBuildExportSection(
        warnings,
        "integration_credentials",
        async () =>
          queryExportRows(env, "integration_credentials", {
            userValue: userId,
            orderBy: "updated_at",
            desc: true,
          }),
        [] as Array<Record<string, unknown>>,
      ),
      integration_sync_state: await safeBuildExportSection(
        warnings,
        "integration_sync_state",
        async () =>
          queryExportRows(env, "integration_sync_state", {
            userValue: userId,
            orderBy: "updated_at",
            desc: true,
          }),
        [] as Array<Record<string, unknown>>,
      ),
    },
    configuration: {
      user_configurations: await safeBuildExportSection(
        warnings,
        "user_configurations",
        async () =>
          queryExportRows(env, "user_configurations", {
            userValue: userId,
            orderBy: "updated_at",
            desc: true,
          }),
        [] as Array<Record<string, unknown>>,
      ),
    },
  };

  const manifest = {
    version: 1,
    generated_at: generatedAt,
    user_id: userId,
    format: "json",
    sections: Object.keys(payload),
    redactions: [
      "OAuth access and refresh tokens are redacted.",
      "Sensitive user configuration values are redacted.",
      "Opaque integration sync cursors are redacted.",
    ],
    warnings,
  };

  return {
    manifest,
    ...payload,
  };
}

async function buildAccountExportResponse(request: Request, env: Env) {
  const userId = await requireAuthenticatedUserId(request, env);
  const payload = await buildPersonalDataExportPayload(request, env, userId);
  const archiveBytes = new TextEncoder().encode(
    JSON.stringify(sortJsonKeysDeep(payload), null, 2),
  );

  const timestamp = new Date().toISOString().replace(/[-:.]/g, "").replace(/\d{3}Z$/, "Z");
  const filename = `personal-data-export_${timestamp}_${randomBase64Url(6)}.json`;
  const storagePath = `${userId}/privacy-exports/${filename}`;

  try {
    await uploadSupabaseStorageObject(
      env,
      EXPORT_BUCKET_NAME,
      storagePath,
      archiveBytes,
      EXPORT_JSON_CONTENT_TYPE,
    );
    const signedUrl = await createSupabaseStorageSignedUrl(
      env,
      EXPORT_BUCKET_NAME,
      storagePath,
      EXPORT_SIGNED_URL_EXPIRY_SECONDS,
    );

    const manifest = asRecord(payload.manifest) ?? {};
    return {
      success: true,
      message: "Your personal data export is ready to download.",
      url: signedUrl,
      filename,
      size_bytes: archiveBytes.byteLength,
      format: "json",
      generated_at:
        typeof manifest.generated_at === "string" ? manifest.generated_at : new Date().toISOString(),
      sections: Array.isArray(manifest.sections) ? manifest.sections : [],
      warnings: Array.isArray(manifest.warnings) ? manifest.warnings : [],
    };
  } catch {
    throw buildErrorResponse(request, env, 500, {
      detail:
        "Personal data export failed. Please try again or contact privacy@pikar-ai.com.",
    });
  }
}

async function buildOnboardingStatusResponse(request: Request, env: Env): Promise<OnboardingStatusResponse> {
  const userId = await requireAuthenticatedUserId(request, env);
  const [profileRow, agentRow] = await Promise.all([
    fetchOnboardingProfileRow(env, userId),
    fetchOnboardingAgentRow(env, userId),
  ]);

  const businessContextCompleted = hasNonEmptyJsonValue(profileRow.business_context);
  const preferencesCompleted = hasNonEmptyJsonValue(profileRow.preferences);
  const agentName =
    typeof agentRow.agent_name === "string" && agentRow.agent_name.trim()
      ? agentRow.agent_name.trim()
      : null;
  const agentSetupCompleted = Boolean(agentName);
  const isCompleted = agentRow.onboarding_completed === true;

  let currentStep = 0;
  if (businessContextCompleted) {
    currentStep = 1;
  }
  if (preferencesCompleted) {
    currentStep = 2;
  }
  if (agentSetupCompleted) {
    currentStep = 3;
  }
  if (isCompleted) {
    currentStep = 4;
  }

  return {
    is_completed: isCompleted,
    current_step: currentStep,
    total_steps: 4,
    business_context_completed: businessContextCompleted,
    preferences_completed: preferencesCompleted,
    agent_setup_completed: agentSetupCompleted,
    persona:
      typeof profileRow.persona === "string" && profileRow.persona.trim()
        ? profileRow.persona.trim()
        : null,
    agent_name: agentName,
  };
}

async function buildOnboardingBusinessContextResponse(request: Request, env: Env) {
  const userId = await requireAuthenticatedUserId(request, env);
  let payload: Record<string, unknown>;
  try {
    payload = (await request.json()) as Record<string, unknown>;
  } catch {
    throw buildErrorResponse(request, env, 400, {
      detail: "Request body must be valid JSON.",
    });
  }

  const context = parseBusinessContextPayload(payload, request, env);
  await ensureOnboardingSeedRows(env, userId);
  await updateSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/users_profile?user_id=eq.${userId}`,
    {
      business_context: context,
      persona: determineOnboardingPersona(context),
      updated_at: new Date().toISOString(),
    },
  );

  return { status: "success" };
}

async function buildOnboardingPreferencesResponse(request: Request, env: Env) {
  const userId = await requireAuthenticatedUserId(request, env);
  let payload: Record<string, unknown>;
  try {
    payload = (await request.json()) as Record<string, unknown>;
  } catch {
    throw buildErrorResponse(request, env, 400, {
      detail: "Request body must be valid JSON.",
    });
  }

  const preferences = parseUserPreferencesPayload(payload, request, env);
  await ensureOnboardingSeedRows(env, userId);
  await updateSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/users_profile?user_id=eq.${userId}`,
    {
      preferences,
      updated_at: new Date().toISOString(),
    },
  );

  return { status: "success" };
}

async function buildOnboardingAgentSetupResponse(request: Request, env: Env) {
  const userId = await requireAuthenticatedUserId(request, env);
  let payload: Record<string, unknown>;
  try {
    payload = (await request.json()) as Record<string, unknown>;
  } catch {
    throw buildErrorResponse(request, env, 400, {
      detail: "Request body must be valid JSON.",
    });
  }

  const setup = parseAgentSetupPayload(payload, request, env);
  await ensureOnboardingSeedRows(env, userId);

  const [profileRow, agentRow] = await Promise.all([
    fetchOnboardingProfileRow(env, userId),
    fetchOnboardingAgentRow(env, userId),
  ]);
  const agentConfiguration = asRecord(agentRow.configuration);
  const currentConfig: Record<string, unknown> = {
    business_context: asRecord(profileRow.business_context) ?? {},
    preferences: asRecord(profileRow.preferences) ?? {},
  };
  if (agentConfiguration?.agent_setup !== undefined) {
    currentConfig.agent_setup = agentConfiguration.agent_setup;
  }
  currentConfig.agent_setup = setup;

  await updateSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/user_executive_agents?user_id=eq.${userId}`,
    {
      configuration: currentConfig,
      agent_name: setup.agent_name,
      updated_at: new Date().toISOString(),
    },
  );

  return { status: "success" };
}

async function buildOnboardingSwitchPersonaResponse(request: Request, env: Env) {
  const userId = await requireAuthenticatedUserId(request, env);
  let payload: Record<string, unknown>;
  try {
    payload = (await request.json()) as Record<string, unknown>;
  } catch {
    throw buildErrorResponse(request, env, 400, {
      detail: "Request body must be valid JSON.",
    });
  }

  const rawPersona = requireTextField(payload, "new_persona", request, env);
  const persona = normalizePersonaTier(rawPersona);
  if (!persona) {
    throw buildErrorResponse(request, env, 400, {
      detail: `Invalid persona: ${rawPersona}. Must be one of solopreneur, startup, sme, enterprise`,
    });
  }

  const updatedAt = new Date().toISOString();
  await Promise.all([
    updateSupabaseAdminRows<Array<Record<string, unknown>>>(
      env,
      `/rest/v1/users_profile?user_id=eq.${userId}`,
      {
        persona,
        updated_at: updatedAt,
      },
    ),
    updateSupabaseAdminRows<Array<Record<string, unknown>>>(
      env,
      `/rest/v1/user_executive_agents?user_id=eq.${userId}`,
      {
        persona,
        updated_at: updatedAt,
      },
    ),
  ]);

  return {
    status: "success",
    persona,
  };
}

function resolveOnboardingFirstName(businessContext: Record<string, unknown>): string | null {
  const role = typeof businessContext.role === "string" ? businessContext.role.trim() : "";
  if (!role) {
    return null;
  }

  const lowerRole = role.toLowerCase();
  const roleKeywords = ["ceo", "cto", "founder", "director", "manager", "vp", "head"];
  if (roleKeywords.some((keyword) => lowerRole.includes(keyword))) {
    return null;
  }

  const firstToken = role.split(/\s+/)[0]?.trim();
  return firstToken || null;
}

async function schedulePostOnboardingSetup(
  env: Env,
  userId: string,
  persona: PersonaTier,
  businessContext: Record<string, unknown>,
): Promise<void> {
  const now = new Date();
  const authUser = await fetchSupabaseAdminAuthUser(env, userId);
  const email = typeof authUser?.email === "string" ? authUser.email : null;

  if (email) {
    const firstName = resolveOnboardingFirstName(businessContext);
    const schedule = [
      { drip_key: "welcome", drip_day: 0, scheduled_at: now.toISOString() },
      {
        drip_key: "tips",
        drip_day: 3,
        scheduled_at: new Date(now.getTime() + 3 * 24 * 60 * 60 * 1000).toISOString(),
      },
      {
        drip_key: "checkin",
        drip_day: 7,
        scheduled_at: new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000).toISOString(),
      },
    ];

    await Promise.all(
      schedule.map((entry) =>
        upsertSupabaseAdminRow<Array<Record<string, unknown>>>(
          env,
          "/rest/v1/onboarding_drip_emails?on_conflict=user_id,drip_key&select=user_id",
          {
            user_id: userId,
            email,
            first_name: firstName,
            persona,
            ...entry,
          },
        )
      ),
    );
  }

  await upsertSupabaseAdminMergeRow<Array<Record<string, unknown>>>(
    env,
    "/rest/v1/onboarding_checklist?on_conflict=user_id&select=user_id",
    {
      user_id: userId,
      persona,
      items: PERSONA_ONBOARDING_CHECKLISTS[persona],
      updated_at: now.toISOString(),
    },
  );
}

async function buildOnboardingCompleteResponse(request: Request, env: Env) {
  const userId = await requireAuthenticatedUserId(request, env);
  await ensureOnboardingSeedRows(env, userId);

  const profileRow = await fetchOnboardingProfileRow(env, userId);
  const businessContext = asRecord(profileRow.business_context);
  if (!businessContext || Object.keys(businessContext).length === 0) {
    throw buildErrorResponse(request, env, 500, {
      detail: "Failed to complete onboarding",
    });
  }

  const persona =
    normalizePersonaTier(typeof profileRow.persona === "string" ? profileRow.persona : null) ??
    determineOnboardingPersona({
      company_name:
        typeof businessContext.company_name === "string" ? businessContext.company_name : "My Business",
      industry: typeof businessContext.industry === "string" ? businessContext.industry : "Other",
      description:
        typeof businessContext.description === "string" ? businessContext.description : "",
      goals: Array.isArray(businessContext.goals)
        ? businessContext.goals.filter((goal): goal is string => typeof goal === "string")
        : ["growth"],
      team_size: typeof businessContext.team_size === "string" ? businessContext.team_size : null,
      role: typeof businessContext.role === "string" ? businessContext.role : null,
      website: typeof businessContext.website === "string" ? businessContext.website : null,
    });

  await updateSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/user_executive_agents?user_id=eq.${userId}`,
    {
      onboarding_completed: true,
      persona,
      updated_at: new Date().toISOString(),
    },
  );

  try {
    await schedulePostOnboardingSetup(env, userId, persona, businessContext);
  } catch {
    // Match the backend behavior: post-onboarding setup is best effort and non-fatal.
  }

  return {
    status: "success",
    persona,
  };
}

async function buildOnboardingExtractContextResponse(request: Request, env: Env) {
  let payload: Record<string, unknown>;
  try {
    payload = (await request.json()) as Record<string, unknown>;
  } catch {
    throw buildErrorResponse(request, env, 400, {
      detail: "Request body must be valid JSON.",
    });
  }

  const sanitizedPayload = parseOnboardingExtractContextPayload(payload, request, env);
  const headers = new Headers(request.headers);
  headers.set("content-type", "application/json");

  const proxiedRequest = new Request(request.url, {
    method: request.method,
    headers,
    body: JSON.stringify(sanitizedPayload),
  });

  return proxyFallback(proxiedRequest, env, "native-verified-proxy");
}

async function buildSupportTicketsListResponse(
  request: Request,
  env: Env,
  url: URL,
): Promise<SupportTicketRecord[]> {
  const userId = await requireAuthenticatedUserId(request, env);
  const limit = parseIntegerQueryParam(url, "limit", 50, 1, 200);
  const offset = parseIntegerQueryParam(url, "offset", 0, 0, 5000);

  const params = new URLSearchParams({
    select:
      "id,user_id,subject,description,customer_email,priority,status,assigned_to,resolution,created_at",
    user_id: `eq.${userId}`,
    order: "created_at.desc",
    limit: String(limit),
    offset: String(offset),
  });

  const status = url.searchParams.get("status")?.trim();
  if (status) {
    params.set("status", `eq.${status}`);
  }

  const priority = url.searchParams.get("priority")?.trim();
  if (priority) {
    params.set("priority", `eq.${priority}`);
  }

  const rows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/support_tickets?${params.toString()}`,
  );
  return rows.map((row) => normalizeSupportTicketRecord(row));
}

async function buildSupportTicketCreateResponse(
  request: Request,
  env: Env,
): Promise<SupportTicketRecord> {
  const userId = await requireAuthenticatedUserId(request, env);
  let payload: Record<string, unknown>;
  try {
    payload = (await request.json()) as Record<string, unknown>;
  } catch {
    throw buildErrorResponse(request, env, 400, {
      detail: "Request body must be valid JSON.",
    });
  }

  const ticket = parseCreateSupportTicketPayload(payload, request, env);
  const rows = await insertSupabaseAdminRow<Array<Record<string, unknown>>>(
    env,
    "/rest/v1/support_tickets?select=id,user_id,subject,description,customer_email,priority,status,assigned_to,resolution,created_at",
    {
      ...ticket,
      user_id: userId,
      status: "new",
      source: "manual",
      sentiment: "neutral",
    },
  );

  return normalizeSupportTicketRecord(asRecord(rows[0]) ?? {});
}

async function buildSupportTicketUpdateResponse(
  request: Request,
  env: Env,
  ticketId: string,
): Promise<SupportTicketRecord> {
  const userId = await requireAuthenticatedUserId(request, env);
  let payload: Record<string, unknown>;
  try {
    payload = (await request.json()) as Record<string, unknown>;
  } catch {
    throw buildErrorResponse(request, env, 400, {
      detail: "Request body must be valid JSON.",
    });
  }

  const update = parseUpdateSupportTicketPayload(payload, request, env);
  const rows = await updateSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/support_tickets?id=eq.${encodeURIComponent(ticketId)}&user_id=eq.${userId}&select=id,user_id,subject,description,customer_email,priority,status,assigned_to,resolution,created_at`,
    update,
  );
  if (rows.length === 0) {
    throw buildErrorResponse(request, env, 404, {
      detail: "Ticket not found",
    });
  }

  return normalizeSupportTicketRecord(asRecord(rows[0]) ?? {});
}

async function buildSupportTicketDeleteResponse(
  request: Request,
  env: Env,
  ticketId: string,
): Promise<Response> {
  const userId = await requireAuthenticatedUserId(request, env);
  const rows = await deleteSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/support_tickets?id=eq.${encodeURIComponent(ticketId)}&user_id=eq.${userId}&select=id`,
  );
  if (rows.length === 0) {
    throw buildErrorResponse(request, env, 404, {
      detail: "Ticket not found",
    });
  }

  return noContentWithCors(request, env);
}

async function buildCommunityPostsListResponse(
  request: Request,
  env: Env,
  url: URL,
): Promise<CommunityPostRecord[]> {
  await requireAuthenticatedUserId(request, env);
  const limit = parseIntegerQueryParam(url, "limit", 50, 1, 200);
  const offset = parseIntegerQueryParam(url, "offset", 0, 0, 5000);

  const params = new URLSearchParams({
    select: "id,user_id,author_name,title,body,category,tags,upvotes,reply_count,is_pinned,created_at,updated_at",
    limit: String(limit),
    offset: String(offset),
  });

  const category = url.searchParams.get("category")?.trim();
  if (category) {
    params.set("category", `eq.${category}`);
  }

  const sort = url.searchParams.get("sort")?.trim().toLowerCase();
  params.set("order", sort === "popular" ? "upvotes.desc,created_at.desc" : "created_at.desc");

  const rows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/community_posts?${params.toString()}`,
  );
  return rows.map((row) => normalizeCommunityPostRecord(row));
}

async function buildCommunityPostCreateResponse(
  request: Request,
  env: Env,
): Promise<CommunityPostRecord> {
  const userId = await requireAuthenticatedUserId(request, env);
  let payload: Record<string, unknown>;
  try {
    payload = (await request.json()) as Record<string, unknown>;
  } catch {
    throw buildErrorResponse(request, env, 400, {
      detail: "Request body must be valid JSON.",
    });
  }

  const post = parseCreateCommunityPostPayload(payload, request, env);
  const authorName = await resolveCommunityAuthorName(env, userId);
  const rows = await insertSupabaseAdminRow<Array<Record<string, unknown>>>(
    env,
    "/rest/v1/community_posts?select=id,user_id,author_name,title,body,category,tags,upvotes,reply_count,is_pinned,created_at,updated_at",
    {
      user_id: userId,
      author_name: authorName,
      ...post,
    },
  );

  return normalizeCommunityPostRecord(asRecord(rows[0]) ?? {});
}

async function fetchCommunityPostRecord(
  env: Env,
  postId: string,
): Promise<Record<string, unknown> | null> {
  const rows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/community_posts?id=eq.${encodeURIComponent(postId)}&select=id,user_id,author_name,title,body,category,tags,upvotes,reply_count,is_pinned,created_at,updated_at&limit=1`,
  );
  return asRecord(rows[0]) ?? null;
}

async function buildCommunityPostDetailResponse(
  request: Request,
  env: Env,
  postId: string,
): Promise<{ post: CommunityPostRecord; comments: CommunityCommentRecord[] }> {
  await requireAuthenticatedUserId(request, env);
  const postRow = await fetchCommunityPostRecord(env, postId);
  if (!postRow) {
    throw buildErrorResponse(request, env, 404, {
      detail: "Post not found",
    });
  }

  const commentRows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/community_comments?post_id=eq.${encodeURIComponent(postId)}&select=id,post_id,user_id,author_name,body,upvotes,created_at&order=created_at.asc`,
  );

  return {
    post: normalizeCommunityPostRecord(postRow),
    comments: commentRows.map((row) => normalizeCommunityCommentRecord(row)),
  };
}

async function buildCommunityCommentCreateResponse(
  request: Request,
  env: Env,
  postId: string,
): Promise<CommunityCommentRecord> {
  const userId = await requireAuthenticatedUserId(request, env);
  let payload: Record<string, unknown>;
  try {
    payload = (await request.json()) as Record<string, unknown>;
  } catch {
    throw buildErrorResponse(request, env, 400, {
      detail: "Request body must be valid JSON.",
    });
  }

  const comment = parseCreateCommunityCommentPayload(payload, request, env);
  const postRow = await fetchCommunityPostRecord(env, postId);
  if (!postRow) {
    throw buildErrorResponse(request, env, 404, {
      detail: "Post not found",
    });
  }

  const authorName = await resolveCommunityAuthorName(env, userId);
  const rows = await insertSupabaseAdminRow<Array<Record<string, unknown>>>(
    env,
    "/rest/v1/community_comments?select=id,post_id,user_id,author_name,body,upvotes,created_at",
    {
      post_id: postId,
      user_id: userId,
      author_name: authorName,
      ...comment,
    },
  );

  return normalizeCommunityCommentRecord(asRecord(rows[0]) ?? {});
}

async function buildCommunityUpvoteToggleResponse(
  request: Request,
  env: Env,
  postId: string,
): Promise<{ upvoted: boolean; upvotes: number }> {
  const userId = await requireAuthenticatedUserId(request, env);
  const postRow = await fetchCommunityPostRecord(env, postId);
  if (!postRow) {
    throw buildErrorResponse(request, env, 404, {
      detail: "Post not found",
    });
  }

  const existingRows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/community_upvotes?user_id=eq.${userId}&post_id=eq.${encodeURIComponent(postId)}&select=user_id&limit=1`,
  );

  let upvoted = false;
  if (existingRows.length > 0) {
    await deleteSupabaseAdminRows<Array<Record<string, unknown>>>(
      env,
      `/rest/v1/community_upvotes?user_id=eq.${userId}&post_id=eq.${encodeURIComponent(postId)}&select=user_id`,
    );
  } else {
    await insertSupabaseAdminRow<Array<Record<string, unknown>>>(
      env,
      "/rest/v1/community_upvotes?select=user_id",
      {
        user_id: userId,
        post_id: postId,
      },
    );
    upvoted = true;
  }

  const upvoteRows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/community_upvotes?post_id=eq.${encodeURIComponent(postId)}&select=user_id`,
  );
  const upvoteCount = upvoteRows.length;

  await updateSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/community_posts?id=eq.${encodeURIComponent(postId)}&select=id`,
    {
      upvotes: upvoteCount,
    },
  );

  return {
    upvoted,
    upvotes: upvoteCount,
  };
}

async function buildPagesListResponse(request: Request, env: Env): Promise<{ pages: LandingPageRecord[]; count: number }> {
  const userId = await requireAuthenticatedUserId(request, env);
  const rows =
    (await invokeSupabaseAdminRpc<Array<Record<string, unknown>>>(
      env,
      "get_user_pages_with_counts",
      { p_user_id: userId },
    )) ?? [];
  const pages = rows.map((row) => normalizeLandingPageRecord(row));
  return {
    pages,
    count: pages.length,
  };
}

async function buildPageGetResponse(request: Request, env: Env, pageId: string): Promise<LandingPageRecord> {
  const userId = await requireAuthenticatedUserId(request, env);
  const normalizedPageId = requirePageId(pageId, request, env);
  const rows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/landing_pages?id=eq.${encodeURIComponent(normalizedPageId)}&user_id=eq.${userId}&select=id,user_id,title,slug,html_content,published,published_at,created_at,updated_at,metadata&limit=1`,
  );
  const row = asRecord(rows[0]) ?? null;
  if (!row) {
    throw buildErrorResponse(request, env, 404, {
      detail: "Page not found",
    });
  }
  return normalizeLandingPageRecord(row);
}

async function buildPageImportResponse(
  request: Request,
  env: Env,
): Promise<LandingPageRecord & { page_id: string; url: string }> {
  const userId = await requireAuthenticatedUserId(request, env);
  const normalizedPageId = requirePageId(pageId, request, env);
  let payload: Record<string, unknown>;
  try {
    payload = (await request.json()) as Record<string, unknown>;
  } catch {
    throw buildErrorResponse(request, env, 400, {
      detail: "Request body must be valid JSON.",
    });
  }

  const page = parsePageImportPayload(payload, request, env);
  const now = new Date().toISOString();
  const baseSlug = slugifyLandingPageTitle(page.title);
  let slug = baseSlug;
  let createdRows: Array<Record<string, unknown>> = [];

  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      createdRows = await insertSupabaseAdminRow<Array<Record<string, unknown>>>(
        env,
        "/rest/v1/landing_pages?select=id,user_id,title,slug,html_content,published,published_at,created_at,updated_at,metadata",
        {
          id: crypto.randomUUID(),
          user_id: userId,
          title: page.title,
          html_content: injectLandingPageSeo(page.title, page.html_content),
          slug,
          published: false,
          metadata: { source: page.source },
          created_at: now,
          updated_at: now,
        },
      );
      break;
    } catch (error) {
      if (attempt === 0 && isSupabaseStatusError(error, 409)) {
        slug = `${baseSlug}-${crypto.randomUUID().slice(0, 6)}`;
        continue;
      }
      throw error;
    }
  }

  const row = normalizeLandingPageRecord(asRecord(createdRows[0]) ?? {});
  return {
    ...row,
    page_id: row.id,
    url: buildLandingPageUrl(request, env, row.slug),
  };
}

async function buildPageUpdateResponse(
  request: Request,
  env: Env,
  pageId: string,
): Promise<LandingPageRecord> {
  const userId = await requireAuthenticatedUserId(request, env);
  let payload: Record<string, unknown>;
  try {
    payload = (await request.json()) as Record<string, unknown>;
  } catch {
    throw buildErrorResponse(request, env, 400, {
      detail: "Request body must be valid JSON.",
    });
  }

  const update = parsePageUpdatePayload(payload, request, env);
  update.updated_at = new Date().toISOString();

  let rows: Array<Record<string, unknown>>;
  try {
    rows = await updateSupabaseAdminRows<Array<Record<string, unknown>>>(
      env,
      `/rest/v1/landing_pages?id=eq.${encodeURIComponent(normalizedPageId)}&user_id=eq.${userId}&select=id,user_id,title,slug,html_content,published,published_at,created_at,updated_at,metadata`,
      update,
    );
  } catch (error) {
    if (isSupabaseStatusError(error, 409)) {
      throw buildErrorResponse(request, env, 409, {
        detail: "Slug already in use",
      });
    }
    throw error;
  }

  const row = asRecord(rows[0]) ?? null;
  if (!row) {
    throw buildErrorResponse(request, env, 404, {
      detail: "Page not found",
    });
  }

  return normalizeLandingPageRecord(row);
}

async function buildPageDeleteResponse(request: Request, env: Env, pageId: string): Promise<{ success: boolean; message: string }> {
  const userId = await requireAuthenticatedUserId(request, env);
  const normalizedPageId = requirePageId(pageId, request, env);
  const existingRows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/landing_pages?id=eq.${encodeURIComponent(normalizedPageId)}&user_id=eq.${userId}&select=id&limit=1`,
  );
  if (!existingRows.length) {
    throw buildErrorResponse(request, env, 404, {
      detail: "Page not found",
    });
  }

  await deleteSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/form_submissions?page_id=eq.${encodeURIComponent(normalizedPageId)}&form_id=is.null&select=id`,
  );
  await deleteSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/landing_pages?id=eq.${encodeURIComponent(normalizedPageId)}&user_id=eq.${userId}&select=id`,
  );

  return {
    success: true,
    message: "Page deleted",
  };
}

async function buildPagePublishResponse(
  request: Request,
  env: Env,
  pageId: string,
): Promise<LandingPageRecord & { url: string }> {
  const userId = await requireAuthenticatedUserId(request, env);
  const normalizedPageId = requirePageId(pageId, request, env);
  const now = new Date().toISOString();
  const rows = await updateSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/landing_pages?id=eq.${encodeURIComponent(normalizedPageId)}&user_id=eq.${userId}&select=id,user_id,title,slug,html_content,published,published_at,created_at,updated_at,metadata`,
    {
      published: true,
      published_at: now,
      updated_at: now,
    },
  );
  const row = asRecord(rows[0]) ?? null;
  if (!row) {
    throw buildErrorResponse(request, env, 404, {
      detail: "Page not found",
    });
  }

  const normalized = normalizeLandingPageRecord(row);
  return {
    ...normalized,
    url: buildLandingPageUrl(request, env, normalized.slug),
  };
}

async function buildPageUnpublishResponse(
  request: Request,
  env: Env,
  pageId: string,
): Promise<LandingPageRecord> {
  const userId = await requireAuthenticatedUserId(request, env);
  const normalizedPageId = requirePageId(pageId, request, env);
  const now = new Date().toISOString();
  const rows = await updateSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/landing_pages?id=eq.${encodeURIComponent(normalizedPageId)}&user_id=eq.${userId}&select=id,user_id,title,slug,html_content,published,published_at,created_at,updated_at,metadata`,
    {
      published: false,
      updated_at: now,
    },
  );
  const row = asRecord(rows[0]) ?? null;
  if (!row) {
    throw buildErrorResponse(request, env, 404, {
      detail: "Page not found",
    });
  }

  return normalizeLandingPageRecord(row);
}

async function buildPageDuplicateResponse(
  request: Request,
  env: Env,
  pageId: string,
): Promise<LandingPageRecord & { page_id: string; url: string }> {
  const normalizedPageId = requirePageId(pageId, request, env);
  const sourcePage = await buildPageGetResponse(request, env, normalizedPageId);
  const userId = sourcePage.user_id;
  const now = new Date().toISOString();
  const baseSlug = `${sourcePage.slug || "page"}-copy`;
  let slug = baseSlug;
  let createdRows: Array<Record<string, unknown>> = [];

  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      createdRows = await insertSupabaseAdminRow<Array<Record<string, unknown>>>(
        env,
        "/rest/v1/landing_pages?select=id,user_id,title,slug,html_content,published,published_at,created_at,updated_at,metadata",
        {
          id: crypto.randomUUID(),
          user_id: userId,
          title: `${sourcePage.title || "Untitled"} (Copy)`,
          html_content: sourcePage.html_content,
          slug,
          published: false,
          metadata: sourcePage.metadata,
          created_at: now,
          updated_at: now,
        },
      );
      break;
    } catch (error) {
      if (attempt === 0 && isSupabaseStatusError(error, 409)) {
        slug = `${baseSlug}-${crypto.randomUUID().slice(0, 6)}`;
        continue;
      }
      throw error;
    }
  }

  const row = normalizeLandingPageRecord(asRecord(createdRows[0]) ?? {});
  return {
    ...row,
    page_id: row.id,
    url: buildLandingPageUrl(request, env, row.slug),
  };
}

async function buildPageSubmitResponse(
  request: Request,
  env: Env,
  pageId: string,
): Promise<Response> {
  const normalizedPageId = requirePageId(pageId, request, env, "Page not found or not published");
  const rawBody = await request.text();
  if (rawBody.length > 10_000) {
    throw buildErrorResponse(request, env, 413, {
      detail: "Payload too large",
    });
  }

  let payload: unknown;
  try {
    payload = rawBody ? JSON.parse(rawBody) : {};
  } catch {
    throw buildErrorResponse(request, env, 400, {
      detail: "Request body must be valid JSON.",
    });
  }

  if (!asRecord(payload)) {
    throw buildErrorResponse(request, env, 400, {
      detail: "Submission payload must be a JSON object",
    });
  }

  const pageRows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/landing_pages?id=eq.${encodeURIComponent(normalizedPageId)}&published=eq.true&select=id&limit=1`,
  );
  if (!pageRows.length) {
    throw buildErrorResponse(request, env, 404, {
      detail: "Page not found or not published",
    });
  }

  const headers = new Headers(request.headers);
  headers.set("content-type", "application/json");
  const proxiedRequest = new Request(request.url, {
    method: request.method,
    headers,
    body: JSON.stringify(payload),
  });

  return proxyFallback(proxiedRequest, env, "native-verified-proxy");
}

async function buildApprovalCreateResponse(
  request: Request,
  env: Env,
): Promise<{ link: string; token: string; expires_at: string }> {
  const requesterUserId = await requireAuthenticatedUserId(request, env);
  let payload: Record<string, unknown>;
  try {
    payload = (await request.json()) as Record<string, unknown>;
  } catch {
    throw buildErrorResponse(request, env, 400, {
      detail: "Request body must be valid JSON.",
    });
  }

  const actionType = requireTextField(payload, "action_type", request, env);
  const bodyPayload = asRecord(payload.payload) ?? {};
  const expiresInRaw = payload.expires_in_hours;
  const expiresInHours =
    expiresInRaw === undefined
      ? 24
      : typeof expiresInRaw === "number" && Number.isInteger(expiresInRaw)
        ? expiresInRaw
        : Number.NaN;
  if (!Number.isInteger(expiresInHours) || expiresInHours < 1 || expiresInHours > 168) {
    throw buildErrorResponse(request, env, 400, {
      detail: "expires_in_hours must be an integer between 1 and 168",
    });
  }

  const token = generateApprovalToken();
  const tokenHash = await hashApprovalToken(token);
  const expiresAt = new Date(Date.now() + expiresInHours * 60 * 60 * 1000).toISOString();
  const approvalPayload: Record<string, unknown> = {
    ...bodyPayload,
    requester_user_id: requesterUserId,
    user_id: requesterUserId,
    public_token: token,
  };

  await insertSupabaseAdminRow<Array<Record<string, unknown>>>(
    env,
    "/rest/v1/approval_requests?select=id",
    {
      token: tokenHash,
      action_type: actionType,
      payload: approvalPayload,
      user_id: requesterUserId,
      expires_at: expiresAt,
      status: "PENDING",
    },
  );

  return {
    link: new URL(`/approval/${token}`, resolvePublicAppOrigin(request, env)).toString(),
    token,
    expires_at: expiresAt,
  };
}

async function buildApprovalRequestResponse(
  request: Request,
  env: Env,
  token: string,
): Promise<ApprovalRequestRecord> {
  const row = await fetchApprovalRowByTokenHash(env, await hashApprovalToken(token));
  if (!row) {
    throw buildErrorResponse(request, env, 404, {
      detail: "Request not found",
    });
  }

  return row;
}

async function buildApprovalDecisionResponse(
  request: Request,
  env: Env,
  token: string,
): Promise<{ success: boolean; status: ApprovalStatus; message: string }> {
  let payload: Record<string, unknown>;
  try {
    payload = (await request.json()) as Record<string, unknown>;
  } catch {
    throw buildErrorResponse(request, env, 400, {
      detail: "Request body must be valid JSON.",
    });
  }

  const bodyToken = requireTextField(payload, "token", request, env);
  if (token !== bodyToken) {
    throw buildErrorResponse(request, env, 400, {
      detail: "Token mismatch",
    });
  }

  const decision = requireTextField(payload, "decision", request, env).toUpperCase();
  if (decision !== "APPROVED" && decision !== "REJECTED") {
    throw buildErrorResponse(request, env, 400, {
      detail: "Invalid decision",
    });
  }

  const tokenHash = await hashApprovalToken(token);
  const current = await fetchApprovalRowByTokenHash(env, tokenHash);
  if (!current) {
    throw buildErrorResponse(request, env, 404, {
      detail: "Request not found",
    });
  }

  const expiresAt = new Date(current.expires_at);
  if (!Number.isFinite(expiresAt.getTime())) {
    throw buildErrorResponse(request, env, 500, {
      detail: "Invalid approval expiry state",
    });
  }

  if (expiresAt.getTime() < Date.now()) {
    await updateSupabaseAdminRows<Array<Record<string, unknown>>>(
      env,
      `/rest/v1/approval_requests?token=eq.${encodeURIComponent(tokenHash)}&status=eq.PENDING&select=id`,
      { status: "EXPIRED" },
    );
    return {
      success: false,
      status: "EXPIRED",
      message: "Link expired",
    };
  }

  const now = new Date().toISOString();
  const rows = await updateSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/approval_requests?token=eq.${encodeURIComponent(tokenHash)}&status=eq.PENDING&select=id,status`,
    {
      status: decision,
      responded_at: now,
      responder_ip: getRequesterIp(request),
    },
  );

  if (!rows.length) {
    return {
      success: false,
      status: current.status,
      message: "Already decided or not found",
    };
  }

  return {
    success: true,
    status: decision,
    message: `Successfully ${decision.toLowerCase()}.`,
  };
}

async function buildPendingApprovalsResponse(
  request: Request,
  env: Env,
): Promise<Array<{ id: string; action_type: string; created_at: string; token: string | null }>> {
  const userId = await requireAuthenticatedUserId(request, env);
  const rows = await fetchUserApprovalRows(env, userId, {
    statusEq: "PENDING",
    limit: 100,
    offset: 0,
  });
  return rows.map((row) => serializePendingApproval(row));
}

async function buildApprovalHistoryResponse(
  request: Request,
  env: Env,
  url: URL,
): Promise<Array<{ id: string; action_type: string; status: ApprovalStatus; created_at: string; responded_at: string | null }>> {
  const userId = await requireAuthenticatedUserId(request, env);
  const limit = parseIntegerQueryParam(url, "limit", 50, 1, 200);
  const offset = parseIntegerQueryParam(url, "offset", 0, 0, 5000);
  const statusParam = url.searchParams.get("status")?.trim().toUpperCase() ?? null;
  if (statusParam && !isApprovalStatus(statusParam)) {
    throw buildErrorResponse(request, env, 400, {
      detail: "status must be one of APPROVED, REJECTED, or EXPIRED",
    });
  }

  let rows = await fetchUserApprovalRows(env, userId, {
    statusNeq: "PENDING",
    limit,
    offset,
  });
  if (statusParam && statusParam !== "PENDING") {
    rows = rows.filter((row) => row.status === statusParam);
  }

  return rows.map((row) => ({
    id: row.id,
    action_type: row.action_type,
    status: row.status,
    created_at: row.created_at,
    responded_at: row.responded_at,
  }));
}

async function buildPendingAdApprovalsResponse(
  request: Request,
  env: Env,
): Promise<Array<{ id: string; created_at: string; expires_at: string; card_data: Record<string, unknown> }>> {
  const userId = await requireAuthenticatedUserId(request, env);
  const params = new URLSearchParams({
    select: "id,action_type,payload,status,created_at,expires_at,responded_at,user_id",
    user_id: `eq.${userId}`,
    action_type: "eq.AD_BUDGET_CHANGE",
    status: "eq.PENDING",
    order: "created_at.desc",
    limit: "50",
  });
  const rows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/approval_requests?${params.toString()}`,
  );

  return rows
    .map((row) => normalizeApprovalRequestRecord(row))
    .filter((row) => approvalRowBelongsToUser(row, userId))
    .map((row) => ({
      id: row.id,
      created_at: row.created_at,
      expires_at: row.expires_at,
      card_data: getAdApprovalCardData(row),
    }));
}

async function buildAdApprovalCardResponse(
  request: Request,
  env: Env,
  approvalId: string,
): Promise<{
  id: string;
  status: ApprovalStatus;
  action_type: string;
  created_at: string;
  expires_at: string;
  card_data: Record<string, unknown>;
}> {
  const userId = await requireAuthenticatedUserId(request, env);
  if (!UUID_RE.test(approvalId)) {
    throw buildErrorResponse(request, env, 404, {
      detail: `Approval request not found: ${approvalId}`,
    });
  }

  const row = await fetchApprovalRowById(env, approvalId);
  if (!row) {
    throw buildErrorResponse(request, env, 404, {
      detail: `Approval request not found: ${approvalId}`,
    });
  }

  if (!approvalRowBelongsToUser(row, userId)) {
    throw buildErrorResponse(request, env, 403, {
      detail: "You do not have permission to view this approval",
    });
  }

  return {
    id: row.id,
    status: row.status,
    action_type: row.action_type,
    created_at: row.created_at,
    expires_at: row.expires_at,
    card_data: getAdApprovalCardData(row),
  };
}

async function buildAdApprovalDecisionResponse(
  request: Request,
  env: Env,
  approvalId: string,
): Promise<Response> {
  const userId = await requireAuthenticatedUserId(request, env);
  if (!UUID_RE.test(approvalId)) {
    throw buildErrorResponse(request, env, 404, {
      detail: `Approval request not found: ${approvalId}`,
    });
  }

  let payload: Record<string, unknown>;
  try {
    payload = (await request.json()) as Record<string, unknown>;
  } catch {
    throw buildErrorResponse(request, env, 400, {
      detail: "Request body must be valid JSON.",
    });
  }

  const decision = requireTextField(payload, "decision", request, env).toLowerCase();
  if (decision !== "approve" && decision !== "reject") {
    throw buildErrorResponse(request, env, 422, {
      detail: "decision must be 'approve' or 'reject'",
    });
  }

  const row = await fetchApprovalRowById(env, approvalId);
  if (!row) {
    throw buildErrorResponse(request, env, 404, {
      detail: `Approval request not found: ${approvalId}`,
    });
  }

  if (!approvalRowBelongsToUser(row, userId)) {
    throw buildErrorResponse(request, env, 403, {
      detail: "You do not have permission to decide this approval",
    });
  }

  if (row.status !== "PENDING") {
    throw buildErrorResponse(request, env, 400, {
      detail: `Approval is not pending (current status: ${row.status})`,
    });
  }

  if (decision === "approve") {
    const headers = new Headers(request.headers);
    headers.set("content-type", "application/json");
    const proxiedRequest = new Request(request.url, {
      method: request.method,
      headers,
      body: JSON.stringify({ decision }),
    });
    return proxyFallback(proxiedRequest, env, "native-verified-proxy");
  }

  await updateSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/approval_requests?id=eq.${encodeURIComponent(approvalId)}&status=eq.PENDING&select=id`,
    {
      status: "REJECTED",
    },
  );

  return jsonWithCors(
    {
      status: "REJECTED",
      executed: false,
      approval_id: approvalId,
    },
    request,
    env,
  );
}

async function buildWebhookEventsResponse(request: Request, env: Env, url: URL) {
  const user = await fetchSupabaseUser(request, env);
  if (!user.id) {
    throw new Response(
      JSON.stringify({ detail: "Invalid authentication credentials" }),
      {
        status: 401,
        headers: { "content-type": "application/json" },
      },
    );
  }

  const limitRaw = Number(url.searchParams.get("limit") ?? "50");
  const limit = Number.isFinite(limitRaw)
    ? Math.max(1, Math.min(200, Math.trunc(limitRaw)))
    : 50;

  const params = new URLSearchParams({
    select: "id,platform,event_type,status,received_at,processed_at",
    user_id: `eq.${user.id}`,
    order: "received_at.desc",
    limit: String(limit),
  });

  const platform = url.searchParams.get("platform")?.trim();
  if (platform) {
    params.set("platform", `eq.${platform}`);
  }

  const status = url.searchParams.get("status")?.trim();
  if (status) {
    params.set("status", `eq.${status}`);
  }

  const events = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/social_webhook_events?${params.toString()}`,
  );

  return { events };
}

async function fetchOwnedWebhookEndpoint(
  env: Env,
  endpointId: string,
  userId: string,
): Promise<OutboundWebhookEndpointRecord | null> {
  const rows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/webhook_endpoints?id=eq.${encodeURIComponent(endpointId)}&user_id=eq.${userId}&select=*&limit=1`,
  );
  const row = asRecord(rows[0]) ?? null;
  return row ? normalizeOutboundWebhookEndpointRecord(row) : null;
}

function buildOutboundWebhookEventsResponse(): OutboundWebhookEventCatalogItem[] {
  return OUTBOUND_WEBHOOK_EVENT_CATALOG.map((entry) => ({
    event_type: entry.event_type,
    description: entry.description,
    schema: entry.schema,
  }));
}

async function buildOutboundWebhookEndpointsListResponse(
  request: Request,
  env: Env,
): Promise<Record<string, unknown>[]> {
  const userId = await requireAuthenticatedUserId(request, env);
  const rows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/webhook_endpoints?user_id=eq.${userId}&select=*&order=created_at.desc`,
  );

  return Promise.all(
    rows.map(async (row) => {
      const endpoint = normalizeOutboundWebhookEndpointRecord(row);
      let preview = "whsec_...????";
      if (endpoint.secret) {
        try {
          preview = maskWebhookSecret(await decryptFernetSecret(endpoint.secret, env));
        } catch {
          preview = "whsec_...????";
        }
      }
      return buildWebhookEndpointResponse(endpoint, preview);
    }),
  );
}

async function buildOutboundWebhookEndpointCreateResponse(
  request: Request,
  env: Env,
): Promise<{ secret: string; endpoint: Record<string, unknown> }> {
  const userId = await requireAuthenticatedUserId(request, env);
  let payload: Record<string, unknown>;
  try {
    payload = (await request.json()) as Record<string, unknown>;
  } catch {
    throw buildErrorResponse(request, env, 400, {
      detail: "Request body must be valid JSON.",
    });
  }

  const url = requireValidWebhookEndpointUrl(payload.url, request, env);
  const events = requireWebhookEventTypes(payload.events, request, env);
  const description = normalizeOptionalText(payload.description);
  const secret = `whsec_${randomBase64Url(32)}`;
  const encryptedSecret = await encryptFernetSecret(secret, env);
  const now = new Date().toISOString();
  const rows = await insertSupabaseAdminRow<Array<Record<string, unknown>>>(
    env,
    "/rest/v1/webhook_endpoints?select=*",
    {
      id: crypto.randomUUID(),
      user_id: userId,
      url,
      secret: encryptedSecret,
      events,
      active: true,
      consecutive_failures: 0,
      created_at: now,
      updated_at: now,
      description,
    },
  );
  const endpoint = normalizeOutboundWebhookEndpointRecord(asRecord(rows[0]) ?? {});
  return {
    secret,
    endpoint: buildWebhookEndpointResponse(endpoint, maskWebhookSecret(secret)),
  };
}

async function buildOutboundWebhookEndpointUpdateResponse(
  request: Request,
  env: Env,
  endpointId: string,
): Promise<Record<string, unknown>> {
  const userId = await requireAuthenticatedUserId(request, env);
  if (!UUID_RE.test(endpointId)) {
    throw buildErrorResponse(request, env, 404, {
      detail: "Webhook endpoint not found",
    });
  }

  const existing = await fetchOwnedWebhookEndpoint(env, endpointId, userId);
  if (!existing) {
    throw buildErrorResponse(request, env, 404, {
      detail: "Webhook endpoint not found",
    });
  }

  let payload: Record<string, unknown>;
  try {
    payload = (await request.json()) as Record<string, unknown>;
  } catch {
    throw buildErrorResponse(request, env, 400, {
      detail: "Request body must be valid JSON.",
    });
  }

  const updates: Record<string, unknown> = {
    updated_at: new Date().toISOString(),
  };
  if (payload.url !== undefined) {
    updates.url = requireValidWebhookEndpointUrl(payload.url, request, env);
  }
  if (payload.events !== undefined) {
    updates.events = requireWebhookEventTypes(payload.events, request, env);
  }
  if (payload.active !== undefined) {
    if (typeof payload.active !== "boolean") {
      throw buildErrorResponse(request, env, 400, {
        detail: "active must be a boolean",
      });
    }
    updates.active = payload.active;
  }
  if (payload.description !== undefined) {
    updates.description = normalizeOptionalText(payload.description);
  }

  const rows = await updateSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/webhook_endpoints?id=eq.${encodeURIComponent(endpointId)}&user_id=eq.${userId}&select=*`,
    updates,
  );
  const endpoint = normalizeOutboundWebhookEndpointRecord(
    asRecord(rows[0]) ?? { ...existing, ...updates },
  );
  let preview = "whsec_...????";
  if (endpoint.secret) {
    try {
      preview = maskWebhookSecret(await decryptFernetSecret(endpoint.secret, env));
    } catch {
      preview = "whsec_...????";
    }
  }
  return buildWebhookEndpointResponse(endpoint, preview);
}

async function buildOutboundWebhookEndpointDeleteResponse(
  request: Request,
  env: Env,
  endpointId: string,
): Promise<{ deleted: true; id: string }> {
  const userId = await requireAuthenticatedUserId(request, env);
  if (!UUID_RE.test(endpointId)) {
    throw buildErrorResponse(request, env, 404, {
      detail: "Webhook endpoint not found",
    });
  }

  const existing = await fetchOwnedWebhookEndpoint(env, endpointId, userId);
  if (!existing) {
    throw buildErrorResponse(request, env, 404, {
      detail: "Webhook endpoint not found",
    });
  }

  await deleteSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/webhook_endpoints?id=eq.${encodeURIComponent(endpointId)}&user_id=eq.${userId}`,
  );
  return { deleted: true, id: endpointId };
}

async function buildOutboundWebhookDeliveriesResponse(
  request: Request,
  env: Env,
  endpointId: string,
  url: URL,
): Promise<OutboundWebhookDeliveryRecord[]> {
  const userId = await requireAuthenticatedUserId(request, env);
  if (!UUID_RE.test(endpointId)) {
    throw buildErrorResponse(request, env, 404, {
      detail: "Webhook endpoint not found",
    });
  }

  const existing = await fetchOwnedWebhookEndpoint(env, endpointId, userId);
  if (!existing) {
    throw buildErrorResponse(request, env, 404, {
      detail: "Webhook endpoint not found",
    });
  }

  const limit = parseIntegerQueryParam(url, "limit", 50, 1, 200);
  const offset = parseIntegerQueryParam(url, "offset", 0, 0, 5000);
  const rows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/webhook_deliveries?endpoint_id=eq.${encodeURIComponent(endpointId)}&select=id,endpoint_id,event_type,status,attempts,response_code,created_at&order=created_at.desc&limit=${limit}&offset=${offset}`,
  );
  return rows.map((row) => normalizeOutboundWebhookDeliveryRecord(row));
}

async function buildOutboundWebhookTestSendResponse(
  request: Request,
  env: Env,
  endpointId: string,
): Promise<{ queued: true; delivery_id: string }> {
  const userId = await requireAuthenticatedUserId(request, env);
  if (!UUID_RE.test(endpointId)) {
    throw buildErrorResponse(request, env, 404, {
      detail: "Webhook endpoint not found",
    });
  }

  const existing = await fetchOwnedWebhookEndpoint(env, endpointId, userId);
  if (!existing) {
    throw buildErrorResponse(request, env, 404, {
      detail: "Webhook endpoint not found",
    });
  }

  const eventType = existing.events[0] || OUTBOUND_WEBHOOK_EVENT_CATALOG[0]?.event_type || "task.created";
  const catalogEntry = OUTBOUND_WEBHOOK_EVENT_CATALOG.find((entry) => entry.event_type === eventType);
  const requiredFields = Array.isArray(catalogEntry?.schema.required)
    ? catalogEntry?.schema.required.filter((value): value is string => typeof value === "string")
    : [];
  const syntheticPayload: Record<string, unknown> = Object.fromEntries(
    requiredFields.map((field) => [field, `test-${field}`]),
  );
  syntheticPayload._test = true;

  const deliveryId = crypto.randomUUID();
  await insertSupabaseAdminRow<Array<Record<string, unknown>>>(
    env,
    "/rest/v1/webhook_deliveries?select=id",
    {
      id: deliveryId,
      endpoint_id: endpointId,
      event_type: eventType,
      payload: syntheticPayload,
      status: "pending",
      attempts: 0,
      next_retry_at: new Date().toISOString(),
    },
  );

  return {
    queued: true,
    delivery_id: deliveryId,
  };
}

function parseIntegerQueryParam(
  url: URL,
  name: string,
  defaultValue: number,
  minimum: number,
  maximum: number,
): number {
  const raw = url.searchParams.get(name);
  if (raw === null) {
    return defaultValue;
  }

  const parsed = Number(raw);
  if (!Number.isInteger(parsed) || parsed < minimum || parsed > maximum) {
    throw new Response(
      JSON.stringify({
        detail: `Query parameter '${name}' must be an integer between ${minimum} and ${maximum}`,
      }),
      {
        status: 400,
        headers: { "content-type": "application/json" },
      },
    );
  }

  return parsed;
}

async function buildActionHistoryResponse(request: Request, env: Env, url: URL) {
  const user = await fetchSupabaseUser(request, env);
  if (!user.id) {
    throw new Response(
      JSON.stringify({ detail: "Invalid authentication credentials" }),
      {
        status: 401,
        headers: { "content-type": "application/json" },
      },
    );
  }

  const days = parseIntegerQueryParam(url, "days", 30, 1, 365);
  const limit = parseIntegerQueryParam(url, "limit", 50, 1, 200);
  const offset = parseIntegerQueryParam(url, "offset", 0, 0, Number.MAX_SAFE_INTEGER);
  const cutoff = new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString();

  const params = new URLSearchParams({
    select: "id,user_id,agent_name,action_type,description,metadata,source_id,source_type,created_at",
    user_id: `eq.${user.id}`,
    created_at: `gte.${cutoff}`,
    order: "created_at.desc",
    limit: String(limit),
    offset: String(offset),
  });

  const agentName = url.searchParams.get("agent_name")?.trim() || null;
  if (agentName) {
    params.set("agent_name", `eq.${agentName}`);
  }

  const actionType = url.searchParams.get("action_type")?.trim() || null;
  if (actionType) {
    params.set("action_type", `eq.${actionType}`);
  }

  const actions = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/unified_action_history?${params.toString()}`,
  );

  return {
    actions,
    total: actions.length,
    filters: {
      agent_name: agentName,
      action_type: actionType,
      days,
    },
  };
}

function isAllowedAuthScheme(value: string): value is "api_key" | "bearer" | "basic" | "oauth2" {
  return value === "api_key" || value === "bearer" || value === "basic" || value === "oauth2";
}

async function buildApiCredentialsListResponse(request: Request, env: Env) {
  const user = await fetchSupabaseUser(request, env);
  if (!user.id) {
    throw new Response(
      JSON.stringify({ detail: "Invalid authentication credentials" }),
      {
        status: 401,
        headers: { "content-type": "application/json" },
      },
    );
  }

  const params = new URLSearchParams({
    select: "id,name,auth_scheme,metadata,created_at,updated_at",
    user_id: `eq.${user.id}`,
    order: "created_at.desc",
  });

  return fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/api_credentials?${params.toString()}`,
  );
}

async function buildApiCredentialCreateResponse(request: Request, env: Env) {
  const user = await fetchSupabaseUser(request, env);
  if (!user.id) {
    throw new Response(
      JSON.stringify({ detail: "Invalid authentication credentials" }),
      {
        status: 401,
        headers: { "content-type": "application/json" },
      },
    );
  }

  let parsed: unknown;
  try {
    parsed = await request.json();
  } catch {
    throw new Response(
      JSON.stringify({ detail: "Invalid JSON payload" }),
      {
        status: 400,
        headers: { "content-type": "application/json" },
      },
    );
  }

  const body = asRecord(parsed);
  const name = typeof body?.name === "string" ? body.name.trim() : "";
  const value = typeof body?.value === "string" ? body.value : "";
  const authScheme = typeof body?.auth_scheme === "string" ? body.auth_scheme.trim() : "api_key";
  const metadata = body?.metadata;

  if (!name || !value.trim()) {
    throw new Response(
      JSON.stringify({ detail: "Fields 'name' and 'value' are required" }),
      {
        status: 400,
        headers: { "content-type": "application/json" },
      },
    );
  }

  if (!isAllowedAuthScheme(authScheme)) {
    throw new Response(
      JSON.stringify({ detail: "Invalid auth_scheme" }),
      {
        status: 400,
        headers: { "content-type": "application/json" },
      },
    );
  }

  if (metadata !== undefined && metadata !== null && !asRecord(metadata)) {
    throw new Response(
      JSON.stringify({ detail: "Field 'metadata' must be an object when provided" }),
      {
        status: 400,
        headers: { "content-type": "application/json" },
      },
    );
  }

  const rows = await insertSupabaseAdminRow<
    Array<{
      id?: string | null;
      name?: string | null;
      auth_scheme?: string | null;
      created_at?: string | null;
    }>
  >(
    env,
    "/rest/v1/api_credentials?select=id,name,auth_scheme,created_at",
    {
      user_id: user.id,
      name,
      encrypted_value: value,
      auth_scheme: authScheme,
      metadata: asRecord(metadata) ?? {},
    },
  );

  const row = rows[0] ?? {};
  return {
    id: row.id ?? null,
    name: row.name ?? name,
    auth_scheme: row.auth_scheme ?? authScheme,
    created_at: row.created_at ?? null,
  };
}

async function buildApiCredentialDeleteResponse(request: Request, env: Env, credentialName: string) {
  const user = await fetchSupabaseUser(request, env);
  if (!user.id) {
    throw new Response(
      JSON.stringify({ detail: "Invalid authentication credentials" }),
      {
        status: 401,
        headers: { "content-type": "application/json" },
      },
    );
  }

  const name = credentialName.trim();
  if (!name) {
    throw new Response(
      JSON.stringify({ detail: "Credential name is required" }),
      {
        status: 400,
        headers: { "content-type": "application/json" },
      },
    );
  }

  const params = new URLSearchParams({
    user_id: `eq.${user.id}`,
    name: `eq.${name}`,
  });

  const rows = await deleteSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/api_credentials?${params.toString()}`,
  );

  if (!rows.length) {
    throw new Response(
      JSON.stringify({ detail: "Credential not found" }),
      {
        status: 404,
        headers: { "content-type": "application/json" },
      },
    );
  }

  return { deleted: true, name };
}

function buildIntegrationProvidersResponse(): IntegrationProvider[] {
  return INTEGRATION_PROVIDERS;
}

function getIntegrationProviderConfig(provider: string): IntegrationProviderConfig | null {
  return INTEGRATION_PROVIDER_CONFIGS[provider] ?? null;
}

function isAdPlatform(provider: string): boolean {
  return provider === "google_ads" || provider === "meta_ads";
}

function buildHtmlResponse(request: Request, env: Env, html: string): Response {
  const response = new Response(html, {
    status: 200,
    headers: { "content-type": "text/html; charset=utf-8" },
  });
  response.headers.set("x-pikar-public-route", "native");
  const corsHeaders = buildCorsHeaders(request, env);
  corsHeaders.forEach((value, key) => response.headers.set(key, value));
  return response;
}

function buildIntegrationSuccessHtml(provider: string): string {
  return `<!DOCTYPE html>
<html>
<head><title>Connected</title></head>
<body>
<p>Successfully connected to ${provider}. This window will close automatically.</p>
<script>
  if (window.opener) {
    window.opener.postMessage({
      type: 'oauth-callback',
      provider: '${provider}',
      success: true
    }, '*');
  }
  setTimeout(function() { window.close(); }, 1500);
</script>
</body>
</html>`;
}

function buildIntegrationBudgetCapPromptHtml(provider: string): string {
  return `<!DOCTYPE html>
<html>
<head><title>Set Budget Cap</title></head>
<body>
<p>Successfully connected to ${provider}. Please set a monthly budget cap to complete setup.</p>
<script>
  if (window.opener) {
    window.opener.postMessage({
      type: 'oauth-callback',
      provider: '${provider}',
      success: true,
      needs_budget_cap: true
    }, '*');
  }
  setTimeout(function() { window.close(); }, 2000);
</script>
</body>
</html>`;
}

function buildIntegrationErrorHtml(provider: string, error: string): string {
  const safeError = error.replace(/'/g, "\\'");
  return `<!DOCTYPE html>
<html>
<head><title>Connection Failed</title></head>
<body>
<p>Failed to connect to ${provider}: ${error}</p>
<script>
  if (window.opener) {
    window.opener.postMessage({
      type: 'oauth-callback',
      provider: '${provider}',
      success: false,
      error: '${safeError}'
    }, '*');
  }
  setTimeout(function() { window.close(); }, 3000);
</script>
</body>
</html>`;
}

function requireValidWebhookEndpointUrl(
  rawValue: unknown,
  request: Request,
  env: Env,
): string {
  const value = normalizeOptionalText(rawValue);
  if (!value) {
    throw buildErrorResponse(request, env, 400, {
      detail: "url is required",
    });
  }

  try {
    const parsed = new URL(value);
    if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
      throw new Error("invalid");
    }
    return parsed.toString();
  } catch {
    throw buildErrorResponse(request, env, 400, {
      detail: "url must be a valid http or https URL",
    });
  }
}

function requireWebhookEventTypes(
  value: unknown,
  request: Request,
  env: Env,
): string[] {
  if (!Array.isArray(value) || !value.length) {
    throw buildErrorResponse(request, env, 400, {
      detail: "events must contain at least one event type",
    });
  }

  const events = value
    .map((item) => (typeof item === "string" ? item.trim() : ""))
    .filter(Boolean);
  if (!events.length) {
    throw buildErrorResponse(request, env, 400, {
      detail: "events must contain at least one event type",
    });
  }

  const unknown = events.filter((eventType) => !OUTBOUND_WEBHOOK_EVENT_TYPES.has(eventType));
  if (unknown.length) {
    throw buildErrorResponse(request, env, 422, {
      detail: `Unknown event types: ${unknown.join(", ")}`,
    });
  }

  return Array.from(new Set(events));
}

async function getOAuthStateCryptoKey(env: Env): Promise<CryptoKey> {
  const secret = env.OAUTH_STATE_SECRET?.trim() || env.INTERNAL_PROXY_TOKEN?.trim();
  if (!secret) {
    throw new Error("OAUTH_STATE_SECRET or INTERNAL_PROXY_TOKEN is required.");
  }

  const secretBytes = new TextEncoder().encode(secret);
  const digest = await crypto.subtle.digest("SHA-256", secretBytes);
  return crypto.subtle.importKey("raw", digest, { name: "AES-GCM" }, false, ["encrypt", "decrypt"]);
}

async function encodeOAuthStateToken(payload: OAuthStatePayload, env: Env): Promise<string> {
  const key = await getOAuthStateCryptoKey(env);
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const plaintext = new TextEncoder().encode(JSON.stringify(payload));
  const encrypted = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, key, plaintext);
  const tokenBytes = new Uint8Array(iv.length + encrypted.byteLength);
  tokenBytes.set(iv, 0);
  tokenBytes.set(new Uint8Array(encrypted), iv.length);
  return toBase64Url(tokenBytes);
}

async function decodeOAuthStateToken(token: string, env: Env): Promise<OAuthStatePayload | null> {
  try {
    const bytes = fromBase64Url(token);
    if (bytes.length <= 12) {
      return null;
    }

    const iv = bytes.slice(0, 12);
    const ciphertext = bytes.slice(12);
    const key = await getOAuthStateCryptoKey(env);
    const decrypted = await crypto.subtle.decrypt({ name: "AES-GCM", iv }, key, ciphertext);
    const payload = JSON.parse(new TextDecoder().decode(decrypted)) as Partial<OAuthStatePayload>;
    if (
      typeof payload.user_id !== "string" ||
      typeof payload.provider !== "string" ||
      typeof payload.nonce !== "string" ||
      typeof payload.exp !== "number"
    ) {
      return null;
    }
    if (payload.exp < Math.floor(Date.now() / 1000)) {
      return null;
    }
    return {
      user_id: payload.user_id,
      provider: payload.provider,
      shop: typeof payload.shop === "string" ? payload.shop : undefined,
      nonce: payload.nonce,
      exp: payload.exp,
    };
  } catch {
    return null;
  }
}

function extractIntegrationAccountName(tokenData: Record<string, unknown>): string {
  for (const field of ["hub_domain", "shop", "team_name", "team", "account_name", "name"]) {
    const value = tokenData[field];
    if (typeof value === "string" && value.trim()) {
      return value;
    }
  }
  return "";
}

async function isBudgetCapSet(env: Env, userId: string, provider: string): Promise<boolean> {
  const params = new URLSearchParams({
    select: "monthly_cap",
    user_id: `eq.${userId}`,
    platform: `eq.${provider}`,
    limit: "1",
  });

  const rows = await fetchSupabaseAdminRows<Array<{ monthly_cap?: number | string | null }>>(
    env,
    `/rest/v1/ad_budget_caps?${params.toString()}`,
  );
  return rows.length > 0;
}

async function encryptFernetSecret(value: string, env: Env): Promise<string> {
  const primaryKey = env.ADMIN_ENCRYPTION_KEY?.split(",").map((item) => item.trim()).find(Boolean);
  if (!primaryKey) {
    throw new Error("ADMIN_ENCRYPTION_KEY is required.");
  }

  const keyBytes = fromBase64Url(primaryKey);
  if (keyBytes.length !== 32) {
    throw new Error("ADMIN_ENCRYPTION_KEY must decode to 32 bytes.");
  }

  const signingKey = keyBytes.slice(0, 16);
  const encryptionKey = keyBytes.slice(16);
  const iv = crypto.getRandomValues(new Uint8Array(16));
  const aesKey = await crypto.subtle.importKey("raw", encryptionKey, { name: "AES-CBC" }, false, ["encrypt"]);
  const ciphertext = new Uint8Array(
    await crypto.subtle.encrypt(
      { name: "AES-CBC", iv },
      aesKey,
      new TextEncoder().encode(value),
    ),
  );

  const timestampSeconds = Math.floor(Date.now() / 1000);
  const timestamp = new Uint8Array(8);
  let remaining = timestampSeconds;
  for (let index = 7; index >= 0; index -= 1) {
    timestamp[index] = remaining & 0xff;
    remaining = Math.floor(remaining / 256);
  }

  const tokenBody = new Uint8Array(1 + timestamp.length + iv.length + ciphertext.length);
  tokenBody[0] = 0x80;
  tokenBody.set(timestamp, 1);
  tokenBody.set(iv, 1 + timestamp.length);
  tokenBody.set(ciphertext, 1 + timestamp.length + iv.length);

  const hmacKey = await crypto.subtle.importKey(
    "raw",
    signingKey,
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const signature = new Uint8Array(await crypto.subtle.sign("HMAC", hmacKey, tokenBody));
  const token = new Uint8Array(tokenBody.length + signature.length);
  token.set(tokenBody, 0);
  token.set(signature, tokenBody.length);
  return toBase64Url(token);
}

function timingSafeEqualBytes(left: Uint8Array, right: Uint8Array): boolean {
  if (left.length !== right.length) {
    return false;
  }

  let diff = 0;
  for (let index = 0; index < left.length; index += 1) {
    diff |= left[index] ^ right[index];
  }
  return diff === 0;
}

async function decryptFernetSecret(value: string, env: Env): Promise<string> {
  const keys = (env.ADMIN_ENCRYPTION_KEY ?? "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  if (!keys.length) {
    throw new Error("ADMIN_ENCRYPTION_KEY is required.");
  }

  const tokenBytes = fromBase64Url(value);
  if (tokenBytes.length < 1 + 8 + 16 + 32) {
    throw new Error("Invalid Fernet token.");
  }

  if (tokenBytes[0] !== 0x80) {
    throw new Error("Unsupported Fernet token version.");
  }

  const tokenBody = tokenBytes.slice(0, tokenBytes.length - 32);
  const signature = tokenBytes.slice(tokenBytes.length - 32);
  const iv = tokenBytes.slice(9, 25);
  const ciphertext = tokenBytes.slice(25, tokenBytes.length - 32);

  for (const key of keys) {
    try {
      const keyBytes = fromBase64Url(key);
      if (keyBytes.length !== 32) {
        continue;
      }

      const signingKey = keyBytes.slice(0, 16);
      const encryptionKey = keyBytes.slice(16);
      const hmacKey = await crypto.subtle.importKey(
        "raw",
        signingKey,
        { name: "HMAC", hash: "SHA-256" },
        false,
        ["sign"],
      );
      const expectedSignature = new Uint8Array(
        await crypto.subtle.sign("HMAC", hmacKey, tokenBody),
      );
      if (!timingSafeEqualBytes(expectedSignature, signature)) {
        continue;
      }

      const aesKey = await crypto.subtle.importKey(
        "raw",
        encryptionKey,
        { name: "AES-CBC" },
        false,
        ["decrypt"],
      );
      const paddedPlaintext = new Uint8Array(
        await crypto.subtle.decrypt({ name: "AES-CBC", iv }, aesKey, ciphertext),
      );
      const padLength = paddedPlaintext[paddedPlaintext.length - 1];
      if (padLength < 1 || padLength > 16 || padLength > paddedPlaintext.length) {
        throw new Error("Invalid Fernet padding.");
      }

      for (let index = paddedPlaintext.length - padLength; index < paddedPlaintext.length; index += 1) {
        if (paddedPlaintext[index] !== padLength) {
          throw new Error("Invalid Fernet padding.");
        }
      }

      const plaintext = paddedPlaintext.slice(0, paddedPlaintext.length - padLength);
      return new TextDecoder().decode(plaintext);
    } catch {
      continue;
    }
  }

  throw new Error("Unable to decrypt Fernet token.");
}

function maskWebhookSecret(secret: string | null): string {
  if (!secret || secret.length < 4) {
    return "whsec_...????";
  }
  return `whsec_...${secret.slice(-4)}`;
}

function buildWebhookEndpointResponse(
  row: OutboundWebhookEndpointRecord,
  secretPreview: string,
): Record<string, unknown> {
  return {
    id: row.id,
    url: row.url,
    events: row.events,
    active: row.active,
    description: row.description,
    consecutive_failures: row.consecutive_failures,
    created_at: row.created_at,
    secret_preview: secretPreview,
  };
}

async function buildIntegrationAuthorizeResponse(
  request: Request,
  env: Env,
  provider: string,
  url: URL,
): Promise<Response> {
  const user = await fetchSupabaseUser(request, env);
  if (!user.id) {
    throw new Response(
      JSON.stringify({ detail: "Invalid authentication credentials" }),
      {
        status: 401,
        headers: { "content-type": "application/json" },
      },
    );
  }

  const config = getIntegrationProviderConfig(provider);
  if (!config) {
    return buildErrorResponse(request, env, 404, { detail: `Unknown provider: ${provider}` });
  }
  if (config.auth_type !== "oauth2") {
    return buildErrorResponse(request, env, 400, {
      detail: `Provider ${provider} does not support OAuth2 authorization`,
    });
  }

  const shop = url.searchParams.get("shop")?.trim() || "";
  if (provider === "shopify" && !shop) {
    return buildErrorResponse(request, env, 400, {
      detail: "Shopify requires a shop parameter (e.g., ?shop=mystore)",
    });
  }

  const clientId = env[config.client_id_env]?.trim() || "";
  if (!clientId) {
    return buildErrorResponse(request, env, 500, {
      detail: `Integration not configured: ${provider}`,
    });
  }

  const redirectUri = `${canonicalRequestOrigin(request)}/integrations/${provider}/callback`;
  const state = await encodeOAuthStateToken(
    {
      user_id: user.id,
      provider,
      shop: shop || undefined,
      nonce: crypto.randomUUID(),
      exp: Math.floor(Date.now() / 1000) + 600,
    },
    env,
  );

  let authUrlTemplate = config.auth_url;
  if (shop && authUrlTemplate.includes("{shop}")) {
    authUrlTemplate = authUrlTemplate.replace("{shop}", shop);
  }

  const authUrl = new URL(authUrlTemplate);
  authUrl.searchParams.set("client_id", clientId);
  authUrl.searchParams.set("redirect_uri", redirectUri);
  authUrl.searchParams.set("response_type", "code");
  authUrl.searchParams.set("scope", config.scopes.join(" "));
  authUrl.searchParams.set("state", state);
  authUrl.searchParams.set("access_type", "offline");
  authUrl.searchParams.set("prompt", "consent");

  return new Response(null, {
    status: 302,
    headers: {
      Location: authUrl.toString(),
      "x-pikar-public-route": "native",
    },
  });
}

async function buildIntegrationCallbackResponse(
  request: Request,
  env: Env,
  provider: string,
  url: URL,
): Promise<Response> {
  const config = getIntegrationProviderConfig(provider);
  if (!config || config.auth_type !== "oauth2") {
    return buildHtmlResponse(request, env, buildIntegrationErrorHtml(provider, "Unknown provider"));
  }

  const code = url.searchParams.get("code")?.trim();
  const stateToken = url.searchParams.get("state")?.trim();
  if (!code || !stateToken) {
    return buildHtmlResponse(
      request,
      env,
      buildIntegrationErrorHtml(provider, "Missing code or state"),
    );
  }

  const state = await decodeOAuthStateToken(stateToken, env);
  if (!state || state.provider !== provider) {
    return buildHtmlResponse(
      request,
      env,
      buildIntegrationErrorHtml(provider, "Invalid or expired state token"),
    );
  }

  const redirectUri = `${canonicalRequestOrigin(request)}/integrations/${provider}/callback`;
  const clientId = env[config.client_id_env]?.trim() || "";
  const clientSecret = env[config.client_secret_env]?.trim() || "";
  if (!clientId || !clientSecret) {
    return buildHtmlResponse(
      request,
      env,
      buildIntegrationErrorHtml(provider, "Integration not configured"),
    );
  }

  let tokenUrl = config.token_url;
  if (state.shop && tokenUrl.includes("{shop}")) {
    tokenUrl = tokenUrl.replace("{shop}", state.shop);
  }

  let tokenData: Record<string, unknown>;
  try {
    const tokenResponse = await fetch(tokenUrl, {
      method: "POST",
      headers: { "content-type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        grant_type: "authorization_code",
        code,
        redirect_uri: redirectUri,
        client_id: clientId,
        client_secret: clientSecret,
      }),
    });
    if (!tokenResponse.ok) {
      return buildHtmlResponse(
        request,
        env,
        buildIntegrationErrorHtml(provider, "Token exchange failed"),
      );
    }
    tokenData = asRecord(await tokenResponse.json()) ?? {};
  } catch {
    return buildHtmlResponse(
      request,
      env,
      buildIntegrationErrorHtml(provider, "Connection error during token exchange"),
    );
  }

  const accessToken = typeof tokenData.access_token === "string" ? tokenData.access_token : "";
  if (!accessToken) {
    return buildHtmlResponse(
      request,
      env,
      buildIntegrationErrorHtml(provider, "Provider did not return an access token"),
    );
  }

  const refreshToken =
    typeof tokenData.refresh_token === "string" ? tokenData.refresh_token : null;
  const tokenType = typeof tokenData.token_type === "string" ? tokenData.token_type : "bearer";
  const scopeValue = tokenData.scope;
  const scopes = Array.isArray(scopeValue)
    ? scopeValue.filter((item): item is string => typeof item === "string").join(" ")
    : typeof scopeValue === "string"
      ? scopeValue
      : "";
  const expiresIn = Number(tokenData.expires_in);
  const expiresAt =
    Number.isFinite(expiresIn) && expiresIn > 0
      ? new Date(Date.now() + expiresIn * 1000).toISOString()
      : null;
  const accountName =
    provider === "shopify" && state.shop
      ? state.shop
      : extractIntegrationAccountName(tokenData);

  try {
    const encryptedAccess = await encryptFernetSecret(accessToken, env);
    const encryptedRefresh = refreshToken ? await encryptFernetSecret(refreshToken, env) : null;

    await upsertSupabaseAdminMergeRow<Array<Record<string, unknown>>>(
      env,
      "/rest/v1/integration_credentials?on_conflict=user_id,provider&select=id",
      {
        user_id: state.user_id,
        provider,
        access_token: encryptedAccess,
        refresh_token: encryptedRefresh,
        token_type: tokenType,
        scopes,
        expires_at: expiresAt,
        account_name: accountName,
      },
    );
  } catch {
    return buildHtmlResponse(
      request,
      env,
      buildIntegrationErrorHtml(provider, "Failed to save credentials"),
    );
  }

  if (isAdPlatform(provider) && !(await isBudgetCapSet(env, state.user_id, provider))) {
    return buildHtmlResponse(request, env, buildIntegrationBudgetCapPromptHtml(provider));
  }

  return buildHtmlResponse(request, env, buildIntegrationSuccessHtml(provider));
}

async function proxyVerifiedWebhook(request: Request, env: Env): Promise<Response> {
  return proxyFallback(request, env, "native-verified-proxy");
}

async function maybeHandleNativeRoute(request: Request, env: Env, url: URL): Promise<Response | null> {
  const corsHeaders = buildCorsHeaders(request, env);

  if (url.pathname === "/health/live") {
    const response = Response.json(buildLiveResponse());
    corsHeaders.forEach((value, key) => response.headers.set(key, value));
    response.headers.set("x-pikar-public-route", "native");
    return response;
  }

  if (url.pathname === "/health/startup") {
    const response = Response.json(buildStartupResponse(env));
    corsHeaders.forEach((value, key) => response.headers.set(key, value));
    response.headers.set("x-pikar-public-route", "native");
    return response;
  }

  if (url.pathname === "/webhooks/linkedin" && request.method === "GET") {
    const challengeCode = url.searchParams.get("challengeCode")?.trim();
    if (!challengeCode) {
      return buildErrorResponse(request, env, 400, {
        detail: "Missing challengeCode query parameter",
      });
    }

    const clientSecret = env.LINKEDIN_CLIENT_SECRET?.trim();
    if (!clientSecret) {
      return buildErrorResponse(request, env, 500, {
        detail: "LinkedIn client secret not configured",
      });
    }

    return jsonWithCors(
      {
        challengeCode,
        challengeResponse: await signHmacSha256Hex(
          clientSecret,
          new TextEncoder().encode(challengeCode),
        ),
      },
      request,
      env,
    );
  }

  if (url.pathname === "/webhooks/linkedin" && request.method === "POST") {
    const webhookSecret = env.LINKEDIN_WEBHOOK_SECRET?.trim();
    if (!webhookSecret) {
      return buildErrorResponse(request, env, 500, {
        detail: "LinkedIn webhook secret not configured",
      });
    }

    const providedSignature = request.headers.get("X-LinkedIn-Signature")?.trim();
    if (!providedSignature) {
      return buildErrorResponse(request, env, 403, {
        detail: "Invalid signature",
      });
    }

    const rawBody = new Uint8Array(await request.arrayBuffer());
    const expectedSignature = await signHmacSha256Hex(webhookSecret, rawBody);
    if (!constantTimeEqual(expectedSignature, providedSignature)) {
      return buildErrorResponse(request, env, 403, {
        detail: "Invalid signature",
      });
    }

    let parsed: unknown;
    try {
      parsed = JSON.parse(new TextDecoder().decode(rawBody));
    } catch {
      return buildErrorResponse(request, env, 400, {
        detail: "Invalid JSON payload",
      });
    }

    const payload = asRecord(parsed);
    if (!payload) {
      return buildErrorResponse(request, env, 400, {
        detail: "Invalid JSON payload",
      });
    }

    const stored = await storeLinkedInWebhookEvent(env, payload);
    return jsonWithCors(
      {
        status: "received",
        event_id: stored.id ?? null,
      },
      request,
      env,
    );
  }

  if (url.pathname === "/webhooks/hubspot" && request.method === "POST") {
    const rawBody = new Uint8Array(await request.clone().arrayBuffer());
    if (!env.HUBSPOT_CLIENT_SECRET?.trim() && !env.HUBSPOT_WEBHOOK_SECRET?.trim()) {
      return null;
    }

    if (!(await verifyHubSpotWebhook(request, env, rawBody))) {
      return buildErrorResponse(request, env, 403, {
        detail: "Invalid signature",
      });
    }

    return proxyVerifiedWebhook(request, env);
  }

  if (url.pathname === "/webhooks/resend" && request.method === "POST") {
    const rawBody = new Uint8Array(await request.clone().arrayBuffer());
    if (!env.RESEND_WEBHOOK_SECRET?.trim()) {
      return null;
    }

    if (!(await verifyResendWebhook(request, env, rawBody))) {
      return buildErrorResponse(request, env, 401, {
        detail: "Invalid webhook signature",
      });
    }

    return proxyVerifiedWebhook(request, env);
  }

  if (url.pathname === "/webhooks/shopify" && request.method === "POST") {
    const rawBody = new Uint8Array(await request.clone().arrayBuffer());
    if (!env.SHOPIFY_WEBHOOK_SECRET?.trim()) {
      return null;
    }

    if (!(await verifyShopifyWebhook(request, env, rawBody))) {
      return buildErrorResponse(request, env, 403, {
        detail: "Invalid signature",
      });
    }

    return proxyVerifiedWebhook(request, env);
  }

  if (url.pathname === "/webhooks/stripe" && request.method === "POST") {
    const rawBody = new Uint8Array(await request.clone().arrayBuffer());
    if (!env.STRIPE_WEBHOOK_SECRET?.trim()) {
      return null;
    }

    if (!(await verifyStripeWebhook(request, env, rawBody))) {
      return buildErrorResponse(request, env, 403, {
        detail: "Invalid signature",
      });
    }

    return proxyVerifiedWebhook(request, env);
  }

  const inboundMatch = /^\/webhooks\/inbound\/([^/]+)$/.exec(url.pathname);
  if (inboundMatch && request.method === "POST") {
    const provider = decodeURIComponent(inboundMatch[1]).trim().toLowerCase();
    const envVar = getInboundSecretEnvVar(provider, env);
    if (!envVar) {
      return buildErrorResponse(request, env, 404, {
        detail: `Unknown provider: ${provider}`,
      });
    }

    const secret = env[envVar]?.trim();
    if (!secret) {
      return buildErrorResponse(request, env, 500, {
        detail: "Webhook secret not configured",
      });
    }

    const signatureHeaderName =
      INBOUND_SIGNATURE_HEADERS[provider] ?? `X-${provider.replace(/(^.|[-_].)/g, (part) => part.replace(/[-_]/g, "").toUpperCase())}-Signature`;
    const providedSignature = request.headers.get(signatureHeaderName)?.trim() ?? "";
    const rawBody = new Uint8Array(await request.arrayBuffer());
    const expectedSignature = await signHmacSha256Hex(secret, rawBody);
    if (!verifyInboundSignature(rawBody, providedSignature, expectedSignature)) {
      return buildErrorResponse(request, env, 403, {
        detail: "Invalid signature",
      });
    }

    let parsed: unknown;
    try {
      parsed = JSON.parse(new TextDecoder().decode(rawBody));
    } catch {
      return buildErrorResponse(request, env, 400, {
        detail: "Invalid JSON payload",
      });
    }

    const payload = asRecord(parsed);
    if (!payload) {
      return buildErrorResponse(request, env, 400, {
        detail: "Invalid JSON payload",
      });
    }

    return jsonWithCors(await storeGenericInboundWebhook(env, provider, payload), request, env);
  }

  if (url.pathname === "/webhooks/events" && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildWebhookEventsResponse(request, env, url), request, env);
  }

  if (url.pathname === "/configuration/mcp-status") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(buildMcpStatusResponse(env), request, env);
  }

  if (url.pathname === "/configuration/user-configs") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildUserConfigsResponse(request, env), request, env);
  }

  if (url.pathname === "/configuration/session-config") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildSessionConfigResponse(request, env), request, env);
  }

  if (url.pathname === "/configuration/social-status") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildSocialStatusResponse(request, env), request, env);
  }

  if (url.pathname === "/configuration/google-workspace-status") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildGoogleWorkspaceStatusResponse(request, env), request, env);
  }

  if (url.pathname === "/configuration/settings" && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildConfigurationSettingsResponse(request, env), request, env);
  }

  if (url.pathname === "/configuration/settings" && request.method === "PATCH") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(
      await buildConfigurationSettingsUpdateResponse(request, env),
      request,
      env,
    );
  }

  if (url.pathname === "/suggestions" && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    await fetchSupabaseUser(request, env);
    return jsonWithCors(buildSuggestionsResponse(url), request, env);
  }

  if ((url.pathname === "/action-history" || url.pathname === "/action-history/") && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildActionHistoryResponse(request, env, url), request, env);
  }

  if (url.pathname === "/finance/invoices" && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildFinanceInvoicesResponse(request, env, url), request, env);
  }

  if (url.pathname === "/finance/assumptions" && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildFinanceAssumptionsResponse(request, env), request, env);
  }

  if (url.pathname === "/finance/revenue-timeseries" && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(
      await buildFinanceRevenueTimeSeriesResponse(request, env, url),
      request,
      env,
    );
  }

  if (url.pathname === "/sales/contacts" && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildSalesContactsResponse(request, env, url), request, env);
  }

  if (url.pathname === "/sales/contacts/activities" && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildSalesContactActivitiesResponse(request, env, url), request, env);
  }

  if (url.pathname === "/sales/connected-accounts" && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildSalesConnectedAccountsResponse(request, env), request, env);
  }

  if (url.pathname === "/sales/campaigns" && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildSalesCampaignsResponse(request, env, url), request, env);
  }

  if (url.pathname === "/sales/page-analytics" && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildSalesPageAnalyticsResponse(request, env, url), request, env);
  }

  if (url.pathname === "/content/bundles" && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildContentBundlesResponse(request, env, url), request, env);
  }

  if (url.pathname === "/content/bundles/deliverables" && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildContentDeliverablesResponse(request, env, url), request, env);
  }

  if (url.pathname === "/content/campaigns" && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildContentCampaignsResponse(request, env, url), request, env);
  }

  if ((url.pathname === "/api-credentials" || url.pathname === "/api-credentials/") && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildApiCredentialsListResponse(request, env), request, env);
  }

  if ((url.pathname === "/api-credentials" || url.pathname === "/api-credentials/") && request.method === "POST") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildApiCredentialCreateResponse(request, env), request, env);
  }

  const apiCredentialDeleteMatch = /^\/api-credentials\/([^/]+)$/.exec(url.pathname);
  if (apiCredentialDeleteMatch && request.method === "DELETE") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    const credentialName = decodeURIComponent(apiCredentialDeleteMatch[1]);
    return jsonWithCors(
      await buildApiCredentialDeleteResponse(request, env, credentialName),
      request,
      env,
    );
  }

  if (url.pathname === "/integrations/providers" && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(buildIntegrationProvidersResponse(), request, env);
  }

  if (url.pathname === "/approvals/create" && request.method === "POST") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildApprovalCreateResponse(request, env), request, env);
  }

  if (url.pathname === "/approvals/pending/list" && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildPendingApprovalsResponse(request, env), request, env);
  }

  if (url.pathname === "/approvals/history" && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildApprovalHistoryResponse(request, env, url), request, env);
  }

  const approvalDecisionMatch = /^\/approvals\/([^/]+)\/decision$/.exec(url.pathname);
  if (approvalDecisionMatch && request.method === "POST") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(
      await buildApprovalDecisionResponse(request, env, decodeURIComponent(approvalDecisionMatch[1])),
      request,
      env,
    );
  }

  const approvalTokenMatch = /^\/approvals\/([^/]+)$/.exec(url.pathname);
  if (approvalTokenMatch && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(
      await buildApprovalRequestResponse(request, env, decodeURIComponent(approvalTokenMatch[1])),
      request,
      env,
    );
  }

  if (url.pathname === "/ad-approvals/pending" && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildPendingAdApprovalsResponse(request, env), request, env);
  }

  const adApprovalDecisionMatch = /^\/ad-approvals\/([^/]+)\/decide$/.exec(url.pathname);
  if (adApprovalDecisionMatch && request.method === "POST") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return buildAdApprovalDecisionResponse(
      request,
      env,
      decodeURIComponent(adApprovalDecisionMatch[1]),
    );
  }

  const adApprovalCardMatch = /^\/ad-approvals\/([^/]+)$/.exec(url.pathname);
  if (adApprovalCardMatch && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(
      await buildAdApprovalCardResponse(request, env, decodeURIComponent(adApprovalCardMatch[1])),
      request,
      env,
    );
  }

  if (url.pathname === "/outbound-webhooks/events" && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(buildOutboundWebhookEventsResponse(), request, env);
  }

  if (url.pathname === "/outbound-webhooks/endpoints" && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(
      await buildOutboundWebhookEndpointsListResponse(request, env),
      request,
      env,
    );
  }

  if (url.pathname === "/outbound-webhooks/endpoints" && request.method === "POST") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCorsStatus(
      await buildOutboundWebhookEndpointCreateResponse(request, env),
      request,
      env,
      201,
    );
  }

  const outboundWebhookTestMatch = /^\/outbound-webhooks\/endpoints\/([^/]+)\/test$/.exec(url.pathname);
  if (outboundWebhookTestMatch && request.method === "POST") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCorsStatus(
      await buildOutboundWebhookTestSendResponse(
        request,
        env,
        decodeURIComponent(outboundWebhookTestMatch[1]),
      ),
      request,
      env,
      202,
    );
  }

  const outboundWebhookDeliveriesMatch = /^\/outbound-webhooks\/endpoints\/([^/]+)\/deliveries$/.exec(url.pathname);
  if (outboundWebhookDeliveriesMatch && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(
      await buildOutboundWebhookDeliveriesResponse(
        request,
        env,
        decodeURIComponent(outboundWebhookDeliveriesMatch[1]),
        url,
      ),
      request,
      env,
    );
  }

  const outboundWebhookEndpointMatch = /^\/outbound-webhooks\/endpoints\/([^/]+)$/.exec(url.pathname);
  if (outboundWebhookEndpointMatch && request.method === "PATCH") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(
      await buildOutboundWebhookEndpointUpdateResponse(
        request,
        env,
        decodeURIComponent(outboundWebhookEndpointMatch[1]),
      ),
      request,
      env,
    );
  }

  if (outboundWebhookEndpointMatch && request.method === "DELETE") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(
      await buildOutboundWebhookEndpointDeleteResponse(
        request,
        env,
        decodeURIComponent(outboundWebhookEndpointMatch[1]),
      ),
      request,
      env,
    );
  }

  if (url.pathname === "/pages" && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildPagesListResponse(request, env), request, env);
  }

  if (url.pathname === "/pages/import" && request.method === "POST") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCorsStatus(await buildPageImportResponse(request, env), request, env, 201);
  }

  const pagePublishMatch = /^\/pages\/([^/]+)\/publish$/.exec(url.pathname);
  if (pagePublishMatch && request.method === "POST") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(
      await buildPagePublishResponse(request, env, decodeURIComponent(pagePublishMatch[1])),
      request,
      env,
    );
  }

  const pageUnpublishMatch = /^\/pages\/([^/]+)\/unpublish$/.exec(url.pathname);
  if (pageUnpublishMatch && request.method === "POST") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(
      await buildPageUnpublishResponse(request, env, decodeURIComponent(pageUnpublishMatch[1])),
      request,
      env,
    );
  }

  const pageDuplicateMatch = /^\/pages\/([^/]+)\/duplicate$/.exec(url.pathname);
  if (pageDuplicateMatch && request.method === "POST") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(
      await buildPageDuplicateResponse(request, env, decodeURIComponent(pageDuplicateMatch[1])),
      request,
      env,
    );
  }

  const pageSubmitMatch = /^\/pages\/([^/]+)\/submit$/.exec(url.pathname);
  if (pageSubmitMatch && request.method === "POST") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return buildPageSubmitResponse(request, env, decodeURIComponent(pageSubmitMatch[1]));
  }

  const pageDetailMatch = /^\/pages\/([^/]+)$/.exec(url.pathname);
  if (pageDetailMatch && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(
      await buildPageGetResponse(request, env, decodeURIComponent(pageDetailMatch[1])),
      request,
      env,
    );
  }

  if (pageDetailMatch && request.method === "PATCH") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(
      await buildPageUpdateResponse(request, env, decodeURIComponent(pageDetailMatch[1])),
      request,
      env,
    );
  }

  if (pageDetailMatch && request.method === "DELETE") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(
      await buildPageDeleteResponse(request, env, decodeURIComponent(pageDetailMatch[1])),
      request,
      env,
    );
  }

  if (url.pathname === "/onboarding/status" && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildOnboardingStatusResponse(request, env), request, env);
  }

  if (url.pathname === "/onboarding/business-context" && request.method === "POST") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildOnboardingBusinessContextResponse(request, env), request, env);
  }

  if (url.pathname === "/onboarding/preferences" && request.method === "POST") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildOnboardingPreferencesResponse(request, env), request, env);
  }

  if (url.pathname === "/onboarding/agent-setup" && request.method === "POST") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildOnboardingAgentSetupResponse(request, env), request, env);
  }

  if (url.pathname === "/onboarding/switch-persona" && request.method === "POST") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildOnboardingSwitchPersonaResponse(request, env), request, env);
  }

  if (url.pathname === "/onboarding/complete" && request.method === "POST") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildOnboardingCompleteResponse(request, env), request, env);
  }

  if (url.pathname === "/onboarding/extract-context" && request.method === "POST") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return buildOnboardingExtractContextResponse(request, env);
  }

  if (url.pathname === "/support/tickets" && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildSupportTicketsListResponse(request, env, url), request, env);
  }

  if (url.pathname === "/support/tickets" && request.method === "POST") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCorsStatus(await buildSupportTicketCreateResponse(request, env), request, env, 201);
  }

  const supportTicketMatch = /^\/support\/tickets\/([^/]+)$/.exec(url.pathname);
  if (supportTicketMatch && request.method === "PATCH") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(
      await buildSupportTicketUpdateResponse(
        request,
        env,
        decodeURIComponent(supportTicketMatch[1]),
      ),
      request,
      env,
    );
  }

  if (supportTicketMatch && request.method === "DELETE") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return buildSupportTicketDeleteResponse(
      request,
      env,
      decodeURIComponent(supportTicketMatch[1]),
    );
  }

  if (url.pathname === "/community/posts" && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildCommunityPostsListResponse(request, env, url), request, env);
  }

  if (url.pathname === "/community/posts" && request.method === "POST") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCorsStatus(await buildCommunityPostCreateResponse(request, env), request, env, 201);
  }

  const communityPostMatch = /^\/community\/posts\/([^/]+)$/.exec(url.pathname);
  if (communityPostMatch && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(
      await buildCommunityPostDetailResponse(
        request,
        env,
        decodeURIComponent(communityPostMatch[1]),
      ),
      request,
      env,
    );
  }

  const communityCommentMatch = /^\/community\/posts\/([^/]+)\/comments$/.exec(url.pathname);
  if (communityCommentMatch && request.method === "POST") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCorsStatus(
      await buildCommunityCommentCreateResponse(
        request,
        env,
        decodeURIComponent(communityCommentMatch[1]),
      ),
      request,
      env,
      201,
    );
  }

  const communityUpvoteMatch = /^\/community\/posts\/([^/]+)\/upvote$/.exec(url.pathname);
  if (communityUpvoteMatch && request.method === "POST") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(
      await buildCommunityUpvoteToggleResponse(
        request,
        env,
        decodeURIComponent(communityUpvoteMatch[1]),
      ),
      request,
      env,
    );
  }

  if (url.pathname === "/teams/workspace" && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildTeamWorkspaceResponse(request, env), request, env);
  }

  if (url.pathname === "/teams/members" && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildTeamMembersResponse(request, env), request, env);
  }

  if (url.pathname === "/teams/invites/details" && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildTeamInviteDetailsResponse(request, env, url), request, env);
  }

  if (url.pathname === "/teams/invites" && request.method === "POST") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildTeamInviteCreateResponse(request, env), request, env);
  }

  if (url.pathname === "/teams/invites/accept" && request.method === "POST") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildTeamInviteAcceptResponse(request, env), request, env);
  }

  if (url.pathname === "/teams/analytics" && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildTeamAnalyticsResponse(request, env), request, env);
  }

  if (url.pathname === "/teams/shared/initiatives" && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildTeamSharedInitiativesResponse(request, env, url), request, env);
  }

  if (url.pathname === "/teams/shared/workflows" && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildTeamSharedWorkflowsResponse(request, env, url), request, env);
  }

  if (url.pathname === "/teams/activity" && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildTeamActivityResponse(request, env, url), request, env);
  }

  if (url.pathname === "/account/facebook-deletion-callback" && request.method === "POST") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildFacebookDeletionCallbackResponse(request, env), request, env);
  }

  if (url.pathname === "/account/export" && request.method === "POST") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildAccountExportResponse(request, env), request, env);
  }

  if (url.pathname === "/account/delete" && request.method === "DELETE") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildAccountDeleteResponse(request, env), request, env);
  }

  const deletionStatusMatch = /^\/account\/deletion-status\/([^/]+)$/.exec(url.pathname);
  if (deletionStatusMatch && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(
      await buildAccountDeletionStatusResponse(
        request,
        env,
        decodeURIComponent(deletionStatusMatch[1]),
      ),
      request,
      env,
    );
  }

  const authorizeMatch = /^\/integrations\/([^/]+)\/authorize$/.exec(url.pathname);
  if (authorizeMatch && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    const provider = decodeURIComponent(authorizeMatch[1]).trim().toLowerCase();
    return buildIntegrationAuthorizeResponse(request, env, provider, url);
  }

  const callbackMatch = /^\/integrations\/([^/]+)\/callback$/.exec(url.pathname);
  if (callbackMatch && request.method === "GET") {
    const provider = decodeURIComponent(callbackMatch[1]).trim().toLowerCase();
    return buildIntegrationCallbackResponse(request, env, provider, url);
  }

  if (url.pathname === "/health/public") {
    return jsonWithCors(
      {
        ok: true,
        service: "pikar-public-api",
        mode: "phase-2",
        checked_at: new Date().toISOString(),
      },
      request,
      env,
    );
  }

  return null;
}

async function proxyFallback(
  request: Request,
  env: Env,
  route: "fallback" | "native-verified-proxy" = "fallback",
): Promise<Response> {
  const incoming = new URL(request.url);
  const origin = normalizeOrigin(env.FALLBACK_BACKEND_ORIGIN, "FALLBACK_BACKEND_ORIGIN");
  const target = new URL(`${origin}${incoming.pathname}${incoming.search}`);
  const headers = new Headers(request.headers);

  if (!headers.has("x-forwarded-host")) {
    headers.set("x-forwarded-host", incoming.host);
  }
  if (!headers.has("x-forwarded-proto")) {
    headers.set("x-forwarded-proto", incoming.protocol.replace(":", ""));
  }

  const response = await fetch(
    new Request(target.toString(), {
      method: request.method,
      headers,
      body: request.method === "GET" || request.method === "HEAD" ? undefined : request.body,
      redirect: "manual",
    }),
  );

  const outgoing = new Headers(response.headers);
  const corsHeaders = buildCorsHeaders(request, env);
  corsHeaders.forEach((value, key) => outgoing.set(key, value));
  outgoing.set("x-pikar-public-route", route);
  outgoing.set("x-pikar-public-target", target.origin);

  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: outgoing,
  });
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (request.method === "OPTIONS") {
      return handlePreflight(request, env);
    }

    try {
      return (await maybeHandleNativeRoute(request, env, url)) ?? (await proxyFallback(request, env));
    } catch (error) {
      if (error instanceof Response) {
        const headers = new Headers(error.headers);
        const corsHeaders = buildCorsHeaders(request, env);
        corsHeaders.forEach((value, key) => headers.set(key, value));
        headers.set("x-pikar-public-route", "native");
        return new Response(error.body, {
          status: error.status,
          statusText: error.statusText,
          headers,
        });
      }

      return Response.json(
        {
          ok: false,
          error: error instanceof Error ? error.message : "Unknown public API error",
        },
        { status: 500 },
      );
    }
  },
};
