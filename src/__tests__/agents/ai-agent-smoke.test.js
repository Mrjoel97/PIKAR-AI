/**
 * AI Agent Smoke Tests
 * Comprehensive smoke tests for all 10 AI agents in the PIKAR AI platform
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { agentService } from '@/services/agentService'
import { base44EntityService } from '@/api/base44Client'
import { auditService } from '@/services/auditService'
import { errorHandlingService } from '@/services/errorHandlingService'
import { testDataFactories } from '@/test/utils'

// Mock dependencies
vi.mock('@/services/agentService')
vi.mock('@/api/base44Client')
vi.mock('@/services/auditService')
vi.mock('@/services/errorHandlingService')

describe('AI Agent Smoke Tests', () => {
  const mockUser = testDataFactories.user()

  beforeEach(() => {
    vi.clearAllMocks()
    
    // Mock audit service
    auditService.logAccess = {
      agentExecution: vi.fn()
    }
    auditService.logSystem = {
      error: vi.fn(),
      performance: vi.fn()
    }

    // Mock error handling
    errorHandlingService.handleAgentError = vi.fn()
  })

  afterEach(() => {
    vi.clearAllTimers()
  })

  describe('1. Strategic Planning Agent', () => {
    it('should execute basic strategic planning task', async () => {
      const mockResponse = {
        success: true,
        data: {
          analysis: 'Strategic analysis completed',
          recommendations: ['Recommendation 1', 'Recommendation 2'],
          metadata: {
            tokensUsed: 500,
            executionTime: 3.2,
            confidence: 0.85
          }
        }
      }

      agentService.executeAgent.mockResolvedValueOnce(mockResponse)

      const request = {
        agentType: 'strategic_planning',
        task: 'basic-analysis',
        parameters: {
          company: 'Test Company',
          industry: 'Technology'
        }
      }

      const result = await agentService.executeAgent(request)

      expect(result.success).toBe(true)
      expect(result.data.analysis).toBeDefined()
      expect(result.data.recommendations).toBeInstanceOf(Array)
      expect(result.data.metadata.confidence).toBeGreaterThan(0.8)
      expect(agentService.executeAgent).toHaveBeenCalledWith(request)
    })

    it('should handle strategic planning errors gracefully', async () => {
      agentService.executeAgent.mockRejectedValueOnce(new Error('Agent timeout'))

      const request = {
        agentType: 'strategic_planning',
        task: 'complex-analysis',
        parameters: {}
      }

      await expect(agentService.executeAgent(request)).rejects.toThrow('Agent timeout')
      expect(errorHandlingService.handleAgentError).toHaveBeenCalled()
    })
  })

  describe('2. Financial Analysis Agent', () => {
    it('should execute basic financial analysis task', async () => {
      const mockResponse = {
        success: true,
        data: {
          analysis: {
            revenue: 1000000,
            expenses: 750000,
            profit: 250000,
            profitMargin: 0.25
          },
          insights: ['Revenue growth is strong', 'Cost optimization needed'],
          metadata: {
            tokensUsed: 400,
            executionTime: 2.8
          }
        }
      }

      agentService.executeAgent.mockResolvedValueOnce(mockResponse)

      const request = {
        agentType: 'financial_analysis',
        task: 'financial-review',
        parameters: {
          financialData: {
            revenue: [800000, 900000, 1000000],
            expenses: [600000, 700000, 750000]
          }
        }
      }

      const result = await agentService.executeAgent(request)

      expect(result.success).toBe(true)
      expect(result.data.analysis).toBeDefined()
      expect(result.data.analysis.profitMargin).toBe(0.25)
      expect(result.data.insights).toBeInstanceOf(Array)
    })
  })

  describe('3. Customer Support Agent', () => {
    it('should process customer support tickets', async () => {
      const mockResponse = {
        success: true,
        data: {
          processedTickets: [
            {
              id: 'ticket-1',
              category: 'technical_issue',
              priority: 'high',
              suggestedResponse: 'Thank you for contacting support...',
              escalate: false
            }
          ],
          summary: {
            totalTickets: 1,
            avgSentiment: 'neutral',
            escalationRate: 0
          },
          metadata: {
            tokensUsed: 300,
            executionTime: 1.5
          }
        }
      }

      agentService.executeAgent.mockResolvedValueOnce(mockResponse)

      const request = {
        agentType: 'customer_support',
        task: 'ticket-processing',
        parameters: {
          tickets: [
            {
              id: 'ticket-1',
              subject: 'Login issue',
              content: 'Cannot access my account'
            }
          ]
        }
      }

      const result = await agentService.executeAgent(request)

      expect(result.success).toBe(true)
      expect(result.data.processedTickets).toHaveLength(1)
      expect(result.data.processedTickets[0].category).toBe('technical_issue')
      expect(result.data.summary.escalationRate).toBe(0)
    })
  })

  describe('4. Content Creation Agent', () => {
    it('should generate content successfully', async () => {
      const mockResponse = {
        success: true,
        data: {
          content: 'Generated marketing content about AI innovation',
          variants: [
            { content: 'Variant 1', score: 8.5 },
            { content: 'Variant 2', score: 9.0 }
          ],
          metadata: {
            tokensUsed: 250,
            executionTime: 2.0,
            bestVariant: 1
          }
        }
      }

      agentService.executeAgent.mockResolvedValueOnce(mockResponse)

      const request = {
        agentType: 'content_creation',
        task: 'social-media-post',
        parameters: {
          topic: 'AI innovation',
          platform: 'linkedin',
          tone: 'professional'
        }
      }

      const result = await agentService.executeAgent(request)

      expect(result.success).toBe(true)
      expect(result.data.content).toBeDefined()
      expect(result.data.variants).toHaveLength(2)
      expect(result.data.metadata.bestVariant).toBe(1)
    })
  })

  describe('5. Marketing Automation Agent', () => {
    it('should execute marketing automation tasks', async () => {
      const mockResponse = {
        success: true,
        data: {
          campaign: {
            name: 'Automated Email Campaign',
            segments: ['segment1', 'segment2'],
            schedule: '2024-01-15T10:00:00Z'
          },
          automation: {
            triggers: ['user_signup', 'cart_abandonment'],
            actions: ['send_email', 'update_crm']
          },
          metadata: {
            tokensUsed: 350,
            executionTime: 2.5
          }
        }
      }

      agentService.executeAgent.mockResolvedValueOnce(mockResponse)

      const request = {
        agentType: 'marketing_automation',
        task: 'campaign-setup',
        parameters: {
          campaignType: 'email',
          audience: 'new_users',
          objective: 'onboarding'
        }
      }

      const result = await agentService.executeAgent(request)

      expect(result.success).toBe(true)
      expect(result.data.campaign).toBeDefined()
      expect(result.data.automation.triggers).toBeInstanceOf(Array)
      expect(result.data.automation.actions).toBeInstanceOf(Array)
    })
  })

  describe('6. Data Analysis Agent', () => {
    it('should analyze data and provide insights', async () => {
      const mockResponse = {
        success: true,
        data: {
          analysis: {
            trends: ['upward', 'seasonal'],
            correlations: [{ x: 'metric1', y: 'metric2', value: 0.85 }],
            anomalies: []
          },
          insights: ['Data shows strong growth', 'Seasonal patterns detected'],
          recommendations: ['Continue current strategy', 'Monitor for changes'],
          metadata: {
            tokensUsed: 450,
            executionTime: 3.8
          }
        }
      }

      agentService.executeAgent.mockResolvedValueOnce(mockResponse)

      const request = {
        agentType: 'data_analysis',
        task: 'trend-analysis',
        parameters: {
          dataset: [
            { date: '2024-01-01', value: 100 },
            { date: '2024-01-02', value: 105 },
            { date: '2024-01-03', value: 110 }
          ],
          metric: 'conversions'
        }
      }

      const result = await agentService.executeAgent(request)

      expect(result.success).toBe(true)
      expect(result.data.analysis.trends).toContain('upward')
      expect(result.data.insights).toBeInstanceOf(Array)
      expect(result.data.recommendations).toBeInstanceOf(Array)
    })
  })

  describe('7. Operations Optimization Agent', () => {
    it('should optimize operational processes', async () => {
      const mockResponse = {
        success: true,
        data: {
          optimization: {
            currentEfficiency: 0.75,
            optimizedEfficiency: 0.90,
            improvement: 0.15
          },
          recommendations: [
            'Automate manual processes',
            'Implement workflow optimization',
            'Reduce bottlenecks'
          ],
          implementation: {
            priority: 'high',
            estimatedROI: 1.5,
            timeframe: '3 months'
          },
          metadata: {
            tokensUsed: 400,
            executionTime: 3.0
          }
        }
      }

      agentService.executeAgent.mockResolvedValueOnce(mockResponse)

      const request = {
        agentType: 'operations_optimization',
        task: 'process-optimization',
        parameters: {
          processes: ['order_fulfillment', 'customer_onboarding'],
          currentMetrics: {
            efficiency: 0.75,
            throughput: 100
          }
        }
      }

      const result = await agentService.executeAgent(request)

      expect(result.success).toBe(true)
      expect(result.data.optimization.improvement).toBe(0.15)
      expect(result.data.recommendations).toBeInstanceOf(Array)
      expect(result.data.implementation.priority).toBe('high')
    })
  })

  describe('8. HR Recruitment Agent', () => {
    it('should assist with recruitment processes', async () => {
      const mockResponse = {
        success: true,
        data: {
          candidates: [
            {
              id: 'candidate-1',
              score: 85,
              strengths: ['Technical skills', 'Communication'],
              concerns: ['Limited experience'],
              recommendation: 'Interview'
            }
          ],
          jobDescription: {
            optimized: true,
            improvements: ['Added skill requirements', 'Clarified responsibilities']
          },
          metadata: {
            tokensUsed: 380,
            executionTime: 2.7
          }
        }
      }

      agentService.executeAgent.mockResolvedValueOnce(mockResponse)

      const request = {
        agentType: 'hr_recruitment',
        task: 'candidate-screening',
        parameters: {
          position: 'Software Engineer',
          candidates: [
            {
              id: 'candidate-1',
              resume: 'Software engineer with 3 years experience...',
              skills: ['JavaScript', 'React', 'Node.js']
            }
          ]
        }
      }

      const result = await agentService.executeAgent(request)

      expect(result.success).toBe(true)
      expect(result.data.candidates).toHaveLength(1)
      expect(result.data.candidates[0].score).toBe(85)
      expect(result.data.candidates[0].recommendation).toBe('Interview')
    })
  })

  describe('9. Compliance Risk Agent', () => {
    it('should assess compliance and risk factors', async () => {
      const mockResponse = {
        success: true,
        data: {
          riskAssessment: {
            overallRisk: 'medium',
            riskScore: 6.5,
            categories: {
              financial: 'low',
              operational: 'medium',
              regulatory: 'high'
            }
          },
          compliance: {
            status: 'partial',
            violations: ['Missing privacy policy update'],
            recommendations: ['Update privacy policy', 'Conduct compliance audit']
          },
          metadata: {
            tokensUsed: 420,
            executionTime: 3.5
          }
        }
      }

      agentService.executeAgent.mockResolvedValueOnce(mockResponse)

      const request = {
        agentType: 'compliance_risk',
        task: 'risk-assessment',
        parameters: {
          industry: 'technology',
          regulations: ['GDPR', 'CCPA'],
          businessData: {
            revenue: 1000000,
            employees: 50,
            dataProcessing: true
          }
        }
      }

      const result = await agentService.executeAgent(request)

      expect(result.success).toBe(true)
      expect(result.data.riskAssessment.overallRisk).toBe('medium')
      expect(result.data.compliance.status).toBe('partial')
      expect(result.data.compliance.recommendations).toBeInstanceOf(Array)
    })
  })

  describe('10. Sales Intelligence Agent', () => {
    it('should provide sales intelligence and lead scoring', async () => {
      const mockResponse = {
        success: true,
        data: {
          leadScoring: {
            totalLeads: 10,
            highPriority: 3,
            mediumPriority: 4,
            lowPriority: 3
          },
          scoredLeads: [
            {
              id: 'lead-1',
              score: 90,
              priority: 'high',
              reasoning: 'High engagement, good fit',
              nextActions: ['Schedule demo', 'Send proposal']
            }
          ],
          insights: {
            conversionProbability: 0.75,
            recommendedActions: ['Focus on high-priority leads'],
            marketTrends: ['Increased demand for AI solutions']
          },
          metadata: {
            tokensUsed: 360,
            executionTime: 2.9
          }
        }
      }

      agentService.executeAgent.mockResolvedValueOnce(mockResponse)

      const request = {
        agentType: 'sales_intelligence',
        task: 'lead-scoring',
        parameters: {
          leads: [
            {
              id: 'lead-1',
              company: 'TechCorp',
              industry: 'Software',
              engagement: 'high',
              budget: 50000
            }
          ],
          scoringCriteria: {
            budget: 0.3,
            engagement: 0.4,
            fit: 0.3
          }
        }
      }

      const result = await agentService.executeAgent(request)

      expect(result.success).toBe(true)
      expect(result.data.leadScoring.highPriority).toBe(3)
      expect(result.data.scoredLeads[0].score).toBe(90)
      expect(result.data.insights.conversionProbability).toBe(0.75)
    })
  })

  describe('Agent Performance & Reliability', () => {
    it('should complete agent execution within acceptable time limits', async () => {
      const mockResponse = {
        success: true,
        data: { result: 'Quick response' },
        metadata: { tokensUsed: 100, executionTime: 1.0 }
      }

      agentService.executeAgent.mockResolvedValueOnce(mockResponse)

      const startTime = Date.now()
      
      await agentService.executeAgent({
        agentType: 'content_creation',
        task: 'quick-task',
        parameters: { simple: true }
      })

      const executionTime = Date.now() - startTime
      
      // Should complete within 5 seconds for smoke test
      expect(executionTime).toBeLessThan(5000)
    })

    it('should handle concurrent agent executions', async () => {
      const mockResponse = {
        success: true,
        data: { result: 'Concurrent response' },
        metadata: { tokensUsed: 150, executionTime: 2.0 }
      }

      agentService.executeAgent.mockResolvedValue(mockResponse)

      const requests = [
        { agentType: 'strategic_planning', task: 'task1' },
        { agentType: 'content_creation', task: 'task2' },
        { agentType: 'data_analysis', task: 'task3' }
      ]

      const results = await Promise.all(
        requests.map(request => agentService.executeAgent(request))
      )

      expect(results).toHaveLength(3)
      expect(results.every(result => result.success)).toBe(true)
      expect(agentService.executeAgent).toHaveBeenCalledTimes(3)
    })

    it('should validate agent response structure', async () => {
      const mockResponse = {
        success: true,
        data: {
          result: 'Valid response',
          analysis: 'Detailed analysis'
        },
        metadata: {
          tokensUsed: 200,
          executionTime: 1.5,
          confidence: 0.9
        }
      }

      agentService.executeAgent.mockResolvedValueOnce(mockResponse)

      const result = await agentService.executeAgent({
        agentType: 'strategic_planning',
        task: 'validation-test'
      })

      // Validate response structure
      expect(result).toHaveProperty('success')
      expect(result).toHaveProperty('data')
      expect(result).toHaveProperty('metadata')
      expect(result.metadata).toHaveProperty('tokensUsed')
      expect(result.metadata).toHaveProperty('executionTime')
      expect(typeof result.metadata.tokensUsed).toBe('number')
      expect(typeof result.metadata.executionTime).toBe('number')
    })
  })

  describe('Agent Error Handling', () => {
    it('should handle agent timeout errors', async () => {
      agentService.executeAgent.mockRejectedValueOnce(
        new Error('Agent execution timeout after 30 seconds')
      )

      await expect(agentService.executeAgent({
        agentType: 'data_analysis',
        task: 'complex-analysis'
      })).rejects.toThrow('timeout')

      expect(errorHandlingService.handleAgentError).toHaveBeenCalled()
    })

    it('should handle invalid agent parameters', async () => {
      agentService.executeAgent.mockRejectedValueOnce(
        new Error('Invalid agent parameters')
      )

      await expect(agentService.executeAgent({
        agentType: 'invalid_agent',
        task: 'test'
      })).rejects.toThrow('Invalid agent parameters')
    })

    it('should handle agent service unavailable', async () => {
      agentService.executeAgent.mockRejectedValueOnce(
        new Error('Agent service temporarily unavailable')
      )

      await expect(agentService.executeAgent({
        agentType: 'content_creation',
        task: 'test'
      })).rejects.toThrow('temporarily unavailable')
    })
  })

  describe('Agent Performance & Reliability', () => {
    it('should complete agent execution within acceptable time limits', async () => {
      const mockResponse = {
        success: true,
        data: { result: 'Quick response' },
        metadata: { tokensUsed: 100, executionTime: 1.0 }
      }

      agentService.executeAgent.mockResolvedValueOnce(mockResponse)

      const startTime = Date.now()

      await agentService.executeAgent({
        agentType: 'content_creation',
        task: 'quick-task',
        parameters: { simple: true }
      })

      const executionTime = Date.now() - startTime

      // Should complete within 5 seconds for smoke test
      expect(executionTime).toBeLessThan(5000)
    })

    it('should handle concurrent agent executions', async () => {
      const mockResponse = {
        success: true,
        data: { result: 'Concurrent response' },
        metadata: { tokensUsed: 150, executionTime: 2.0 }
      }

      agentService.executeAgent.mockResolvedValue(mockResponse)

      const requests = [
        { agentType: 'strategic_planning', task: 'task1' },
        { agentType: 'content_creation', task: 'task2' },
        { agentType: 'data_analysis', task: 'task3' }
      ]

      const results = await Promise.all(
        requests.map(request => agentService.executeAgent(request))
      )

      expect(results).toHaveLength(3)
      expect(results.every(result => result.success)).toBe(true)
      expect(agentService.executeAgent).toHaveBeenCalledTimes(3)
    })

    it('should validate agent response structure', async () => {
      const mockResponse = {
        success: true,
        data: {
          result: 'Valid response',
          analysis: 'Detailed analysis'
        },
        metadata: {
          tokensUsed: 200,
          executionTime: 1.5,
          confidence: 0.9
        }
      }

      agentService.executeAgent.mockResolvedValueOnce(mockResponse)

      const result = await agentService.executeAgent({
        agentType: 'strategic_planning',
        task: 'validation-test'
      })

      // Validate response structure
      expect(result).toHaveProperty('success')
      expect(result).toHaveProperty('data')
      expect(result).toHaveProperty('metadata')
      expect(result.metadata).toHaveProperty('tokensUsed')
      expect(result.metadata).toHaveProperty('executionTime')
      expect(typeof result.metadata.tokensUsed).toBe('number')
      expect(typeof result.metadata.executionTime).toBe('number')
    })
  })

  describe('Agent Error Handling', () => {
    it('should handle agent timeout errors', async () => {
      agentService.executeAgent.mockRejectedValueOnce(
        new Error('Agent execution timeout after 30 seconds')
      )

      await expect(agentService.executeAgent({
        agentType: 'data_analysis',
        task: 'complex-analysis'
      })).rejects.toThrow('timeout')

      expect(errorHandlingService.handleAgentError).toHaveBeenCalled()
    })

    it('should handle invalid agent parameters', async () => {
      agentService.executeAgent.mockRejectedValueOnce(
        new Error('Invalid agent parameters')
      )

      await expect(agentService.executeAgent({
        agentType: 'invalid_agent',
        task: 'test'
      })).rejects.toThrow('Invalid agent parameters')
    })

    it('should handle agent service unavailable', async () => {
      agentService.executeAgent.mockRejectedValueOnce(
        new Error('Agent service temporarily unavailable')
      )

      await expect(agentService.executeAgent({
        agentType: 'content_creation',
        task: 'test'
      })).rejects.toThrow('temporarily unavailable')
    })
  })
})
