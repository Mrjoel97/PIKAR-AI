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
  verifier?: string;
  redirect_uri?: string;
};

type SocialOAuthProviderConfig = {
  auth_url: string;
  token_url: string;
  scopes: string[];
  client_id_env: string;
  client_secret_env: string;
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

type MonitoringJobType = "competitor" | "market" | "topic";
type MonitoringJobImportance = "critical" | "normal" | "low";

type MonitoringJobRecord = {
  id: string;
  user_id: string;
  topic: string;
  monitoring_type: MonitoringJobType;
  importance: MonitoringJobImportance;
  is_active: boolean;
  keyword_triggers: string[];
  pinned_urls: string[];
  excluded_urls: string[];
  last_run_at: string | null;
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

type GovernanceApprovalDecision = "approved" | "rejected";

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

type DataIoColumnType = "text" | "enum" | "numeric" | "integer" | "date";

type DataIoColumnDefinition = {
  type: DataIoColumnType;
  values?: readonly string[];
  min?: number;
  max?: number;
};

type DataIoTableDefinition = {
  label: string;
  required: string[];
  columns: Record<string, DataIoColumnDefinition>;
};

type ParsedDataIoCsv = {
  headers: string[];
  rows: string[][];
  rowCount: number;
};

type DataIoValidationError = {
  row: number;
  column: string;
  value: unknown;
  reason: string;
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
const MONITORING_JOB_TYPES = ["competitor", "market", "topic"] as const;
const MONITORING_JOB_IMPORTANCE_LEVELS = ["critical", "normal", "low"] as const;

const ACCOUNT_DELETE_SUCCESS_MESSAGE =
  "Your account and all associated data have been permanently deleted. Compliance audit records that must be retained have been anonymized — your identity has been removed.";
const EXPORT_BUCKET_NAME = "generated-documents";
const EXPORT_SIGNED_URL_EXPIRY_SECONDS = 24 * 60 * 60;
const EXPORT_JSON_CONTENT_TYPE = "application/json; charset=utf-8";
const DATA_IO_MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024;
const DATA_IO_COMMIT_BATCH_SIZE = 100;
const DATA_IO_SSE_THRESHOLD_ROWS = 1000;
const DATA_IO_CSV_CONTENT_TYPE = "text/csv; charset=utf-8";
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

const DATA_IO_TABLES: Record<string, DataIoTableDefinition> = {
  contacts: {
    label: "Contacts",
    required: ["name"],
    columns: {
      name: { type: "text" },
      email: { type: "text" },
      phone: { type: "text" },
      company: { type: "text" },
      lifecycle_stage: {
        type: "enum",
        values: ["lead", "qualified", "opportunity", "customer", "churned", "inactive"],
      },
      source: {
        type: "enum",
        values: ["form_submission", "stripe_payment", "manual", "import", "referral", "social", "other"],
      },
      estimated_value: { type: "numeric", min: 0 },
      notes: { type: "text" },
    },
  },
  financial_records: {
    label: "Financial Records",
    required: ["amount"],
    columns: {
      transaction_type: { type: "text" },
      amount: { type: "numeric", min: 0 },
      currency: { type: "text" },
      category: { type: "text" },
      description: { type: "text" },
      transaction_date: { type: "date" },
    },
  },
  initiatives: {
    label: "Initiatives",
    required: ["title"],
    columns: {
      title: { type: "text" },
      description: { type: "text" },
      priority: { type: "text" },
      status: { type: "text" },
      progress: { type: "integer", min: 0, max: 100 },
    },
  },
  content_bundles: {
    label: "Content Bundles",
    required: ["title"],
    columns: {
      source: { type: "text" },
      title: { type: "text" },
      prompt: { type: "text" },
      bundle_type: {
        type: "enum",
        values: ["social", "blog", "email", "ad", "video", "general"],
      },
      status: {
        type: "enum",
        values: ["draft", "scheduled", "published", "archived"],
      },
    },
  },
  support_tickets: {
    label: "Support Tickets",
    required: ["subject"],
    columns: {
      subject: { type: "text" },
      description: { type: "text" },
      customer_email: { type: "text" },
      priority: { type: "text" },
      status: { type: "text" },
    },
  },
  recruitment_candidates: {
    label: "Candidates",
    required: ["name"],
    columns: {
      name: { type: "text" },
      email: { type: "text" },
      resume_url: { type: "text" },
      status: { type: "text" },
    },
  },
  compliance_risks: {
    label: "Compliance Risks",
    required: ["title"],
    columns: {
      title: { type: "text" },
      description: { type: "text" },
      severity: { type: "text" },
      mitigation_plan: { type: "text" },
      owner: { type: "text" },
      status: { type: "text" },
    },
  },
  compliance_audits: {
    label: "Compliance Audits",
    required: ["title"],
    columns: {
      title: { type: "text" },
      scope: { type: "text" },
      auditor: { type: "text" },
      scheduled_date: { type: "date" },
      status: { type: "text" },
      findings: { type: "text" },
    },
  },
};

const EMAIL_SEQUENCE_VALID_STATUS_TRANSITIONS: Record<string, string[]> = {
  draft: ["active"],
  active: ["paused", "completed"],
  paused: ["active", "completed"],
  completed: [],
};

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

const SOCIAL_OAUTH_PROVIDER_CONFIGS: Record<string, SocialOAuthProviderConfig> = {
  linkedin: {
    auth_url: "https://www.linkedin.com/oauth/v2/authorization",
    token_url: "https://www.linkedin.com/oauth/v2/accessToken",
    scopes: ["openid", "profile", "w_member_social"],
    client_id_env: "LINKEDIN_CLIENT_ID",
    client_secret_env: "LINKEDIN_CLIENT_SECRET",
  },
  twitter: {
    auth_url: "https://twitter.com/i/oauth2/authorize",
    token_url: "https://api.twitter.com/2/oauth2/token",
    scopes: ["tweet.read", "tweet.write", "users.read", "offline.access"],
    client_id_env: "TWITTER_CLIENT_ID",
    client_secret_env: "TWITTER_CLIENT_SECRET",
  },
  facebook: {
    auth_url: "https://www.facebook.com/v18.0/dialog/oauth",
    token_url: "https://graph.facebook.com/v18.0/oauth/access_token",
    scopes: [
      "pages_show_list",
      "pages_manage_posts",
      "pages_read_engagement",
      "read_insights",
    ],
    client_id_env: "FACEBOOK_APP_ID",
    client_secret_env: "FACEBOOK_APP_SECRET",
  },
  instagram: {
    auth_url: "https://www.facebook.com/v18.0/dialog/oauth",
    token_url: "https://graph.facebook.com/v18.0/oauth/access_token",
    scopes: [
      "instagram_basic",
      "instagram_content_publish",
      "instagram_manage_insights",
      "pages_show_list",
    ],
    client_id_env: "FACEBOOK_APP_ID",
    client_secret_env: "FACEBOOK_APP_SECRET",
  },
  youtube: {
    auth_url: "https://accounts.google.com/o/oauth2/v2/auth",
    token_url: "https://oauth2.googleapis.com/token",
    scopes: [
      "https://www.googleapis.com/auth/youtube.upload",
      "https://www.googleapis.com/auth/youtube",
    ],
    client_id_env: "GOOGLE_CLIENT_ID",
    client_secret_env: "GOOGLE_CLIENT_SECRET",
  },
  tiktok: {
    auth_url: "https://www.tiktok.com/v2/auth/authorize/",
    token_url: "https://open.tiktokapis.com/v2/oauth/token/",
    scopes: ["user.info.basic", "video.publish", "video.upload"],
    client_id_env: "TIKTOK_CLIENT_KEY",
    client_secret_env: "TIKTOK_CLIENT_SECRET",
  },
};

const CONFIGURATION_MUTABLE_KEYS = new Set([
  "notification_preferences",
  "theme",
  "language",
  "timezone",
  "persona",
  "onboarding_step",
  "dashboard_layout",
  "briefing_schedule",
  "email_digest_frequency",
  "auto_triage_enabled",
  "sessions",
  "TAVILY_API_KEY",
  "FIRECRAWL_API_KEY",
  "STITCH_API_KEY",
  "STRIPE_API_KEY",
  "CANVA_API_KEY",
  "RESEND_API_KEY",
  "HUBSPOT_API_KEY",
  "GOOGLE_SEO_SERVICE_ACCOUNT_JSON",
  "GOOGLE_ANALYTICS_PROPERTY_ID",
]);

const SENSITIVE_CONFIGURATION_KEYS = new Set([
  "TAVILY_API_KEY",
  "FIRECRAWL_API_KEY",
  "STITCH_API_KEY",
  "STRIPE_API_KEY",
  "CANVA_API_KEY",
  "RESEND_API_KEY",
  "HUBSPOT_API_KEY",
  "GOOGLE_SEO_SERVICE_ACCOUNT_JSON",
]);

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

const NATIVE_FAMILY_ROOT_404_PATHS = new Set([
  "/webhooks",
  "/approvals",
  "/community",
  "/account",
  "/teams",
  "/integrations",
  "/configuration",
  "/support",
  "/onboarding",
  "/finance",
  "/sales",
  "/content",
  "/governance",
  "/learning",
  "/kpis",
  "/data-io",
  "/ad-approvals",
  "/outbound-webhooks",
]);

function isNativeFamilyRoot404Path(pathname: string): boolean {
  const normalized =
    pathname.length > 1 && pathname.endsWith("/") ? pathname.slice(0, -1) : pathname;
  return NATIVE_FAMILY_ROOT_404_PATHS.has(normalized);
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

async function postSupabaseAdminPayload<T>(
  env: Env,
  path: string,
  payload: unknown,
  prefer = "return=representation",
): Promise<T> {
  const context = getSupabaseAdminContext(env);
  const headers = new Headers(context.headers);
  headers.set("Prefer", prefer);

  const response = await fetch(`${context.supabaseUrl}${path}`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error(`Supabase admin insert failed with ${response.status}.`);
  }

  if (prefer === "return=minimal" || response.status === 204) {
    return null as T;
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

function normalizeGovernanceApprovalDecision(value: unknown): GovernanceApprovalDecision | null {
  if (typeof value !== "string") {
    return null;
  }

  const normalized = value.trim().toLowerCase();
  return normalized === "approved" || normalized === "rejected"
    ? normalized
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

function parseGovernanceApprovalChainCreatePayload(
  payload: Record<string, unknown>,
  request: Request,
  env: Env,
): {
  action_type: string;
  resource_id: string | null;
  resource_label: string | null;
  steps: Array<{ role_label: string; approver_user_id?: string | null }> | null;
} {
  const actionType = requireTextField(payload, "action_type", request, env);
  const resourceId = normalizeOptionalText(payload.resource_id);
  const resourceLabel = normalizeOptionalText(payload.resource_label);

  let steps: Array<{ role_label: string; approver_user_id?: string | null }> | null = null;
  if (payload.steps !== undefined && payload.steps !== null) {
    if (!Array.isArray(payload.steps)) {
      throw buildErrorResponse(request, env, 400, {
        detail: "steps must be an array",
      });
    }

    steps = payload.steps.map((step, index) => {
      const record = asRecord(step);
      if (!record) {
        throw buildErrorResponse(request, env, 400, {
          detail: `steps[${index}] must be an object`,
        });
      }

      const roleLabel = requireTextField(record, "role_label", request, env);
      const approverUserId = normalizeOptionalText(record.approver_user_id);
      return {
        role_label: roleLabel,
        ...(approverUserId ? { approver_user_id: approverUserId } : {}),
      };
    });
  }

  return {
    action_type: actionType,
    resource_id: resourceId,
    resource_label: resourceLabel,
    steps,
  };
}

function parseGovernanceApprovalDecisionPayload(
  payload: Record<string, unknown>,
  request: Request,
  env: Env,
): { decision: GovernanceApprovalDecision; comment: string | null } {
  const decision = normalizeGovernanceApprovalDecision(payload.decision);
  if (!decision) {
    throw buildErrorResponse(request, env, 400, {
      detail: "decision must be either approved or rejected",
    });
  }

  return {
    decision,
    comment: normalizeOptionalText(payload.comment),
  };
}

function normalizeMonitoringJobType(value: unknown): MonitoringJobType | null {
  if (typeof value !== "string") {
    return null;
  }

  const normalized = value.trim().toLowerCase();
  return MONITORING_JOB_TYPES.includes(normalized as MonitoringJobType)
    ? (normalized as MonitoringJobType)
    : null;
}

function normalizeMonitoringJobImportance(value: unknown): MonitoringJobImportance | null {
  if (typeof value !== "string") {
    return null;
  }

  const normalized = value.trim().toLowerCase();
  return MONITORING_JOB_IMPORTANCE_LEVELS.includes(normalized as MonitoringJobImportance)
    ? (normalized as MonitoringJobImportance)
    : null;
}

function normalizeMonitoringJobRecord(record: Record<string, unknown>): MonitoringJobRecord {
  const createdAt =
    typeof record.created_at === "string" ? record.created_at : new Date().toISOString();
  const updatedAt =
    typeof record.updated_at === "string" ? record.updated_at : createdAt;

  return {
    id: typeof record.id === "string" ? record.id : "",
    user_id: typeof record.user_id === "string" ? record.user_id : "",
    topic: typeof record.topic === "string" ? record.topic : "",
    monitoring_type: normalizeMonitoringJobType(record.monitoring_type) ?? "competitor",
    importance: normalizeMonitoringJobImportance(record.importance) ?? "normal",
    is_active: record.is_active === true,
    keyword_triggers: normalizeStringArrayValues(record.keyword_triggers),
    pinned_urls: normalizeStringArrayValues(record.pinned_urls),
    excluded_urls: normalizeStringArrayValues(record.excluded_urls),
    last_run_at: typeof record.last_run_at === "string" ? record.last_run_at : null,
    created_at: createdAt,
    updated_at: updatedAt,
  };
}

function parseCreateMonitoringJobPayload(
  payload: Record<string, unknown>,
  request: Request,
  env: Env,
): {
  topic: string;
  monitoring_type: MonitoringJobType;
  importance: MonitoringJobImportance;
  keyword_triggers: string[];
  pinned_urls: string[];
  excluded_urls: string[];
} {
  const topic = requireTextField(payload, "topic", request, env);
  const monitoringType = normalizeMonitoringJobType(payload.monitoring_type) ?? "competitor";
  const importance = normalizeMonitoringJobImportance(payload.importance) ?? "normal";

  const keywordTriggers = normalizeOptionalStringArray(payload.keyword_triggers);
  if (payload.keyword_triggers !== undefined && payload.keyword_triggers !== null && !keywordTriggers) {
    throw buildErrorResponse(request, env, 400, {
      detail: "keyword_triggers must be an array of strings",
    });
  }

  const pinnedUrls = normalizeOptionalStringArray(payload.pinned_urls);
  if (payload.pinned_urls !== undefined && payload.pinned_urls !== null && !pinnedUrls) {
    throw buildErrorResponse(request, env, 400, {
      detail: "pinned_urls must be an array of strings",
    });
  }

  const excludedUrls = normalizeOptionalStringArray(payload.excluded_urls);
  if (payload.excluded_urls !== undefined && payload.excluded_urls !== null && !excludedUrls) {
    throw buildErrorResponse(request, env, 400, {
      detail: "excluded_urls must be an array of strings",
    });
  }

  return {
    topic,
    monitoring_type: monitoringType,
    importance,
    keyword_triggers: keywordTriggers ?? [],
    pinned_urls: pinnedUrls ?? [],
    excluded_urls: excludedUrls ?? [],
  };
}

function parseUpdateMonitoringJobPayload(
  payload: Record<string, unknown>,
  request: Request,
  env: Env,
): Record<string, unknown> {
  const update: Record<string, unknown> = {};

  if (payload.is_active !== undefined && payload.is_active !== null) {
    if (typeof payload.is_active !== "boolean") {
      throw buildErrorResponse(request, env, 400, {
        detail: "is_active must be a boolean",
      });
    }
    update.is_active = payload.is_active;
  }

  if (payload.importance !== undefined && payload.importance !== null) {
    const importance = normalizeMonitoringJobImportance(payload.importance);
    if (!importance) {
      throw buildErrorResponse(request, env, 400, {
        detail: "importance must be one of critical, normal, low",
      });
    }
    update.importance = importance;
  }

  if (payload.keyword_triggers !== undefined && payload.keyword_triggers !== null) {
    const keywordTriggers = normalizeOptionalStringArray(payload.keyword_triggers);
    if (!keywordTriggers) {
      throw buildErrorResponse(request, env, 400, {
        detail: "keyword_triggers must be an array of strings",
      });
    }
    update.keyword_triggers = keywordTriggers;
  }

  if (payload.pinned_urls !== undefined && payload.pinned_urls !== null) {
    const pinnedUrls = normalizeOptionalStringArray(payload.pinned_urls);
    if (!pinnedUrls) {
      throw buildErrorResponse(request, env, 400, {
        detail: "pinned_urls must be an array of strings",
      });
    }
    update.pinned_urls = pinnedUrls;
  }

  if (payload.excluded_urls !== undefined && payload.excluded_urls !== null) {
    const excludedUrls = normalizeOptionalStringArray(payload.excluded_urls);
    if (!excludedUrls) {
      throw buildErrorResponse(request, env, 400, {
        detail: "excluded_urls must be an array of strings",
      });
    }
    update.excluded_urls = excludedUrls;
  }

  if (Object.keys(update).length === 0) {
    throw buildErrorResponse(request, env, 400, {
      detail: "No fields provided to update",
    });
  }

  return update;
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

function isFeatureAllowedForTier(
  featureKey: "teams" | "sales" | "reports" | "governance",
  tier: PersonaTier,
): boolean {
  const minTierByFeature: Record<
    "teams" | "sales" | "reports" | "governance",
    PersonaTier
  > = {
    teams: "startup",
    sales: "solopreneur",
    reports: "solopreneur",
    governance: "enterprise",
  };

  return TIER_ORDER.indexOf(tier) >= TIER_ORDER.indexOf(minTierByFeature[featureKey]);
}

function buildFeatureGatePayload(
  featureKey: "teams" | "sales" | "reports" | "governance",
  currentTier: PersonaTier,
) {
  const featureMeta: Record<
    "teams" | "sales" | "reports" | "governance",
    { label: string; requiredTier: PersonaTier }
  > = {
    teams: {
      label: "Team Workspace",
      requiredTier: "startup",
    },
    sales: {
      label: "Sales Pipeline & CRM",
      requiredTier: "solopreneur",
    },
    reports: {
      label: "Reports",
      requiredTier: "solopreneur",
    },
    governance: {
      label: "SSO & Governance",
      requiredTier: "enterprise",
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

function categorizeStripeTransaction(
  description: string,
  transactionType: string,
  metadata: Record<string, unknown> | null = null,
): string {
  if (transactionType === "payout") {
    return "transfers";
  }
  if (transactionType === "revenue") {
    return "revenue";
  }
  if (transactionType === "fee") {
    return "taxes_fees";
  }

  const descLower = description.toLowerCase();
  const keywordRules: Record<string, string[]> = {
    marketing: [
      "google ads",
      "facebook ads",
      "meta ads",
      "tiktok ads",
      "linkedin ads",
      "mailchimp",
      "sendgrid",
      "hubspot marketing",
      "semrush",
      "ahrefs",
    ],
    saas_tools: [
      "slack",
      "notion",
      "github",
      "vercel",
      "figma",
      "canva",
      "zapier",
      "airtable",
      "jira",
      "confluence",
      "1password",
      "dropbox",
    ],
    payroll: ["gusto", "payroll", "salary", "wages", "adp", "rippling"],
    infrastructure: [
      "aws",
      "amazon web services",
      "gcp",
      "google cloud",
      "heroku",
      "digitalocean",
      "cloudflare",
      "datadog",
      "sentry",
    ],
    professional_services: [
      "legal",
      "accounting",
      "consulting",
      "lawyer",
      "attorney",
      "cpa",
      "bookkeeper",
    ],
    office: ["office", "coworking", "wework", "rent", "utilities", "internet"],
    travel: ["airline", "hotel", "uber", "lyft", "airbnb", "flight"],
    taxes_fees: ["stripe fee", "tax", "irs", "state tax", "processing fee"],
    cogs: ["manufacturing", "materials", "shipping", "fulfillment", "warehouse"],
  };

  for (const [category, keywords] of Object.entries(keywordRules)) {
    if (keywords.some((keyword) => descLower.includes(keyword))) {
      return category;
    }
  }

  if (metadata?.stripe_type === "stripe_fee") {
    return "taxes_fees";
  }

  return "other";
}

async function resolveStripeWebhookUserId(env: Env): Promise<string | null> {
  const rows = await fetchSupabaseAdminRows<Array<{ user_id?: string | null }>>(
    env,
    "/rest/v1/integration_credentials?provider=eq.stripe&select=user_id&limit=1",
  );
  return rows[0]?.user_id ?? null;
}

async function upsertStripeFinancialRecord(
  env: Env,
  payload: Record<string, unknown>,
): Promise<void> {
  const eventType = normalizeOptionalText(payload.type);
  const data = asRecord(asRecord(payload.data)?.object);
  if (!eventType || !data) {
    throw new Error("Invalid Stripe event payload");
  }

  const userId = await resolveStripeWebhookUserId(env);
  if (!userId) {
    throw new Error("No Stripe user found");
  }

  let row: Record<string, unknown> | null = null;
  const nowIso = new Date().toISOString();

  if (eventType === "payment_intent.succeeded") {
    const paymentIntentId = normalizeOptionalText(data.id);
    if (!paymentIntentId) {
      throw new Error("Missing Stripe payment intent id");
    }
    const description = normalizeOptionalText(data.description) ?? "Stripe payment";
    row = {
      user_id: userId,
      transaction_type: "revenue",
      amount: Math.abs(Number(data.amount_received ?? 0)) / 100,
      currency: String(data.currency ?? "usd").toUpperCase(),
      description,
      source_type: "stripe",
      source_id: paymentIntentId,
      external_id: `pi_${paymentIntentId}`,
      transaction_date: nowIso,
      metadata: { stripe_event: eventType },
      category: categorizeStripeTransaction(description, "revenue", { stripe_event: eventType }),
    };
  } else if (eventType === "charge.refunded") {
    const chargeId = normalizeOptionalText(data.id);
    if (!chargeId) {
      throw new Error("Missing Stripe charge id");
    }
    const description = normalizeOptionalText(data.description) ?? "Stripe refund";
    row = {
      user_id: userId,
      transaction_type: "refund",
      amount: Math.abs(Number(data.amount_refunded ?? 0)) / 100,
      currency: String(data.currency ?? "usd").toUpperCase(),
      description,
      source_type: "stripe",
      source_id: chargeId,
      external_id: `re_${chargeId}`,
      transaction_date: nowIso,
      metadata: { stripe_event: eventType },
      category: categorizeStripeTransaction(description, "refund", { stripe_event: eventType }),
    };
  } else if (eventType === "payout.paid") {
    const payoutId = normalizeOptionalText(data.id);
    if (!payoutId) {
      throw new Error("Missing Stripe payout id");
    }
    const description = normalizeOptionalText(data.description) ?? "Stripe payout";
    row = {
      user_id: userId,
      transaction_type: "payout",
      amount: Math.abs(Number(data.amount ?? 0)) / 100,
      currency: String(data.currency ?? "usd").toUpperCase(),
      description,
      source_type: "stripe",
      source_id: payoutId,
      external_id: `po_${payoutId}`,
      transaction_date: nowIso,
      metadata: { stripe_event: eventType },
      category: categorizeStripeTransaction(description, "payout", { stripe_event: eventType }),
    };
  }

  if (!row) {
    return;
  }

  await upsertSupabaseAdminRow<Array<Record<string, unknown>>>(
    env,
    "/rest/v1/financial_records?on_conflict=external_id&select=id",
    row,
  );
}

async function buildStripeWebhookResponse(
  request: Request,
  env: Env,
  rawBody: Uint8Array,
): Promise<Record<string, unknown>> {
  let parsed: unknown;
  try {
    parsed = JSON.parse(new TextDecoder().decode(rawBody));
  } catch {
    throw buildErrorResponse(request, env, 400, {
      detail: "Invalid JSON payload",
    });
  }

  const payload = asRecord(parsed);
  if (!payload) {
    throw buildErrorResponse(request, env, 400, {
      detail: "Invalid JSON payload",
    });
  }

  const eventType = normalizeOptionalText(payload.type) ?? "unknown";

  if (
    eventType !== "payment_intent.succeeded" &&
    eventType !== "charge.refunded" &&
    eventType !== "payout.paid"
  ) {
    return {
      status: "ignored",
      event_type: eventType,
    };
  }

  try {
    await upsertStripeFinancialRecord(env, payload);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Stripe processing failed";
    if (message === "No Stripe user found") {
      return {
        status: "skipped",
        reason: "no_stripe_user",
      };
    }

    throw buildErrorResponse(request, env, 500, {
      detail: message,
    });
  }

  return {
    status: "processed",
    event_type: eventType,
  };
}

async function fetchResendReceivedEmail(
  env: Env,
  emailId: string,
): Promise<Record<string, unknown>> {
  const apiKey = env.RESEND_API_KEY?.trim();
  if (!apiKey) {
    return {};
  }

  try {
    const response = await fetch(`https://api.resend.com/emails/${encodeURIComponent(emailId)}`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      return {};
    }

    return (asRecord(await response.json()) ?? {});
  } catch {
    return {};
  }
}

async function forwardResendInboundEmail(
  env: Env,
  input: {
    subject: string;
    bodyHtml: string | null;
    bodyText: string | null;
    originalFrom: string;
  },
): Promise<boolean> {
  const apiKey = env.RESEND_API_KEY?.trim();
  const toAddress = env.RESEND_FORWARD_TO?.trim();
  const fromEmail = env.RESEND_FROM_EMAIL?.trim() || "noreply@pikar-ai.com";
  if (!apiKey || !toAddress) {
    return false;
  }

  const htmlBody = input.bodyHtml
    ? `<div style="padding:12px;margin-bottom:16px;border-left:4px solid #6366f1;background:#f8fafc;border-radius:4px;"><strong>Forwarded email</strong><br>From: ${input.originalFrom}<br>Subject: ${input.subject}</div><hr style='border:none;border-top:1px solid #e2e8f0;margin:16px 0;'>${input.bodyHtml}`
    : `<pre>--- Forwarded email ---\nFrom: ${input.originalFrom}\nSubject: ${input.subject}\n---\n\n${input.bodyText ?? "(empty body)"}</pre>`;

  try {
    const response = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        from: `Pikar AI Mail <${fromEmail}>`,
        to: [toAddress],
        subject: `[Fwd] ${input.subject} (from ${input.originalFrom})`,
        html: htmlBody,
        reply_to: input.originalFrom,
      }),
    });
    return response.ok;
  } catch {
    return false;
  }
}

async function handleResendSequenceEvent(
  env: Env,
  eventType: string,
  payload: Record<string, unknown>,
): Promise<void> {
  try {
    const data = asRecord(payload.data) ?? {};
    const headers = asRecord(data.headers) ?? {};
    const tags = asRecord(data.tags) ?? {};
    const enrollmentId =
      normalizeOptionalText(headers["X-Pikar-Enrollment-Id"]) ??
      normalizeOptionalText(tags.pikar_enrollment_id);
    if (!enrollmentId) {
      return;
    }

    const stepRaw =
      normalizeOptionalText(headers["X-Pikar-Step"]) ??
      normalizeOptionalText(tags.pikar_step);
    const stepNumber = stepRaw ? Number.parseInt(stepRaw, 10) || 0 : 0;

    if (eventType === "email.bounced") {
      await insertSupabaseAdminRow<Array<Record<string, unknown>>>(
        env,
        "/rest/v1/email_tracking_events?select=id",
        {
          enrollment_id: enrollmentId,
          step_number: stepNumber,
          event_type: "bounced",
          metadata: {},
        },
      );
      await updateSupabaseAdminRows<Array<Record<string, unknown>>>(
        env,
        `/rest/v1/email_sequence_enrollments?id=eq.${encodeURIComponent(enrollmentId)}`,
        {
          status: "bounced",
        },
      );
      return;
    }

    if (eventType === "email.opened" || eventType === "email.clicked") {
      await insertSupabaseAdminRow<Array<Record<string, unknown>>>(
        env,
        "/rest/v1/email_tracking_events?select=id",
        {
          enrollment_id: enrollmentId,
          step_number: stepNumber,
          event_type: eventType === "email.opened" ? "open" : "click",
          metadata: {
            source: "resend_webhook",
            resend_event: eventType,
          },
        },
      );
    }
  } catch {
    return;
  }
}

async function buildResendWebhookResponse(
  request: Request,
  env: Env,
  rawBody: Uint8Array,
): Promise<Record<string, unknown>> {
  let parsed: unknown;
  try {
    parsed = JSON.parse(new TextDecoder().decode(rawBody));
  } catch {
    throw buildErrorResponse(request, env, 400, {
      detail: "Invalid JSON payload",
    });
  }

  const payload = asRecord(parsed);
  if (!payload) {
    throw buildErrorResponse(request, env, 400, {
      detail: "Invalid JSON payload",
    });
  }

  const eventType = normalizeOptionalText(payload.type) ?? "unknown";
  if (
    eventType === "email.bounced" ||
    eventType === "email.opened" ||
    eventType === "email.clicked"
  ) {
    await handleResendSequenceEvent(env, eventType, payload);
    return {
      status: "processed",
      event_type: eventType,
    };
  }

  if (eventType !== "email.received") {
    return {
      status: "ignored",
      event_type: eventType,
    };
  }

  const data = asRecord(payload.data) ?? {};
  const emailId = normalizeOptionalText(data.email_id);
  if (!emailId) {
    throw buildErrorResponse(request, env, 400, {
      detail: "Missing email_id in event data",
    });
  }

  const fullEmail = await fetchResendReceivedEmail(env, emailId);
  const normalizeAddressList = (value: unknown, fallback: unknown): string[] => {
    const target = value ?? fallback;
    if (Array.isArray(target)) {
      return target.filter((item): item is string => typeof item === "string");
    }
    const single = normalizeOptionalText(target);
    return single ? [single] : [];
  };

  const fromAddress =
    normalizeOptionalText(data.from) ?? normalizeOptionalText(fullEmail.from) ?? "unknown";
  const subject =
    normalizeOptionalText(data.subject) ??
    normalizeOptionalText(fullEmail.subject) ??
    "(no subject)";
  const bodyHtml = normalizeOptionalText(fullEmail.html);
  const bodyText = normalizeOptionalText(fullEmail.text);
  const headers = asRecord(fullEmail.headers) ?? {};
  const attachments = Array.isArray(data.attachments)
    ? data.attachments
    : Array.isArray(fullEmail.attachments)
      ? fullEmail.attachments
      : [];
  const messageId =
    normalizeOptionalText(data.message_id) ?? normalizeOptionalText(fullEmail.message_id);

  const storedRows = await upsertSupabaseAdminRow<Array<{ id?: string | null }>>(
    env,
    "/rest/v1/inbound_emails?on_conflict=resend_email_id&select=id",
    {
      resend_email_id: emailId,
      from_address: fromAddress,
      to_addresses: normalizeAddressList(data.to, fullEmail.to),
      cc_addresses: normalizeAddressList(data.cc, fullEmail.cc),
      bcc_addresses: normalizeAddressList(data.bcc, fullEmail.bcc),
      subject,
      body_html: bodyHtml,
      body_text: bodyText,
      headers,
      attachments,
      message_id: messageId,
      status: "received",
    },
  );

  const recordId = storedRows[0]?.id ?? null;
  const forwarded = await forwardResendInboundEmail(env, {
    subject,
    bodyHtml,
    bodyText,
    originalFrom: fromAddress,
  });

  if (recordId) {
    const updatePayload: Record<string, unknown> = {
      status: forwarded ? "forwarded" : "received",
    };
    if (forwarded) {
      updatePayload.forwarded_to = env.RESEND_FORWARD_TO?.trim() ?? null;
      updatePayload.forwarded_at = new Date().toISOString();
    }

    await updateSupabaseAdminRows<Array<Record<string, unknown>>>(
      env,
      `/rest/v1/inbound_emails?id=eq.${encodeURIComponent(recordId)}`,
      updatePayload,
    );
  }

  return {
    status: "processed",
    email_id: emailId,
    forwarded,
  };
}

async function fetchIntegrationCredentialRows(
  env: Env,
  provider: string,
): Promise<Array<Record<string, unknown>>> {
  return fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/integration_credentials?provider=eq.${encodeURIComponent(provider)}&select=user_id,access_token,refresh_token,account_name,expires_at,token_type,scopes`,
  );
}

async function resolveShopifyWebhookUser(
  env: Env,
  shopDomain: string,
): Promise<string | null> {
  const rows = await fetchIntegrationCredentialRows(env, "shopify");
  if (!rows.length) {
    return null;
  }

  const shopSlug = shopDomain.replace(/\.myshopify\.com$/i, "");
  for (const row of rows) {
    const accountName = typeof row.account_name === "string" ? row.account_name : "";
    if (accountName === shopSlug || accountName === shopDomain) {
      return typeof row.user_id === "string" ? row.user_id : null;
    }
  }

  return typeof rows[0]?.user_id === "string" ? rows[0].user_id : null;
}

async function createLowStockNotifications(
  env: Env,
  userId: string,
): Promise<number> {
  const rows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/shopify_products?user_id=eq.${encodeURIComponent(userId)}&select=id,shopify_product_id,title,inventory_quantity,low_stock_threshold`,
  );

  const lowStock = rows.filter((row) => {
    const inventory = typeof row.inventory_quantity === "number"
      ? row.inventory_quantity
      : Number(row.inventory_quantity ?? 0);
    const threshold = typeof row.low_stock_threshold === "number"
      ? row.low_stock_threshold
      : Number(row.low_stock_threshold ?? 10);
    return Number.isFinite(inventory) && Number.isFinite(threshold) && inventory < threshold;
  });

  let count = 0;
  for (const product of lowStock) {
    const title = typeof product.title === "string" && product.title.trim()
      ? product.title
      : "Unknown Product";
    const inventory = typeof product.inventory_quantity === "number"
      ? product.inventory_quantity
      : Number(product.inventory_quantity ?? 0);
    const threshold = typeof product.low_stock_threshold === "number"
      ? product.low_stock_threshold
      : Number(product.low_stock_threshold ?? 10);

    await insertSupabaseAdminRow<Array<Record<string, unknown>>>(
      env,
      "/rest/v1/notifications?select=id",
      {
        user_id: userId,
        title: "Low Stock Alert",
        message: `${title} is low on stock (${inventory} remaining, threshold: ${threshold})`,
        type: "warning",
        link: "/dashboard/inventory",
        is_read: false,
        metadata: {
          product_id: product.id,
          shopify_product_id: product.shopify_product_id,
          inventory_quantity: inventory,
          low_stock_threshold: threshold,
        },
      },
    );
    count += 1;
  }

  return count;
}

async function buildShopifyWebhookResponse(
  request: Request,
  env: Env,
  rawBody: Uint8Array,
): Promise<Record<string, unknown>> {
  let parsed: unknown;
  try {
    parsed = JSON.parse(new TextDecoder().decode(rawBody));
  } catch {
    throw buildErrorResponse(request, env, 400, {
      detail: "Invalid JSON payload",
    });
  }

  const payload = asRecord(parsed);
  if (!payload) {
    throw buildErrorResponse(request, env, 400, {
      detail: "Invalid JSON payload",
    });
  }

  const topic = request.headers.get("X-Shopify-Topic")?.trim() ?? "unknown";
  const shopDomain = request.headers.get("X-Shopify-Shop-Domain")?.trim() ?? "";
  const userId = await resolveShopifyWebhookUser(env, shopDomain);
  if (!userId) {
    return { status: "skipped" };
  }

  if (topic === "orders/create") {
    const shopifyOrderId = String(payload.id ?? "");
    const totalPrice = Number.parseFloat(String(payload.total_price ?? "0")) || 0;
    const subtotalPrice = Number.parseFloat(String(payload.subtotal_price ?? "0")) || 0;
    const currency = typeof payload.currency === "string" ? payload.currency : "USD";
    const lineItems = Array.isArray(payload.line_items)
      ? payload.line_items.map((item) => {
          const row = asRecord(item) ?? {};
          return {
            title: typeof row.title === "string" ? row.title : "",
            quantity: typeof row.quantity === "number" ? row.quantity : Number(row.quantity ?? 0),
            price: typeof row.price === "string" ? row.price : String(row.price ?? "0"),
          };
        })
      : [];

    await upsertSupabaseAdminRow<Array<Record<string, unknown>>>(
      env,
      "/rest/v1/shopify_orders?on_conflict=user_id,shopify_order_id&select=id",
      {
        user_id: userId,
        shopify_order_id: shopifyOrderId,
        order_number: typeof payload.name === "string" ? payload.name : "",
        email: typeof payload.email === "string" ? payload.email : "",
        financial_status: typeof payload.financial_status === "string" ? payload.financial_status : "",
        fulfillment_status: typeof payload.fulfillment_status === "string" ? payload.fulfillment_status : null,
        total_price: totalPrice,
        subtotal_price: subtotalPrice,
        currency,
        line_items: lineItems,
        customer: asRecord(payload.customer) ?? {},
        created_at_shopify: typeof payload.created_at === "string" ? payload.created_at : null,
      },
    );

    await upsertSupabaseAdminRow<Array<Record<string, unknown>>>(
      env,
      "/rest/v1/financial_records?on_conflict=external_id&select=id",
      {
        user_id: userId,
        title: `Shopify Order ${typeof payload.name === "string" ? payload.name : shopifyOrderId}`,
        amount: totalPrice,
        currency,
        transaction_type: "revenue",
        source_type: "shopify",
        external_id: `shop_order_${shopifyOrderId}`,
        transaction_date: typeof payload.created_at === "string" ? payload.created_at : new Date().toISOString(),
      },
    );

    return { status: "processed" };
  }

  if (topic === "orders/updated") {
    const shopifyOrderId = String(payload.id ?? "");
    const lineItems = Array.isArray(payload.line_items)
      ? payload.line_items.map((item) => {
          const row = asRecord(item) ?? {};
          return {
            title: typeof row.title === "string" ? row.title : "",
            quantity: typeof row.quantity === "number" ? row.quantity : Number(row.quantity ?? 0),
            price: typeof row.price === "string" ? row.price : String(row.price ?? "0"),
          };
        })
      : [];

    await updateSupabaseAdminRows<Array<Record<string, unknown>>>(
      env,
      `/rest/v1/shopify_orders?user_id=eq.${encodeURIComponent(userId)}&shopify_order_id=eq.${encodeURIComponent(shopifyOrderId)}`,
      {
        financial_status: typeof payload.financial_status === "string" ? payload.financial_status : "",
        fulfillment_status: typeof payload.fulfillment_status === "string" ? payload.fulfillment_status : null,
        total_price: Number.parseFloat(String(payload.total_price ?? "0")) || 0,
        subtotal_price: Number.parseFloat(String(payload.subtotal_price ?? "0")) || 0,
        line_items: lineItems,
        customer: asRecord(payload.customer) ?? {},
      },
    );
    return { status: "processed" };
  }

  if (topic === "products/update") {
    const shopifyProductId = String(payload.id ?? "");
    let totalInventory = 0;
    const variants = Array.isArray(payload.variants)
      ? payload.variants.map((item) => {
          const row = asRecord(item) ?? {};
          const quantity = typeof row.inventory_quantity === "number"
            ? row.inventory_quantity
            : Number(row.inventory_quantity ?? 0);
          totalInventory += Number.isFinite(quantity) ? quantity : 0;
          return {
            id: String(row.id ?? ""),
            title: typeof row.title === "string" ? row.title : "",
            price: typeof row.price === "string" ? row.price : String(row.price ?? "0"),
            inventory_quantity: Number.isFinite(quantity) ? quantity : 0,
            sku: typeof row.sku === "string" ? row.sku : "",
          };
        })
      : [];
    const image = asRecord(payload.image);

    await upsertSupabaseAdminRow<Array<Record<string, unknown>>>(
      env,
      "/rest/v1/shopify_products?on_conflict=user_id,shopify_product_id&select=id",
      {
        user_id: userId,
        shopify_product_id: shopifyProductId,
        title: typeof payload.title === "string" ? payload.title : "",
        vendor: typeof payload.vendor === "string" ? payload.vendor : "",
        product_type: typeof payload.product_type === "string" ? payload.product_type : "",
        status: typeof payload.status === "string" ? payload.status : "",
        variants,
        image_url: typeof image?.src === "string" ? image.src : null,
        inventory_quantity: totalInventory,
      },
    );
    return { status: "processed" };
  }

  if (topic === "inventory_levels/update") {
    const available = typeof payload.available === "number"
      ? payload.available
      : Number(payload.available ?? 0);

    await updateSupabaseAdminRows<Array<Record<string, unknown>>>(
      env,
      `/rest/v1/shopify_products?user_id=eq.${encodeURIComponent(userId)}`,
      {
        inventory_quantity: Number.isFinite(available) ? available : 0,
      },
    );
    await createLowStockNotifications(env, userId);
    return { status: "processed" };
  }

  return { status: "skipped" };
}

async function resolveHubSpotWebhookUser(
  env: Env,
  portalId: string,
): Promise<{ userId: string | null; accessToken: string | null }> {
  const rows = await fetchIntegrationCredentialRows(env, "hubspot");
  if (!rows.length) {
    return { userId: null, accessToken: null };
  }

  let matched = rows[0];
  for (const row of rows) {
    const accountName = typeof row.account_name === "string" ? row.account_name : "";
    if (accountName === portalId || accountName.includes(portalId)) {
      matched = row;
      break;
    }
  }

  const userId = typeof matched.user_id === "string" ? matched.user_id : null;
  const encryptedAccessToken = typeof matched.access_token === "string" ? matched.access_token : "";
  if (!userId || !encryptedAccessToken) {
    return { userId: null, accessToken: null };
  }

  try {
    return {
      userId,
      accessToken: await decryptFernetSecret(encryptedAccessToken, env),
    };
  } catch {
    return { userId, accessToken: null };
  }
}

async function fetchHubSpotObject(
  accessToken: string,
  objectType: "contacts" | "deals",
  objectId: string,
  properties: string[],
): Promise<Record<string, unknown> | null> {
  const params = new URLSearchParams();
  for (const property of properties) {
    params.append("properties", property);
  }

  try {
    const response = await fetch(
      `https://api.hubapi.com/crm/v3/objects/${objectType}/${encodeURIComponent(objectId)}?${params.toString()}`,
      {
        method: "GET",
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Type": "application/json",
        },
      },
    );
    if (!response.ok) {
      return null;
    }
    return asRecord(await response.json()) ?? null;
  } catch {
    return null;
  }
}

async function processHubSpotContactWebhook(
  env: Env,
  userId: string,
  accessToken: string,
  event: Record<string, unknown>,
): Promise<void> {
  const objectId = String(event.objectId ?? "");
  const subscriptionType = typeof event.subscriptionType === "string" ? event.subscriptionType : "";
  if (!objectId || (subscriptionType !== "contact.creation" && subscriptionType !== "contact.propertyChange")) {
    return;
  }

  const hsContact = await fetchHubSpotObject(accessToken, "contacts", objectId, [
    "email",
    "firstname",
    "lastname",
    "phone",
    "company",
    "lifecyclestage",
    "hs_lastmodifieddate",
  ]);
  if (!hsContact) {
    return;
  }

  const props = asRecord(hsContact.properties) ?? {};
  const firstname = typeof props.firstname === "string" ? props.firstname : "";
  const lastname = typeof props.lastname === "string" ? props.lastname : "";
  const lifecycleRaw = typeof props.lifecyclestage === "string" ? props.lifecyclestage.toLowerCase() : "";
  const lifecycleMap: Record<string, string> = {
    subscriber: "lead",
    lead: "lead",
    marketingqualifiedlead: "qualified",
    salesqualifiedlead: "opportunity",
    opportunity: "opportunity",
    customer: "customer",
    evangelist: "customer",
    other: "inactive",
  };

  const metadataEntries = Object.fromEntries(
    Object.entries(props).filter(([key]) => !["email", "firstname", "lastname", "phone", "company"].includes(key)),
  );

  await upsertSupabaseAdminRow<Array<Record<string, unknown>>>(
    env,
    "/rest/v1/contacts?on_conflict=user_id,hubspot_contact_id&select=id",
    {
      user_id: userId,
      hubspot_contact_id: objectId,
      name: `${firstname} ${lastname}`.trim() || "Unknown",
      email: typeof props.email === "string" ? props.email : null,
      phone: typeof props.phone === "string" ? props.phone : null,
      company: typeof props.company === "string" ? props.company : null,
      lifecycle_stage: lifecycleMap[lifecycleRaw] ?? "lead",
      source: "import",
      metadata: {
        hubspot_properties: metadataEntries,
      },
    },
  );
}

async function processHubSpotDealWebhook(
  env: Env,
  userId: string,
  accessToken: string,
  event: Record<string, unknown>,
): Promise<void> {
  const objectId = String(event.objectId ?? "");
  const subscriptionType = typeof event.subscriptionType === "string" ? event.subscriptionType : "";
  if (!objectId || (subscriptionType !== "deal.creation" && subscriptionType !== "deal.propertyChange")) {
    return;
  }

  const hsDeal = await fetchHubSpotObject(accessToken, "deals", objectId, [
    "dealname",
    "pipeline",
    "dealstage",
    "amount",
    "closedate",
    "hs_lastmodifieddate",
  ]);
  if (!hsDeal) {
    return;
  }

  const props = asRecord(hsDeal.properties) ?? {};
  const metadataEntries = Object.fromEntries(
    Object.entries(props).filter(([key]) => !["dealname", "pipeline", "dealstage", "amount", "closedate"].includes(key)),
  );

  await upsertSupabaseAdminRow<Array<Record<string, unknown>>>(
    env,
    "/rest/v1/hubspot_deals?on_conflict=user_id,hubspot_deal_id&select=id",
    {
      user_id: userId,
      hubspot_deal_id: objectId,
      deal_name: typeof props.dealname === "string" ? props.dealname : "Untitled Deal",
      pipeline: typeof props.pipeline === "string" ? props.pipeline : null,
      stage: typeof props.dealstage === "string" ? props.dealstage : null,
      amount: typeof props.amount === "string" && props.amount.trim() ? Number.parseFloat(props.amount) : null,
      close_date: typeof props.closedate === "string" ? props.closedate : null,
      properties: metadataEntries,
    },
  );
}

async function buildHubSpotWebhookResponse(
  request: Request,
  env: Env,
  rawBody: Uint8Array,
): Promise<Record<string, unknown>> {
  let parsed: unknown;
  try {
    parsed = JSON.parse(new TextDecoder().decode(rawBody));
  } catch {
    throw buildErrorResponse(request, env, 400, {
      detail: "Invalid JSON payload",
    });
  }

  const events = Array.isArray(parsed) ? parsed : [parsed];
  let processed = 0;
  for (const entry of events) {
    const event = asRecord(entry);
    if (!event) {
      continue;
    }

    const portalId = String(event.portalId ?? "");
    const subscriptionType = typeof event.subscriptionType === "string" ? event.subscriptionType : "";
    const { userId, accessToken } = await resolveHubSpotWebhookUser(env, portalId);
    if (!userId || !accessToken) {
      continue;
    }

    if (subscriptionType.startsWith("contact.")) {
      await processHubSpotContactWebhook(env, userId, accessToken, event);
      processed += 1;
    } else if (subscriptionType.startsWith("deal.")) {
      await processHubSpotDealWebhook(env, userId, accessToken, event);
      processed += 1;
    }
  }

  return {
    status: "processed",
    events_processed: processed,
  };
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

function isAllowedConfigurationRedirectUri(redirectUri: string, env: Env): boolean {
  try {
    const parsed = new URL(redirectUri);
    if (parsed.protocol !== "https:" && parsed.protocol !== "http:") {
      return false;
    }

    const allowedOrigins = new Set(
      [getPrimaryAppOrigin(env), ...(env.ALLOWED_ORIGINS ?? "").split(",")]
        .map((item) => item.trim().replace(/\/+$/g, ""))
        .filter(Boolean),
    );

    return allowedOrigins.has(parsed.origin.replace(/\/+$/g, ""));
  } catch {
    return false;
  }
}

async function buildPkcePair(): Promise<{ verifier: string; challenge: string }> {
  const verifier = randomBase64Url(48);
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier));
  return {
    verifier,
    challenge: toBase64Url(new Uint8Array(digest)),
  };
}

async function encodeConfigurationSocialState(
  payload: OAuthStatePayload,
  platform: string,
  env: Env,
): Promise<string> {
  const token = await encodeOAuthStateToken(payload, env);
  return `pikar:${platform}:${token}`;
}

async function decodeConfigurationSocialState(
  state: string,
  platform: string,
  env: Env,
): Promise<OAuthStatePayload | null> {
  let token = state.trim();
  const prefixedMatch = /^pikar:([^:]+):(.+)$/.exec(token);
  if (prefixedMatch) {
    if (prefixedMatch[1] !== platform) {
      return null;
    }
    token = prefixedMatch[2];
  }

  const payload = await decodeOAuthStateToken(token, env);
  if (!payload || payload.provider !== platform) {
    return null;
  }

  return payload;
}

async function buildSaveUserConfigResponse(request: Request, env: Env) {
  const userId = await requireAuthenticatedUserId(request, env);

  let payload: Record<string, unknown>;
  try {
    payload = asRecord(await request.json()) ?? {};
  } catch {
    return {
      success: false,
      message: "Request body must be valid JSON",
    };
  }

  const key = normalizeOptionalText(payload.key);
  const rawValue = payload.value;
  if (!key) {
    return {
      success: false,
      message: "Configuration key is required",
    };
  }
  if (typeof rawValue !== "string") {
    return {
      success: false,
      message: "Configuration value must be a string",
    };
  }
  if (!CONFIGURATION_MUTABLE_KEYS.has(key)) {
    return {
      success: false,
      message: `Configuration key '${key}' is not allowed`,
    };
  }

  try {
    const isSensitive = SENSITIVE_CONFIGURATION_KEYS.has(key);
    const storedValue = isSensitive ? await encryptFernetSecret(rawValue, env) : rawValue;

    await upsertSupabaseAdminMergeRow<Array<Record<string, unknown>>>(
      env,
      "/rest/v1/user_configurations?on_conflict=user_id,config_key&select=id",
      {
        user_id: userId,
        config_key: key,
        config_value: storedValue,
        is_sensitive: isSensitive,
        updated_at: new Date().toISOString(),
      },
    );

    return {
      success: true,
      message: `Configuration '${key}' saved successfully`,
    };
  } catch (error) {
    return {
      success: false,
      message: `Failed to save configuration: ${error instanceof Error ? error.message : "unknown error"}`,
    };
  }
}

async function buildConnectSocialResponse(request: Request, env: Env) {
  const userId = await requireAuthenticatedUserId(request, env);

  let payload: Record<string, unknown>;
  try {
    payload = asRecord(await request.json()) ?? {};
  } catch {
    return { error: "Request body must be valid JSON" };
  }

  const platform = normalizeOptionalText(payload.platform);
  const redirectUri = normalizeOptionalText(payload.redirect_uri);
  if (!platform || !redirectUri) {
    return { error: "platform and redirect_uri are required" };
  }

  const config = getSocialOAuthProviderConfig(platform);
  if (!config) {
    return { error: `Unsupported platform: ${platform}` };
  }

  if (!isAllowedConfigurationRedirectUri(redirectUri, env)) {
    return { error: "Invalid redirect URI" };
  }

  const clientId = env[config.client_id_env]?.trim() || "";
  if (!clientId) {
    return { error: `Missing ${config.client_id_env} in environment` };
  }

  try {
    const { verifier, challenge } = await buildPkcePair();
    const state = await encodeConfigurationSocialState(
      {
        user_id: userId,
        provider: platform,
        nonce: crypto.randomUUID(),
        exp: Math.floor(Date.now() / 1000) + 600,
        verifier,
        redirect_uri: redirectUri,
      },
      platform,
      env,
    );

    const authUrl = new URL(config.auth_url);
    authUrl.searchParams.set("client_id", clientId);
    authUrl.searchParams.set("redirect_uri", redirectUri);
    authUrl.searchParams.set("response_type", "code");
    authUrl.searchParams.set("scope", config.scopes.join(" "));
    authUrl.searchParams.set("state", state);
    authUrl.searchParams.set("code_challenge", challenge);
    authUrl.searchParams.set("code_challenge_method", "S256");

    return {
      authorization_url: authUrl.toString(),
      state,
    };
  } catch (error) {
    return {
      error: error instanceof Error ? error.message : "Failed to build authorization URL",
    };
  }
}

async function buildDisconnectSocialResponse(request: Request, env: Env) {
  const userId = await requireAuthenticatedUserId(request, env);

  let payload: Record<string, unknown>;
  try {
    payload = asRecord(await request.json()) ?? {};
  } catch {
    return { success: false, message: "Request body must be valid JSON" };
  }

  const platform = normalizeOptionalText(payload.platform);
  if (!platform) {
    return { success: false, message: "platform is required" };
  }

  try {
    await updateSupabaseAdminRows<Array<Record<string, unknown>>>(
      env,
      `/rest/v1/connected_accounts?user_id=eq.${encodeURIComponent(userId)}&platform=eq.${encodeURIComponent(platform)}`,
      {
        status: "revoked",
      },
    );

    return {
      success: true,
      message: `Disconnected ${platform}`,
    };
  } catch (error) {
    return {
      success: false,
      message: `Failed to disconnect: ${error instanceof Error ? error.message : "unknown error"}`,
    };
  }
}

async function buildConfigurationOAuthCallbackResponse(
  request: Request,
  env: Env,
  platform: string,
  url: URL,
) {
  const config = getSocialOAuthProviderConfig(platform);
  if (!config) {
    return { success: false, error: `Unsupported platform: ${platform}` };
  }

  const code = normalizeOptionalText(url.searchParams.get("code"));
  const state = normalizeOptionalText(url.searchParams.get("state"));
  if (!code || !state) {
    return { success: false, error: "Missing code or state" };
  }

  const oauthState = await decodeConfigurationSocialState(state, platform, env);
  if (!oauthState?.user_id || !oauthState.verifier || !oauthState.redirect_uri) {
    return { success: false, error: "Invalid or expired state parameter" };
  }

  if (!isAllowedConfigurationRedirectUri(oauthState.redirect_uri, env)) {
    return { success: false, error: "Invalid redirect URI" };
  }

  const clientId = env[config.client_id_env]?.trim() || "";
  const clientSecret = env[config.client_secret_env]?.trim() || "";
  if (!clientId || !clientSecret) {
    return { success: false, error: `Missing ${config.client_id_env} or ${config.client_secret_env}` };
  }

  let tokenResponse: Response;
  try {
    tokenResponse = await fetch(config.token_url, {
      method: "POST",
      headers: {
        "content-type": "application/x-www-form-urlencoded",
      },
      body: new URLSearchParams({
        grant_type: "authorization_code",
        code,
        redirect_uri: oauthState.redirect_uri,
        client_id: clientId,
        client_secret: clientSecret,
        code_verifier: oauthState.verifier,
      }),
    });
  } catch {
    return { success: false, error: "Connection error during token exchange" };
  }

  let tokenData: Record<string, unknown> = {};
  let errorBody = "";
  try {
    tokenData = asRecord(await tokenResponse.json()) ?? {};
  } catch {
    try {
      errorBody = (await tokenResponse.text()).slice(0, 300);
    } catch {
      errorBody = "";
    }
  }

  if (!tokenResponse.ok) {
    return {
      success: false,
      error: errorBody ? `Token exchange failed: ${errorBody}` : "Token exchange failed",
    };
  }

  const accessToken = normalizeOptionalText(tokenData.access_token);
  if (!accessToken) {
    return { success: false, error: "Provider did not return an access token" };
  }

  const refreshToken = normalizeOptionalText(tokenData.refresh_token);
  const expiresInRaw = tokenData.expires_in;
  const expiresIn =
    typeof expiresInRaw === "number"
      ? expiresInRaw
      : typeof expiresInRaw === "string"
        ? Number(expiresInRaw)
        : Number.NaN;
  const expiresAt =
    Number.isFinite(expiresIn) && expiresIn > 0
      ? new Date(Date.now() + expiresIn * 1000).toISOString()
      : null;

  try {
    await upsertSupabaseAdminMergeRow<Array<Record<string, unknown>>>(
      env,
      "/rest/v1/connected_accounts?on_conflict=user_id,platform&select=id",
      {
        user_id: oauthState.user_id,
        platform,
        access_token: accessToken,
        refresh_token: refreshToken,
        token_expires_at: expiresAt,
        scopes: config.scopes,
        status: "active",
      },
    );

    return {
      success: true,
      platform,
      message: `Successfully connected ${platform} account`,
    };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : "Failed to store connection",
    };
  }
}

function getDataIoTableDefinition(request: Request, env: Env, tableName: string): DataIoTableDefinition {
  const definition = DATA_IO_TABLES[tableName];
  if (!definition) {
    throw buildErrorResponse(request, env, 400, {
      detail: `Unknown table: ${tableName}`,
    });
  }

  return definition;
}

function normalizeDataIoOnDuplicate(
  value: unknown,
  request: Request,
  env: Env,
): "skip" | "update" {
  const normalized = typeof value === "string" ? value.trim().toLowerCase() : "skip";
  if (normalized === "skip" || normalized === "update") {
    return normalized;
  }

  throw buildErrorResponse(request, env, 400, {
    detail: "on_duplicate must be either 'skip' or 'update'.",
  });
}

function normalizeDataIoHeader(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

function parseDataIoCsv(csvBytes: Uint8Array, request: Request, env: Env): ParsedDataIoCsv {
  if (csvBytes.byteLength > DATA_IO_MAX_FILE_SIZE_BYTES) {
    throw buildErrorResponse(request, env, 413, {
      detail: `File size exceeds 50 MB limit (${csvBytes.byteLength} bytes)`,
    });
  }

  const text = new TextDecoder().decode(csvBytes).replace(/^\uFEFF/, "");
  if (!text.trim()) {
    throw buildErrorResponse(request, env, 400, {
      detail: "CSV file is empty.",
    });
  }

  const parsedRows: string[][] = [];
  let row: string[] = [];
  let field = "";
  let inQuotes = false;

  for (let index = 0; index < text.length; index += 1) {
    const character = text[index];
    if (inQuotes) {
      if (character === "\"") {
        if (text[index + 1] === "\"") {
          field += "\"";
          index += 1;
        } else {
          inQuotes = false;
        }
      } else {
        field += character;
      }
      continue;
    }

    if (character === "\"") {
      inQuotes = true;
      continue;
    }

    if (character === ",") {
      row.push(field);
      field = "";
      continue;
    }

    if (character === "\r" || character === "\n") {
      if (character === "\r" && text[index + 1] === "\n") {
        index += 1;
      }
      row.push(field);
      parsedRows.push(row);
      row = [];
      field = "";
      continue;
    }

    field += character;
  }

  if (inQuotes) {
    throw buildErrorResponse(request, env, 400, {
      detail: "CSV parsing failed: unmatched quote found in the file.",
    });
  }

  if (field.length > 0 || row.length > 0) {
    row.push(field);
    parsedRows.push(row);
  }

  const nonEmptyRows = parsedRows.filter((candidate, index) => index === 0 || candidate.some((cell) => cell.trim()));
  if (nonEmptyRows.length === 0) {
    throw buildErrorResponse(request, env, 400, {
      detail: "CSV file is empty.",
    });
  }

  const headers = nonEmptyRows[0].map((header) => header.trim());
  if (headers.length === 0 || headers.some((header) => !header)) {
    throw buildErrorResponse(request, env, 400, {
      detail: "CSV header row must contain non-empty column names.",
    });
  }

  const rows = nonEmptyRows.slice(1).map((candidate) =>
    headers.map((_, columnIndex) => (candidate[columnIndex] ?? "").trim()),
  );

  return {
    headers,
    rows,
    rowCount: rows.length,
  };
}

function normalizeDataIoColumnMapping(
  value: unknown,
  request: Request,
  env: Env,
  tableName: string,
): Record<string, string> {
  const definition = getDataIoTableDefinition(request, env, tableName);
  const mappingRecord = asRecord(value);
  if (!mappingRecord) {
    throw buildErrorResponse(request, env, 400, {
      detail: "column_mapping must be an object.",
    });
  }

  const validColumns = new Set(Object.keys(definition.columns));
  const mapping: Record<string, string> = {};
  for (const [csvColumn, targetColumn] of Object.entries(mappingRecord)) {
    if (typeof targetColumn !== "string" || !targetColumn.trim()) {
      throw buildErrorResponse(request, env, 400, {
        detail: "column_mapping values must be non-empty strings.",
      });
    }

    const normalizedTarget = targetColumn.trim();
    if (!validColumns.has(normalizedTarget)) {
      throw buildErrorResponse(request, env, 400, {
        detail: `Unknown target column '${normalizedTarget}' for table '${tableName}'.`,
      });
    }

    mapping[csvColumn] = normalizedTarget;
  }

  return mapping;
}

function buildDataIoPreview(
  document: ParsedDataIoCsv,
  columnMapping: Record<string, string>,
  limit = 10,
): Array<Record<string, unknown>> {
  const headerIndex = new Map(document.headers.map((header, index) => [header, index]));
  return document.rows.slice(0, limit).map((row) => {
    const previewRow: Record<string, unknown> = {};
    for (const [csvColumn, targetColumn] of Object.entries(columnMapping)) {
      const columnIndex = headerIndex.get(csvColumn);
      if (columnIndex === undefined) {
        continue;
      }
      previewRow[targetColumn] = row[columnIndex] || null;
    }
    return previewRow;
  });
}

function validateDataIoDocument(
  document: ParsedDataIoCsv,
  columnMapping: Record<string, string>,
  tableName: string,
  request: Request,
  env: Env,
): DataIoValidationError[] {
  const definition = getDataIoTableDefinition(request, env, tableName);
  const reverseMapping = new Map<string, string>();
  for (const [csvColumn, targetColumn] of Object.entries(columnMapping)) {
    reverseMapping.set(targetColumn, csvColumn);
  }

  const headerIndex = new Map(document.headers.map((header, index) => [header, index]));
  const errors: DataIoValidationError[] = [];

  for (let rowIndex = 0; rowIndex < document.rows.length; rowIndex += 1) {
    const row = document.rows[rowIndex];

    for (const requiredColumn of definition.required) {
      const csvColumn = reverseMapping.get(requiredColumn);
      if (!csvColumn) {
        errors.push({
          row: rowIndex + 1,
          column: requiredColumn,
          value: null,
          reason: `Required column '${requiredColumn}' is not mapped from CSV`,
        });
        continue;
      }

      const columnIndex = headerIndex.get(csvColumn);
      const rawValue = columnIndex === undefined ? "" : row[columnIndex] ?? "";
      if (!rawValue.trim()) {
        errors.push({
          row: rowIndex + 1,
          column: requiredColumn,
          value: rawValue || null,
          reason: `Required field '${requiredColumn}' is empty`,
        });
      }
    }

    for (const [csvColumn, targetColumn] of Object.entries(columnMapping)) {
      const columnIndex = headerIndex.get(csvColumn);
      if (columnIndex === undefined) {
        continue;
      }

      const rawValue = row[columnIndex] ?? "";
      if (!rawValue.trim()) {
        continue;
      }

      const columnDefinition = definition.columns[targetColumn];
      if (!columnDefinition) {
        continue;
      }

      if (columnDefinition.type === "enum") {
        const normalizedValue = rawValue.trim().toLowerCase();
        const validValues = (columnDefinition.values ?? []).map((item) => item.toLowerCase());
        if (!validValues.includes(normalizedValue)) {
          errors.push({
            row: rowIndex + 1,
            column: targetColumn,
            value: rawValue,
            reason: `Invalid value '${rawValue}' for '${targetColumn}'. Valid options: ${(columnDefinition.values ?? []).join(", ")}`,
          });
        }
        continue;
      }

      if (columnDefinition.type === "numeric") {
        const parsed = Number(rawValue);
        if (!Number.isFinite(parsed)) {
          errors.push({
            row: rowIndex + 1,
            column: targetColumn,
            value: rawValue,
            reason: `Expected numeric value for '${targetColumn}', got '${rawValue}'`,
          });
          continue;
        }

        if (typeof columnDefinition.min === "number" && parsed < columnDefinition.min) {
          errors.push({
            row: rowIndex + 1,
            column: targetColumn,
            value: rawValue,
            reason: `Value ${parsed} below minimum ${columnDefinition.min}`,
          });
        }
        continue;
      }

      if (columnDefinition.type === "integer") {
        const parsed = Number(rawValue);
        if (!Number.isInteger(parsed)) {
          errors.push({
            row: rowIndex + 1,
            column: targetColumn,
            value: rawValue,
            reason: `Expected integer value for '${targetColumn}', got '${rawValue}'`,
          });
          continue;
        }

        if (typeof columnDefinition.min === "number" && parsed < columnDefinition.min) {
          errors.push({
            row: rowIndex + 1,
            column: targetColumn,
            value: rawValue,
            reason: `Value ${parsed} below minimum ${columnDefinition.min}`,
          });
        }
        if (typeof columnDefinition.max === "number" && parsed > columnDefinition.max) {
          errors.push({
            row: rowIndex + 1,
            column: targetColumn,
            value: rawValue,
            reason: `Value ${parsed} above maximum ${columnDefinition.max}`,
          });
        }
        continue;
      }

      if (columnDefinition.type === "date" && Number.isNaN(Date.parse(rawValue))) {
        errors.push({
          row: rowIndex + 1,
          column: targetColumn,
          value: rawValue,
          reason: `Expected date value for '${targetColumn}', got '${rawValue}'`,
        });
      }
    }
  }

  return errors;
}

function coerceDataIoCellValue(value: string, definition: DataIoColumnDefinition): unknown {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }

  if (definition.type === "numeric" || definition.type === "integer") {
    return Number(trimmed);
  }

  if (definition.type === "enum") {
    return trimmed.toLowerCase();
  }

  return trimmed;
}

async function fetchDataIoSavedMapping(
  env: Env,
  userId: string,
  tableName: string,
): Promise<Record<string, string> | null> {
  const context = getSupabaseAdminContext(env);
  const params = new URLSearchParams({
    select: "mapping",
    user_id: `eq.${userId}`,
    table_name: `eq.${tableName}`,
    limit: "1",
  });

  const response = await fetch(`${context.supabaseUrl}/rest/v1/csv_column_mappings?${params.toString()}`, {
    method: "GET",
    headers: context.headers,
  });

  if (response.status === 404 || response.status === 400) {
    return null;
  }

  if (!response.ok) {
    throw new Error(`Supabase admin request failed with ${response.status}.`);
  }

  const rows = (await response.json()) as Array<{ mapping?: Record<string, string> | null }>;
  const mapping = asRecord(rows[0]?.mapping ?? null);
  if (!mapping) {
    return null;
  }

  const result: Record<string, string> = {};
  for (const [csvColumn, targetColumn] of Object.entries(mapping)) {
    if (typeof targetColumn === "string" && targetColumn.trim()) {
      result[csvColumn] = targetColumn.trim();
    }
  }

  return Object.keys(result).length > 0 ? result : null;
}

async function persistDataIoMapping(
  env: Env,
  userId: string,
  tableName: string,
  mapping: Record<string, string>,
): Promise<void> {
  const context = getSupabaseAdminContext(env);
  const headers = new Headers(context.headers);
  headers.set("Prefer", "resolution=merge-duplicates,return=minimal");

  const response = await fetch(
    `${context.supabaseUrl}/rest/v1/csv_column_mappings?on_conflict=user_id,table_name`,
    {
      method: "POST",
      headers,
      body: JSON.stringify({
        user_id: userId,
        table_name: tableName,
        mapping,
      }),
    },
  );

  if (!response.ok && response.status !== 404 && response.status !== 400) {
    throw new Error(`Supabase admin upsert failed with ${response.status}.`);
  }
}

function buildDataIoSuggestedMapping(
  headers: string[],
  tableName: string,
  savedMapping: Record<string, string> | null,
): Record<string, string> {
  const targetColumns = Object.keys(DATA_IO_TABLES[tableName]?.columns ?? {});
  const normalizedTargets = new Map(targetColumns.map((column) => [normalizeDataIoHeader(column), column]));

  if (savedMapping) {
    const savedColumns = new Set(Object.keys(savedMapping));
    if (headers.every((header) => savedColumns.has(header))) {
      return headers.reduce<Record<string, string>>((accumulator, header) => {
        const targetColumn = savedMapping[header];
        if (targetColumn && targetColumns.includes(targetColumn)) {
          accumulator[header] = targetColumn;
        }
        return accumulator;
      }, {});
    }
  }

  return headers.reduce<Record<string, string>>((accumulator, header) => {
    const targetColumn = normalizedTargets.get(normalizeDataIoHeader(header));
    if (targetColumn) {
      accumulator[header] = targetColumn;
    }
    return accumulator;
  }, {});
}

function getDataIoStoragePath(userId: string): string {
  const timestamp = new Date().toISOString().replace(/[-:.]/g, "").replace(/\d{3}Z$/, "Z");
  return `${userId}/data-io-staging/${timestamp}_${randomBase64Url(8)}.csv`;
}

async function fetchDataIoStagedCsv(
  env: Env,
  userId: string,
  csvDataKey: string,
  request: Request,
): Promise<Uint8Array> {
  const normalizedKey = csvDataKey.replace(/^\/+/, "");
  if (!normalizedKey.startsWith(`${userId}/data-io-staging/`) || normalizedKey.includes("..")) {
    throw buildErrorResponse(request, env, 400, {
      detail: "csv_data_key is invalid.",
    });
  }

  const context = getSupabaseAdminContext(env);
  const response = await fetch(
    `${context.supabaseUrl}/storage/v1/object/authenticated/${EXPORT_BUCKET_NAME}/${normalizedKey}`,
    {
      method: "GET",
      headers: {
        apikey: context.headers.apikey,
        Authorization: context.headers.Authorization,
      },
    },
  );

  if (response.status === 404) {
    throw buildErrorResponse(request, env, 410, {
      detail: "CSV data has expired. Please re-upload the file.",
    });
  }

  if (!response.ok) {
    throw new Error(`Supabase storage download failed with ${response.status}.`);
  }

  return new Uint8Array(await response.arrayBuffer());
}

function buildDataIoValidationSummary(errors: DataIoValidationError[], rowCount: number) {
  const errorRows = new Set(errors.map((error) => error.row));
  return {
    valid: errors.length === 0,
    errors,
    valid_count: rowCount - errorRows.size,
    error_count: errorRows.size,
  };
}

async function buildDataIoTablesResponse(request: Request, env: Env) {
  await requireAuthenticatedUserId(request, env);
  return Object.entries(DATA_IO_TABLES).map(([name, definition]) => ({
    name,
    label: definition.label,
    columns: definition.columns,
    required: definition.required,
  }));
}

async function buildDataIoUploadResponse(request: Request, env: Env, url: URL) {
  const userId = await requireAuthenticatedUserId(request, env);
  const targetTable = requireTextField(
    { target_table: url.searchParams.get("target_table") },
    "target_table",
    request,
    env,
  );
  getDataIoTableDefinition(request, env, targetTable);

  const formData = await request.formData();
  const file = formData.get("file");
  if (!(file instanceof File)) {
    throw buildErrorResponse(request, env, 400, {
      detail: "file is required",
    });
  }

  if (!file.name.toLowerCase().endsWith(".csv")) {
    throw buildErrorResponse(request, env, 400, {
      detail: "Only CSV files are accepted",
    });
  }

  const csvBytes = new Uint8Array(await file.arrayBuffer());
  const document = parseDataIoCsv(csvBytes, request, env);
  const csvDataKey = getDataIoStoragePath(userId);
  await uploadSupabaseStorageObject(env, EXPORT_BUCKET_NAME, csvDataKey, csvBytes, DATA_IO_CSV_CONTENT_TYPE);

  const savedMapping = await fetchDataIoSavedMapping(env, userId, targetTable);
  const suggestedMappings = buildDataIoSuggestedMapping(document.headers, targetTable, savedMapping);

  return {
    csv_data_key: csvDataKey,
    column_headers: document.headers,
    row_count: document.rowCount,
    preview: buildDataIoPreview(document, suggestedMappings, 10),
    suggested_mappings: suggestedMappings,
  };
}

async function buildDataIoValidateResponse(request: Request, env: Env) {
  const userId = await requireAuthenticatedUserId(request, env);
  let payload: Record<string, unknown>;
  try {
    payload = (await request.json()) as Record<string, unknown>;
  } catch {
    throw buildErrorResponse(request, env, 400, {
      detail: "Request body must be valid JSON.",
    });
  }

  const targetTable = requireTextField(payload, "target_table", request, env);
  const csvDataKey = requireTextField(payload, "csv_data_key", request, env);
  const columnMapping = normalizeDataIoColumnMapping(payload.column_mapping, request, env, targetTable);
  const csvBytes = await fetchDataIoStagedCsv(env, userId, csvDataKey, request);
  const document = parseDataIoCsv(csvBytes, request, env);
  const errors = validateDataIoDocument(document, columnMapping, targetTable, request, env);
  return buildDataIoValidationSummary(errors, document.rowCount);
}

async function postDataIoRows(
  env: Env,
  tableName: string,
  rows: Array<Record<string, unknown>>,
  options: {
    upsert?: boolean;
    onConflict?: string;
  } = {},
): Promise<void> {
  const context = getSupabaseAdminContext(env);
  const headers = new Headers(context.headers);
  headers.set(
    "Prefer",
    options.upsert ? "resolution=merge-duplicates,return=minimal" : "return=minimal",
  );

  const targetUrl = new URL(`${context.supabaseUrl}/rest/v1/${tableName}`);
  if (options.onConflict) {
    targetUrl.searchParams.set("on_conflict", options.onConflict);
  }

  const response = await fetch(targetUrl.toString(), {
    method: "POST",
    headers,
    body: JSON.stringify(rows),
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail ? `Supabase admin insert failed with ${response.status}: ${detail}` : `Supabase admin insert failed with ${response.status}.`);
  }
}

async function commitDataIoDocument(
  env: Env,
  userId: string,
  document: ParsedDataIoCsv,
  columnMapping: Record<string, string>,
  tableName: string,
  onDuplicate: "skip" | "update",
  request: Request,
  progressCallback?: (percent: number) => void,
) {
  const definition = getDataIoTableDefinition(request, env, tableName);
  const headerIndex = new Map(document.headers.map((header, index) => [header, index]));

  const allRows = document.rows.map((row) => {
    const rowPayload: Record<string, unknown> = { user_id: userId };
    for (const [csvColumn, targetColumn] of Object.entries(columnMapping)) {
      const columnIndex = headerIndex.get(csvColumn);
      if (columnIndex === undefined) {
        continue;
      }
      rowPayload[targetColumn] = coerceDataIoCellValue(row[columnIndex] ?? "", definition.columns[targetColumn]);
    }
    return rowPayload;
  });

  let imported = 0;
  let skipped = 0;
  const errors: DataIoValidationError[] = [];

  for (let batchStart = 0; batchStart < allRows.length; batchStart += DATA_IO_COMMIT_BATCH_SIZE) {
    const batchEnd = Math.min(batchStart + DATA_IO_COMMIT_BATCH_SIZE, allRows.length);
    const batch = allRows.slice(batchStart, batchEnd);

    try {
      if (onDuplicate === "update" && tableName === "contacts") {
        await postDataIoRows(env, tableName, batch, { upsert: true, onConflict: "user_id,email" });
      } else {
        await postDataIoRows(env, tableName, batch);
      }
      imported += batch.length;
    } catch (error) {
      if (onDuplicate === "skip") {
        for (const rowPayload of batch) {
          try {
            await postDataIoRows(env, tableName, [rowPayload]);
            imported += 1;
          } catch {
            skipped += 1;
          }
        }
      } else {
        skipped += batch.length;
        errors.push({
          row: batchStart + 1,
          column: "",
          value: "",
          reason: `Batch insert failed: ${error instanceof Error ? error.message : "Unknown error"}`,
        });
      }
    }

    if (progressCallback && allRows.length > 0) {
      progressCallback(Math.min(100, (batchEnd / allRows.length) * 100));
    }
  }

  return {
    imported_count: imported,
    skipped_count: skipped,
    errors,
  };
}

async function parseDataIoCommitRequest(request: Request, env: Env) {
  const userId = await requireAuthenticatedUserId(request, env);
  let payload: Record<string, unknown>;
  try {
    payload = (await request.json()) as Record<string, unknown>;
  } catch {
    throw buildErrorResponse(request, env, 400, {
      detail: "Request body must be valid JSON.",
    });
  }

  const targetTable = requireTextField(payload, "target_table", request, env);
  const csvDataKey = requireTextField(payload, "csv_data_key", request, env);
  const columnMapping = normalizeDataIoColumnMapping(payload.column_mapping, request, env, targetTable);
  const onDuplicate = normalizeDataIoOnDuplicate(payload.on_duplicate, request, env);
  const csvBytes = await fetchDataIoStagedCsv(env, userId, csvDataKey, request);
  const document = parseDataIoCsv(csvBytes, request, env);

  return {
    userId,
    targetTable,
    columnMapping,
    onDuplicate,
    document,
  };
}

function buildDataIoSseResponse(
  request: Request,
  env: Env,
  executor: (notifyProgress: (percent: number) => void) => Promise<{
    imported_count: number;
    skipped_count: number;
    errors: DataIoValidationError[];
  }>,
): Response {
  const encoder = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      const send = (event: string, payload: unknown) => {
        controller.enqueue(encoder.encode(`event: ${event}\ndata: ${JSON.stringify(payload)}\n\n`));
      };

      try {
        send("start", { status: "processing" });
        const result = await executor((percent) => send("progress", { progress: percent }));
        send("complete", result);
      } catch (error) {
        send("error", {
          detail: error instanceof Error ? error.message : "The import could not be completed.",
        });
      } finally {
        controller.close();
      }
    },
  });

  const headers = buildCorsHeaders(request, env);
  headers.set("Content-Type", "text/event-stream");
  headers.set("Cache-Control", "no-cache");
  headers.set("Connection", "keep-alive");
  headers.set("x-pikar-public-route", "native");
  return new Response(stream, { headers });
}

