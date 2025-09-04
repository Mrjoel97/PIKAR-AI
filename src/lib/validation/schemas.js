import { z } from 'zod';

// Base validation schemas for common data types
export const BaseSchemas = {
  id: z.string().uuid(),
  email: z.string().email(),
  url: z.string().url(),
  phone: z.string().regex(/^\+?[1-9]\d{1,14}$/),
  date: z.string().datetime(),
  positiveNumber: z.number().positive(),
  nonNegativeNumber: z.number().min(0),
  currency: z.number().min(0).max(999999999.99),
  percentage: z.number().min(0).max(100),
  slug: z.string().regex(/^[a-z0-9-]+$/),
  name: z.string().min(1).max(255).trim(),
  description: z.string().max(2000).optional(),
  status: z.enum(['draft', 'active', 'paused', 'completed', 'archived']),
  priority: z.enum(['low', 'medium', 'high', 'critical']),
  tier: z.enum(['solopreneur', 'startup', 'sme', 'enterprise'])
};

// User-related schemas
export const UserSchema = z.object({
  id: BaseSchemas.id.optional(),
  email: BaseSchemas.email,
  name: BaseSchemas.name,
  tier: BaseSchemas.tier,
  avatar: BaseSchemas.url.optional(),
  phone: BaseSchemas.phone.optional(),
  company: BaseSchemas.name.optional(),
  role: z.string().max(100).optional(),
  preferences: z.object({
    notifications: z.boolean().default(true),
    theme: z.enum(['light', 'dark', 'system']).default('system'),
    language: z.string().length(2).default('en')
  }).optional()
});

export const UserUpdateSchema = UserSchema.partial().omit({ id: true });

// Campaign-related schemas
const CampaignBaseSchema = z.object({
  id: BaseSchemas.id.optional(),
  name: BaseSchemas.name,
  description: BaseSchemas.description,
  budget: BaseSchemas.currency,
  status: BaseSchemas.status,
  startDate: BaseSchemas.date,
  endDate: BaseSchemas.date,
  platform: z.enum(['facebook', 'instagram', 'twitter', 'linkedin', 'youtube', 'tiktok']),
  targetAudience: z.object({
    ageRange: z.object({
      min: z.number().min(13).max(100),
      max: z.number().min(13).max(100)
    }),
    gender: z.enum(['all', 'male', 'female', 'other']).optional(),
    location: z.string().optional(),
    interests: z.array(z.string()).optional()
  }).optional(),
  metrics: z.object({
    impressions: BaseSchemas.nonNegativeNumber.optional(),
    clicks: BaseSchemas.nonNegativeNumber.optional(),
    conversions: BaseSchemas.nonNegativeNumber.optional(),
    spend: BaseSchemas.currency.optional(),
    ctr: BaseSchemas.percentage.optional(),
    cpc: BaseSchemas.currency.optional()
  }).optional()
});

export const CampaignSchema = CampaignBaseSchema.refine(data => new Date(data.startDate) < new Date(data.endDate), {
  message: "End date must be after start date",
  path: ["endDate"]
});

export const CampaignCreateSchema = CampaignBaseSchema.omit({ id: true });
export const CampaignUpdateSchema = CampaignBaseSchema.partial().omit({ id: true });

// Ticket/Support schemas
export const TicketSchema = z.object({
  id: BaseSchemas.id.optional(),
  title: BaseSchemas.name,
  description: z.string().min(10).max(5000),
  priority: BaseSchemas.priority,
  status: z.enum(['open', 'in_progress', 'resolved', 'closed']),
  category: z.enum(['technical', 'billing', 'feature_request', 'bug_report', 'general']),
  assignedTo: BaseSchemas.id.optional(),
  createdBy: BaseSchemas.id,
  tags: z.array(z.string().max(50)).max(10).optional(),
  attachments: z.array(z.object({
    filename: z.string(),
    url: BaseSchemas.url,
    size: z.number().positive(),
    type: z.string()
  })).optional()
});

export const TicketCreateSchema = TicketSchema.omit({ id: true, createdBy: true });
export const TicketUpdateSchema = TicketSchema.partial().omit({ id: true, createdBy: true });

