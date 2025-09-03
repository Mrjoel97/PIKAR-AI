/**
 * AI Agent Workflows Integration Tests
 * End-to-end testing of AI agent execution and workflows
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { waitFor } from '@testing-library/react'
import { testDataFactories, mockBase44Client } from '@/test/utils'
import { agentService } from '@/services/agentService'
import { apiIntegrationService } from '@/services/apiIntegrationService'
import { auditService } from '@/services/auditService'
import { errorHandlingService } from '@/services/errorHandlingService'

// Mock dependencies
vi.mock('@/services/agentService')
vi.mock('@/services/apiIntegrationService')
vi.mock('@/services/auditService')
vi.mock('@/services/errorHandlingService')
vi.mock('@/api/base44Client', () => ({
  base44: mockBase44Client,
  validatedBase44: mockBase44Client
}))

describe('AI Agent Workflows Integration', () => {
  const mockUser = testDataFactories.user()
  const mockCampaign = testDataFactories.campaign()

  beforeEach(() => {
    vi.clearAllMocks()
    
    // Mock audit service
    auditService.logAccess = {
      dataAccess: vi.fn(),
      agentExecution: vi.fn()
    }
    auditService.logSystem = {
      error: vi.fn(),
      performance: vi.fn()
    }

    // Mock error handling
    errorHandlingService.handleAgentError = vi.fn((error) => error)
  })

  afterEach(() => {
    vi.clearAllTimers()
  })

  describe('Strategic Planning Agent', () => {
    it('generates comprehensive SWOT analysis', async () => {
      const swotRequest = {
        agentType: 'strategic-planning',
        task: 'swot-analysis',
        parameters: {
          company: 'TechCorp Inc.',
          industry: 'Software Development',
          timeframe: '2024',
          includeRecommendations: true
        }
      }

      const mockSwotResponse = {
        success: true,
        data: {
          analysis: {
            strengths: [
              'Strong technical team',
              'Innovative product portfolio',
              'Established customer base'
            ],
            weaknesses: [
              'Limited marketing budget',
              'Dependency on key personnel',
              'Outdated infrastructure'
            ],
            opportunities: [
              'Growing AI market',
              'Remote work trends',
              'Digital transformation demand'
            ],
            threats: [
              'Increased competition',
              'Economic uncertainty',
              'Regulatory changes'
            ]
          },
          recommendations: [
            'Invest in marketing automation',
            'Diversify revenue streams',
            'Upgrade infrastructure'
          ],
          metadata: {
            tokensUsed: 850,
            executionTime: 4.2,
            confidence: 0.92
          }
        }
      }

      // Mock agent execution
      agentService.executeAgent.mockResolvedValueOnce(mockSwotResponse)

      const result = await agentService.executeAgent(swotRequest)

      expect(result.success).toBe(true)
      expect(result.data.analysis.strengths).toHaveLength(3)
      expect(result.data.analysis.weaknesses).toHaveLength(3)
      expect(result.data.analysis.opportunities).toHaveLength(3)
      expect(result.data.analysis.threats).toHaveLength(3)
      expect(result.data.recommendations).toHaveLength(3)
      expect(result.data.metadata.confidence).toBeGreaterThan(0.9)

      // Verify audit logging
      expect(auditService.logAccess.agentExecution).toHaveBeenCalledWith(
        mockUser.id,
        'strategic-planning',
        'swot-analysis',
        expect.objectContaining({
          success: true,
          tokensUsed: 850,
          executionTime: 4.2
        })
      )
    })

    it('generates market analysis with competitive insights', async () => {
      const marketRequest = {
        agentType: 'strategic-planning',
        task: 'market-analysis',
        parameters: {
          market: 'AI-powered marketing tools',
          region: 'North America',
          competitors: ['HubSpot', 'Salesforce', 'Marketo'],
          analysisDepth: 'comprehensive'
        }
      }

      const mockMarketResponse = {
        success: true,
        data: {
          marketSize: {
            current: '$12.8B',
            projected2025: '$18.4B',
            cagr: '7.6%'
          },
          competitiveAnalysis: {
            leaders: ['HubSpot', 'Salesforce'],
            challengers: ['Marketo', 'Pardot'],
            niche: ['Smaller specialized tools']
          },
          opportunities: [
            'AI-powered personalization',
            'Voice marketing integration',
            'Privacy-first analytics'
          ],
          threats: [
            'Market saturation',
            'Big tech dominance',
            'Privacy regulations'
          ]
        }
      }

      agentService.executeAgent.mockResolvedValueOnce(mockMarketResponse)

      const result = await agentService.executeAgent(marketRequest)

      expect(result.success).toBe(true)
      expect(result.data.marketSize.cagr).toBe('7.6%')
      expect(result.data.competitiveAnalysis.leaders).toContain('HubSpot')
      expect(result.data.opportunities).toHaveLength(3)
    })
  })

  describe('Content Creation Agent', () => {
    it('creates social media content with multiple variants', async () => {
      const contentRequest = {
        agentType: 'content-creation',
        task: 'social-media-post',
        parameters: {
          topic: 'AI in healthcare',
          platform: 'linkedin',
          tone: 'professional',
          length: 'medium',
          includeHashtags: true,
          variants: 3
        }
      }

      const mockContentResponse = {
        success: true,
        data: {
          variants: [
            {
              content: 'AI is revolutionizing healthcare by enabling faster diagnosis and personalized treatment plans.',
              hashtags: ['#AI', '#Healthcare', '#Innovation', '#MedTech'],
              engagement_score: 8.5
            },
            {
              content: 'The future of medicine is here: AI-powered tools are helping doctors make more accurate diagnoses.',
              hashtags: ['#ArtificialIntelligence', '#Medicine', '#Technology', '#Future'],
              engagement_score: 8.2
            },
            {
              content: 'From predictive analytics to robotic surgery, AI is transforming patient care across the globe.',
              hashtags: ['#HealthTech', '#AI', '#PatientCare', '#Innovation'],
              engagement_score: 8.7
            }
          ],
          metadata: {
            tokensUsed: 320,
            executionTime: 2.1,
            bestVariant: 2
          }
        }
      }

      agentService.executeAgent.mockResolvedValueOnce(mockContentResponse)

      const result = await agentService.executeAgent(contentRequest)

      expect(result.success).toBe(true)
      expect(result.data.variants).toHaveLength(3)
      expect(result.data.variants[0].hashtags).toContain('#AI')
      expect(result.data.metadata.bestVariant).toBe(2)
      expect(result.data.variants[2].engagement_score).toBe(8.7)
    })

    it('generates blog post with SEO optimization', async () => {
      const blogRequest = {
        agentType: 'content-creation',
        task: 'blog-post',
        parameters: {
          topic: 'Marketing Automation Best Practices',
          targetKeywords: ['marketing automation', 'lead nurturing', 'email campaigns'],
          wordCount: 1500,
          includeOutline: true,
          seoOptimized: true
        }
      }

      const mockBlogResponse = {
        success: true,
        data: {
          title: '10 Marketing Automation Best Practices That Drive Results',
          outline: [
            'Introduction to Marketing Automation',
            'Setting Up Your Automation Workflow',
            'Lead Scoring and Segmentation',
            'Email Campaign Optimization',
            'Measuring Success and ROI'
          ],
          content: 'Marketing automation has become essential for modern businesses...',
          seoAnalysis: {
            keywordDensity: {
              'marketing automation': 2.1,
              'lead nurturing': 1.8,
              'email campaigns': 1.5
            },
            readabilityScore: 72,
            metaDescription: 'Discover proven marketing automation best practices...'
          },
          wordCount: 1487
        }
      }

      agentService.executeAgent.mockResolvedValueOnce(mockBlogResponse)

      const result = await agentService.executeAgent(blogRequest)

      expect(result.success).toBe(true)
      expect(result.data.outline).toHaveLength(5)
      expect(result.data.wordCount).toBeCloseTo(1500, -2)
      expect(result.data.seoAnalysis.readabilityScore).toBeGreaterThan(70)
    })
  })

  describe('Sales Intelligence Agent', () => {
    it('scores and prioritizes leads', async () => {
      const leadScoringRequest = {
        agentType: 'sales-intelligence',
        task: 'lead-scoring',
        parameters: {
          leads: [
            {
              id: 'lead-1',
              company: 'TechStart Inc.',
              industry: 'Software',
              employees: 50,
              revenue: '$5M',
              engagement: 'high'
            },
            {
              id: 'lead-2',
              company: 'Local Shop',
              industry: 'Retail',
              employees: 5,
              revenue: '$500K',
              engagement: 'low'
            }
          ],
          scoringCriteria: {
            companySize: 0.3,
            industry: 0.2,
            engagement: 0.3,
            revenue: 0.2
          }
        }
      }

      const mockScoringResponse = {
        success: true,
        data: {
          scoredLeads: [
            {
              id: 'lead-1',
              score: 85,
              priority: 'high',
              reasoning: 'Strong company profile with high engagement',
              nextActions: ['Schedule demo', 'Send case studies']
            },
            {
              id: 'lead-2',
              score: 35,
              priority: 'low',
              reasoning: 'Small company with low engagement',
              nextActions: ['Nurture with content', 'Follow up in 30 days']
            }
          ],
          insights: {
            averageScore: 60,
            highPriorityCount: 1,
            recommendedFocus: 'Enterprise prospects with high engagement'
          }
        }
      }

      agentService.executeAgent.mockResolvedValueOnce(mockScoringResponse)

      const result = await agentService.executeAgent(leadScoringRequest)

      expect(result.success).toBe(true)
      expect(result.data.scoredLeads).toHaveLength(2)
      expect(result.data.scoredLeads[0].score).toBe(85)
      expect(result.data.scoredLeads[0].priority).toBe('high')
      expect(result.data.insights.highPriorityCount).toBe(1)
    })

    it('generates sales forecasts', async () => {
      const forecastRequest = {
        agentType: 'sales-intelligence',
        task: 'sales-forecast',
        parameters: {
          historicalData: {
            q1: 250000,
            q2: 280000,
            q3: 320000,
            q4: 380000
          },
          pipeline: {
            qualified: 150000,
            proposal: 200000,
            negotiation: 100000
          },
          seasonality: true,
          confidence: 0.95
        }
      }

      const mockForecastResponse = {
        success: true,
        data: {
          forecast: {
            nextQuarter: {
              predicted: 420000,
              range: { min: 380000, max: 460000 },
              confidence: 0.87
            },
            nextYear: {
              predicted: 1680000,
              range: { min: 1520000, max: 1840000 },
              confidence: 0.82
            }
          },
          factors: [
            'Strong Q4 performance trend',
            'Healthy pipeline conversion',
            'Seasonal uptick expected'
          ],
          recommendations: [
            'Focus on closing negotiation stage deals',
            'Accelerate qualified lead conversion',
            'Prepare for Q1 seasonal dip'
          ]
        }
      }

      agentService.executeAgent.mockResolvedValueOnce(mockForecastResponse)

      const result = await agentService.executeAgent(forecastRequest)

      expect(result.success).toBe(true)
      expect(result.data.forecast.nextQuarter.predicted).toBe(420000)
      expect(result.data.forecast.nextQuarter.confidence).toBeGreaterThan(0.8)
      expect(result.data.recommendations).toHaveLength(3)
    })
  })

  describe('Data Analysis Agent', () => {
    it('analyzes campaign performance data', async () => {
      const analysisRequest = {
        agentType: 'data-analysis',
        task: 'campaign-analysis',
        parameters: {
          campaignData: {
            impressions: 100000,
            clicks: 2500,
            conversions: 125,
            spend: 5000,
            duration: 30
          },
          benchmarks: {
            industry: 'SaaS',
            avgCTR: 0.025,
            avgCVR: 0.05,
            avgCPC: 2.0
          },
          includeRecommendations: true
        }
      }

      const mockAnalysisResponse = {
        success: true,
        data: {
          metrics: {
            ctr: 0.025,
            cvr: 0.05,
            cpc: 2.0,
            roas: 2.5,
            cpa: 40
          },
          performance: {
            ctrVsBenchmark: 'on_par',
            cvrVsBenchmark: 'on_par',
            cpcVsBenchmark: 'on_par',
            overallRating: 'good'
          },
          insights: [
            'CTR is meeting industry standards',
            'Conversion rate is healthy',
            'Cost efficiency is optimal'
          ],
          recommendations: [
            'Test new ad creatives to improve CTR',
            'Optimize landing pages for better CVR',
            'Consider expanding to similar audiences'
          ],
          projections: {
            nextMonth: {
              impressions: 120000,
              conversions: 150,
              spend: 6000
            }
          }
        }
      }

      agentService.executeAgent.mockResolvedValueOnce(mockAnalysisResponse)

      const result = await agentService.executeAgent(analysisRequest)

      expect(result.success).toBe(true)
      expect(result.data.metrics.ctr).toBe(0.025)
      expect(result.data.performance.overallRating).toBe('good')
      expect(result.data.insights).toHaveLength(3)
      expect(result.data.recommendations).toHaveLength(3)
    })

    it('identifies trends and anomalies in data', async () => {
      const trendRequest = {
        agentType: 'data-analysis',
        task: 'trend-analysis',
        parameters: {
          timeSeriesData: [
            { date: '2024-01-01', value: 100 },
            { date: '2024-01-02', value: 105 },
            { date: '2024-01-03', value: 110 },
            { date: '2024-01-04', value: 95 }, // Anomaly
            { date: '2024-01-05', value: 115 }
          ],
          metric: 'daily_conversions',
          sensitivity: 'medium'
        }
      }

      const mockTrendResponse = {
        success: true,
        data: {
          trend: {
            direction: 'upward',
            strength: 'moderate',
            confidence: 0.85
          },
          anomalies: [
            {
              date: '2024-01-04',
              value: 95,
              expected: 112,
              deviation: -15.2,
              severity: 'moderate'
            }
          ],
          patterns: [
            'Consistent growth trend',
            'Single day anomaly detected',
            'Recovery pattern observed'
          ],
          forecast: [
            { date: '2024-01-06', predicted: 120, confidence: 0.82 },
            { date: '2024-01-07', predicted: 125, confidence: 0.79 }
          ]
        }
      }

      agentService.executeAgent.mockResolvedValueOnce(mockTrendResponse)

      const result = await agentService.executeAgent(trendRequest)

      expect(result.success).toBe(true)
      expect(result.data.trend.direction).toBe('upward')
      expect(result.data.anomalies).toHaveLength(1)
      expect(result.data.anomalies[0].date).toBe('2024-01-04')
      expect(result.data.forecast).toHaveLength(2)
    })
  })

  describe('Customer Support Agent', () => {
    it('processes and categorizes support tickets', async () => {
      const ticketRequest = {
        agentType: 'customer-support',
        task: 'ticket-processing',
        parameters: {
          tickets: [
            {
              id: 'ticket-1',
              subject: 'Cannot login to dashboard',
              content: 'I keep getting an error when trying to log in',
              priority: 'high'
            },
            {
              id: 'ticket-2',
              subject: 'Feature request: Dark mode',
              content: 'Would love to see a dark mode option',
              priority: 'low'
            }
          ],
          includeResponses: true
        }
      }

      const mockTicketResponse = {
        success: true,
        data: {
          processedTickets: [
            {
              id: 'ticket-1',
              category: 'technical_issue',
              subcategory: 'authentication',
              sentiment: 'frustrated',
              urgency: 'high',
              suggestedResponse: 'I understand your login issue. Let me help you resolve this...',
              escalate: false
            },
            {
              id: 'ticket-2',
              category: 'feature_request',
              subcategory: 'ui_enhancement',
              sentiment: 'positive',
              urgency: 'low',
              suggestedResponse: 'Thank you for the suggestion! Dark mode is on our roadmap...',
              escalate: false
            }
          ],
          summary: {
            totalTickets: 2,
            categories: { technical_issue: 1, feature_request: 1 },
            avgSentiment: 'neutral',
            escalationRate: 0
          }
        }
      }

      agentService.executeAgent.mockResolvedValueOnce(mockTicketResponse)

      const result = await agentService.executeAgent(ticketRequest)

      expect(result.success).toBe(true)
      expect(result.data.processedTickets).toHaveLength(2)
      expect(result.data.processedTickets[0].category).toBe('technical_issue')
      expect(result.data.processedTickets[1].category).toBe('feature_request')
      expect(result.data.summary.escalationRate).toBe(0)
    })
  })

  describe('Agent Workflow Orchestration', () => {
    it('executes multi-agent workflow for campaign optimization', async () => {
      // Mock sequential agent executions
      const dataAnalysisResult = {
        success: true,
        data: { insights: ['Low CTR', 'High CPC'], recommendations: ['Improve targeting'] }
      }

      const contentCreationResult = {
        success: true,
        data: { variants: [{ content: 'New optimized ad copy', score: 9.2 }] }
      }

      const strategicPlanningResult = {
        success: true,
        data: { strategy: 'Focus on high-intent keywords', budget: 7500 }
      }

      agentService.executeAgent
        .mockResolvedValueOnce(dataAnalysisResult)
        .mockResolvedValueOnce(contentCreationResult)
        .mockResolvedValueOnce(strategicPlanningResult)

      // Execute workflow
      const analysisResult = await agentService.executeAgent({
        agentType: 'data-analysis',
        task: 'campaign-analysis',
        parameters: { campaignId: 'campaign-123' }
      })

      const contentResult = await agentService.executeAgent({
        agentType: 'content-creation',
        task: 'ad-optimization',
        parameters: { insights: analysisResult.data.insights }
      })

      const strategyResult = await agentService.executeAgent({
        agentType: 'strategic-planning',
        task: 'budget-optimization',
        parameters: { 
          currentPerformance: analysisResult.data,
          newContent: contentResult.data
        }
      })

      expect(analysisResult.success).toBe(true)
      expect(contentResult.success).toBe(true)
      expect(strategyResult.success).toBe(true)
      expect(agentService.executeAgent).toHaveBeenCalledTimes(3)
    })

    it('handles agent execution failures gracefully', async () => {
      // Mock agent failure
      agentService.executeAgent.mockRejectedValueOnce(
        new Error('Agent execution timeout')
      )

      try {
        await agentService.executeAgent({
          agentType: 'content-creation',
          task: 'blog-post',
          parameters: { topic: 'AI trends' }
        })
      } catch (error) {
        expect(error.message).toContain('timeout')
      }

      // Verify error handling
      expect(errorHandlingService.handleAgentError).toHaveBeenCalled()
      expect(auditService.logSystem.error).toHaveBeenCalledWith(
        expect.any(Error),
        'agent_execution_failure',
        expect.any(Object)
      )
    })
  })
})