async function buildDataIoCommitResponse(request: Request, env: Env): Promise<Response> {
  const parsed = await parseDataIoCommitRequest(request, env);
  const executor = async (notifyProgress?: (percent: number) => void) => {
    const result = await commitDataIoDocument(
      env,
      parsed.userId,
      parsed.document,
      parsed.columnMapping,
      parsed.targetTable,
      parsed.onDuplicate,
      request,
      notifyProgress,
    );
    if (result.imported_count > 0) {
      await persistDataIoMapping(env, parsed.userId, parsed.targetTable, parsed.columnMapping);
    }
    return result;
  };

  if (parsed.document.rowCount > DATA_IO_SSE_THRESHOLD_ROWS) {
    return buildDataIoSseResponse(request, env, (notifyProgress) => executor(notifyProgress));
  }

  return jsonWithCors(await executor(), request, env);
}

async function queryDataIoExportRows(
  env: Env,
  userId: string,
  tableName: string,
): Promise<Array<Record<string, unknown>>> {
  switch (tableName) {
    case "contacts":
    case "financial_records":
    case "initiatives":
    case "content_bundles":
    case "support_tickets":
    case "recruitment_candidates":
    case "compliance_risks":
    case "compliance_audits":
      return queryExportRows(env, tableName, {
        userValue: userId,
        orderBy: "created_at",
        desc: true,
      });
    default:
      throw new Error(`Unsupported export table '${tableName}'.`);
  }
}