// Report schemas
export const ReportSchema = z.object({
  id: BaseSchemas.id.optional(),
  name: BaseSchemas.name,
  type: z.enum(['campaign_performance', 'user_analytics', 'financial', 'custom']),
  dateRange: z.object({
    start: BaseSchemas.date,
    end: BaseSchemas.date
  }),
  filters: z.record(z.any()).optional(),
  format: z.enum(['pdf', 'csv', 'json', 'xlsx']),
  schedule: z.object({
    frequency: z.enum(['once', 'daily', 'weekly', 'monthly']),
    time: z.string().regex(/^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$/).optional(),
    dayOfWeek: z.number().min(0).max(6).optional(),
    dayOfMonth: z.number().min(1).max(31).optional()
  }).optional()
});

export const ReportCreateSchema = ReportSchema.omit({ id: true });
export const ReportUpdateSchema = ReportSchema.partial().omit({ id: true });

// File upload schemas
export const FileUploadSchema = z.object({
  filename: z.string().min(1).max(255),
  size: z.number().positive().max(50 * 1024 * 1024), // 50MB max
  type: z.string().regex(/^[a-zA-Z0-9]+\/[a-zA-Z0-9\-\+\.]+$/),
  content: z.string().optional(), // base64 content
  metadata: z.record(z.any()).optional()
}).refine(data => {
  const allowedTypes = [
    'image/jpeg', 'image/png', 'image/gif', 'image/webp',
    'application/pdf', 'text/csv', 'application/json',
    'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
  ];
  return allowedTypes.includes(data.type);
}, {
  message: "File type not allowed",
  path: ["type"]
});

// API Key schemas
export const ApiKeySchema = z.object({
  id: BaseSchemas.id.optional(),
  name: BaseSchemas.name,
  key: z.string().min(32).max(128),
  permissions: z.array(z.enum(['read', 'write', 'admin'])),
  status: z.enum(['active', 'inactive', 'revoked']),
  expiresAt: BaseSchemas.date.optional(),
  lastUsed: BaseSchemas.date.optional(),
  rateLimits: z.object({
    requestsPerMinute: z.number().positive().max(10000),
    requestsPerHour: z.number().positive().max(100000),
    requestsPerDay: z.number().positive().max(1000000)
  }).optional()
});

export const ApiKeyCreateSchema = ApiKeySchema.omit({ id: true, key: true, lastUsed: true });
export const ApiKeyUpdateSchema = ApiKeySchema.partial().omit({ id: true, key: true });

// AI Agent schemas
export const AgentSchema = z.object({
  id: BaseSchemas.id.optional(),
  name: BaseSchemas.name,
  type: z.enum([
    'strategic_planning', 'financial_analysis', 'customer_support',
    'content_creation', 'marketing_automation', 'data_analysis',
    'operations_optimization', 'hr_recruitment', 'compliance_risk',
    'sales_intelligence'
  ]),
  description: BaseSchemas.description,
  status: z.enum(['active', 'inactive', 'training', 'error']),
  configuration: z.object({
    model: z.string(),
    temperature: z.number().min(0).max(2),
    maxTokens: z.number().positive().max(4000),
    systemPrompt: z.string().max(5000),
    tools: z.array(z.string()).optional(),
    knowledgeBase: z.array(BaseSchemas.id).optional()
  }),
  metrics: z.object({
    totalInvocations: BaseSchemas.nonNegativeNumber.optional(),
    successRate: BaseSchemas.percentage.optional(),
    averageResponseTime: BaseSchemas.nonNegativeNumber.optional(),
    lastUsed: BaseSchemas.date.optional()
  }).optional()
});

export const AgentCreateSchema = AgentSchema.omit({ id: true, metrics: true });
export const AgentUpdateSchema = AgentSchema.partial().omit({ id: true, metrics: true });

// Agent Invocation schemas
export const AgentInvocationSchema = z.object({
  id: BaseSchemas.id.optional(),
  agentId: BaseSchemas.id,
  userId: BaseSchemas.id,
  input: z.object({
    prompt: z.string().min(1).max(10000),
    context: z.record(z.any()).optional(),
    parameters: z.record(z.any()).optional()
  }),
  output: z.object({
    response: z.string(),
    confidence: BaseSchemas.percentage.optional(),
    tokensUsed: z.number().positive().optional(),
    processingTime: z.number().positive().optional()
  }).optional(),
  status: z.enum(['pending', 'processing', 'completed', 'failed']),
  error: z.string().optional(),
  createdAt: BaseSchemas.date.optional()
});

