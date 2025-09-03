import { supabase } from '@/lib/supabase'

function makeTableEntity(table) {
  return {
    async create(data) {
      const { data: session } = await supabase.auth.getSession()
      const user_id = session?.session?.user?.id || null
      const payload = user_id ? { ...data, user_id } : data
      const { data: row, error } = await supabase.from(table).insert(payload).select().single()
      if (error) throw error
      return row
    },
    async update(id, updates) {
      const { data, error } = await supabase.from(table).update(updates).eq('id', id).select().single()
      if (error) throw error
      return data
    },
    async get(id) {
      const { data, error } = await supabase.from(table).select('*').eq('id', id).single()
      if (error) throw error
      return data
    },
    async list(orderBy = '-created_at', limit = 50, filters = {}) {
      let query = supabase.from(table).select('*')
      if (orderBy) {
        const asc = !orderBy.startsWith('-')
        const col = orderBy.replace('-', '')
        query = query.order(col, { ascending: asc, nullsFirst: false })
      }
      Object.entries(filters || {}).forEach(([k, v]) => {
        if (v != null) query = query.eq(k, v)
      })
      if (limit) query = query.limit(limit)
      const { data, error } = await query
      if (error) throw error
      return data
    }
  }
}

export const DataAnalysisReport = makeTableEntity('data_analysis_reports')
export const OperationsAnalysis = makeTableEntity('operations_analyses')
export const FinancialAnalysis = makeTableEntity('financial_analyses')
export const QualityDocument = makeTableEntity('quality_documents')
export const SalesLead = {
  ...makeTableEntity('sales_leads'),
  async schema() {
    return {
      type: 'object',
      properties: {
        company_name: { type: 'string' },
        contact_person: { type: 'string' },
        industry: { type: 'string' },
        website: { type: 'string' },
        email: { type: 'string' },
        phone: { type: 'string' }
      },
      required: ['company_name', 'contact_person', 'industry']
    }
  }
}
export const BusinessInitiative = makeTableEntity('business_initiatives')
export const InitiativeDeliverable = makeTableEntity('initiative_deliverables')
export const LearningPath = makeTableEntity('learning_paths')
export const UserProgress = makeTableEntity('user_progress')
export const CustomAgent = makeTableEntity('custom_agents')
export const CustomAgentInteraction = makeTableEntity('custom_agent_interactions')

// Placeholder exports to keep interface intact. Implement as needed.
export const GeneratedContent = {}
export const StrategicAnalysis = {}
export const SupportTicket = {}
export const MarketingCampaign = {}
export const CandidateScreening = {}
export const ComplianceReport = {}
export const UserSubscription = {}
export const UsageAnalytics = {}
export const Workflow = {}
export const WorkflowStep = {}
export const AuditLog = {}
export const AgentTrainingSession = {}
export const DevelopmentTask = {}
export const DatabaseMigration = {}
export const MigrationExecution = {}
export const Achievement = {}
export const LearningChallenge = {}
export const KnowledgeBaseDocument = {}
export const WorkflowTemplate = {}
export const ValidationRun = {}
export const SocialCampaign = {}
export const SocialAdVariant = {}
export const SocialPost = {}
export const ABTest = {}
export const SocialAuthAccount = {}
export const MetaAdAccount = {}
export const MetaCampaign = {}
export const MetaAdSet = {}
export const MetaAd = {}
export const APIRateLimit = {}
export const APIJobQueue = {}
export const LinkedInAdAccount = {}
export const LinkedInCampaign = {}
export const LinkedInCompanyPage = {}
export const LinkedInLeadGenForm = {}
export const LinkedInLead = {}
export const TwitterAdAccount = {}
export const TwitterCampaign = {}
export const TwitterPromotedTweet = {}
export const TwitterStreamRule = {}
export const TwitterStreamTweet = {}
export const TwitterBulkOperation = {}
export const YouTubeChannel = {}
export const YouTubeVideo = {}
export const YouTubePlaylist = {}
export const YouTubeAnalytics = {}
export const TikTokAccount = {}
export const TikTokVideo = {}
export const TikTokAdAccount = {}
export const TikTokCampaign = {}
export const TikTokAdGroup = {}
export const TikTokAd = {}
export const CorrectiveAction = makeTableEntity('corrective_actions')

// auth sdk replacement
export const User = {
  async getCurrent() {
    const { data } = await supabase.auth.getUser()
    return data?.user || null
  }
}