function serializeDataIoCsv(records: Array<Record<string, unknown>>): Uint8Array {
  if (records.length === 0) {
    return new Uint8Array();
  }

  const columns: string[] = [];
  const seen = new Set<string>();
  for (const record of records) {
    for (const key of Object.keys(record)) {
      if (seen.has(key)) {
        continue;
      }
      seen.add(key);
      columns.push(key);
    }
  }

  const escape = (value: unknown) => {
    if (value === null || value === undefined) {
      return "";
    }

    const stringValue = typeof value === "object" ? JSON.stringify(value) : String(value);
    if (/[",\r\n]/.test(stringValue)) {
      return `"${stringValue.replace(/"/g, "\"\"")}"`;
    }
    return stringValue;
  };

  const lines = [
    columns.join(","),
    ...records.map((record) => columns.map((column) => escape(record[column])).join(",")),
  ];

  return new TextEncoder().encode(lines.join("\r\n"));
}

async function buildDataIoExportResponse(
  request: Request,
  env: Env,
  tableName: string,
) {
  const userId = await requireAuthenticatedUserId(request, env);
  const definition = getDataIoTableDefinition(request, env, tableName);
  const rows = await queryDataIoExportRows(env, userId, tableName);
  const csvBytes = serializeDataIoCsv(rows);
  const timestamp = new Date().toISOString().replace(/[-:.]/g, "").replace(/\d{3}Z$/, "Z");
  const filename = `${tableName}_${timestamp}.csv`;
  const storagePath = `${userId}/exports/${filename}`;

  await uploadSupabaseStorageObject(env, EXPORT_BUCKET_NAME, storagePath, csvBytes, DATA_IO_CSV_CONTENT_TYPE);
  const signedUrl = await createSupabaseStorageSignedUrl(
    env,
    EXPORT_BUCKET_NAME,
    storagePath,
    EXPORT_SIGNED_URL_EXPIRY_SECONDS,
  );

  return {
    url: signedUrl,
    filename,
    size_bytes: csvBytes.byteLength,
    label: definition.label,
  };
}

function normalizeEmailSequenceStatus(
  value: unknown,
  request: Request,
  env: Env,
): "draft" | "active" | "paused" | "completed" {
  const normalized = typeof value === "string" ? value.trim().toLowerCase() : "";
  if (normalized === "draft" || normalized === "active" || normalized === "paused" || normalized === "completed") {
    return normalized;
  }

  throw buildErrorResponse(request, env, 400, {
    detail: "status must be one of draft, active, paused, completed",
  });
}

function normalizeEmailSequenceStep(
  step: unknown,
  index: number,
  request: Request,
  env: Env,
) {
  const record = asRecord(step);
  if (!record) {
    throw buildErrorResponse(request, env, 400, {
      detail: `steps[${index}] must be an object`,
    });
  }

  const subjectTemplate = requireTextField(record, "subject_template", request, env);
  const bodyTemplate = requireTextField(record, "body_template", request, env);
  const delayHoursRaw = record.delay_hours;
  const delayHours =
    typeof delayHoursRaw === "number"
      ? delayHoursRaw
      : typeof delayHoursRaw === "string" && delayHoursRaw.trim()
        ? Number(delayHoursRaw)
        : 0;
  if (!Number.isInteger(delayHours) || delayHours < 0) {
    throw buildErrorResponse(request, env, 400, {
      detail: `steps[${index}].delay_hours must be a non-negative integer`,
    });
  }

  const delayType = typeof record.delay_type === "string" && record.delay_type.trim()
    ? record.delay_type.trim()
    : "after_previous";
  if (delayType !== "after_previous" && delayType !== "at_time") {
    throw buildErrorResponse(request, env, 400, {
      detail: `steps[${index}].delay_type must be either after_previous or at_time`,
    });
  }

  return {
    subject_template: subjectTemplate,
    body_template: bodyTemplate,
    delay_hours: delayHours,
    delay_type: delayType,
  };
}

function buildInFilter(values: string[]): string {
  return `in.(${values.map((value) => `"${value.replace(/"/g, "\\\"")}"`).join(",")})`;
}