export const AgentInvocationCreateSchema = AgentInvocationSchema.omit({
  id: true, output: true, status: true, error: true, createdAt: true
});

// Social Media schemas
export const SocialPostSchema = z.object({
  id: BaseSchemas.id.optional(),
  platform: z.enum(['facebook', 'instagram', 'twitter', 'linkedin', 'youtube', 'tiktok']),
  content: z.object({
    text: z.string().max(2000).optional(),
    images: z.array(BaseSchemas.url).max(10).optional(),
    video: BaseSchemas.url.optional(),
    link: BaseSchemas.url.optional(),
    hashtags: z.array(z.string().regex(/^#[a-zA-Z0-9_]+$/)).max(30).optional()
  }),
  scheduling: z.object({
    publishAt: BaseSchemas.date.optional(),
    timezone: z.string().optional()
  }).optional(),
  targeting: z.object({
    audience: z.string().optional(),
    location: z.string().optional(),
    demographics: z.record(z.any()).optional()
  }).optional(),
  status: z.enum(['draft', 'scheduled', 'published', 'failed']),
  metrics: z.object({
    impressions: BaseSchemas.nonNegativeNumber.optional(),
    engagements: BaseSchemas.nonNegativeNumber.optional(),
    clicks: BaseSchemas.nonNegativeNumber.optional(),
    shares: BaseSchemas.nonNegativeNumber.optional()
  }).optional()
});

export const SocialPostCreateSchema = SocialPostSchema.omit({ id: true, metrics: true });
export const SocialPostUpdateSchema = SocialPostSchema.partial().omit({ id: true, metrics: true });

// Analytics schemas
export const AnalyticsQuerySchema = z.object({
  metrics: z.array(z.string()).min(1),
  dimensions: z.array(z.string()).optional(),
  dateRange: z.object({
    start: BaseSchemas.date,
    end: BaseSchemas.date
  }),
  filters: z.array(z.object({
    field: z.string(),
    operator: z.enum(['eq', 'ne', 'gt', 'gte', 'lt', 'lte', 'in', 'nin', 'contains']),
    value: z.any()
  })).optional(),
  groupBy: z.array(z.string()).optional(),
  orderBy: z.array(z.object({
    field: z.string(),
    direction: z.enum(['asc', 'desc'])
  })).optional(),
  limit: z.number().positive().max(10000).optional()
});

// Workflow schemas
export const WorkflowSchema = z.object({
  id: BaseSchemas.id.optional(),
  name: BaseSchemas.name,
  description: BaseSchemas.description,
  trigger: z.object({
    type: z.enum(['manual', 'schedule', 'webhook', 'event']),
    configuration: z.record(z.any())
  }),
  steps: z.array(z.object({
    id: z.string(),
    type: z.enum(['agent_invocation', 'api_call', 'condition', 'delay', 'notification']),
    configuration: z.record(z.any()),
    nextSteps: z.array(z.string()).optional()
  })),
  status: z.enum(['active', 'inactive', 'draft']),
  version: z.number().positive(),
  tags: z.array(z.string()).optional()
});

export const WorkflowCreateSchema = WorkflowSchema.omit({ id: true, version: true });
export const WorkflowUpdateSchema = WorkflowSchema.partial().omit({ id: true });

// Authentication schemas
export const LoginSchema = z.object({
  email: BaseSchemas.email,
  password: z.string().min(8).max(128),
  rememberMe: z.boolean().optional()
});

export const RegisterSchema = z.object({
  email: BaseSchemas.email,
  password: z.string().min(8).max(128).regex(
    /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]/,
    "Password must contain at least one uppercase letter, one lowercase letter, one number, and one special character"
  ),
  confirmPassword: z.string(),
  name: BaseSchemas.name,
  company: BaseSchemas.name.optional(),
  tier: BaseSchemas.tier
}).refine(data => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ["confirmPassword"]
});

export const PasswordResetSchema = z.object({
  email: BaseSchemas.email
});

export const PasswordChangeSchema = z.object({
  currentPassword: z.string().min(8).max(128),
  newPassword: z.string().min(8).max(128).regex(
    /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]/,
    "Password must contain at least one uppercase letter, one lowercase letter, one number, and one special character"
  ),
  confirmPassword: z.string()
}).refine(data => data.newPassword === data.confirmPassword, {
  message: "Passwords don't match",
  path: ["confirmPassword"]
});

