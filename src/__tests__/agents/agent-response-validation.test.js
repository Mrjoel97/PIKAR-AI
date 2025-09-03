/**
 * Agent Response Validation Tests
 * Tests for validating AI agent response formats and data integrity
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { agentResponseValidator } from '@/services/agentResponseValidator'
import { AgentSchema } from '@/lib/validation/schemas'
import { testDataFactories } from '@/test/utils'

// Mock dependencies
vi.mock('@/services/auditService')

describe('Agent Response Validation Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Response Structure Validation', () => {
    it('should validate basic agent response structure', () => {
      const validResponse = {
        success: true,
        data: {
          result: 'Agent execution completed',
          analysis: 'Detailed analysis results'
        },
        metadata: {
          tokensUsed: 250,
          executionTime: 2.5,
          confidence: 0.85
        }
      }

      const validation = agentResponseValidator.validateResponse(validResponse)
      
      expect(validation.isValid).toBe(true)
      expect(validation.errors).toHaveLength(0)
    })

    it('should reject response with missing required fields', () => {
      const invalidResponse = {
        success: true,
        data: {
          result: 'Agent execution completed'
        }
        // Missing metadata
      }

      const validation = agentResponseValidator.validateResponse(invalidResponse)
      
      expect(validation.isValid).toBe(false)
      expect(validation.errors).toContain('Missing required field: metadata')
    })

    it('should validate metadata structure', () => {
      const responseWithInvalidMetadata = {
        success: true,
        data: { result: 'Test' },
        metadata: {
          tokensUsed: 'invalid', // Should be number
          executionTime: -1, // Should be positive
          confidence: 1.5 // Should be between 0 and 1
        }
      }

      const validation = agentResponseValidator.validateResponse(responseWithInvalidMetadata)
      
      expect(validation.isValid).toBe(false)
      expect(validation.errors).toContain('tokensUsed must be a positive number')
      expect(validation.errors).toContain('executionTime must be a positive number')
      expect(validation.errors).toContain('confidence must be between 0 and 1')
    })
  })

  describe('Agent-Specific Response Validation', () => {
    it('should validate Strategic Planning Agent response', () => {
      const strategicResponse = {
        success: true,
        data: {
          analysis: {
            strengths: ['Strong team', 'Good product'],
            weaknesses: ['Limited budget', 'Small market'],
            opportunities: ['New markets', 'Technology trends'],
            threats: ['Competition', 'Economic downturn']
          },
          recommendations: [
            'Expand to new markets',
            'Invest in R&D',
            'Improve marketing'
          ],
          actionPlan: {
            shortTerm: ['Hire marketing team'],
            mediumTerm: ['Launch new product'],
            longTerm: ['International expansion']
          }
        },
        metadata: {
          tokensUsed: 500,
          executionTime: 4.2,
          confidence: 0.92
        }
      }

      const validation = agentResponseValidator.validateStrategicPlanningResponse(strategicResponse)
      
      expect(validation.isValid).toBe(true)
      expect(validation.errors).toHaveLength(0)
    })

    it('should validate Content Creation Agent response', () => {
      const contentResponse = {
        success: true,
        data: {
          content: 'Generated marketing content about AI innovation',
          variants: [
            {
              content: 'Variant 1 content',
              score: 8.5,
              platform: 'linkedin',
              hashtags: ['#AI', '#Innovation']
            },
            {
              content: 'Variant 2 content',
              score: 9.0,
              platform: 'twitter',
              hashtags: ['#Tech', '#Future']
            }
          ],
          seoAnalysis: {
            keywordDensity: 2.1,
            readabilityScore: 75,
            metaDescription: 'SEO optimized description'
          }
        },
        metadata: {
          tokensUsed: 300,
          executionTime: 2.8,
          bestVariant: 1
        }
      }

      const validation = agentResponseValidator.validateContentCreationResponse(contentResponse)
      
      expect(validation.isValid).toBe(true)
      expect(validation.errors).toHaveLength(0)
    })

    it('should validate Sales Intelligence Agent response', () => {
      const salesResponse = {
        success: true,
        data: {
          leadScoring: {
            totalLeads: 50,
            highPriority: 15,
            mediumPriority: 20,
            lowPriority: 15
          },
          scoredLeads: [
            {
              id: 'lead-1',
              score: 85,
              priority: 'high',
              reasoning: 'High engagement and good fit',
              nextActions: ['Schedule demo', 'Send proposal'],
              conversionProbability: 0.75
            }
          ],
          insights: {
            topPerformingChannels: ['email', 'social'],
            bestTimeToContact: '10:00-12:00',
            seasonalTrends: ['Q4 uptick expected']
          }
        },
        metadata: {
          tokensUsed: 400,
          executionTime: 3.5,
          confidence: 0.88
        }
      }

      const validation = agentResponseValidator.validateSalesIntelligenceResponse(salesResponse)
      
      expect(validation.isValid).toBe(true)
      expect(validation.errors).toHaveLength(0)
    })

    it('should validate Data Analysis Agent response', () => {
      const dataResponse = {
        success: true,
        data: {
          analysis: {
            trends: ['upward', 'seasonal'],
            correlations: [
              { x: 'metric1', y: 'metric2', value: 0.85, significance: 'high' }
            ],
            anomalies: [
              { date: '2024-01-15', value: 150, expected: 100, deviation: 50 }
            ],
            patterns: ['Weekly cyclical pattern', 'Monthly growth trend']
          },
          insights: [
            'Strong upward trend detected',
            'Seasonal patterns consistent with previous year'
          ],
          recommendations: [
            'Continue current strategy',
            'Monitor for trend changes',
            'Investigate anomaly on 2024-01-15'
          ],
          forecast: {
            nextPeriod: { predicted: 120, confidence: 0.82 },
            nextQuarter: { predicted: 450, confidence: 0.75 }
          }
        },
        metadata: {
          tokensUsed: 450,
          executionTime: 4.1,
          confidence: 0.91
        }
      }

      const validation = agentResponseValidator.validateDataAnalysisResponse(dataResponse)
      
      expect(validation.isValid).toBe(true)
      expect(validation.errors).toHaveLength(0)
    })
  })

  describe('Response Data Integrity', () => {
    it('should validate numeric ranges and constraints', () => {
      const responseWithInvalidRanges = {
        success: true,
        data: {
          scores: [150, -10, 0.5], // Scores should be 0-100
          percentages: [1.5, -0.2, 0.8], // Percentages should be 0-1
          ratings: [6, 0, 3] // Ratings should be 1-5
        },
        metadata: {
          tokensUsed: 200,
          executionTime: 1.5,
          confidence: 0.85
        }
      }

      const validation = agentResponseValidator.validateDataIntegrity(responseWithInvalidRanges)
      
      expect(validation.isValid).toBe(false)
      expect(validation.errors).toContain('Score 150 exceeds maximum value of 100')
      expect(validation.errors).toContain('Score -10 is below minimum value of 0')
      expect(validation.errors).toContain('Percentage 1.5 exceeds maximum value of 1')
    })

    it('should validate array lengths and required elements', () => {
      const responseWithInvalidArrays = {
        success: true,
        data: {
          recommendations: [], // Should have at least 1 element
          variants: new Array(20).fill({ content: 'test' }), // Should have max 10 elements
          categories: ['cat1'] // Should have 2-5 elements
        },
        metadata: {
          tokensUsed: 200,
          executionTime: 1.5,
          confidence: 0.85
        }
      }

      const validation = agentResponseValidator.validateDataIntegrity(responseWithInvalidArrays)
      
      expect(validation.isValid).toBe(false)
      expect(validation.errors).toContain('recommendations array cannot be empty')
      expect(validation.errors).toContain('variants array exceeds maximum length of 10')
      expect(validation.errors).toContain('categories array must have 2-5 elements')
    })

    it('should validate string formats and patterns', () => {
      const responseWithInvalidStrings = {
        success: true,
        data: {
          email: 'invalid-email', // Should be valid email format
          url: 'not-a-url', // Should be valid URL format
          date: '2024-13-45', // Should be valid date format
          phoneNumber: '123', // Should be valid phone format
          currency: 'invalid-currency' // Should be valid currency code
        },
        metadata: {
          tokensUsed: 200,
          executionTime: 1.5,
          confidence: 0.85
        }
      }

      const validation = agentResponseValidator.validateDataIntegrity(responseWithInvalidStrings)
      
      expect(validation.isValid).toBe(false)
      expect(validation.errors).toContain('Invalid email format')
      expect(validation.errors).toContain('Invalid URL format')
      expect(validation.errors).toContain('Invalid date format')
    })
  })

  describe('Performance Validation', () => {
    it('should validate execution time thresholds', () => {
      const slowResponse = {
        success: true,
        data: { result: 'Slow execution' },
        metadata: {
          tokensUsed: 200,
          executionTime: 35.0, // Exceeds 30 second threshold
          confidence: 0.85
        }
      }

      const validation = agentResponseValidator.validatePerformance(slowResponse)
      
      expect(validation.isValid).toBe(false)
      expect(validation.warnings).toContain('Execution time exceeds recommended threshold of 30 seconds')
    })

    it('should validate token usage efficiency', () => {
      const inefficientResponse = {
        success: true,
        data: { result: 'Short result' },
        metadata: {
          tokensUsed: 2000, // High token usage for simple result
          executionTime: 2.5,
          confidence: 0.85
        }
      }

      const validation = agentResponseValidator.validatePerformance(inefficientResponse)
      
      expect(validation.isValid).toBe(true) // Still valid but with warnings
      expect(validation.warnings).toContain('High token usage for result complexity')
    })

    it('should validate confidence thresholds', () => {
      const lowConfidenceResponse = {
        success: true,
        data: { result: 'Low confidence result' },
        metadata: {
          tokensUsed: 200,
          executionTime: 2.5,
          confidence: 0.45 // Below 0.5 threshold
        }
      }

      const validation = agentResponseValidator.validatePerformance(lowConfidenceResponse)
      
      expect(validation.isValid).toBe(true)
      expect(validation.warnings).toContain('Low confidence score below recommended threshold of 0.5')
    })
  })

  describe('Security Validation', () => {
    it('should detect potential security issues in responses', () => {
      const unsafeResponse = {
        success: true,
        data: {
          result: 'User password is: password123',
          analysis: 'SQL query: SELECT * FROM users WHERE id = 1',
          recommendations: ['Execute: rm -rf /']
        },
        metadata: {
          tokensUsed: 200,
          executionTime: 2.5,
          confidence: 0.85
        }
      }

      const validation = agentResponseValidator.validateSecurity(unsafeResponse)
      
      expect(validation.isValid).toBe(false)
      expect(validation.errors).toContain('Potential sensitive data exposure detected')
      expect(validation.errors).toContain('Potential SQL injection pattern detected')
      expect(validation.errors).toContain('Potentially dangerous command detected')
    })

    it('should validate content for inappropriate material', () => {
      const inappropriateResponse = {
        success: true,
        data: {
          content: 'This content contains inappropriate language and harmful suggestions',
          recommendations: ['Use discriminatory practices', 'Ignore safety regulations']
        },
        metadata: {
          tokensUsed: 200,
          executionTime: 2.5,
          confidence: 0.85
        }
      }

      const validation = agentResponseValidator.validateSecurity(inappropriateResponse)
      
      expect(validation.isValid).toBe(false)
      expect(validation.errors).toContain('Potentially inappropriate content detected')
      expect(validation.errors).toContain('Potentially harmful recommendation detected')
    })
  })

  describe('Cross-Agent Consistency', () => {
    it('should validate consistency between related agent responses', () => {
      const strategicResponse = {
        data: {
          recommendations: ['Expand to European markets', 'Increase R&D budget'],
          budget: { total: 1000000, marketing: 300000, rd: 400000 }
        }
      }

      const financialResponse = {
        data: {
          budget: { total: 800000, marketing: 200000, rd: 300000 }, // Inconsistent with strategic
          projections: { revenue: 1200000, expenses: 800000 }
        }
      }

      const validation = agentResponseValidator.validateConsistency([strategicResponse, financialResponse])
      
      expect(validation.isValid).toBe(false)
      expect(validation.errors).toContain('Budget inconsistency detected between agents')
    })

    it('should validate data flow between sequential agents', () => {
      const dataAnalysisOutput = {
        data: {
          insights: ['Low conversion rate', 'High bounce rate'],
          metrics: { conversionRate: 0.02, bounceRate: 0.75 }
        }
      }

      const contentCreationInput = {
        parameters: {
          insights: ['Low conversion rate'], // Missing 'High bounce rate'
          targetMetrics: { conversionRate: 0.05 } // Different from analysis
        }
      }

      const validation = agentResponseValidator.validateDataFlow(dataAnalysisOutput, contentCreationInput)
      
      expect(validation.isValid).toBe(false)
      expect(validation.errors).toContain('Incomplete data transfer between agents')
      expect(validation.warnings).toContain('Target metrics differ from analysis results')
    })
  })
})