async function fetchOwnedEmailSequence(
  env: Env,
  userId: string,
  sequenceId: string,
): Promise<Record<string, unknown> | null> {
  const rows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/email_sequences?id=eq.${encodeURIComponent(sequenceId)}&user_id=eq.${userId}&select=*&limit=1`,
  );
  return rows[0] ?? null;
}

async function fetchEmailSequenceSteps(
  env: Env,
  sequenceId: string,
): Promise<Array<Record<string, unknown>>> {
  return fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/email_sequence_steps?sequence_id=eq.${encodeURIComponent(sequenceId)}&select=*&order=step_number.asc`,
  );
}

async function fetchEmailSequenceEnrollments(
  env: Env,
  sequenceId: string,
): Promise<Array<Record<string, unknown>>> {
  return fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/email_sequence_enrollments?sequence_id=eq.${encodeURIComponent(sequenceId)}&select=*`,
  );
}

function buildEmailSequenceEnrollmentStats(enrollments: Array<Record<string, unknown>>) {
  return {
    active: enrollments.filter((enrollment) => enrollment.status === "active").length,
    completed: enrollments.filter((enrollment) => enrollment.status === "completed").length,
    total: enrollments.length,
  };
}

async function buildEmailSequenceDetailResponse(
  request: Request,
  env: Env,
  sequenceId: string,
) {
  const userId = await requireAuthenticatedUserId(request, env);
  const sequence = await fetchOwnedEmailSequence(env, userId, sequenceId);
  if (!sequence) {
    throw buildErrorResponse(request, env, 404, {
      detail: "Sequence not found",
    });
  }

  const [steps, enrollments] = await Promise.all([
    fetchEmailSequenceSteps(env, sequenceId),
    fetchEmailSequenceEnrollments(env, sequenceId),
  ]);

  return {
    ...sequence,
    steps,
    enrollment_stats: buildEmailSequenceEnrollmentStats(enrollments),
  };
}

async function buildEmailSequencesListResponse(request: Request, env: Env) {
  const userId = await requireAuthenticatedUserId(request, env);
  const sequences = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/email_sequences?user_id=eq.${userId}&select=*&order=created_at.desc`,
  );
  if (sequences.length === 0) {
    return [];
  }

  const sequenceIds = sequences
    .map((sequence) => (typeof sequence.id === "string" ? sequence.id : null))
    .filter((value): value is string => Boolean(value));

  const enrollments = sequenceIds.length > 0
    ? await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
        env,
        `/rest/v1/email_sequence_enrollments?sequence_id=${encodeURIComponent(buildInFilter(sequenceIds))}&select=sequence_id`,
      )
    : [];

  const counts = enrollments.reduce<Record<string, number>>((accumulator, enrollment) => {
    const sequenceId = typeof enrollment.sequence_id === "string" ? enrollment.sequence_id : "";
    if (!sequenceId) {
      return accumulator;
    }
    accumulator[sequenceId] = (accumulator[sequenceId] ?? 0) + 1;
    return accumulator;
  }, {});

  return sequences.map((sequence) => ({
    ...sequence,
    enrollment_count:
      typeof sequence.id === "string" ? counts[sequence.id] ?? 0 : 0,
  }));
}

async function buildEmailSequenceCreateResponse(request: Request, env: Env) {
  const userId = await requireAuthenticatedUserId(request, env);
  let payload: Record<string, unknown>;
  try {
    payload = (await request.json()) as Record<string, unknown>;
  } catch {
    throw buildErrorResponse(request, env, 400, {
      detail: "Request body must be valid JSON.",
    });
  }

  const name = requireTextField(payload, "name", request, env);
  const rawSteps = payload.steps;
  if (!Array.isArray(rawSteps)) {
    throw buildErrorResponse(request, env, 400, {
      detail: "steps must be an array",
    });
  }

  const steps = rawSteps.map((step, index) => normalizeEmailSequenceStep(step, index, request, env));
  const sequenceRows = await insertSupabaseAdminRow<Array<Record<string, unknown>>>(
    env,
    "/rest/v1/email_sequences?select=*",
    {
      user_id: userId,
      name,
      status: "draft",
      ...(normalizeOptionalText(payload.campaign_id) ? { campaign_id: normalizeOptionalText(payload.campaign_id) } : {}),
    },
  );
  const sequence = sequenceRows[0];
  const sequenceId = typeof sequence?.id === "string" ? sequence.id : "";
  if (!sequenceId) {
    throw new Error("Email sequence creation returned no id.");
  }

  let createdSteps: Array<Record<string, unknown>> = [];
  if (steps.length > 0) {
    createdSteps = await postSupabaseAdminPayload<Array<Record<string, unknown>>>(
      env,
      "/rest/v1/email_sequence_steps?select=*",
      steps.map((step, index) => ({
        sequence_id: sequenceId,
        step_number: index,
        ...step,
      })),
    );
  }

  return {
    ...sequence,
    steps: createdSteps,
  };
}

async function buildEmailSequenceStatusUpdateResponse(
  request: Request,
  env: Env,
  sequenceId: string,
) {
  const userId = await requireAuthenticatedUserId(request, env);
  let payload: Record<string, unknown>;
  try {
    payload = (await request.json()) as Record<string, unknown>;
  } catch {
    throw buildErrorResponse(request, env, 400, {
      detail: "Request body must be valid JSON.",
    });
  }

  const targetStatus = normalizeEmailSequenceStatus(payload.status, request, env);
  const sequence = await fetchOwnedEmailSequence(env, userId, sequenceId);
  if (!sequence) {
    throw buildErrorResponse(request, env, 404, {
      detail: "Sequence not found",
    });
  }

  const currentStatus = typeof sequence.status === "string" ? sequence.status : "draft";
  const allowed = EMAIL_SEQUENCE_VALID_STATUS_TRANSITIONS[currentStatus] ?? [];
  if (!allowed.includes(targetStatus)) {
    throw buildErrorResponse(request, env, 400, {
      detail: `Cannot transition from '${currentStatus}' to '${targetStatus}'. Allowed: ${allowed.join(", ")}`,
    });
  }

  const rows = await updateSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/email_sequences?id=eq.${encodeURIComponent(sequenceId)}&user_id=eq.${userId}&select=*`,
    {
      status: targetStatus,
      updated_at: new Date().toISOString(),
    },
  );

  return rows[0] ?? sequence;
}

async function buildEmailSequenceDeleteResponse(
  request: Request,
  env: Env,
  sequenceId: string,
) {
  const userId = await requireAuthenticatedUserId(request, env);
  const rows = await deleteSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/email_sequences?id=eq.${encodeURIComponent(sequenceId)}&user_id=eq.${userId}&select=id`,
  );
  if (!rows.length) {
    throw buildErrorResponse(request, env, 404, {
      detail: "Sequence not found",
    });
  }

  return {
    status: "deleted",
  };
}