// Quality Management System schemas
export const CorrectiveActionSchema = z.object({
  id: BaseSchemas.id.optional(),
  title: BaseSchemas.name,
  non_conformity: z.string().min(10).max(2000),
  root_cause_analysis: z.string().max(2000).optional(),
  action_plan: z.string().min(10).max(2000),
  assigned_to: BaseSchemas.name,
  due_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  priority: z.enum(['Low', 'Medium', 'High', 'Critical']),
  verification_method: z.string().max(500).optional(),
  iso_clause: z.string().max(100).optional(),
  status: z.enum(['open', 'in_progress', 'completed', 'verified', 'closed']).default('open'),
  completion_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).optional(),
  verification_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).optional(),
  effectiveness_review: z.string().max(1000).optional()
}).refine(data => {
  const dueDate = new Date(data.due_date);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return dueDate >= today;
}, {
  message: "Due date must be today or in the future",
  path: ["due_date"]
});

export const CorrectiveActionCreateSchema = CorrectiveActionSchema.omit({
  id: true,
  status: true,
  completion_date: true,
  verification_date: true
});

export const CorrectiveActionUpdateSchema = CorrectiveActionSchema.partial().omit({ id: true });

// Document Management schemas
export const DocumentSchema = z.object({
  id: BaseSchemas.id.optional(),
  title: BaseSchemas.name,
  description: BaseSchemas.description,
  category: z.enum(['policy', 'procedure', 'work_instruction', 'form', 'record', 'manual']),
  version: z.string().regex(/^\d+\.\d+$/),
  status: z.enum(['draft', 'review', 'approved', 'obsolete']),
  author: BaseSchemas.name,
  reviewer: BaseSchemas.name.optional(),
  approver: BaseSchemas.name.optional(),
  effective_date: BaseSchemas.date.optional(),
  review_date: BaseSchemas.date.optional(),
  file_url: BaseSchemas.url.optional(),
  tags: z.array(z.string()).optional(),
  access_level: z.enum(['public', 'internal', 'confidential', 'restricted'])
});

export const DocumentCreateSchema = DocumentSchema.omit({ id: true });
export const DocumentUpdateSchema = DocumentSchema.partial().omit({ id: true });

// Learning Management schemas
export const LearningPathSchema = z.object({
  id: BaseSchemas.id.optional(),
  title: BaseSchemas.name,
  description: BaseSchemas.description,
  category: z.enum(['technical', 'compliance', 'leadership', 'soft_skills', 'product']),
  difficulty: z.enum(['beginner', 'intermediate', 'advanced']),
  estimated_duration: z.number().positive(), // in minutes
  prerequisites: z.array(BaseSchemas.id).optional(),
  modules: z.array(z.object({
    id: z.string(),
    title: z.string(),
    type: z.enum(['video', 'document', 'quiz', 'assignment', 'discussion']),
    duration: z.number().positive(),
    required: z.boolean().default(true)
  })),
  status: z.enum(['draft', 'published', 'archived']),
  tags: z.array(z.string()).optional()
});

export const LearningPathCreateSchema = LearningPathSchema.omit({ id: true });
export const LearningPathUpdateSchema = LearningPathSchema.partial().omit({ id: true });

// Migration schemas
export const DatabaseMigrationSchema = z.object({
  id: BaseSchemas.id.optional(),
  name: BaseSchemas.name,
  description: BaseSchemas.description,
  version: z.string().regex(/^\d{4}\.\d{2}\.\d{2}\.\d{3}$/),
  sql_up: z.string().min(1),
  sql_down: z.string().min(1),
  dependencies: z.array(BaseSchemas.id).optional(),
  estimated_duration: z.number().positive().optional(),
  risk_level: z.enum(['low', 'medium', 'high', 'critical']),
  rollback_plan: z.string().optional(),
  validation_queries: z.array(z.string()).optional(),
  status: z.enum(['pending', 'running', 'completed', 'failed', 'rolled_back'])
});

export const DatabaseMigrationCreateSchema = DatabaseMigrationSchema.omit({
  id: true,
  status: true
});

export const DatabaseMigrationUpdateSchema = DatabaseMigrationSchema.partial().omit({ id: true });
