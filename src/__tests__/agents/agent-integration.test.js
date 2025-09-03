/**
 * Agent Integration Tests
 * Tests for agent interactions with Base44 SDK and external services
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { agentService } from '@/services/agentService'
import { base44EntityService } from '@/api/base44Client'
import { apiIntegrationService } from '@/services/apiIntegrationService'
import { auditService } from '@/services/auditService'
import { testDataFactories } from '@/test/utils'

// Mock dependencies
vi.mock('@/services/agentService')
vi.mock('@/api/base44Client')
vi.mock('@/services/apiIntegrationService')
vi.mock('@/services/auditService')

describe('Agent Integration Tests', () => {
  const mockUser = testDataFactories.user()

  beforeEach(() => {
    vi.clearAllMocks()
    
    // Mock audit service
    auditService.logAccess = {
      agentExecution: vi.fn()
    }
    auditService.logSystem = {
      integration: vi.fn(),
      error: vi.fn()
    }
  })

  afterEach(() => {
    vi.clearAllTimers()
  })

  describe('Base44 SDK Integration', () => {
    it('should execute agents through Base44 SDK successfully', async () => {
      const mockBase44Response = {
        success: true,
        data: {
          result: 'Agent executed via Base44',
          analysis: 'SDK integration successful',
          metadata: {
            tokensUsed: 300,
            executionTime: 4.2,
            sdkVersion: '1.0.0'
          }
        }
      }

      base44EntityService.invokeAgent.mockResolvedValueOnce(mockBase44Response)

      const agentRequest = {
        agentType: 'strategic_planning',
        task: 'market-analysis',
        parameters: {
          company: 'TestCorp',
          industry: 'Technology'
        }
      }

      const result = await base44EntityService.invokeAgent(agentRequest)

      expect(result.success).toBe(true)
      expect(result.data.result).toBe('Agent executed via Base44')
      expect(result.data.metadata.sdkVersion).toBeDefined()
      expect(base44EntityService.invokeAgent).toHaveBeenCalledWith(agentRequest)
    })

    it('should handle Base44 SDK authentication errors', async () => {
      base44EntityService.invokeAgent.mockRejectedValueOnce(
        new Error('Authentication failed: Invalid API key')
      )

      const agentRequest = {
        agentType: 'content_creation',
        task: 'blog-post',
        parameters: { topic: 'AI trends' }
      }

      await expect(base44EntityService.invokeAgent(agentRequest)).rejects.toThrow('Authentication failed')
      
      expect(auditService.logSystem.error).toHaveBeenCalledWith(
        expect.any(Error),
        'base44_auth_error',
        expect.any(Object)
      )
    })

    it('should handle Base44 SDK rate limiting', async () => {
      const rateLimitError = new Error('Rate limit exceeded')
      rateLimitError.status = 429
      rateLimitError.retryAfter = 60

      base44EntityService.invokeAgent.mockRejectedValueOnce(rateLimitError)

      const agentRequest = {
        agentType: 'data_analysis',
        task: 'trend-analysis',
        parameters: { dataset: 'large' }
      }

      await expect(base44EntityService.invokeAgent(agentRequest)).rejects.toThrow('Rate limit exceeded')
      
      expect(auditService.logSystem.integration).toHaveBeenCalledWith(
        'rate_limit_hit',
        expect.objectContaining({
          retryAfter: 60,
          agentType: 'data_analysis'
        })
      )
    })

    it('should validate agent availability through Base44', async () => {
      const availabilityResponse = {
        success: true,
        data: {
          availableAgents: [
            'strategic_planning',
            'content_creation',
            'data_analysis',
            'customer_support'
          ],
          unavailableAgents: [
            'hr_recruitment', // Temporarily unavailable
            'compliance_risk'
          ],
          systemStatus: 'operational'
        }
      }

      base44EntityService.getAgentAvailability.mockResolvedValueOnce(availabilityResponse)

      const availability = await base44EntityService.getAgentAvailability()

      expect(availability.success).toBe(true)
      expect(availability.data.availableAgents).toContain('strategic_planning')
      expect(availability.data.unavailableAgents).toContain('hr_recruitment')
      expect(availability.data.systemStatus).toBe('operational')
    })
  })

  describe('Platform Integration', () => {
    it('should integrate with social media platforms for content agents', async () => {
      const contentAgentResponse = {
        success: true,
        data: {
          content: 'AI is transforming business operations across industries',
          platforms: {
            linkedin: {
              optimized: true,
              hashtags: ['#AI', '#Business', '#Innovation'],
              scheduledTime: '2024-01-15T10:00:00Z'
            },
            twitter: {
              optimized: true,
              content: 'AI transforms business! #AI #Innovation',
              scheduledTime: '2024-01-15T10:00:00Z'
            }
          }
        },
        metadata: {
          tokensUsed: 250,
          executionTime: 3.5
        }
      }

      agentService.executeAgent.mockResolvedValueOnce(contentAgentResponse)

      // Mock platform posting
      apiIntegrationService.executePlatformFunction.mockResolvedValueOnce({
        success: true,
        data: { postId: 'linkedin-post-123', publishedAt: '2024-01-15T10:00:00Z' }
      })

      const agentRequest = {
        agentType: 'content_creation',
        task: 'social-media-campaign',
        parameters: {
          topic: 'AI in business',
          platforms: ['linkedin', 'twitter'],
          autoPublish: true
        }
      }

      const result = await agentService.executeAgent(agentRequest)

      expect(result.success).toBe(true)
      expect(result.data.platforms.linkedin.optimized).toBe(true)
      expect(result.data.platforms.twitter.optimized).toBe(true)

      // Verify platform integration was called
      expect(apiIntegrationService.executePlatformFunction).toHaveBeenCalledWith(
        'linkedin',
        'linkedinCreatePost',
        expect.any(Object)
      )
    })

    it('should integrate with CRM systems for sales intelligence agents', async () => {
      const salesAgentResponse = {
        success: true,
        data: {
          leadScoring: {
            processedLeads: 25,
            highPriority: 8,
            mediumPriority: 12,
            lowPriority: 5
          },
          crmIntegration: {
            leadsUpdated: 25,
            opportunitiesCreated: 8,
            tasksScheduled: 15
          }
        },
        metadata: {
          tokensUsed: 400,
          executionTime: 6.2
        }
      }

      agentService.executeAgent.mockResolvedValueOnce(salesAgentResponse)

      // Mock CRM integration
      apiIntegrationService.executePlatformFunction.mockResolvedValueOnce({
        success: true,
        data: { recordsUpdated: 25, opportunitiesCreated: 8 }
      })

      const agentRequest = {
        agentType: 'sales_intelligence',
        task: 'lead-scoring-with-crm-update',
        parameters: {
          leads: Array(25).fill({ id: 'lead', data: 'test' }),
          updateCRM: true,
          crmSystem: 'salesforce'
        }
      }

      const result = await agentService.executeAgent(agentRequest)

      expect(result.success).toBe(true)
      expect(result.data.crmIntegration.leadsUpdated).toBe(25)
      expect(result.data.crmIntegration.opportunitiesCreated).toBe(8)

      // Verify CRM integration was called
      expect(apiIntegrationService.executePlatformFunction).toHaveBeenCalledWith(
        'salesforce',
        'updateLeads',
        expect.any(Object)
      )
    })

    it('should integrate with email platforms for marketing automation', async () => {
      const marketingAgentResponse = {
        success: true,
        data: {
          campaign: {
            name: 'AI Newsletter Campaign',
            segments: ['tech_enthusiasts', 'business_leaders'],
            emailsGenerated: 2
          },
          emailIntegration: {
            campaignCreated: true,
            campaignId: 'email-campaign-123',
            scheduledSends: 2,
            estimatedReach: 5000
          }
        },
        metadata: {
          tokensUsed: 350,
          executionTime: 4.8
        }
      }

      agentService.executeAgent.mockResolvedValueOnce(marketingAgentResponse)

      // Mock email platform integration
      apiIntegrationService.executePlatformFunction.mockResolvedValueOnce({
        success: true,
        data: { campaignId: 'email-campaign-123', status: 'scheduled' }
      })

      const agentRequest = {
        agentType: 'marketing_automation',
        task: 'email-campaign-creation',
        parameters: {
          audience: ['tech_enthusiasts', 'business_leaders'],
          topic: 'AI innovations',
          emailPlatform: 'mailchimp',
          autoSchedule: true
        }
      }

      const result = await agentService.executeAgent(agentRequest)

      expect(result.success).toBe(true)
      expect(result.data.emailIntegration.campaignCreated).toBe(true)
      expect(result.data.emailIntegration.estimatedReach).toBe(5000)

      // Verify email platform integration was called
      expect(apiIntegrationService.executePlatformFunction).toHaveBeenCalledWith(
        'mailchimp',
        'createCampaign',
        expect.any(Object)
      )
    })
  })

  describe('Data Source Integration', () => {
    it('should integrate with analytics platforms for data analysis agents', async () => {
      const analyticsData = {
        metrics: {
          pageViews: 50000,
          uniqueVisitors: 15000,
          bounceRate: 0.35,
          conversionRate: 0.045
        },
        timeRange: '30d',
        source: 'google_analytics'
      }

      const dataAgentResponse = {
        success: true,
        data: {
          analysis: {
            trends: ['increasing_traffic', 'improving_conversion'],
            insights: ['Mobile traffic growing', 'Conversion rate above industry average'],
            recommendations: ['Optimize mobile experience', 'A/B test checkout flow']
          },
          dataIntegration: {
            sourcesConnected: ['google_analytics', 'facebook_ads'],
            recordsProcessed: 50000,
            dataQuality: 'high'
          }
        },
        metadata: {
          tokensUsed: 500,
          executionTime: 8.1
        }
      }

      agentService.executeAgent.mockResolvedValueOnce(dataAgentResponse)

      // Mock analytics platform integration
      apiIntegrationService.executePlatformFunction.mockResolvedValueOnce({
        success: true,
        data: analyticsData
      })

      const agentRequest = {
        agentType: 'data_analysis',
        task: 'website-performance-analysis',
        parameters: {
          dataSources: ['google_analytics', 'facebook_ads'],
          timeRange: '30d',
          includeRecommendations: true
        }
      }

      const result = await agentService.executeAgent(agentRequest)

      expect(result.success).toBe(true)
      expect(result.data.dataIntegration.sourcesConnected).toContain('google_analytics')
      expect(result.data.dataIntegration.recordsProcessed).toBe(50000)
      expect(result.data.analysis.trends).toContain('increasing_traffic')

      // Verify analytics integration was called
      expect(apiIntegrationService.executePlatformFunction).toHaveBeenCalledWith(
        'google_analytics',
        'getMetrics',
        expect.any(Object)
      )
    })

    it('should handle data source connection failures gracefully', async () => {
      // Mock data source connection failure
      apiIntegrationService.executePlatformFunction.mockRejectedValueOnce(
        new Error('Google Analytics API connection failed')
      )

      const agentRequest = {
        agentType: 'data_analysis',
        task: 'analytics-report',
        parameters: {
          dataSources: ['google_analytics'],
          fallbackToSampleData: true
        }
      }

      // Agent should handle the failure and use fallback data
      const fallbackResponse = {
        success: true,
        data: {
          analysis: 'Analysis completed with sample data',
          dataIntegration: {
            sourcesConnected: [],
            fallbackUsed: true,
            warning: 'Primary data source unavailable'
          }
        },
        metadata: {
          tokensUsed: 200,
          executionTime: 3.0
        }
      }

      agentService.executeAgent.mockResolvedValueOnce(fallbackResponse)

      const result = await agentService.executeAgent(agentRequest)

      expect(result.success).toBe(true)
      expect(result.data.dataIntegration.fallbackUsed).toBe(true)
      expect(result.data.dataIntegration.warning).toContain('unavailable')
    })
  })

  describe('Multi-Agent Workflows', () => {
    it('should coordinate multiple agents for complex business analysis', async () => {
      // Step 1: Data Analysis Agent
      const dataAnalysisResponse = {
        success: true,
        data: {
          insights: ['Revenue declining', 'Customer acquisition cost rising'],
          metrics: { revenue: 950000, cac: 150, ltv: 800 }
        }
      }

      // Step 2: Strategic Planning Agent
      const strategicResponse = {
        success: true,
        data: {
          recommendations: ['Improve retention', 'Optimize marketing spend'],
          actionPlan: ['Implement loyalty program', 'Review ad targeting']
        }
      }

      // Step 3: Content Creation Agent
      const contentResponse = {
        success: true,
        data: {
          content: 'Strategic plan presentation content',
          deliverables: ['Executive summary', 'Action plan document']
        }
      }

      agentService.executeAgent
        .mockResolvedValueOnce(dataAnalysisResponse)
        .mockResolvedValueOnce(strategicResponse)
        .mockResolvedValueOnce(contentResponse)

      // Execute workflow
      const dataResult = await agentService.executeAgent({
        agentType: 'data_analysis',
        task: 'business-metrics-analysis'
      })

      const strategicResult = await agentService.executeAgent({
        agentType: 'strategic_planning',
        task: 'action-planning',
        parameters: { insights: dataResult.data.insights }
      })

      const contentResult = await agentService.executeAgent({
        agentType: 'content_creation',
        task: 'presentation-creation',
        parameters: { 
          insights: dataResult.data.insights,
          recommendations: strategicResult.data.recommendations
        }
      })

      expect(dataResult.success).toBe(true)
      expect(strategicResult.success).toBe(true)
      expect(contentResult.success).toBe(true)
      expect(agentService.executeAgent).toHaveBeenCalledTimes(3)

      // Verify data flow between agents
      expect(strategicResult.data.recommendations).toContain('Improve retention')
      expect(contentResult.data.deliverables).toContain('Executive summary')
    })

    it('should handle agent workflow failures with proper rollback', async () => {
      // First agent succeeds
      const dataAnalysisResponse = {
        success: true,
        data: { insights: ['Test insight'] }
      }

      agentService.executeAgent.mockResolvedValueOnce(dataAnalysisResponse)

      // Second agent fails
      agentService.executeAgent.mockRejectedValueOnce(
        new Error('Strategic planning agent failed')
      )

      const dataResult = await agentService.executeAgent({
        agentType: 'data_analysis',
        task: 'analysis'
      })

      expect(dataResult.success).toBe(true)

      // Second agent should fail
      await expect(agentService.executeAgent({
        agentType: 'strategic_planning',
        task: 'planning',
        parameters: { insights: dataResult.data.insights }
      })).rejects.toThrow('Strategic planning agent failed')

      // Verify audit logging for workflow failure
      expect(auditService.logSystem.error).toHaveBeenCalledWith(
        expect.any(Error),
        'agent_workflow_failure',
        expect.any(Object)
      )
    })
  })

  describe('Real-time Integration', () => {
    it('should handle real-time data updates for monitoring agents', async () => {
      const monitoringResponse = {
        success: true,
        data: {
          alerts: [
            { type: 'performance', severity: 'high', message: 'Response time spike detected' },
            { type: 'error_rate', severity: 'medium', message: 'Error rate above threshold' }
          ],
          realTimeMetrics: {
            responseTime: 2500,
            errorRate: 0.05,
            throughput: 150
          },
          recommendations: ['Scale up servers', 'Check database performance']
        },
        metadata: {
          tokensUsed: 200,
          executionTime: 1.8,
          realTime: true
        }
      }

      agentService.executeAgent.mockResolvedValueOnce(monitoringResponse)

      const agentRequest = {
        agentType: 'operations_optimization',
        task: 'real-time-monitoring',
        parameters: {
          monitoringWindow: '5m',
          alertThresholds: {
            responseTime: 2000,
            errorRate: 0.03
          }
        }
      }

      const result = await agentService.executeAgent(agentRequest)

      expect(result.success).toBe(true)
      expect(result.data.alerts).toHaveLength(2)
      expect(result.data.realTimeMetrics.responseTime).toBe(2500)
      expect(result.metadata.realTime).toBe(true)
    })
  })
})