async function buildEmailSequenceEnrollResponse(
  request: Request,
  env: Env,
  sequenceId: string,
) {
  const userId = await requireAuthenticatedUserId(request, env);
  let payload: Record<string, unknown>;
  try {
    payload = (await request.json()) as Record<string, unknown>;
  } catch {
    throw buildErrorResponse(request, env, 400, {
      detail: "Request body must be valid JSON.",
    });
  }

  const contactIds = normalizeStringArrayField(payload, "contact_ids", request, env);
  const timezone = normalizeOptionalText(payload.timezone) ?? "UTC";
  const sequence = await fetchOwnedEmailSequence(env, userId, sequenceId);
  if (!sequence) {
    throw buildErrorResponse(request, env, 404, {
      detail: "Sequence not found",
    });
  }
  if (sequence.status !== "active") {
    throw buildErrorResponse(request, env, 400, {
      detail: `Sequence ${sequenceId} is not active`,
    });
  }

  const [stepRows, existingEnrollments, contactRows] = await Promise.all([
    fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
      env,
      `/rest/v1/email_sequence_steps?sequence_id=eq.${encodeURIComponent(sequenceId)}&step_number=eq.0&select=delay_hours&limit=1`,
    ),
    fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
      env,
      `/rest/v1/email_sequence_enrollments?sequence_id=eq.${encodeURIComponent(sequenceId)}&contact_id=${encodeURIComponent(buildInFilter(contactIds))}&select=contact_id,status`,
    ),
    fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
      env,
      `/rest/v1/contacts?id=${encodeURIComponent(buildInFilter(contactIds))}&user_id=eq.${userId}&select=id,metadata`,
    ),
  ]);

  const delayHours = typeof stepRows[0]?.delay_hours === "number"
    ? stepRows[0].delay_hours
    : typeof stepRows[0]?.delay_hours === "string"
      ? Number(stepRows[0].delay_hours)
      : 0;
  const nextSendAt = new Date(Date.now() + Math.max(0, delayHours) * 60 * 60 * 1000).toISOString();

  const existingStatuses = new Map(
    existingEnrollments
      .map((row) => [typeof row.contact_id === "string" ? row.contact_id : "", typeof row.status === "string" ? row.status : ""])
      .filter(([contactId]) => Boolean(contactId)),
  );
  const contactMetadata = new Map(
    contactRows
      .map((row) => [typeof row.id === "string" ? row.id : "", asRecord(row.metadata) ?? {}])
      .filter(([contactId]) => Boolean(contactId)),
  );

  const records: Array<Record<string, unknown>> = [];
  let skipped = 0;
  for (const contactId of contactIds) {
    const metadata = contactMetadata.get(contactId);
    if (!metadata) {
      skipped += 1;
      continue;
    }
    if (metadata.unsubscribed === true) {
      skipped += 1;
      continue;
    }

    const existingStatus = existingStatuses.get(contactId);
    if (existingStatus === "active" || existingStatus === "completed") {
      skipped += 1;
      continue;
    }

    records.push({
      sequence_id: sequenceId,
      contact_id: contactId,
      current_step: 0,
      status: "active",
      next_send_at: nextSendAt,
      timezone,
    });
  }

  if (records.length > 0) {
    await postSupabaseAdminPayload<null>(
      env,
      "/rest/v1/email_sequence_enrollments",
      records,
      "return=minimal",
    );
  }

  return {
    enrolled: records.length,
    skipped: skipped + (contactIds.length - records.length - skipped),
  };
}

async function buildEmailSequenceUnenrollResponse(
  request: Request,
  env: Env,
  enrollmentId: string,
) {
  const userId = await requireAuthenticatedUserId(request, env);
  const enrollmentRows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/email_sequence_enrollments?id=eq.${encodeURIComponent(enrollmentId)}&select=id,sequence_id,status&limit=1`,
  );
  const enrollment = enrollmentRows[0];
  if (!enrollment || typeof enrollment.sequence_id !== "string") {
    throw buildErrorResponse(request, env, 404, {
      detail: `Enrollment ${enrollmentId} not found`,
    });
  }

  const sequence = await fetchOwnedEmailSequence(env, userId, enrollment.sequence_id);
  if (!sequence) {
    throw buildErrorResponse(request, env, 404, {
      detail: `Enrollment ${enrollmentId} not found`,
    });
  }

  const rows = await updateSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/email_sequence_enrollments?id=eq.${encodeURIComponent(enrollmentId)}&select=*`,
    {
      status: "paused",
    },
  );
  if (!rows.length) {
    throw buildErrorResponse(request, env, 404, {
      detail: `Enrollment ${enrollmentId} not found`,
    });
  }

  return rows[0];
}

async function buildEmailSequencePerformanceResponse(
  request: Request,
  env: Env,
  sequenceId: string,
) {
  const userId = await requireAuthenticatedUserId(request, env);
  const sequence = await fetchOwnedEmailSequence(env, userId, sequenceId);
  if (!sequence) {
    throw buildErrorResponse(request, env, 404, {
      detail: `Sequence ${sequenceId} not found`,
    });
  }

  const enrollments = await fetchEmailSequenceEnrollments(env, sequenceId);
  const totalEnrollments = enrollments.length;
  if (totalEnrollments === 0) {
    return {
      total_enrollments: 0,
      open_rate: 0.0,
      click_rate: 0.0,
      bounce_rate: 0.0,
      completion_rate: 0.0,
    };
  }

  const enrollmentIds = enrollments
    .map((enrollment) => (typeof enrollment.id === "string" ? enrollment.id : null))
    .filter((value): value is string => Boolean(value));
  const completed = enrollments.filter((enrollment) => enrollment.status === "completed").length;
  const events = enrollmentIds.length > 0
    ? await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
        env,
        `/rest/v1/email_tracking_events?enrollment_id=${encodeURIComponent(buildInFilter(enrollmentIds))}&select=event_type,enrollment_id`,
      )
    : [];

  const opens = new Set<string>();
  const clicks = new Set<string>();
  const bounces = new Set<string>();
  const delivered = new Set<string>();

  for (const event of events) {
    const enrollmentId = typeof event.enrollment_id === "string" ? event.enrollment_id : "";
    const eventType = typeof event.event_type === "string" ? event.event_type : "";
    if (!enrollmentId || !eventType) {
      continue;
    }

    if (eventType === "open") {
      opens.add(enrollmentId);
    } else if (eventType === "click") {
      clicks.add(enrollmentId);
    } else if (eventType === "bounce" || eventType === "bounced") {
      bounces.add(enrollmentId);
    } else if (eventType === "delivered") {
      delivered.add(enrollmentId);
    }
  }

  const base = delivered.size || totalEnrollments;
  return {
    total_enrollments: totalEnrollments,
    total_delivered: delivered.size,
    total_opens: opens.size,
    total_clicks: clicks.size,
    total_bounces: bounces.size,
    open_rate: base ? Number((opens.size / base).toFixed(4)) : 0.0,
    click_rate: base ? Number((clicks.size / base).toFixed(4)) : 0.0,
    bounce_rate: base ? Number((bounces.size / base).toFixed(4)) : 0.0,
    completion_rate: totalEnrollments ? Number((completed / totalEnrollments).toFixed(4)) : 0.0,
  };
}

async function buildMonitoringJobsListResponse(
  request: Request,
  env: Env,
): Promise<{ jobs: MonitoringJobRecord[]; count: number }> {
  const userId = await requireAuthenticatedUserId(request, env);
  const rows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/monitoring_jobs?user_id=eq.${userId}&select=*&order=created_at.desc`,
  );
  const jobs = rows.map((row) => normalizeMonitoringJobRecord(row));
  return {
    jobs,
    count: jobs.length,
  };
}

async function buildMonitoringJobCreateResponse(
  request: Request,
  env: Env,
): Promise<{ job: MonitoringJobRecord }> {
  const userId = await requireAuthenticatedUserId(request, env);
  let payload: Record<string, unknown>;
  try {
    payload = (await request.json()) as Record<string, unknown>;
  } catch {
    throw buildErrorResponse(request, env, 400, {
      detail: "Request body must be valid JSON.",
    });
  }

  const job = parseCreateMonitoringJobPayload(payload, request, env);
  const rows = await insertSupabaseAdminRow<Array<Record<string, unknown>>>(
    env,
    "/rest/v1/monitoring_jobs?select=*",
    {
      ...job,
      user_id: userId,
      is_active: true,
    },
  );

  return {
    job: normalizeMonitoringJobRecord(asRecord(rows[0]) ?? {}),
  };
}

async function buildMonitoringJobUpdateResponse(
  request: Request,
  env: Env,
  jobId: string,
): Promise<{ job: MonitoringJobRecord }> {
  const userId = await requireAuthenticatedUserId(request, env);
  let payload: Record<string, unknown>;
  try {
    payload = (await request.json()) as Record<string, unknown>;
  } catch {
    throw buildErrorResponse(request, env, 400, {
      detail: "Request body must be valid JSON.",
    });
  }

  const update = parseUpdateMonitoringJobPayload(payload, request, env);
  const rows = await updateSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/monitoring_jobs?id=eq.${encodeURIComponent(jobId)}&user_id=eq.${userId}&select=*`,
    {
      ...update,
      updated_at: new Date().toISOString(),
    },
  );
  if (rows.length === 0) {
    throw buildErrorResponse(request, env, 404, {
      detail: "Monitoring job not found",
    });
  }

  return {
    job: normalizeMonitoringJobRecord(asRecord(rows[0]) ?? {}),
  };
}

async function buildMonitoringJobDeleteResponse(
  request: Request,
  env: Env,
  jobId: string,
): Promise<{ deleted: true; job_id: string }> {
  const userId = await requireAuthenticatedUserId(request, env);
  await deleteSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/monitoring_jobs?id=eq.${encodeURIComponent(jobId)}&user_id=eq.${userId}&select=id`,
  );
  return {
    deleted: true,
    job_id: jobId,
  };
}

const INITIATIVE_PHASES = ["ideation", "validation", "prototype", "build", "scale"] as const;
const INITIATIVE_CHECKLIST_STATUSES = [
  "pending",
  "in_progress",
  "completed",
  "blocked",
  "skipped",
] as const;
const INITIATIVE_CHECKLIST_SORT_FIELDS = new Set([
  "sort_order",
  "created_at",
  "updated_at",
  "due_at",
  "status",
  "title",
]);
const INITIATIVE_OPERATIONAL_STATE_KEY = "operational_state";

function buildDefaultInitiativePhaseProgress(): Record<string, number> {
  return {
    ideation: 0,
    validation: 0,
    prototype: 0,
    build: 0,
    scale: 0,
  };
}

function ensureInitiativeArray(value: unknown): unknown[] {
  if (Array.isArray(value)) {
    return value;
  }
  if (value === null || value === undefined || value === "") {
    return [];
  }
  return [value];
}

function buildDefaultInitiativeTrustSummary(): Record<string, unknown> {
  return {
    trust_counts: {},
    verification_counts: {},
    approval_state: "not_required",
    verification_status: "not_started",
    last_failure_reason: null,
  };
}

function normalizeInitiativePhase(value: unknown): (typeof INITIATIVE_PHASES)[number] {
  return typeof value === "string" && INITIATIVE_PHASES.includes(value as (typeof INITIATIVE_PHASES)[number])
    ? (value as (typeof INITIATIVE_PHASES)[number])
    : "ideation";
}

function normalizeInitiativePhaseProgress(value: unknown): Record<string, number> {
  const normalized = buildDefaultInitiativePhaseProgress();
  const record = asRecord(value);
  if (!record) {
    return normalized;
  }

  for (const phase of INITIATIVE_PHASES) {
    const raw = record[phase];
    const parsed =
      typeof raw === "number"
        ? raw
        : typeof raw === "string"
          ? Number.parseFloat(raw)
          : Number.NaN;
    if (Number.isFinite(parsed)) {
      normalized[phase] = Math.max(0, Math.min(100, Math.round(parsed)));
    }
  }

  return normalized;
}

function normalizeInitiativeOperationalState(row: Record<string, unknown>): Record<string, unknown> {
  const initiative = { ...row };
  const metadata = asRecord(initiative.metadata) ?? {};
  const opState = asRecord(metadata[INITIATIVE_OPERATIONAL_STATE_KEY]) ?? {};
  const trustSummary = {
    ...buildDefaultInitiativeTrustSummary(),
    ...(asRecord(opState.trust_summary) ?? {}),
  };

  const normalized = {
    goal:
      normalizeOptionalText(opState.goal) ??
      normalizeOptionalText(metadata.goal) ??
      normalizeOptionalText(initiative.description) ??
      normalizeOptionalText(initiative.title) ??
      "",
    success_criteria: ensureInitiativeArray(opState.success_criteria ?? metadata.success_criteria),
    owner_agents: ensureInitiativeArray(opState.owner_agents ?? metadata.owner_agents),
    primary_workflow:
      normalizeOptionalText(opState.primary_workflow) ??
      normalizeOptionalText(metadata.workflow_template_name) ??
      normalizeOptionalText(metadata.primary_workflow),
    deliverables: ensureInitiativeArray(opState.deliverables ?? metadata.deliverables),
    evidence: ensureInitiativeArray(opState.evidence ?? metadata.evidence),
    blockers: ensureInitiativeArray(opState.blockers ?? metadata.blockers),
    next_actions: ensureInitiativeArray(opState.next_actions ?? metadata.next_actions),
    current_phase:
      normalizeOptionalText(opState.current_phase) ??
      normalizeOptionalText(initiative.phase) ??
      normalizeOptionalText(metadata.current_phase) ??
      "ideation",
    verification_status:
      normalizeOptionalText(opState.verification_status) ??
      normalizeOptionalText(metadata.verification_status) ??
      "not_started",
    trust_summary: trustSummary,
    workflow_execution_id:
      normalizeOptionalText(initiative.workflow_execution_id) ??
      normalizeOptionalText(opState.workflow_execution_id),
  };

  metadata[INITIATIVE_OPERATIONAL_STATE_KEY] = normalized;
  initiative.metadata = metadata;
  initiative.phase = normalizeInitiativePhase(initiative.phase);
  initiative.phase_progress = normalizeInitiativePhaseProgress(initiative.phase_progress);
  initiative.goal = normalized.goal;
  initiative.success_criteria = normalized.success_criteria;
  initiative.owner_agents = normalized.owner_agents;
  initiative.primary_workflow = normalized.primary_workflow;
  initiative.deliverables = normalized.deliverables;
  initiative.evidence = normalized.evidence;
  initiative.blockers = normalized.blockers;
  initiative.next_actions = normalized.next_actions;
  initiative.current_phase = normalized.current_phase;
  initiative.verification_status = normalized.verification_status;
  initiative.trust_summary = normalized.trust_summary;
  initiative.workflow_execution_id = normalized.workflow_execution_id;
  return initiative;
}

function buildInitiativeReportRow(
  userId: string,
  initiative: Record<string, unknown>,
): Record<string, unknown> {
  const title = normalizeOptionalText(initiative.title) ?? "Initiative";
  const metadata = asRecord(initiative.metadata) ?? {};
  const phase = normalizeOptionalText(initiative.phase) ?? "ideation";
  const status = normalizeOptionalText(initiative.status) ?? "not_started";
  const desired = typeof metadata.desired_outcomes === "string" ? metadata.desired_outcomes.slice(0, 500) : "";
  const timeline = typeof metadata.timeline === "string" ? metadata.timeline.slice(0, 200) : "";
  const summaryParts = [`Phase: ${phase}. Status: ${status}.`];
  if (desired) {
    summaryParts.push(` Outcomes: ${desired.slice(0, 200)}${desired.length > 200 ? "..." : ""}`);
  }
  if (timeline) {
    summaryParts.push(` Timeline: ${timeline}`);
  }
  const summary = summaryParts.join(" ");
  const contentParts = [
    normalizeOptionalText(initiative.description) ?? "",
    `\nPhase: ${phase}`,
    `Status: ${status}`,
  ];
  if (desired) {
    contentParts.push(`\nDesired outcomes: ${desired}`);
  }
  if (timeline) {
    contentParts.push(`\nTimeline: ${timeline}`);
  }

  return {
    user_id: userId,
    title,
    category: "Initiative",
    status: "Completed",
    summary,
    content: contentParts.filter(Boolean).join("\n") || summary,
    source_type: "initiative",
    source_id: initiative.id,
    metadata: { phase, status },
  };
}

async function upsertInitiativeUserReport(
  env: Env,
  userId: string,
  initiative: Record<string, unknown>,
): Promise<void> {
  if (typeof initiative.id !== "string" || !initiative.id) {
    return;
  }

  try {
    await upsertSupabaseAdminRow<Array<Record<string, unknown>>>(
      env,
      "/rest/v1/user_reports?on_conflict=user_id,source_type,source_id&select=id",
      buildInitiativeReportRow(userId, initiative),
    );
  } catch {
    // Preserve backend behavior: reports are best-effort side effects.
  }
}

async function writeInitiativeGovernanceEvent(
  env: Env,
  userId: string,
  actionType: string,
  initiativeId: string | null,
  details: Record<string, unknown>,
): Promise<void> {
  await postSupabaseAdminPayload<null>(
    env,
    "/rest/v1/governance_audit_log",
    {
      user_id: userId,
      action_type: actionType,
      resource_type: "initiative",
      resource_id: initiativeId,
      details,
    },
    "return=minimal",
  );
}

async function fetchOwnedInitiative(
  env: Env,
  userId: string,
  initiativeId: string,
): Promise<Record<string, unknown> | null> {
  const rows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/initiatives?${new URLSearchParams({
      select: "*",
      id: `eq.${initiativeId}`,
      user_id: `eq.${userId}`,
      limit: "1",
    }).toString()}`,
  );
  return rows[0] ?? null;
}

async function hydrateInitiativeContext(
  env: Env,
  initiative: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  const hydrated = normalizeInitiativeOperationalState(initiative);
  hydrated.journey_outcomes_prompt = null;
  const metadata = asRecord(hydrated.metadata) ?? {};
  const journeyId = normalizeOptionalText(metadata.journey_id);
  if (!journeyId) {
    return hydrated;
  }

  try {
    const rows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
      env,
      `/rest/v1/user_journeys?${new URLSearchParams({
        select: "outcomes_prompt",
        id: `eq.${journeyId}`,
        limit: "1",
      }).toString()}`,
    );
    hydrated.journey_outcomes_prompt = normalizeOptionalText(rows[0]?.outcomes_prompt);
  } catch {
    hydrated.journey_outcomes_prompt = null;
  }

  return hydrated;
}

async function buildInitiativeTemplatesResponse(
  request: Request,
  env: Env,
  url: URL,
): Promise<{ templates: Array<Record<string, unknown>>; count: number }> {
  const personaFilter = url.searchParams.get("persona")?.trim();
  const categoryFilter = url.searchParams.get("category")?.trim();
  const params = new URLSearchParams({
    select: "*",
    order: "title.asc",
  });

  if (personaFilter) {
    params.set("persona", `eq.${personaFilter}`);
  } else if (getSupabaseRequestContext(request, env)) {
    try {
      const userId = await requireAuthenticatedUserId(request, env);
      params.set("persona", `eq.${await resolveEffectivePersonaTier(request, env, userId)}`);
    } catch {
      // Keep templates broadly readable through the edge if caller auth is missing.
    }
  }
  if (categoryFilter) {
    params.set("category", `eq.${categoryFilter}`);
  }

  const templates = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/initiative_templates?${params.toString()}`,
  );
  return {
    templates,
    count: templates.length,
  };
}

async function buildInitiativeFromTemplateResponse(
  request: Request,
  env: Env,
): Promise<{ initiative: Record<string, unknown>; success: true }> {
  const userId = await requireAuthenticatedUserId(request, env);
  let payload: Record<string, unknown>;
  try {
    payload = (await request.json()) as Record<string, unknown>;
  } catch {
    throw buildErrorResponse(request, env, 400, { detail: "Request body must be valid JSON." });
  }

  const templateId = normalizeOptionalText(payload.template_id);
  if (!templateId) {
    throw buildErrorResponse(request, env, 400, { detail: "template_id is required" });
  }

  const templateRows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/initiative_templates?${new URLSearchParams({
      select: "*",
      id: `eq.${templateId}`,
      limit: "1",
    }).toString()}`,
  );
  const template = templateRows[0];
  if (!template) {
    throw buildErrorResponse(request, env, 404, { detail: `Template ${templateId} not found` });
  }

  const insertedRows = await insertSupabaseAdminRow<Array<Record<string, unknown>>>(
    env,
    "/rest/v1/initiatives?select=*",
    {
      title: normalizeOptionalText(payload.title_override) ?? normalizeOptionalText(template.title) ?? "Initiative",
      description: normalizeOptionalText(template.description) ?? "",
      priority: normalizeOptionalText(template.priority) ?? "medium",
      status: "not_started",
      progress: 0,
      phase: "ideation",
      phase_progress: buildDefaultInitiativePhaseProgress(),
      template_id: templateId,
      user_id: userId,
      metadata: {
        template_title: template.title,
        phases: Array.isArray(template.phases) ? template.phases : [],
        suggested_workflows: Array.isArray(template.suggested_workflows)
          ? template.suggested_workflows
          : [],
        kpis: Array.isArray(template.kpis) ? template.kpis : [],
      },
    },
  );

  const initiative = normalizeInitiativeOperationalState(asRecord(insertedRows[0]) ?? {});
  await writeInitiativeGovernanceEvent(env, userId, "initiative.created", normalizeOptionalText(initiative.id), {
    title: initiative.title ?? null,
    source: "template",
  });
  return {
    initiative,
    success: true,
  };
}

async function buildInitiativeFromJourneyResponse(
  request: Request,
  env: Env,
): Promise<{ initiative: Record<string, unknown>; success: true }> {
  const userId = await requireAuthenticatedUserId(request, env);
  let payload: Record<string, unknown>;
  try {
    payload = (await request.json()) as Record<string, unknown>;
  } catch {
    throw buildErrorResponse(request, env, 400, { detail: "Request body must be valid JSON." });
  }

  const journeyId = normalizeOptionalText(payload.journey_id);
  if (!journeyId) {
    throw buildErrorResponse(request, env, 400, { detail: "journey_id is required" });
  }

  const journeyRows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/user_journeys?${new URLSearchParams({
      select: "*",
      id: `eq.${journeyId}`,
      limit: "1",
    }).toString()}`,
  );
  const journey = journeyRows[0];
  if (!journey) {
    throw buildErrorResponse(request, env, 404, { detail: "Journey not found" });
  }

  const desiredOutcomes = normalizeOptionalText(payload.desired_outcomes);
  const timeline = normalizeOptionalText(payload.timeline);
  const insertedRows = await insertSupabaseAdminRow<Array<Record<string, unknown>>>(
    env,
    "/rest/v1/initiatives?select=*",
    {
      title: normalizeOptionalText(payload.title_override) ?? normalizeOptionalText(journey.title) ?? "Initiative",
      description:
        normalizeOptionalText(journey.description) ??
        `Initiative based on the "${normalizeOptionalText(journey.title) ?? "journey"}" user journey`,
      priority: "medium",
      user_id: userId,
      status: "not_started",
      progress: 0,
      phase: "ideation",
      phase_progress: buildDefaultInitiativePhaseProgress(),
      metadata: {
        source: "user_journey",
        journey_id: journey.id,
        journey_title: journey.title,
        journey_stages: Array.isArray(journey.stages) ? journey.stages : [],
        kpis: Array.isArray(journey.kpis) ? journey.kpis : [],
        desired_outcomes: desiredOutcomes,
        timeline,
      },
    },
  );

  const initiative = normalizeInitiativeOperationalState(asRecord(insertedRows[0]) ?? {});
  await writeInitiativeGovernanceEvent(env, userId, "initiative.created", normalizeOptionalText(initiative.id), {
    title: initiative.title ?? null,
    source: "user_journey",
  });
  return {
    initiative,
    success: true,
  };
}

async function buildInitiativesListResponse(
  request: Request,
  env: Env,
  url: URL,
): Promise<{ success: true; initiatives: Array<Record<string, unknown>>; count: number }> {
  const userId = await requireAuthenticatedUserId(request, env);
  const limit = parseIntegerQueryParam(url, "limit", 50, 1, 200);
  const params = new URLSearchParams({
    select: "*",
    order: "created_at.desc",
    limit: String(limit),
  });

  const membership = await getWorkspaceMembershipForUser(env, userId);
  const memberIds = membership?.workspace_id ? await getWorkspaceMemberIds(env, membership.workspace_id) : [];
  if (memberIds.length > 1) {
    params.set("user_id", `in.(${memberIds.join(",")})`);
  } else {
    params.set("user_id", `eq.${userId}`);
  }

  const status = url.searchParams.get("status")?.trim();
  const phase = url.searchParams.get("phase")?.trim();
  const priority = url.searchParams.get("priority")?.trim();
  if (status) {
    params.set("status", `eq.${status}`);
  }
  if (phase) {
    params.set("phase", `eq.${phase}`);
  }
  if (priority) {
    params.set("priority", `eq.${priority}`);
  }

  const rows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/initiatives?${params.toString()}`,
  );
  const initiatives = rows.map((row) => normalizeInitiativeOperationalState(row));
  return {
    success: true,
    initiatives,
    count: initiatives.length,
  };
}

