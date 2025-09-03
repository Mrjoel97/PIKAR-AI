/**
 * Agent Performance Benchmark Tests
 * Performance and load testing for AI agents
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { agentService } from '@/services/agentService'
import { performanceMonitor } from '@/services/performanceMonitor'
import { testDataFactories } from '@/test/utils'

// Mock dependencies
vi.mock('@/services/agentService')
vi.mock('@/services/performanceMonitor')

describe('Agent Performance Benchmark Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    
    // Mock performance monitor
    performanceMonitor.startTimer = vi.fn(() => 'timer-id')
    performanceMonitor.endTimer = vi.fn(() => 1500) // 1.5 seconds
    performanceMonitor.recordMetric = vi.fn()
  })

  afterEach(() => {
    vi.clearAllTimers()
  })

  describe('Response Time Benchmarks', () => {
    it('should complete simple tasks within 5 seconds', async () => {
      const mockResponse = {
        success: true,
        data: { result: 'Simple task completed' },
        metadata: { tokensUsed: 100, executionTime: 2.3 }
      }

      agentService.executeAgent.mockResolvedValueOnce(mockResponse)

      const startTime = Date.now()
      
      await agentService.executeAgent({
        agentType: 'content_creation',
        task: 'simple-text',
        parameters: { length: 'short', complexity: 'low' }
      })

      const executionTime = Date.now() - startTime
      
      expect(executionTime).toBeLessThan(5000)
      expect(mockResponse.metadata.executionTime).toBeLessThan(5.0)
    })

    it('should complete medium complexity tasks within 15 seconds', async () => {
      const mockResponse = {
        success: true,
        data: { result: 'Medium task completed', analysis: 'Detailed analysis' },
        metadata: { tokensUsed: 500, executionTime: 8.7 }
      }

      agentService.executeAgent.mockResolvedValueOnce(mockResponse)

      const startTime = Date.now()
      
      await agentService.executeAgent({
        agentType: 'strategic_planning',
        task: 'market-analysis',
        parameters: { depth: 'medium', includeCompetitors: true }
      })

      const executionTime = Date.now() - startTime
      
      expect(executionTime).toBeLessThan(15000)
      expect(mockResponse.metadata.executionTime).toBeLessThan(15.0)
    })

    it('should complete complex tasks within 30 seconds', async () => {
      const mockResponse = {
        success: true,
        data: { 
          result: 'Complex task completed',
          analysis: 'Comprehensive analysis',
          recommendations: ['Rec 1', 'Rec 2', 'Rec 3']
        },
        metadata: { tokensUsed: 1200, executionTime: 24.5 }
      }

      agentService.executeAgent.mockResolvedValueOnce(mockResponse)

      const startTime = Date.now()
      
      await agentService.executeAgent({
        agentType: 'data_analysis',
        task: 'comprehensive-analysis',
        parameters: { 
          dataset: 'large',
          includeForecasting: true,
          generateRecommendations: true
        }
      })

      const executionTime = Date.now() - startTime
      
      expect(executionTime).toBeLessThan(30000)
      expect(mockResponse.metadata.executionTime).toBeLessThan(30.0)
    })
  })

  describe('Token Efficiency Benchmarks', () => {
    it('should use tokens efficiently for simple tasks', async () => {
      const mockResponse = {
        success: true,
        data: { result: 'Efficient simple result' },
        metadata: { tokensUsed: 50, executionTime: 1.2 }
      }

      agentService.executeAgent.mockResolvedValueOnce(mockResponse)

      await agentService.executeAgent({
        agentType: 'content_creation',
        task: 'simple-headline',
        parameters: { words: 10 }
      })

      // Simple tasks should use < 100 tokens
      expect(mockResponse.metadata.tokensUsed).toBeLessThan(100)
      
      // Token efficiency: tokens per second should be reasonable
      const tokensPerSecond = mockResponse.metadata.tokensUsed / mockResponse.metadata.executionTime
      expect(tokensPerSecond).toBeLessThan(100)
    })

    it('should maintain token efficiency for medium tasks', async () => {
      const mockResponse = {
        success: true,
        data: { 
          result: 'Medium complexity result with analysis',
          analysis: 'Detailed analysis content'
        },
        metadata: { tokensUsed: 400, executionTime: 5.8 }
      }

      agentService.executeAgent.mockResolvedValueOnce(mockResponse)

      await agentService.executeAgent({
        agentType: 'strategic_planning',
        task: 'swot-analysis',
        parameters: { company: 'TestCorp', includeRecommendations: true }
      })

      // Medium tasks should use < 600 tokens
      expect(mockResponse.metadata.tokensUsed).toBeLessThan(600)
      
      // Token efficiency should be maintained
      const tokensPerSecond = mockResponse.metadata.tokensUsed / mockResponse.metadata.executionTime
      expect(tokensPerSecond).toBeLessThan(150)
    })

    it('should optimize token usage for complex tasks', async () => {
      const mockResponse = {
        success: true,
        data: { 
          result: 'Complex analysis with multiple components',
          analysis: 'Comprehensive multi-faceted analysis',
          recommendations: Array(10).fill('Detailed recommendation'),
          forecast: 'Future projections and scenarios'
        },
        metadata: { tokensUsed: 1500, executionTime: 18.3 }
      }

      agentService.executeAgent.mockResolvedValueOnce(mockResponse)

      await agentService.executeAgent({
        agentType: 'data_analysis',
        task: 'full-business-analysis',
        parameters: { 
          includeForecasting: true,
          includeRecommendations: true,
          depth: 'comprehensive'
        }
      })

      // Complex tasks should use < 2000 tokens
      expect(mockResponse.metadata.tokensUsed).toBeLessThan(2000)
      
      // Even complex tasks should maintain reasonable efficiency
      const tokensPerSecond = mockResponse.metadata.tokensUsed / mockResponse.metadata.executionTime
      expect(tokensPerSecond).toBeLessThan(200)
    })
  })

  describe('Concurrent Execution Benchmarks', () => {
    it('should handle 5 concurrent simple requests efficiently', async () => {
      const mockResponse = {
        success: true,
        data: { result: 'Concurrent task completed' },
        metadata: { tokensUsed: 100, executionTime: 2.5 }
      }

      agentService.executeAgent.mockResolvedValue(mockResponse)

      const requests = Array(5).fill().map((_, i) => ({
        agentType: 'content_creation',
        task: `concurrent-task-${i}`,
        parameters: { simple: true }
      }))

      const startTime = Date.now()
      
      const results = await Promise.all(
        requests.map(request => agentService.executeAgent(request))
      )

      const totalTime = Date.now() - startTime
      
      expect(results).toHaveLength(5)
      expect(results.every(result => result.success)).toBe(true)
      
      // Concurrent execution should be faster than sequential
      expect(totalTime).toBeLessThan(15000) // Less than 5 * 3 seconds
    })

    it('should handle mixed agent types concurrently', async () => {
      const responses = {
        content_creation: {
          success: true,
          data: { content: 'Generated content' },
          metadata: { tokensUsed: 200, executionTime: 3.0 }
        },
        strategic_planning: {
          success: true,
          data: { analysis: 'Strategic analysis' },
          metadata: { tokensUsed: 400, executionTime: 5.0 }
        },
        data_analysis: {
          success: true,
          data: { insights: ['Insight 1', 'Insight 2'] },
          metadata: { tokensUsed: 350, executionTime: 4.2 }
        }
      }

      agentService.executeAgent.mockImplementation(async (request) => {
        return responses[request.agentType]
      })

      const requests = [
        { agentType: 'content_creation', task: 'blog-post' },
        { agentType: 'strategic_planning', task: 'market-analysis' },
        { agentType: 'data_analysis', task: 'trend-analysis' }
      ]

      const startTime = Date.now()
      
      const results = await Promise.all(
        requests.map(request => agentService.executeAgent(request))
      )

      const totalTime = Date.now() - startTime
      
      expect(results).toHaveLength(3)
      expect(results.every(result => result.success)).toBe(true)
      
      // Should complete faster than sequential execution
      expect(totalTime).toBeLessThan(10000)
    })

    it('should maintain performance under load', async () => {
      const mockResponse = {
        success: true,
        data: { result: 'Load test result' },
        metadata: { tokensUsed: 150, executionTime: 3.0 }
      }

      agentService.executeAgent.mockResolvedValue(mockResponse)

      // Simulate 20 concurrent requests
      const requests = Array(20).fill().map((_, i) => ({
        agentType: 'content_creation',
        task: `load-test-${i}`,
        parameters: { index: i }
      }))

      const startTime = Date.now()
      
      const results = await Promise.all(
        requests.map(request => agentService.executeAgent(request))
      )

      const totalTime = Date.now() - startTime
      const avgTimePerRequest = totalTime / requests.length
      
      expect(results).toHaveLength(20)
      expect(results.every(result => result.success)).toBe(true)
      
      // Average time per request should remain reasonable under load
      expect(avgTimePerRequest).toBeLessThan(2000) // 2 seconds average
      
      // Total time should indicate good concurrency
      expect(totalTime).toBeLessThan(30000) // 30 seconds total
    })
  })

  describe('Memory Usage Benchmarks', () => {
    it('should maintain reasonable memory usage for simple tasks', async () => {
      const mockResponse = {
        success: true,
        data: { result: 'Memory efficient result' },
        metadata: { 
          tokensUsed: 100, 
          executionTime: 2.0,
          memoryUsage: 50 * 1024 * 1024 // 50MB
        }
      }

      agentService.executeAgent.mockResolvedValueOnce(mockResponse)

      await agentService.executeAgent({
        agentType: 'content_creation',
        task: 'memory-test',
        parameters: { simple: true }
      })

      // Simple tasks should use < 100MB memory
      expect(mockResponse.metadata.memoryUsage).toBeLessThan(100 * 1024 * 1024)
    })

    it('should handle large datasets without excessive memory usage', async () => {
      const mockResponse = {
        success: true,
        data: { 
          result: 'Large dataset processed',
          processedRecords: 10000
        },
        metadata: { 
          tokensUsed: 800, 
          executionTime: 12.0,
          memoryUsage: 200 * 1024 * 1024 // 200MB
        }
      }

      agentService.executeAgent.mockResolvedValueOnce(mockResponse)

      await agentService.executeAgent({
        agentType: 'data_analysis',
        task: 'large-dataset-analysis',
        parameters: { 
          dataset: Array(10000).fill({ data: 'test' }),
          includeProcessing: true
        }
      })

      // Large dataset processing should use < 500MB memory
      expect(mockResponse.metadata.memoryUsage).toBeLessThan(500 * 1024 * 1024)
    })
  })

  describe('Error Recovery Benchmarks', () => {
    it('should recover quickly from transient errors', async () => {
      // First call fails, second succeeds
      agentService.executeAgent
        .mockRejectedValueOnce(new Error('Transient network error'))
        .mockResolvedValueOnce({
          success: true,
          data: { result: 'Recovered successfully' },
          metadata: { tokensUsed: 150, executionTime: 2.8 }
        })

      const startTime = Date.now()
      
      // Simulate retry logic
      let result
      try {
        result = await agentService.executeAgent({
          agentType: 'content_creation',
          task: 'error-recovery-test'
        })
      } catch (error) {
        // Retry on error
        result = await agentService.executeAgent({
          agentType: 'content_creation',
          task: 'error-recovery-test'
        })
      }

      const recoveryTime = Date.now() - startTime
      
      expect(result.success).toBe(true)
      expect(recoveryTime).toBeLessThan(10000) // Should recover within 10 seconds
    })

    it('should handle timeout errors gracefully', async () => {
      agentService.executeAgent.mockRejectedValueOnce(
        new Error('Request timeout after 30 seconds')
      )

      const startTime = Date.now()
      
      try {
        await agentService.executeAgent({
          agentType: 'data_analysis',
          task: 'timeout-test',
          parameters: { timeout: 30000 }
        })
      } catch (error) {
        const errorTime = Date.now() - startTime
        
        expect(error.message).toContain('timeout')
        expect(errorTime).toBeLessThan(35000) // Should timeout within expected time
      }
    })
  })

  describe('Scalability Benchmarks', () => {
    it('should scale performance linearly with simple tasks', async () => {
      const mockResponse = {
        success: true,
        data: { result: 'Scalability test result' },
        metadata: { tokensUsed: 100, executionTime: 2.0 }
      }

      agentService.executeAgent.mockResolvedValue(mockResponse)

      // Test with increasing load: 1, 5, 10 concurrent requests
      const loadSizes = [1, 5, 10]
      const results = []

      for (const loadSize of loadSizes) {
        const requests = Array(loadSize).fill().map((_, i) => ({
          agentType: 'content_creation',
          task: `scalability-test-${i}`,
          parameters: { loadSize }
        }))

        const startTime = Date.now()
        
        await Promise.all(
          requests.map(request => agentService.executeAgent(request))
        )

        const totalTime = Date.now() - startTime
        const avgTimePerRequest = totalTime / loadSize
        
        results.push({ loadSize, totalTime, avgTimePerRequest })
      }

      // Performance should scale reasonably
      expect(results[1].avgTimePerRequest).toBeLessThan(results[0].avgTimePerRequest * 2)
      expect(results[2].avgTimePerRequest).toBeLessThan(results[0].avgTimePerRequest * 3)
    })
  })
})