async function buildInitiativeDetailResponse(
  request: Request,
  env: Env,
  initiativeId: string,
): Promise<{ success: true; initiative: Record<string, unknown> }> {
  const userId = await requireAuthenticatedUserId(request, env);
  const initiative = await fetchOwnedInitiative(env, userId, initiativeId);
  if (!initiative) {
    throw buildErrorResponse(request, env, 404, { detail: "Initiative not found" });
  }

  return {
    success: true,
    initiative: await hydrateInitiativeContext(env, initiative),
  };
}

async function buildInitiativeUpdateResponse(
  request: Request,
  env: Env,
  initiativeId: string,
): Promise<{ success: true; initiative: Record<string, unknown> }> {
  const userId = await requireAuthenticatedUserId(request, env);
  let payload: Record<string, unknown>;
  try {
    payload = (await request.json()) as Record<string, unknown>;
  } catch {
    throw buildErrorResponse(request, env, 400, { detail: "Request body must be valid JSON." });
  }

  const existing = await fetchOwnedInitiative(env, userId, initiativeId);
  if (!existing) {
    throw buildErrorResponse(request, env, 404, { detail: "Initiative not found or access denied" });
  }

  const update: Record<string, unknown> = {};
  const status = normalizeOptionalText(payload.status);
  if (status !== null) {
    update.status = status;
  }
  if (payload.progress !== undefined) {
    const progress =
      typeof payload.progress === "number"
        ? payload.progress
        : typeof payload.progress === "string"
          ? Number.parseFloat(payload.progress)
          : Number.NaN;
    if (!Number.isFinite(progress) || progress < 0 || progress > 100) {
      throw buildErrorResponse(request, env, 400, { detail: "progress must be between 0 and 100" });
    }
    update.progress = Math.round(progress);
  }
  const title = normalizeOptionalText(payload.title);
  if (title !== null) {
    update.title = title;
  }
  const description = normalizeOptionalText(payload.description);
  if (description !== null) {
    update.description = description;
  }
  if (payload.phase !== undefined) {
    if (typeof payload.phase !== "string" || !INITIATIVE_PHASES.includes(payload.phase as (typeof INITIATIVE_PHASES)[number])) {
      throw buildErrorResponse(request, env, 400, { detail: "Invalid initiative phase" });
    }
    update.phase = payload.phase;
  }
  if (payload.phase_progress !== undefined) {
    const phaseProgress = asRecord(payload.phase_progress);
    if (!phaseProgress) {
      throw buildErrorResponse(request, env, 400, { detail: "phase_progress must be an object" });
    }
    update.phase_progress = normalizeInitiativePhaseProgress(phaseProgress);
  }
  if (payload.metadata !== undefined) {
    const metadataPatch = asRecord(payload.metadata);
    if (!metadataPatch) {
      throw buildErrorResponse(request, env, 400, { detail: "metadata must be an object" });
    }
    update.metadata = {
      ...(asRecord(existing.metadata) ?? {}),
      ...metadataPatch,
    };
  }
  if (payload.workflow_execution_id !== undefined) {
    update.workflow_execution_id = normalizeOptionalText(payload.workflow_execution_id);
  }

  if (Object.keys(update).length === 0) {
    return {
      success: true,
      initiative: await hydrateInitiativeContext(env, existing),
    };
  }

  update.updated_at = new Date().toISOString();
  const rows = await updateSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/initiatives?id=eq.${encodeURIComponent(initiativeId)}&user_id=eq.${userId}&select=*`,
    update,
  );
  if (rows.length === 0) {
    throw buildErrorResponse(request, env, 404, { detail: "Initiative not found or access denied" });
  }

  const initiative = normalizeInitiativeOperationalState(asRecord(rows[0]) ?? {});
  await upsertInitiativeUserReport(env, userId, initiative);
  return {
    success: true,
    initiative: await hydrateInitiativeContext(env, initiative),
  };
}

async function buildInitiativeDeleteResponse(
  request: Request,
  env: Env,
  initiativeId: string,
): Promise<{ success: true }> {
  const userId = await requireAuthenticatedUserId(request, env);
  const rows = await deleteSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/initiatives?id=eq.${encodeURIComponent(initiativeId)}&user_id=eq.${userId}&select=id`,
  );
  if (rows.length === 0) {
    throw buildErrorResponse(request, env, 404, { detail: "Initiative not found" });
  }

  await writeInitiativeGovernanceEvent(env, userId, "initiative.deleted", initiativeId, {});
  return { success: true };
}

async function ensureInitiativeOwnership(
  env: Env,
  userId: string,
  initiativeId: string,
): Promise<void> {
  const initiative = await fetchOwnedInitiative(env, userId, initiativeId);
  if (!initiative) {
    throw new Error("Initiative not found");
  }
}

async function buildInitiativeChecklistResponse(
  request: Request,
  env: Env,
  initiativeId: string,
  url: URL,
): Promise<{ items: Array<Record<string, unknown>>; count: number }> {
  const userId = await requireAuthenticatedUserId(request, env);
  try {
    await ensureInitiativeOwnership(env, userId, initiativeId);
  } catch {
    throw buildErrorResponse(request, env, 404, { detail: "Initiative not found" });
  }

  const limit = parseIntegerQueryParam(url, "limit", 100, 1, 500);
  const offset = parseIntegerQueryParam(url, "offset", 0, 0, 5000);
  const sortBy = url.searchParams.get("sort_by")?.trim() ?? "sort_order";
  const sortOrder = url.searchParams.get("sort_order")?.trim().toLowerCase() ?? "asc";
  if (!INITIATIVE_CHECKLIST_SORT_FIELDS.has(sortBy)) {
    throw buildErrorResponse(request, env, 400, { detail: `Invalid sort_by '${sortBy}'` });
  }
  if (sortOrder !== "asc" && sortOrder !== "desc") {
    throw buildErrorResponse(request, env, 400, { detail: `Invalid sort_order '${sortOrder}'` });
  }

  const params = new URLSearchParams({
    select: "*",
    initiative_id: `eq.${initiativeId}`,
    user_id: `eq.${userId}`,
    is_deleted: "eq.false",
    order: `${sortBy}.${sortOrder}`,
    limit: String(limit),
    offset: String(offset),
  });
  const phase = url.searchParams.get("phase")?.trim();
  const status = url.searchParams.get("status")?.trim();
  const ownerLabel = url.searchParams.get("owner_label")?.trim();
  const dueBefore = url.searchParams.get("due_before")?.trim();
  const dueAfter = url.searchParams.get("due_after")?.trim();
  if (phase) {
    params.set("phase", `eq.${phase}`);
  }
  if (status) {
    params.set("status", `eq.${status}`);
  }
  if (ownerLabel) {
    params.set("owner_label", `ilike.*${ownerLabel}*`);
  }
  if (dueBefore) {
    params.append("due_at", `lte.${dueBefore}`);
  }
  if (dueAfter) {
    params.append("due_at", `gte.${dueAfter}`);
  }

  const items = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/initiative_checklist_items?${params.toString()}`,
  );
  return {
    items,
    count: items.length,
  };
}

async function logInitiativeChecklistEvent(
  env: Env,
  itemId: string | null,
  initiativeId: string,
  userId: string,
  eventType: string,
  payload: Record<string, unknown>,
): Promise<void> {
  try {
    await insertSupabaseAdminRow<Array<Record<string, unknown>>>(
      env,
      "/rest/v1/initiative_checklist_item_events?select=id",
      {
        item_id: itemId,
        initiative_id: initiativeId,
        user_id: userId,
        event_type: eventType,
        payload,
        actor_user_id: userId,
      },
    );
  } catch {
    // Best-effort parity with backend audit writes.
  }
}

async function buildInitiativeChecklistCreateResponse(
  request: Request,
  env: Env,
  initiativeId: string,
): Promise<{ item: Record<string, unknown>; success: true }> {
  const userId = await requireAuthenticatedUserId(request, env);
  try {
    await ensureInitiativeOwnership(env, userId, initiativeId);
  } catch {
    throw buildErrorResponse(request, env, 404, { detail: "Initiative not found" });
  }

  let payload: Record<string, unknown>;
  try {
    payload = (await request.json()) as Record<string, unknown>;
  } catch {
    throw buildErrorResponse(request, env, 400, { detail: "Request body must be valid JSON." });
  }

  const title = normalizeOptionalText(payload.title);
  if (!title) {
    throw buildErrorResponse(request, env, 400, { detail: "title is required" });
  }
  const phase = normalizeOptionalText(payload.phase);
  if (!phase || !INITIATIVE_PHASES.includes(phase as (typeof INITIATIVE_PHASES)[number])) {
    throw buildErrorResponse(request, env, 400, { detail: "Invalid phase" });
  }
  const status = normalizeOptionalText(payload.status) ?? "pending";
  if (!INITIATIVE_CHECKLIST_STATUSES.includes(status as (typeof INITIATIVE_CHECKLIST_STATUSES)[number])) {
    throw buildErrorResponse(request, env, 400, { detail: "Invalid status" });
  }

  const itemRows = await insertSupabaseAdminRow<Array<Record<string, unknown>>>(
    env,
    "/rest/v1/initiative_checklist_items?select=*",
    {
      initiative_id: initiativeId,
      user_id: userId,
      phase,
      title,
      description: normalizeOptionalText(payload.description),
      status,
      owner_user_id: normalizeOptionalText(payload.owner_user_id),
      owner_label: normalizeOptionalText(payload.owner_label),
      due_at: normalizeOptionalText(payload.due_at),
      evidence: Array.isArray(payload.evidence) ? payload.evidence : [],
      sort_order:
        typeof payload.sort_order === "number"
          ? Math.trunc(payload.sort_order)
          : typeof payload.sort_order === "string"
            ? Number.parseInt(payload.sort_order, 10) || 0
            : 0,
      metadata: asRecord(payload.metadata) ?? {},
      created_by: userId,
      updated_by: userId,
    },
  );
  const item = asRecord(itemRows[0]) ?? {};
  await logInitiativeChecklistEvent(env, normalizeOptionalText(item.id), initiativeId, userId, "created", {
    after: item,
  });
  return {
    item,
    success: true,
  };
}

async function buildInitiativeChecklistUpdateResponse(
  request: Request,
  env: Env,
  initiativeId: string,
  itemId: string,
): Promise<{ item: Record<string, unknown>; success: true }> {
  const userId = await requireAuthenticatedUserId(request, env);
  try {
    await ensureInitiativeOwnership(env, userId, initiativeId);
  } catch {
    throw buildErrorResponse(request, env, 404, { detail: "Initiative not found" });
  }

  let payload: Record<string, unknown>;
  try {
    payload = (await request.json()) as Record<string, unknown>;
  } catch {
    throw buildErrorResponse(request, env, 400, { detail: "Request body must be valid JSON." });
  }

  const beforeRows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/initiative_checklist_items?${new URLSearchParams({
      select: "*",
      id: `eq.${itemId}`,
      initiative_id: `eq.${initiativeId}`,
      user_id: `eq.${userId}`,
      is_deleted: "eq.false",
      limit: "1",
    }).toString()}`,
  );
  const before = beforeRows[0];
  if (!before) {
    throw buildErrorResponse(request, env, 404, { detail: "Checklist item not found" });
  }

  const patch: Record<string, unknown> = { updated_by: userId };
  if (payload.title !== undefined) {
    patch.title = normalizeOptionalText(payload.title);
  }
  if (payload.description !== undefined) {
    patch.description = normalizeOptionalText(payload.description);
  }
  if (payload.phase !== undefined) {
    const phase = normalizeOptionalText(payload.phase);
    if (!phase || !INITIATIVE_PHASES.includes(phase as (typeof INITIATIVE_PHASES)[number])) {
      throw buildErrorResponse(request, env, 400, { detail: "Invalid phase" });
    }
    patch.phase = phase;
  }
  if (payload.status !== undefined) {
    const status = normalizeOptionalText(payload.status);
    if (!status || !INITIATIVE_CHECKLIST_STATUSES.includes(status as (typeof INITIATIVE_CHECKLIST_STATUSES)[number])) {
      throw buildErrorResponse(request, env, 400, { detail: "Invalid status" });
    }
    patch.status = status;
  }
  if (payload.owner_user_id !== undefined) {
    patch.owner_user_id = normalizeOptionalText(payload.owner_user_id);
  }
  if (payload.owner_label !== undefined) {
    patch.owner_label = normalizeOptionalText(payload.owner_label);
  }
  if (payload.due_at !== undefined) {
    patch.due_at = normalizeOptionalText(payload.due_at);
  }
  if (payload.evidence !== undefined) {
    patch.evidence = Array.isArray(payload.evidence) ? payload.evidence : [];
  }
  if (payload.sort_order !== undefined) {
    const sortOrder =
      typeof payload.sort_order === "number"
        ? Math.trunc(payload.sort_order)
        : typeof payload.sort_order === "string"
          ? Number.parseInt(payload.sort_order, 10)
          : Number.NaN;
    if (!Number.isFinite(sortOrder)) {
      throw buildErrorResponse(request, env, 400, { detail: "sort_order must be an integer" });
    }
    patch.sort_order = sortOrder;
  }
  if (payload.metadata !== undefined) {
    const metadata = asRecord(payload.metadata);
    if (!metadata) {
      throw buildErrorResponse(request, env, 400, { detail: "metadata must be an object" });
    }
    patch.metadata = {
      ...(asRecord(before.metadata) ?? {}),
      ...metadata,
    };
  }

  const rows = await updateSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/initiative_checklist_items?id=eq.${encodeURIComponent(itemId)}&initiative_id=eq.${encodeURIComponent(initiativeId)}&user_id=eq.${userId}&select=*`,
    patch,
  );
  if (rows.length === 0) {
    throw buildErrorResponse(request, env, 404, { detail: "Checklist item not found" });
  }
  const item = asRecord(rows[0]) ?? {};
  await logInitiativeChecklistEvent(
    env,
    itemId,
    initiativeId,
    userId,
    patch.status !== undefined && patch.status !== before.status ? "status_changed" : "updated",
    {
      before,
      after: item,
    },
  );
  return {
    item,
    success: true,
  };
}

async function buildInitiativeChecklistDeleteResponse(
  request: Request,
  env: Env,
  initiativeId: string,
  itemId: string,
): Promise<{ success: true }> {
  const userId = await requireAuthenticatedUserId(request, env);
  try {
    await ensureInitiativeOwnership(env, userId, initiativeId);
  } catch {
    throw buildErrorResponse(request, env, 404, { detail: "Initiative not found" });
  }

  const beforeRows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/initiative_checklist_items?${new URLSearchParams({
      select: "*",
      id: `eq.${itemId}`,
      initiative_id: `eq.${initiativeId}`,
      user_id: `eq.${userId}`,
      is_deleted: "eq.false",
      limit: "1",
    }).toString()}`,
  );
  const before = beforeRows[0];
  if (!before) {
    throw buildErrorResponse(request, env, 404, { detail: "Checklist item not found" });
  }

  await updateSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/initiative_checklist_items?id=eq.${encodeURIComponent(itemId)}&initiative_id=eq.${encodeURIComponent(initiativeId)}&user_id=eq.${userId}&select=id`,
    {
      is_deleted: true,
      deleted_at: new Date().toISOString(),
      updated_by: userId,
    },
  );
  await logInitiativeChecklistEvent(env, itemId, initiativeId, userId, "deleted", { before });
  return { success: true };
}

async function buildInitiativeChecklistEventsResponse(
  request: Request,
  env: Env,
  initiativeId: string,
  url: URL,
): Promise<{ events: Array<Record<string, unknown>>; count: number }> {
  const userId = await requireAuthenticatedUserId(request, env);
  try {
    await ensureInitiativeOwnership(env, userId, initiativeId);
  } catch {
    throw buildErrorResponse(request, env, 404, { detail: "Initiative not found" });
  }

  const limit = parseIntegerQueryParam(url, "limit", 100, 1, 500);
  const offset = parseIntegerQueryParam(url, "offset", 0, 0, 5000);
  const params = new URLSearchParams({
    select: "*",
    initiative_id: `eq.${initiativeId}`,
    user_id: `eq.${userId}`,
    order: "created_at.desc",
    limit: String(limit),
    offset: String(offset),
  });
  const eventType = url.searchParams.get("event_type")?.trim();
  const itemId = url.searchParams.get("item_id")?.trim();
  const actorUserId = url.searchParams.get("actor_user_id")?.trim();
  if (eventType) {
    params.set("event_type", `eq.${eventType}`);
  }
  if (itemId) {
    params.set("item_id", `eq.${itemId}`);
  }
  if (actorUserId) {
    params.set("actor_user_id", `eq.${actorUserId}`);
  }

  const events = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/initiative_checklist_item_events?${params.toString()}`,
  );
  return {
    events,
    count: events.length,
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

async function buildReportsListResponse(request: Request, env: Env, url: URL) {
  const userId = await requireAuthenticatedUserId(request, env);
  const featureDenied = await requireFeatureAccess(request, env, "reports", userId);
  if (featureDenied) {
    throw featureDenied;
  }

  const limit = parseIntegerQueryParam(url, "limit", 100, 1, 500);
  const offset = parseIntegerQueryParam(url, "offset", 0, 0, 5000);
  const params = new URLSearchParams({
    select:
      "id,title,category,status,summary,source_type,source_id,metadata,created_at,updated_at",
    user_id: `eq.${userId}`,
    order: "created_at.desc",
    limit: String(limit),
    offset: String(offset),
  });

  const category = url.searchParams.get("category")?.trim();
  if (category) {
    params.set("category", `eq.${category}`);
  }

  const sourceType = url.searchParams.get("source_type")?.trim();
  if (sourceType) {
    params.set("source_type", `eq.${sourceType}`);
  }

  const search = url.searchParams.get("search")?.trim();
  if (search) {
    params.set("or", `(title.ilike.*${search}*,summary.ilike.*${search}*)`);
  }

  return fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/user_reports?${params.toString()}`,
  );
}

async function buildReportCategoriesResponse(
  request: Request,
  env: Env,
): Promise<{ categories: string[] }> {
  const userId = await requireAuthenticatedUserId(request, env);
  const featureDenied = await requireFeatureAccess(request, env, "reports", userId);
  if (featureDenied) {
    throw featureDenied;
  }

  const params = new URLSearchParams({
    select: "category",
    user_id: `eq.${userId}`,
  });
  const rows = await fetchSupabaseAdminRows<Array<{ category?: string | null }>>(
    env,
    `/rest/v1/user_reports?${params.toString()}`,
  );
  const categories = Array.from(
    new Set(
      rows
        .map((row) => row.category?.trim() ?? "")
        .filter((value) => value.length > 0),
    ),
  ).sort((left, right) => left.localeCompare(right));

  return { categories };
}

async function buildReportDetailResponse(request: Request, env: Env, reportId: string) {
  const userId = await requireAuthenticatedUserId(request, env);
  const featureDenied = await requireFeatureAccess(request, env, "reports", userId);
  if (featureDenied) {
    throw featureDenied;
  }

  const params = new URLSearchParams({
    select: "*",
    id: `eq.${reportId}`,
    user_id: `eq.${userId}`,
    limit: "1",
  });
  const rows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/user_reports?${params.toString()}`,
  );
  const report = rows[0];
  if (!report) {
    throw buildErrorResponse(request, env, 404, {
      detail: "Report not found",
    });
  }

  return report;
}

async function buildGovernanceAuditLogResponse(request: Request, env: Env, url: URL) {
  const userId = await requireAuthenticatedUserId(request, env);
  const featureDenied = await requireFeatureAccess(request, env, "governance", userId);
  if (featureDenied) {
    throw featureDenied;
  }

  const limit = parseIntegerQueryParam(url, "limit", 50, 1, 200);
  const offset = parseIntegerQueryParam(url, "offset", 0, 0, 5000);
  const params = new URLSearchParams({
    select: "id,user_id,action_type,resource_type,resource_id,details,created_at",
    user_id: `eq.${userId}`,
    order: "created_at.desc",
    limit: String(limit),
    offset: String(offset),
  });

  const actionType = url.searchParams.get("action_type")?.trim();
  if (actionType) {
    params.set("action_type", `eq.${actionType}`);
  }

  return fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/governance_audit_log?${params.toString()}`,
  );
}

async function buildGovernancePortfolioHealthResponse(
  request: Request,
  env: Env,
): Promise<Record<string, unknown>> {
  const userId = await requireAuthenticatedUserId(request, env);
  const featureDenied = await requireFeatureAccess(request, env, "governance", userId);
  if (featureDenied) {
    throw featureDenied;
  }

  let initiativeCompletion = 0;
  let riskCoverage = 0;
  let resourceAllocation = 0;
  const initiativeBreakdown = {
    in_progress: 0,
    completed: 0,
    blocked: 0,
    not_started: 0,
    total: 0,
  };
  let workflowSuccessRate = 0;
  let currentRevenue = 0;
  let priorRevenue = 0;

  try {
    const rows = await fetchSupabaseAdminRows<Array<{ status?: string | null }>>(
      env,
      `/rest/v1/initiatives?${new URLSearchParams({
        select: "id,status",
        user_id: `eq.${userId}`,
        status: "in.(in_progress,blocked,not_started,completed)",
      }).toString()}`,
    );
    initiativeBreakdown.total = rows.length;
    for (const row of rows) {
      const status = row.status ?? "";
      if (status in initiativeBreakdown) {
        initiativeBreakdown[status as keyof typeof initiativeBreakdown] += 1;
      }
    }
    if (initiativeBreakdown.total > 0) {
      initiativeCompletion = (initiativeBreakdown.completed / initiativeBreakdown.total) * 100;
    }
  } catch {
    // Preserve backend behavior: missing inputs degrade gracefully.
  }

  try {
    const rows = await fetchSupabaseAdminRows<Array<{ mitigation_plan?: unknown }>>(
      env,
      `/rest/v1/compliance_risks?${new URLSearchParams({
        select: "id,mitigation_plan",
        user_id: `eq.${userId}`,
      }).toString()}`,
    );
    if (rows.length > 0) {
      const covered = rows.filter(
        (row) => row.mitigation_plan !== null && row.mitigation_plan !== undefined,
      ).length;
      riskCoverage = (covered / rows.length) * 100;
    }
  } catch {
    // Preserve backend behavior: missing inputs degrade gracefully.
  }

  try {
    const rows = await fetchSupabaseAdminRows<Array<{ owner_user_id?: string | null }>>(
      env,
      `/rest/v1/initiatives?${new URLSearchParams({
        select: "id,owner_user_id",
        user_id: `eq.${userId}`,
      }).toString()}`,
    );
    if (rows.length > 0) {
      const assigned = rows.filter(
        (row) => typeof row.owner_user_id === "string" && row.owner_user_id.length > 0,
      ).length;
      resourceAllocation = (assigned / rows.length) * 100;
    }
  } catch {
    // Preserve backend behavior: missing inputs degrade gracefully.
  }

  try {
    const rows = await fetchSupabaseAdminRows<Array<{ status?: string | null }>>(
      env,
      `/rest/v1/workflow_executions?${new URLSearchParams({
        select: "id,status",
        user_id: `eq.${userId}`,
      }).toString()}`,
    );
    if (rows.length > 0) {
      const completed = rows.filter((row) => row.status === "completed").length;
      workflowSuccessRate = Math.round((completed / rows.length) * 100);
    }
  } catch {
    // Preserve backend behavior: missing inputs degrade gracefully.
  }

  try {
    const now = new Date();
    const currentMonthStart = new Date(
      Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1, 0, 0, 0, 0),
    );
    const priorMonthStart = new Date(
      Date.UTC(now.getUTCFullYear(), now.getUTCMonth() - 1, 1, 0, 0, 0, 0),
    );

    const currentParams = new URLSearchParams({
      select: "amount",
      user_id: `eq.${userId}`,
      status: "eq.paid",
    });
    currentParams.append("created_at", `gte.${currentMonthStart.toISOString()}`);

    const priorParams = new URLSearchParams({
      select: "amount",
      user_id: `eq.${userId}`,
      status: "eq.paid",
    });
    priorParams.append("created_at", `gte.${priorMonthStart.toISOString()}`);
    priorParams.append("created_at", `lt.${currentMonthStart.toISOString()}`);

    const [currentRows, priorRows] = await Promise.all([
      fetchSupabaseAdminRows<Array<{ amount?: number | string | null }>>(
        env,
        `/rest/v1/orders?${currentParams.toString()}`,
      ),
      fetchSupabaseAdminRows<Array<{ amount?: number | string | null }>>(
        env,
        `/rest/v1/orders?${priorParams.toString()}`,
      ),
    ]);

    currentRevenue = currentRows.reduce((total, row) => {
      const amount =
        typeof row.amount === "number"
          ? row.amount
          : typeof row.amount === "string"
            ? Number.parseFloat(row.amount) || 0
            : 0;
      return total + amount;
    }, 0);
    priorRevenue = priorRows.reduce((total, row) => {
      const amount =
        typeof row.amount === "number"
          ? row.amount
          : typeof row.amount === "string"
            ? Number.parseFloat(row.amount) || 0
            : 0;
      return total + amount;
    }, 0);
  } catch {
    // Preserve backend behavior: missing inputs degrade gracefully.
  }

  return {
    score: Math.round(
      initiativeCompletion * 0.4 + riskCoverage * 0.3 + resourceAllocation * 0.3,
    ),
    components: {
      initiative_completion: Number(initiativeCompletion.toFixed(1)),
      risk_coverage: Number(riskCoverage.toFixed(1)),
      resource_allocation: Number(resourceAllocation.toFixed(1)),
      initiative_breakdown: initiativeBreakdown,
      workflow_success_rate: workflowSuccessRate,
      revenue_trend: {
        current_month: Number(currentRevenue.toFixed(2)),
        prior_month: Number(priorRevenue.toFixed(2)),
      },
    },
  };
}

async function buildGovernanceApprovalChainsResponse(request: Request, env: Env) {
  const userId = await requireAuthenticatedUserId(request, env);
  const featureDenied = await requireFeatureAccess(request, env, "governance", userId);
  if (featureDenied) {
    throw featureDenied;
  }

  const chainRows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/approval_chains?${new URLSearchParams({
      select: "id,user_id,action_type,resource_id,resource_label,status,created_at,resolved_at",
      user_id: `eq.${userId}`,
      status: "eq.pending",
      order: "created_at.desc",
    }).toString()}`,
  );
  if (!chainRows.length) {
    return [];
  }

  const chainIds = chainRows
    .map((row) => (typeof row.id === "string" ? row.id : null))
    .filter((value): value is string => Boolean(value));
  const stepRows = chainIds.length
    ? await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
        env,
        `/rest/v1/approval_chain_steps?${new URLSearchParams({
          select: "id,chain_id,step_order,role_label,approver_user_id,status,decided_at,comment",
          chain_id: `in.(${chainIds.join(",")})`,
          order: "step_order.asc",
        }).toString()}`,
      )
    : [];

  const stepsByChain = new Map<string, Array<Record<string, unknown>>>();
  for (const step of stepRows) {
    const chainId = typeof step.chain_id === "string" ? step.chain_id : null;
    if (!chainId) {
      continue;
    }
    const existing = stepsByChain.get(chainId) ?? [];
    existing.push(step);
    stepsByChain.set(chainId, existing);
  }

  return chainRows.map((chain) => ({
    ...chain,
    steps: stepsByChain.get(typeof chain.id === "string" ? chain.id : "") ?? [],
  }));
}

async function buildGovernanceApprovalChainDetailResponse(
  request: Request,
  env: Env,
  chainId: string,
) {
  const userId = await requireAuthenticatedUserId(request, env);
  const featureDenied = await requireFeatureAccess(request, env, "governance", userId);
  if (featureDenied) {
    throw featureDenied;
  }

  const chainRows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/approval_chains?${new URLSearchParams({
      select: "id,user_id,action_type,resource_id,resource_label,status,created_at,resolved_at",
      id: `eq.${chainId}`,
      limit: "1",
    }).toString()}`,
  );
  const chain = chainRows[0];
  if (!chain) {
    throw buildErrorResponse(request, env, 404, {
      detail: "Approval chain not found",
    });
  }

  const stepRows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/approval_chain_steps?${new URLSearchParams({
      select: "id,chain_id,step_order,role_label,approver_user_id,status,decided_at,comment",
      chain_id: `eq.${chainId}`,
      order: "step_order.asc",
    }).toString()}`,
  );

  return {
    ...chain,
    steps: stepRows,
  };
}

async function buildGovernanceApprovalChainCreateResponse(request: Request, env: Env) {
  const userId = await requireAuthenticatedUserId(request, env);
  const featureDenied = await requireFeatureAccess(request, env, "governance", userId);
  if (featureDenied) {
    throw featureDenied;
  }

  const { workspace, role } = await getOrCreateWorkspaceForUser(env, userId);
  const currentRole = role?.trim().toLowerCase() ?? null;
  if (currentRole !== "admin") {
    throw buildWorkspaceRoleDeniedResponse(request, env, currentRole, ["admin"]);
  }

  let payload: Record<string, unknown>;
  try {
    payload = (await request.json()) as Record<string, unknown>;
  } catch {
    throw buildErrorResponse(request, env, 400, {
      detail: "Request body must be valid JSON.",
    });
  }

  const chainPayload = parseGovernanceApprovalChainCreatePayload(payload, request, env);
  const chainRows = await insertSupabaseAdminRow<Array<Record<string, unknown>>>(
    env,
    "/rest/v1/approval_chains?select=id,user_id,action_type,resource_id,resource_label,status,created_at,resolved_at",
    {
      user_id: userId,
      action_type: chainPayload.action_type,
      ...(chainPayload.resource_id ? { resource_id: chainPayload.resource_id } : {}),
      ...(chainPayload.resource_label ? { resource_label: chainPayload.resource_label } : {}),
      status: "pending",
    },
  );
  const chain = chainRows[0];
  const chainId = typeof chain?.id === "string" ? chain.id : "";
  if (!chainId) {
    throw new Error("Approval chain creation returned no id.");
  }

  const defaultSteps = [
    { step_order: 1, role_label: "reviewer" },
    { step_order: 2, role_label: "approver" },
    { step_order: 3, role_label: "executive" },
  ];
  const stepDefinitions = chainPayload.steps?.length
    ? chainPayload.steps.map((step, index) => ({
        chain_id: chainId,
        step_order: index + 1,
        role_label: step.role_label,
        ...(step.approver_user_id ? { approver_user_id: step.approver_user_id } : {}),
        status: "pending",
      }))
    : defaultSteps.map((step) => ({
        chain_id: chainId,
        step_order: step.step_order,
        role_label: step.role_label,
        status: "pending",
      }));

  const stepRows = await postSupabaseAdminPayload<Array<Record<string, unknown>>>(
    env,
    "/rest/v1/approval_chain_steps?select=id,chain_id,step_order,role_label,approver_user_id,status,decided_at,comment",
    stepDefinitions,
  );

  await postSupabaseAdminPayload<null>(
    env,
    "/rest/v1/governance_audit_log",
    {
      user_id: userId,
      action_type: "approval_chain.created",
      resource_type: "approval_chain",
      resource_id: chainId,
      details: {
        action_type: chainPayload.action_type,
        resource_label: chainPayload.resource_label,
        workspace_id: workspace.id,
      },
    },
    "return=minimal",
  );

  return {
    ...chain,
    steps: stepRows,
  };
}

async function buildGovernanceApprovalChainDecisionResponse(
  request: Request,
  env: Env,
  chainId: string,
  stepOrder: number,
) {
  const userId = await requireAuthenticatedUserId(request, env);
  const featureDenied = await requireFeatureAccess(request, env, "governance", userId);
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

  const decisionPayload = parseGovernanceApprovalDecisionPayload(payload, request, env);
  const nowIso = new Date().toISOString();

  const chainRows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/approval_chains?${new URLSearchParams({
      select: "id,status",
      id: `eq.${chainId}`,
      limit: "1",
    }).toString()}`,
  );
  const chain = chainRows[0];
  if (!chain) {
    throw buildErrorResponse(request, env, 404, {
      detail: "Approval chain not found",
    });
  }

  const stepRows = await updateSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/approval_chain_steps?chain_id=eq.${encodeURIComponent(chainId)}&step_order=eq.${stepOrder}&select=id,chain_id,step_order,role_label,approver_user_id,status,decided_at,comment`,
    {
      status: decisionPayload.decision,
      decided_at: nowIso,
      approver_user_id: userId,
      comment: decisionPayload.comment,
    },
  );
  if (stepRows.length === 0) {
    throw buildErrorResponse(request, env, 404, {
      detail: "Approval chain step not found",
    });
  }

  if (decisionPayload.decision === "rejected") {
    await updateSupabaseAdminRows<Array<Record<string, unknown>>>(
      env,
      `/rest/v1/approval_chains?id=eq.${encodeURIComponent(chainId)}&select=id`,
      {
        status: "rejected",
        resolved_at: nowIso,
      },
    );
  } else {
    const maxStepRows = await fetchSupabaseAdminRows<Array<{ step_order?: number | string | null }>>(
      env,
      `/rest/v1/approval_chain_steps?${new URLSearchParams({
        select: "step_order",
        chain_id: `eq.${chainId}`,
        order: "step_order.desc",
        limit: "1",
      }).toString()}`,
    );
    const maxStepOrder = typeof maxStepRows[0]?.step_order === "number"
      ? maxStepRows[0].step_order
      : typeof maxStepRows[0]?.step_order === "string"
        ? Number.parseInt(maxStepRows[0].step_order, 10) || 0
        : 0;
    if (stepOrder >= maxStepOrder) {
      await updateSupabaseAdminRows<Array<Record<string, unknown>>>(
        env,
        `/rest/v1/approval_chains?id=eq.${encodeURIComponent(chainId)}&select=id`,
        {
          status: "approved",
          resolved_at: nowIso,
        },
      );
    }
  }

  await postSupabaseAdminPayload<null>(
    env,
    "/rest/v1/governance_audit_log",
    {
      user_id: userId,
      action_type: "approval.decided",
      resource_type: "approval_chain",
      resource_id: chainId,
      details: {
        step_order: stepOrder,
        decision: decisionPayload.decision,
        comment: decisionPayload.comment,
      },
    },
    "return=minimal",
  );

  return buildGovernanceApprovalChainDetailResponse(request, env, chainId);
}

async function buildLearningCoursesResponse(request: Request, env: Env, url: URL) {
  await requireAuthenticatedUserId(request, env);

  const params = new URLSearchParams({
    select:
      "id,title,description,category,difficulty,duration_minutes,lessons_count,thumbnail_gradient,is_recommended,sort_order,created_at",
    order: "sort_order.asc",
  });

  const category = url.searchParams.get("category")?.trim();
  if (category) {
    params.set("category", `eq.${category}`);
  }

  return fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/learning_courses?${params.toString()}`,
  );
}

async function buildLearningProgressResponse(request: Request, env: Env) {
  const userId = await requireAuthenticatedUserId(request, env);

  const progressRows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/learning_progress?${new URLSearchParams({
      select:
        "id,user_id,course_id,progress_percent,status,started_at,completed_at,updated_at",
      user_id: `eq.${userId}`,
      order: "updated_at.desc",
    }).toString()}`,
  );
  if (!progressRows.length) {
    return [];
  }

  const courseIds = progressRows
    .map((row) => (typeof row.course_id === "string" ? row.course_id : null))
    .filter((value): value is string => Boolean(value));

  const courseRows = courseIds.length
    ? await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
        env,
        `/rest/v1/learning_courses?${new URLSearchParams({
          select:
            "id,title,description,category,difficulty,duration_minutes,lessons_count,thumbnail_gradient,is_recommended,sort_order,created_at",
          id: `in.(${courseIds.join(",")})`,
        }).toString()}`,
      )
    : [];
  const courseMap = new Map<string, Record<string, unknown>>();
  for (const course of courseRows) {
    if (typeof course.id === "string") {
      courseMap.set(course.id, course);
    }
  }

  return progressRows.map((row) => ({
    ...row,
    progress_percent:
      typeof row.progress_percent === "number"
        ? row.progress_percent
        : typeof row.progress_percent === "string"
          ? Number.parseFloat(row.progress_percent) || 0
          : 0,
    learning_courses:
      typeof row.course_id === "string" ? courseMap.get(row.course_id) ?? null : null,
  }));
}

function parseLearningProgressPayload(
  payload: Record<string, unknown>,
  request: Request,
  env: Env,
): { progress_percent: number } {
  const rawValue = payload.progress_percent;
  const progressPercent =
    typeof rawValue === "number"
      ? rawValue
      : typeof rawValue === "string"
        ? Number.parseFloat(rawValue)
        : Number.NaN;

  if (!Number.isFinite(progressPercent)) {
    throw buildErrorResponse(request, env, 400, {
      detail: "progress_percent must be a number",
    });
  }

  return {
    progress_percent: progressPercent,
  };
}

async function buildLearningCourseStartResponse(
  request: Request,
  env: Env,
  courseId: string,
) {
  const userId = await requireAuthenticatedUserId(request, env);

  const courseRows = await fetchSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/learning_courses?${new URLSearchParams({
      select: "id",
      id: `eq.${courseId}`,
      limit: "1",
    }).toString()}`,
  );
  if (!courseRows.length) {
    throw buildErrorResponse(request, env, 404, {
      detail: "Course not found",
    });
  }

  const nowIso = new Date().toISOString();
  const rows = await postSupabaseAdminPayload<Array<Record<string, unknown>>>(
    env,
    "/rest/v1/learning_progress?on_conflict=user_id,course_id&select=*",
    {
      user_id: userId,
      course_id: courseId,
      status: "in_progress",
      progress_percent: 0,
      started_at: nowIso,
    },
    "resolution=merge-duplicates,return=representation",
  );

  const row = rows[0];
  if (!row) {
    throw new Error("Failed to start course");
  }

  return {
    ...row,
    progress_percent:
      typeof row.progress_percent === "number"
        ? row.progress_percent
        : typeof row.progress_percent === "string"
          ? Number.parseFloat(row.progress_percent) || 0
          : 0,
  };
}

async function buildLearningProgressUpdateResponse(
  request: Request,
  env: Env,
  courseId: string,
) {
  const userId = await requireAuthenticatedUserId(request, env);
  let payload: Record<string, unknown>;
  try {
    payload = (await request.json()) as Record<string, unknown>;
  } catch {
    throw buildErrorResponse(request, env, 400, {
      detail: "Request body must be valid JSON.",
    });
  }

  const progressPayload = parseLearningProgressPayload(payload, request, env);
  const updateData: Record<string, unknown> = {
    progress_percent: progressPayload.progress_percent,
  };
  if (progressPayload.progress_percent >= 100) {
    updateData.status = "completed";
    updateData.completed_at = new Date().toISOString();
  } else if (progressPayload.progress_percent > 0) {
    updateData.status = "in_progress";
  }

  const rows = await updateSupabaseAdminRows<Array<Record<string, unknown>>>(
    env,
    `/rest/v1/learning_progress?user_id=eq.${encodeURIComponent(userId)}&course_id=eq.${encodeURIComponent(courseId)}&select=*`,
    updateData,
  );
  const row = rows[0];
  if (!row) {
    throw buildErrorResponse(request, env, 404, {
      detail: "Progress record not found",
    });
  }

  return {
    ...row,
    progress_percent:
      typeof row.progress_percent === "number"
        ? row.progress_percent
        : typeof row.progress_percent === "string"
          ? Number.parseFloat(row.progress_percent) || 0
          : 0,
  };
}

function formatKpiCurrency(amount: number | null, currency = "USD") {
  if (amount === null) {
    return "$0";
  }

  const symbol = currency.toUpperCase() === "USD" ? "$" : `${currency.toUpperCase()} `;
  return `${symbol}${amount.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

function formatKpiPercent(numerator: number, denominator: number) {
  if (denominator === 0) {
    return "0%";
  }

  return `${Math.round((numerator / denominator) * 100)}%`;
}

async function fetchSupabaseAdminRowsSafe<T>(env: Env, path: string): Promise<T[]> {
  try {
    return await fetchSupabaseAdminRows<T[]>(env, path);
  } catch {
    return [];
  }
}

function getCurrentMonthStartIso() {
  const now = new Date();
  return new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1, 0, 0, 0, 0)).toISOString();
}

function getPriorMonthBoundsIso() {
  const now = new Date();
  const currentMonthStart = new Date(
    Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1, 0, 0, 0, 0),
  );
  const priorMonthStart = new Date(
    Date.UTC(now.getUTCFullYear(), now.getUTCMonth() - 1, 1, 0, 0, 0, 0),
  );

  return {
    currentMonthStart: currentMonthStart.toISOString(),
    priorMonthStart: priorMonthStart.toISOString(),
  };
}

async function buildPersonaKpisResponse(request: Request, env: Env) {
  const userId = await requireAuthenticatedUserId(request, env);
  const persona = getRequestPersonaOverride(request) ?? "solopreneur";

  if (persona === "startup") {
    const { currentMonthStart, priorMonthStart } = getPriorMonthBoundsIso();

    const [currentOrders, priorOrders, pipelineRows, teamRows] = await Promise.all([
      fetchSupabaseAdminRowsSafe<Record<string, unknown>>(
        env,
        `/rest/v1/orders?${new URLSearchParams({
          select: "total_amount",
          user_id: `eq.${userId}`,
          status: "eq.paid",
        })
          .toString()}&created_at=gte.${encodeURIComponent(currentMonthStart)}`,
      ),
      fetchSupabaseAdminRowsSafe<Record<string, unknown>>(
        env,
        `/rest/v1/orders?${new URLSearchParams({
          select: "total_amount",
          user_id: `eq.${userId}`,
          status: "eq.paid",
        })
          .toString()}&created_at=gte.${encodeURIComponent(priorMonthStart)}&created_at=lt.${encodeURIComponent(currentMonthStart)}`,
      ),
      fetchSupabaseAdminRowsSafe<Record<string, unknown>>(
        env,
        `/rest/v1/contacts?${new URLSearchParams({
          select: "estimated_value",
          user_id: `eq.${userId}`,
          lifecycle_stage: "in.(opportunity,qualified)",
        }).toString()}`,
      ),
      fetchSupabaseAdminRowsSafe<Record<string, unknown>>(
        env,
        `/rest/v1/workspace_members?${new URLSearchParams({
          select: "id",
          user_id: `eq.${userId}`,
        }).toString()}`,
      ),
    ]);

    const currentRevenue = currentOrders.reduce((total, row) => {
      const amount =
        typeof row.total_amount === "number"
          ? row.total_amount
          : typeof row.total_amount === "string"
            ? Number.parseFloat(row.total_amount) || 0
            : 0;
      return total + amount;
    }, 0);
    const priorRevenue = priorOrders.reduce((total, row) => {
      const amount =
        typeof row.total_amount === "number"
          ? row.total_amount
          : typeof row.total_amount === "string"
            ? Number.parseFloat(row.total_amount) || 0
            : 0;
      return total + amount;
    }, 0);
    const pipelineValue = pipelineRows.reduce((total, row) => {
      const value =
        typeof row.estimated_value === "number"
          ? row.estimated_value
          : typeof row.estimated_value === "string"
            ? Number.parseFloat(row.estimated_value) || 0
            : 0;
      return total + value;
    }, 0);

    const growthValue =
      priorRevenue === 0
        ? "+0%"
        : `${Math.round(((currentRevenue - priorRevenue) / priorRevenue) * 100) >= 0 ? "+" : ""}${Math.round(((currentRevenue - priorRevenue) / priorRevenue) * 100)}%`;

    return {
      persona,
      kpis: [
        {
          label: "Revenue",
          value: formatKpiCurrency(currentRevenue),
          unit: "currency",
          subtitle: "No paid orders this month yet — close your first deal",
        },
        {
          label: "Pipeline Value",
          value: formatKpiCurrency(pipelineValue),
          unit: "currency",
          subtitle: "Qualify contacts to build your sales pipeline",
        },
        {
          label: "Team Size",
          value: String(teamRows.length),
          unit: "members",
          subtitle: "Invite team members to your workspace to see headcount",
        },
        {
          label: "Growth Rate (MoM)",
          value: growthValue,
          unit: "percent",
          subtitle: "Revenue growth will appear once you have two months of data",
        },
      ],
    };
  }

  if (persona === "sme") {
    const currentMonthStart = getCurrentMonthStartIso();
    const [orderRows, departmentRows, complianceRows, taskRows] = await Promise.all([
      fetchSupabaseAdminRowsSafe<Record<string, unknown>>(
        env,
        `/rest/v1/orders?${new URLSearchParams({
          select: "total_amount",
          user_id: `eq.${userId}`,
          status: "eq.paid",
        })
          .toString()}&created_at=gte.${encodeURIComponent(currentMonthStart)}`,
      ),
      fetchSupabaseAdminRowsSafe<Record<string, unknown>>(
        env,
        `/rest/v1/departments?${new URLSearchParams({
          select: "id,status",
        }).toString()}`,
      ),
      fetchSupabaseAdminRowsSafe<Record<string, unknown>>(
        env,
        `/rest/v1/compliance_risks?${new URLSearchParams({
          select: "id,status",
          user_id: `eq.${userId}`,
        }).toString()}`,
      ),
      fetchSupabaseAdminRowsSafe<Record<string, unknown>>(
        env,
        `/rest/v1/tasks?${new URLSearchParams({
          select: "id",
          user_id: `eq.${userId}`,
          status: "eq.open",
        }).toString()}`,
      ),
    ]);

    const revenue = orderRows.reduce((total, row) => {
      const amount =
        typeof row.total_amount === "number"
          ? row.total_amount
          : typeof row.total_amount === "string"
            ? Number.parseFloat(row.total_amount) || 0
            : 0;
      return total + amount;
    }, 0);
    const activeDepartments = departmentRows.filter((row) => row.status === "RUNNING").length;
    const resolvedRisks = complianceRows.filter(
      (row) => row.status === "mitigated" || row.status === "resolved",
    ).length;

    return {
      persona,
      kpis: [
        {
          label: "Revenue",
          value: formatKpiCurrency(revenue),
          unit: "currency",
          subtitle: "No paid orders this month — configure your billing integration",
        },
        {
          label: "Active Departments",
          value: String(activeDepartments),
          unit: "departments",
          subtitle: "Set departments to RUNNING to track active operational units",
        },
        {
          label: "Compliance Score",
          value: formatKpiPercent(resolvedRisks, complianceRows.length),
          unit: "percent",
          subtitle: "Log compliance risks and resolve them to improve your score",
        },
        {
          label: "Open Tasks",
          value: String(taskRows.length),
          unit: "tasks",
          subtitle: "Create tasks to track team work items and deadlines",
        },
      ],
    };
  }

  if (persona === "enterprise") {
    const [initiativeRows, complianceRows, orderRows, departmentRows] = await Promise.all([
      fetchSupabaseAdminRowsSafe<Record<string, unknown>>(
        env,
        `/rest/v1/initiatives?${new URLSearchParams({
          select: "id,status,progress",
          user_id: `eq.${userId}`,
          status: "in.(in_progress,blocked,not_started)",
        }).toString()}`,
      ),
      fetchSupabaseAdminRowsSafe<Record<string, unknown>>(
        env,
        `/rest/v1/compliance_risks?${new URLSearchParams({
          select: "id,mitigation_plan",
          user_id: `eq.${userId}`,
        }).toString()}`,
      ),
      fetchSupabaseAdminRowsSafe<Record<string, unknown>>(
        env,
        `/rest/v1/orders?${new URLSearchParams({
          select: "total_amount",
          user_id: `eq.${userId}`,
          status: "eq.paid",
        }).toString()}`,
      ),
      fetchSupabaseAdminRowsSafe<Record<string, unknown>>(
        env,
        `/rest/v1/departments?${new URLSearchParams({
          select: "id",
        }).toString()}`,
      ),
    ]);

    const onTrack = initiativeRows.filter((row) => {
      const progress =
        typeof row.progress === "number"
          ? row.progress
          : typeof row.progress === "string"
            ? Number.parseFloat(row.progress) || 0
            : 0;
      return row.status === "in_progress" && progress >= 50;
    }).length;
    const withMitigation = complianceRows.filter((row) => Boolean(row.mitigation_plan)).length;
    const totalRevenue = orderRows.reduce((total, row) => {
      const amount =
        typeof row.total_amount === "number"
          ? row.total_amount
          : typeof row.total_amount === "string"
            ? Number.parseFloat(row.total_amount) || 0
            : 0;
      return total + amount;
    }, 0);

    return {
      persona,
      kpis: [
        {
          label: "Portfolio Health %",
          value: formatKpiPercent(onTrack, initiativeRows.length),
          unit: "percent",
          subtitle:
            "Create strategic initiatives and track progress to measure portfolio health",
        },
        {
          label: "Risk Score",
          value: formatKpiPercent(withMitigation, complianceRows.length),
          unit: "percent",
          subtitle: "Add mitigation plans to compliance risks to improve your risk score",
        },
        {
          label: "Total Revenue",
          value: formatKpiCurrency(totalRevenue),
          unit: "currency",
          subtitle: "Connect your billing to track cumulative revenue across all time",
        },
        {
          label: "Department Count",
          value: String(departmentRows.length),
          unit: "departments",
          subtitle: "Add departments to your org chart to see the full structure",
        },
      ],
    };
  }

  const sevenDaysAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString();
  const [invoiceRows, orderRows, pipelineRows, contentRows, integrationRows] = await Promise.all([
    fetchSupabaseAdminRowsSafe<Record<string, unknown>>(
      env,
      `/rest/v1/invoices?${new URLSearchParams({
        select: "order_id",
        user_id: `eq.${userId}`,
        status: "eq.paid",
      }).toString()}`,
    ),
    fetchSupabaseAdminRowsSafe<Record<string, unknown>>(
      env,
      `/rest/v1/orders?${new URLSearchParams({
        select: "id,total_amount",
        user_id: `eq.${userId}`,
        status: "eq.paid",
      }).toString()}`,
    ),
    fetchSupabaseAdminRowsSafe<Record<string, unknown>>(
      env,
      `/rest/v1/contacts?${new URLSearchParams({
        select: "estimated_value",
        user_id: `eq.${userId}`,
        lifecycle_stage: "in.(opportunity,qualified)",
      }).toString()}`,
    ),
    fetchSupabaseAdminRowsSafe<Record<string, unknown>>(
      env,
      `/rest/v1/content_bundles?${new URLSearchParams({
        select: "id",
        user_id: `eq.${userId}`,
      })
        .toString()}&created_at=gte.${encodeURIComponent(sevenDaysAgo)}`,
    ),
    fetchSupabaseAdminRowsSafe<Record<string, unknown>>(
      env,
      `/rest/v1/user_integrations?${new URLSearchParams({
        select: "id",
        user_id: `eq.${userId}`,
        status: "eq.connected",
      }).toString()}`,
    ),
  ]);

  const paidOrderIds = new Set(
    invoiceRows
      .map((row) => (typeof row.order_id === "string" ? row.order_id : null))
      .filter((value): value is string => Boolean(value)),
  );
  const revenue = orderRows.reduce((total, row) => {
    if (typeof row.id !== "string" || !paidOrderIds.has(row.id)) {
      return total;
    }
    const amount =
      typeof row.total_amount === "number"
        ? row.total_amount
        : typeof row.total_amount === "string"
          ? Number.parseFloat(row.total_amount) || 0
          : 0;
    return total + amount;
  }, 0);
  const pipelineValue = pipelineRows.reduce((total, row) => {
    const value =
      typeof row.estimated_value === "number"
        ? row.estimated_value
        : typeof row.estimated_value === "string"
          ? Number.parseFloat(row.estimated_value) || 0
          : 0;
    return total + value;
  }, 0);

  return {
    persona: "solopreneur",
    kpis: [
      {
        label: "Revenue",
        value: formatKpiCurrency(revenue),
        unit: "currency",
        subtitle: "No revenue yet — complete your first sale to see this update",
      },
      {
        label: "Weekly Pipeline",
        value: formatKpiCurrency(pipelineValue),
        unit: "currency",
        subtitle: "Add contacts in opportunity/qualified stage to see pipeline value",
      },
      {
        label: "Content Created",
        value: String(contentRows.length),
        unit: "pieces",
        subtitle: "Create content bundles to track your weekly output",
      },
      {
        label: "Connected Integrations",
        value: String(integrationRows.length),
        unit: "integrations",
        subtitle: "Connect apps like Gmail, Stripe, or Calendly to unlock automation",
      },
    ],
  };
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
  featureKey: "teams" | "sales" | "reports" | "governance",
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

function getSocialOAuthProviderConfig(platform: string): SocialOAuthProviderConfig | null {
  return SOCIAL_OAUTH_PROVIDER_CONFIGS[platform] ?? null;
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
      verifier: typeof payload.verifier === "string" ? payload.verifier : undefined,
      redirect_uri: typeof payload.redirect_uri === "string" ? payload.redirect_uri : undefined,
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
    const rawBody = new Uint8Array(await request.arrayBuffer());
    if (!env.HUBSPOT_CLIENT_SECRET?.trim() && !env.HUBSPOT_WEBHOOK_SECRET?.trim()) {
      return null;
    }

    if (!(await verifyHubSpotWebhook(request, env, rawBody))) {
      return buildErrorResponse(request, env, 403, {
        detail: "Invalid signature",
      });
    }

    return jsonWithCors(await buildHubSpotWebhookResponse(request, env, rawBody), request, env);
  }

  if (url.pathname === "/webhooks/resend" && request.method === "POST") {
    const rawBody = new Uint8Array(await request.arrayBuffer());
    if (!env.RESEND_WEBHOOK_SECRET?.trim()) {
      return null;
    }

    if (!(await verifyResendWebhook(request, env, rawBody))) {
      return buildErrorResponse(request, env, 401, {
        detail: "Invalid webhook signature",
      });
    }

    return jsonWithCors(await buildResendWebhookResponse(request, env, rawBody), request, env);
  }

  if (url.pathname === "/webhooks/shopify" && request.method === "POST") {
    const rawBody = new Uint8Array(await request.arrayBuffer());
    if (!env.SHOPIFY_WEBHOOK_SECRET?.trim()) {
      return null;
    }

    if (!(await verifyShopifyWebhook(request, env, rawBody))) {
      return buildErrorResponse(request, env, 403, {
        detail: "Invalid signature",
      });
    }

    return jsonWithCors(await buildShopifyWebhookResponse(request, env, rawBody), request, env);
  }

  if (url.pathname === "/webhooks/stripe" && request.method === "POST") {
    const rawBody = new Uint8Array(await request.arrayBuffer());
    if (!env.STRIPE_WEBHOOK_SECRET?.trim()) {
      return null;
    }

    if (!(await verifyStripeWebhook(request, env, rawBody))) {
      return buildErrorResponse(request, env, 403, {
        detail: "Invalid signature",
      });
    }

    return jsonWithCors(await buildStripeWebhookResponse(request, env, rawBody), request, env);
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

  if (url.pathname === "/configuration/save-user-config" && request.method === "POST") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildSaveUserConfigResponse(request, env), request, env);
  }

  if (url.pathname === "/configuration/connect-social" && request.method === "POST") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildConnectSocialResponse(request, env), request, env);
  }

  if (url.pathname === "/configuration/disconnect-social" && request.method === "POST") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildDisconnectSocialResponse(request, env), request, env);
  }

  const configurationOAuthCallbackMatch = /^\/configuration\/oauth\/callback\/([^/]+)$/.exec(url.pathname);
  if (configurationOAuthCallbackMatch && request.method === "GET") {
    return jsonWithCors(
      await buildConfigurationOAuthCallbackResponse(
        request,
        env,
        decodeURIComponent(configurationOAuthCallbackMatch[1]),
        url,
      ),
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

  if ((url.pathname === "/data-io/tables" || url.pathname === "/data-io/tables/") && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildDataIoTablesResponse(request, env), request, env);
  }

  if ((url.pathname === "/data-io/upload" || url.pathname === "/data-io/upload/") && request.method === "POST") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildDataIoUploadResponse(request, env, url), request, env);
  }

  if ((url.pathname === "/data-io/validate" || url.pathname === "/data-io/validate/") && request.method === "POST") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildDataIoValidateResponse(request, env), request, env);
  }

  if ((url.pathname === "/data-io/commit" || url.pathname === "/data-io/commit/") && request.method === "POST") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return buildDataIoCommitResponse(request, env);
  }

  const dataIoExportMatch = /^\/data-io\/export\/([^/]+)$/.exec(url.pathname);
  if (dataIoExportMatch && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(
      await buildDataIoExportResponse(request, env, decodeURIComponent(dataIoExportMatch[1])),
      request,
      env,
    );
  }

  if ((url.pathname === "/monitoring-jobs" || url.pathname === "/monitoring-jobs/") && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildMonitoringJobsListResponse(request, env), request, env);
  }

  if ((url.pathname === "/monitoring-jobs" || url.pathname === "/monitoring-jobs/") && request.method === "POST") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCorsStatus(await buildMonitoringJobCreateResponse(request, env), request, env, 201);
  }

  const monitoringJobMatch = /^\/monitoring-jobs\/([^/]+)$/.exec(url.pathname);
  if (monitoringJobMatch && request.method === "PATCH") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(
      await buildMonitoringJobUpdateResponse(
        request,
        env,
        decodeURIComponent(monitoringJobMatch[1]),
      ),
      request,
      env,
    );
  }

  if (monitoringJobMatch && request.method === "DELETE") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(
      await buildMonitoringJobDeleteResponse(
        request,
        env,
        decodeURIComponent(monitoringJobMatch[1]),
      ),
      request,
      env,
    );
  }

  if ((url.pathname === "/email-sequences" || url.pathname === "/email-sequences/") && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildEmailSequencesListResponse(request, env), request, env);
  }

  if ((url.pathname === "/email-sequences" || url.pathname === "/email-sequences/") && request.method === "POST") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCorsStatus(await buildEmailSequenceCreateResponse(request, env), request, env, 201);
  }

  const emailSequenceDetailMatch = /^\/email-sequences\/([^/]+)$/.exec(url.pathname);
  if (emailSequenceDetailMatch && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(
      await buildEmailSequenceDetailResponse(
        request,
        env,
        decodeURIComponent(emailSequenceDetailMatch[1]),
      ),
      request,
      env,
    );
  }

  if (emailSequenceDetailMatch && request.method === "DELETE") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(
      await buildEmailSequenceDeleteResponse(
        request,
        env,
        decodeURIComponent(emailSequenceDetailMatch[1]),
      ),
      request,
      env,
    );
  }

  const emailSequenceStatusMatch = /^\/email-sequences\/([^/]+)\/status$/.exec(url.pathname);
  if (emailSequenceStatusMatch && request.method === "PATCH") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(
      await buildEmailSequenceStatusUpdateResponse(
        request,
        env,
        decodeURIComponent(emailSequenceStatusMatch[1]),
      ),
      request,
      env,
    );
  }

  const emailSequenceEnrollMatch = /^\/email-sequences\/([^/]+)\/enroll$/.exec(url.pathname);
  if (emailSequenceEnrollMatch && request.method === "POST") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(
      await buildEmailSequenceEnrollResponse(
        request,
        env,
        decodeURIComponent(emailSequenceEnrollMatch[1]),
      ),
      request,
      env,
    );
  }

  const emailSequenceEnrollmentDeleteMatch = /^\/email-sequences\/enrollments\/([^/]+)$/.exec(
    url.pathname,
  );
  if (emailSequenceEnrollmentDeleteMatch && request.method === "DELETE") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(
      await buildEmailSequenceUnenrollResponse(
        request,
        env,
        decodeURIComponent(emailSequenceEnrollmentDeleteMatch[1]),
      ),
      request,
      env,
    );
  }

  const emailSequencePerformanceMatch = /^\/email-sequences\/([^/]+)\/performance$/.exec(
    url.pathname,
  );
  if (emailSequencePerformanceMatch && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(
      await buildEmailSequencePerformanceResponse(
        request,
        env,
        decodeURIComponent(emailSequencePerformanceMatch[1]),
      ),
      request,
      env,
    );
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

  if ((url.pathname === "/reports" || url.pathname === "/reports/") && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildReportsListResponse(request, env, url), request, env);
  }

  if (url.pathname === "/reports/categories" && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildReportCategoriesResponse(request, env), request, env);
  }

  const reportMatch = /^\/reports\/([^/]+)$/.exec(url.pathname);
  if (reportMatch && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(
      await buildReportDetailResponse(request, env, decodeURIComponent(reportMatch[1])),
      request,
      env,
    );
  }

  if (url.pathname === "/governance/audit-log" && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildGovernanceAuditLogResponse(request, env, url), request, env);
  }

  if (url.pathname === "/governance/portfolio-health" && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildGovernancePortfolioHealthResponse(request, env), request, env);
  }

  if (
    (url.pathname === "/governance/approval-chains" ||
      url.pathname === "/governance/approval-chains/") &&
    request.method === "GET"
  ) {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildGovernanceApprovalChainsResponse(request, env), request, env);
  }

  if (
    (url.pathname === "/governance/approval-chains" ||
      url.pathname === "/governance/approval-chains/") &&
    request.method === "POST"
  ) {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCorsStatus(
      await buildGovernanceApprovalChainCreateResponse(request, env),
      request,
      env,
      201,
    );
  }

  const governanceApprovalChainMatch = /^\/governance\/approval-chains\/([^/]+)$/.exec(
    url.pathname,
  );
  if (governanceApprovalChainMatch && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(
      await buildGovernanceApprovalChainDetailResponse(
        request,
        env,
        decodeURIComponent(governanceApprovalChainMatch[1]),
      ),
      request,
      env,
    );
  }

  const governanceApprovalDecisionMatch =
    /^\/governance\/approval-chains\/([^/]+)\/steps\/(\d+)\/decide$/.exec(url.pathname);
  if (governanceApprovalDecisionMatch && request.method === "POST") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(
      await buildGovernanceApprovalChainDecisionResponse(
        request,
        env,
        decodeURIComponent(governanceApprovalDecisionMatch[1]),
        Number.parseInt(governanceApprovalDecisionMatch[2], 10),
      ),
      request,
      env,
    );
  }

  if (url.pathname === "/learning/courses" && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildLearningCoursesResponse(request, env, url), request, env);
  }

  if (url.pathname === "/learning/progress" && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildLearningProgressResponse(request, env), request, env);
  }

  const learningCourseStartMatch = /^\/learning\/progress\/([^/]+)\/start$/.exec(url.pathname);
  if (learningCourseStartMatch && request.method === "POST") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCorsStatus(
      await buildLearningCourseStartResponse(
        request,
        env,
        decodeURIComponent(learningCourseStartMatch[1]),
      ),
      request,
      env,
      201,
    );
  }

  const learningProgressUpdateMatch = /^\/learning\/progress\/([^/]+)$/.exec(url.pathname);
  if (learningProgressUpdateMatch && request.method === "PATCH") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(
      await buildLearningProgressUpdateResponse(
        request,
        env,
        decodeURIComponent(learningProgressUpdateMatch[1]),
      ),
      request,
      env,
    );
  }

  if (url.pathname === "/kpis/persona" && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildPersonaKpisResponse(request, env), request, env);
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

  if (url.pathname === "/initiatives/templates" && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildInitiativeTemplatesResponse(request, env, url), request, env);
  }

  if (url.pathname === "/initiatives/from-template" && request.method === "POST") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCorsStatus(
      await buildInitiativeFromTemplateResponse(request, env),
      request,
      env,
      201,
    );
  }

  if (url.pathname === "/initiatives/from-journey" && request.method === "POST") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCorsStatus(
      await buildInitiativeFromJourneyResponse(request, env),
      request,
      env,
      201,
    );
  }

  if ((url.pathname === "/initiatives" || url.pathname === "/initiatives/") && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(await buildInitiativesListResponse(request, env, url), request, env);
  }

  const initiativeChecklistEventsMatch = /^\/initiatives\/([^/]+)\/checklist\/events$/.exec(url.pathname);
  if (initiativeChecklistEventsMatch && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(
      await buildInitiativeChecklistEventsResponse(
        request,
        env,
        decodeURIComponent(initiativeChecklistEventsMatch[1]),
        url,
      ),
      request,
      env,
    );
  }

  const initiativeChecklistItemMatch = /^\/initiatives\/([^/]+)\/checklist\/([^/]+)$/.exec(url.pathname);
  if (initiativeChecklistItemMatch && request.method === "PATCH") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(
      await buildInitiativeChecklistUpdateResponse(
        request,
        env,
        decodeURIComponent(initiativeChecklistItemMatch[1]),
        decodeURIComponent(initiativeChecklistItemMatch[2]),
      ),
      request,
      env,
    );
  }

  if (initiativeChecklistItemMatch && request.method === "DELETE") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(
      await buildInitiativeChecklistDeleteResponse(
        request,
        env,
        decodeURIComponent(initiativeChecklistItemMatch[1]),
        decodeURIComponent(initiativeChecklistItemMatch[2]),
      ),
      request,
      env,
    );
  }

  const initiativeChecklistMatch = /^\/initiatives\/([^/]+)\/checklist$/.exec(url.pathname);
  if (initiativeChecklistMatch && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(
      await buildInitiativeChecklistResponse(
        request,
        env,
        decodeURIComponent(initiativeChecklistMatch[1]),
        url,
      ),
      request,
      env,
    );
  }

  if (initiativeChecklistMatch && request.method === "POST") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCorsStatus(
      await buildInitiativeChecklistCreateResponse(
        request,
        env,
        decodeURIComponent(initiativeChecklistMatch[1]),
      ),
      request,
      env,
      201,
    );
  }

  const initiativeMatch = /^\/initiatives\/([^/]+)$/.exec(url.pathname);
  if (initiativeMatch && request.method === "GET") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(
      await buildInitiativeDetailResponse(
        request,
        env,
        decodeURIComponent(initiativeMatch[1]),
      ),
      request,
      env,
    );
  }

  if (initiativeMatch && request.method === "PATCH") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(
      await buildInitiativeUpdateResponse(
        request,
        env,
        decodeURIComponent(initiativeMatch[1]),
      ),
      request,
      env,
    );
  }

  if (initiativeMatch && request.method === "DELETE") {
    const denied = requireEdgeAccess(request, env);
    if (denied) {
      return denied;
    }

    return jsonWithCors(
      await buildInitiativeDeleteResponse(
        request,
        env,
        decodeURIComponent(initiativeMatch[1]),
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

  if ((request.method === "GET" || request.method === "HEAD") && isNativeFamilyRoot404Path(url.pathname)) {
    return buildErrorResponse(request, env, 404, { detail: "Not Found" });
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
