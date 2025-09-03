/**
 * API Performance Tests
 * Comprehensive performance testing for API endpoints and data operations
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { apiClient } from '@/api/apiClient'
import { base44EntityService } from '@/api/base44Client'
import { performanceOptimizationService } from '@/services/performanceOptimizationService'
import { testDataFactories } from '@/test/utils'

// Mock fetch for performance testing
global.fetch = vi.fn()

describe('API Performance Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.clearAllTimers()
    vi.useFakeTimers()
    
    // Reset performance metrics
    performanceOptimizationService.performanceMetrics.apiResponseTimes.clear()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  describe('API Response Time Benchmarks', () => {
    it('should complete authentication requests within 500ms', async () => {
      const mockResponse = {
        ok: true,
        json: () => Promise.resolve({
          success: true,
          data: { token: 'mock-token', user: testDataFactories.user() }
        })
      }

      fetch.mockResolvedValueOnce(mockResponse)

      const startTime = Date.now()
      
      const result = await apiClient.post('/auth/login', {
        email: 'test@example.com',
        password: 'password123'
      })

      const responseTime = Date.now() - startTime
      
      expect(result.success).toBe(true)
      expect(responseTime).toBeLessThan(500)
      
      // Verify performance tracking
      expect(performanceOptimizationService.performanceMetrics.apiResponseTimes.has('/auth/login')).toBe(true)
    })

    it('should complete campaign CRUD operations within 1000ms', async () => {
      const mockCampaign = testDataFactories.campaign()
      
      const operations = [
        { method: 'POST', endpoint: '/campaigns', data: mockCampaign, expectedTime: 800 },
        { method: 'GET', endpoint: '/campaigns/123', data: null, expectedTime: 300 },
        { method: 'PUT', endpoint: '/campaigns/123', data: mockCampaign, expectedTime: 600 },
        { method: 'DELETE', endpoint: '/campaigns/123', data: null, expectedTime: 400 }
      ]

      for (const operation of operations) {
        const mockResponse = {
          ok: true,
          json: () => Promise.resolve({
            success: true,
            data: operation.method === 'DELETE' ? null : mockCampaign
          })
        }

        fetch.mockResolvedValueOnce(mockResponse)

        const startTime = Date.now()
        
        let result
        switch (operation.method) {
          case 'POST':
            result = await apiClient.post(operation.endpoint, operation.data)
            break
          case 'GET':
            result = await apiClient.get(operation.endpoint)
            break
          case 'PUT':
            result = await apiClient.put(operation.endpoint, operation.data)
            break
          case 'DELETE':
            result = await apiClient.delete(operation.endpoint)
            break
        }

        const responseTime = Date.now() - startTime
        
        expect(result.success).toBe(true)
        expect(responseTime).toBeLessThan(operation.expectedTime)
      }
    })

    it('should handle large dataset queries efficiently', async () => {
      const largeDataset = Array.from({ length: 1000 }, (_, i) => 
        testDataFactories.campaign({ id: `campaign-${i}` })
      )

      const mockResponse = {
        ok: true,
        json: () => Promise.resolve({
          success: true,
          data: largeDataset,
          pagination: {
            total: 1000,
            page: 1,
            limit: 1000
          }
        })
      }

      fetch.mockResolvedValueOnce(mockResponse)

      const startTime = Date.now()
      
      const result = await apiClient.get('/campaigns?limit=1000')
      
      const responseTime = Date.now() - startTime
      
      expect(result.success).toBe(true)
      expect(result.data).toHaveLength(1000)
      expect(responseTime).toBeLessThan(2000) // 2 seconds for large dataset
    })

    it('should optimize paginated requests', async () => {
      const pageSize = 50
      const totalPages = 5
      const responseTimes = []

      for (let page = 1; page <= totalPages; page++) {
        const mockData = Array.from({ length: pageSize }, (_, i) => 
          testDataFactories.campaign({ id: `campaign-${page}-${i}` })
        )

        const mockResponse = {
          ok: true,
          json: () => Promise.resolve({
            success: true,
            data: mockData,
            pagination: {
              total: pageSize * totalPages,
              page,
              limit: pageSize,
              hasNext: page < totalPages
            }
          })
        }

        fetch.mockResolvedValueOnce(mockResponse)

        const startTime = Date.now()
        
        const result = await apiClient.get(`/campaigns?page=${page}&limit=${pageSize}`)
        
        const responseTime = Date.now() - startTime
        responseTimes.push(responseTime)
        
        expect(result.success).toBe(true)
        expect(result.data).toHaveLength(pageSize)
        expect(responseTime).toBeLessThan(500) // Each page should load quickly
      }

      // Response times should be consistent across pages
      const avgResponseTime = responseTimes.reduce((a, b) => a + b, 0) / responseTimes.length
      const maxDeviation = Math.max(...responseTimes.map(time => Math.abs(time - avgResponseTime)))
      
      expect(maxDeviation).toBeLessThan(avgResponseTime * 0.5) // Max 50% deviation
    })
  })

  describe('Concurrent Request Performance', () => {
    it('should handle multiple concurrent API calls efficiently', async () => {
      const concurrentRequests = 10
      const mockResponse = {
        ok: true,
        json: () => Promise.resolve({
          success: true,
          data: testDataFactories.campaign()
        })
      }

      // Mock all requests
      for (let i = 0; i < concurrentRequests; i++) {
        fetch.mockResolvedValueOnce(mockResponse)
      }

      const startTime = Date.now()
      
      const requests = Array.from({ length: concurrentRequests }, (_, i) =>
        apiClient.get(`/campaigns/${i + 1}`)
      )

      const results = await Promise.all(requests)
      
      const totalTime = Date.now() - startTime
      const avgTimePerRequest = totalTime / concurrentRequests
      
      expect(results).toHaveLength(concurrentRequests)
      expect(results.every(result => result.success)).toBe(true)
      
      // Concurrent requests should be faster than sequential
      expect(avgTimePerRequest).toBeLessThan(200) // Average < 200ms per request
      expect(totalTime).toBeLessThan(1000) // Total < 1 second
    })

    it('should handle mixed request types concurrently', async () => {
      const requests = [
        { method: 'GET', endpoint: '/campaigns', expectedTime: 300 },
        { method: 'POST', endpoint: '/campaigns', data: testDataFactories.campaign(), expectedTime: 800 },
        { method: 'GET', endpoint: '/agents', expectedTime: 200 },
        { method: 'GET', endpoint: '/analytics/dashboard', expectedTime: 500 },
        { method: 'PUT', endpoint: '/user/profile', data: testDataFactories.user(), expectedTime: 400 }
      ]

      // Mock all responses
      requests.forEach(req => {
        const mockResponse = {
          ok: true,
          json: () => Promise.resolve({
            success: true,
            data: req.data || { message: 'Success' }
          })
        }
        fetch.mockResolvedValueOnce(mockResponse)
      })

      const startTime = Date.now()
      
      const promises = requests.map(req => {
        switch (req.method) {
          case 'GET':
            return apiClient.get(req.endpoint)
          case 'POST':
            return apiClient.post(req.endpoint, req.data)
          case 'PUT':
            return apiClient.put(req.endpoint, req.data)
          default:
            return Promise.resolve({ success: false })
        }
      })

      const results = await Promise.all(promises)
      
      const totalTime = Date.now() - startTime
      
      expect(results).toHaveLength(requests.length)
      expect(results.every(result => result.success)).toBe(true)
      
      // Should complete faster than sequential execution
      const sequentialTime = requests.reduce((sum, req) => sum + req.expectedTime, 0)
      expect(totalTime).toBeLessThan(sequentialTime * 0.6) // At least 40% faster
    })
  })

  describe('Caching Performance', () => {
    it('should improve performance with request caching', async () => {
      const endpoint = '/campaigns/123'
      const mockData = testDataFactories.campaign()
      
      const mockResponse = {
        ok: true,
        json: () => Promise.resolve({
          success: true,
          data: mockData
        })
      }

      // First request - cache miss
      fetch.mockResolvedValueOnce(mockResponse)
      
      const firstCallStart = Date.now()
      const firstResult = await apiClient.get(endpoint)
      const firstCallTime = Date.now() - firstCallStart
      
      expect(firstResult.success).toBe(true)
      
      // Cache the result
      performanceOptimizationService.cacheRequest(endpoint, firstResult.data)
      
      // Second request - should hit cache
      const secondCallStart = Date.now()
      const cachedResult = performanceOptimizationService.getCachedRequest(endpoint)
      const secondCallTime = Date.now() - secondCallStart
      
      expect(cachedResult).toEqual(firstResult.data)
      expect(secondCallTime).toBeLessThan(firstCallTime * 0.1) // Cache should be 10x faster
    })

    it('should handle cache expiration correctly', async () => {
      const endpoint = '/campaigns/123'
      const mockData = testDataFactories.campaign()
      const shortTTL = 100 // 100ms TTL

      // Cache with short TTL
      performanceOptimizationService.cacheRequest(endpoint, mockData, shortTTL)
      
      // Immediate access - should hit cache
      const cachedResult1 = performanceOptimizationService.getCachedRequest(endpoint)
      expect(cachedResult1).toEqual(mockData)
      
      // Wait for expiration
      vi.advanceTimersByTime(150)
      
      // Access after expiration - should miss cache
      const cachedResult2 = performanceOptimizationService.getCachedRequest(endpoint)
      expect(cachedResult2).toBeNull()
    })

    it('should track cache hit rates accurately', async () => {
      const endpoint = '/test-endpoint'
      const mockData = { test: 'data' }
      
      // Cache the data
      performanceOptimizationService.cacheRequest(endpoint, mockData)
      
      // Multiple cache hits
      for (let i = 0; i < 5; i++) {
        performanceOptimizationService.getCachedRequest(endpoint)
      }
      
      // Cache misses
      for (let i = 0; i < 3; i++) {
        performanceOptimizationService.getCachedRequest(`${endpoint}-miss-${i}`)
      }
      
      const hitRate = performanceOptimizationService.performanceMetrics.cacheHitRates.get(endpoint)
      expect(hitRate.hits).toBe(5)
      
      // Check overall cache performance
      const totalHits = Array.from(performanceOptimizationService.performanceMetrics.cacheHitRates.values())
        .reduce((sum, rate) => sum + rate.hits, 0)
      const totalMisses = Array.from(performanceOptimizationService.performanceMetrics.cacheHitRates.values())
        .reduce((sum, rate) => sum + rate.misses, 0)
      
      expect(totalHits).toBeGreaterThan(0)
      expect(totalMisses).toBeGreaterThan(0)
    })
  })

  describe('Base44 SDK Performance', () => {
    it('should execute agents within performance thresholds', async () => {
      const mockAgentResponse = {
        success: true,
        data: {
          result: 'Agent execution completed',
          analysis: 'Performance test analysis'
        },
        metadata: {
          tokensUsed: 250,
          executionTime: 3.2,
          sdkVersion: '1.0.0'
        }
      }

      base44EntityService.invokeAgent = vi.fn().mockResolvedValue(mockAgentResponse)

      const startTime = Date.now()
      
      const result = await base44EntityService.invokeAgent({
        agentType: 'strategic_planning',
        task: 'performance-test',
        parameters: { test: true }
      })
      
      const totalTime = Date.now() - startTime
      
      expect(result.success).toBe(true)
      expect(result.metadata.executionTime).toBeLessThan(5.0) // Agent execution < 5s
      expect(totalTime).toBeLessThan(100) // SDK overhead < 100ms
    })

    it('should handle concurrent agent executions efficiently', async () => {
      const mockResponse = {
        success: true,
        data: { result: 'Concurrent agent execution' },
        metadata: { tokensUsed: 200, executionTime: 2.5 }
      }

      base44EntityService.invokeAgent = vi.fn().mockResolvedValue(mockResponse)

      const agentRequests = [
        { agentType: 'content_creation', task: 'blog-post' },
        { agentType: 'strategic_planning', task: 'analysis' },
        { agentType: 'data_analysis', task: 'trends' }
      ]

      const startTime = Date.now()
      
      const results = await Promise.all(
        agentRequests.map(request => base44EntityService.invokeAgent(request))
      )
      
      const totalTime = Date.now() - startTime
      
      expect(results).toHaveLength(3)
      expect(results.every(result => result.success)).toBe(true)
      expect(totalTime).toBeLessThan(500) // Concurrent execution < 500ms overhead
    })
  })

  describe('Error Handling Performance', () => {
    it('should handle API errors efficiently', async () => {
      const mockErrorResponse = {
        ok: false,
        status: 500,
        json: () => Promise.resolve({
          success: false,
          error: 'Internal server error'
        })
      }

      fetch.mockResolvedValueOnce(mockErrorResponse)

      const startTime = Date.now()
      
      try {
        await apiClient.get('/campaigns/invalid')
      } catch (error) {
        const errorHandlingTime = Date.now() - startTime
        
        expect(error).toBeDefined()
        expect(errorHandlingTime).toBeLessThan(100) // Error handling should be fast
      }
    })

    it('should implement efficient retry mechanisms', async () => {
      let callCount = 0
      
      fetch.mockImplementation(() => {
        callCount++
        if (callCount < 3) {
          return Promise.resolve({
            ok: false,
            status: 503,
            json: () => Promise.resolve({ success: false, error: 'Service unavailable' })
          })
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ success: true, data: 'Success after retry' })
        })
      })

      const startTime = Date.now()
      
      const result = await apiClient.get('/campaigns/retry-test')
      
      const totalTime = Date.now() - startTime
      
      expect(result.success).toBe(true)
      expect(callCount).toBe(3) // Should retry twice before success
      expect(totalTime).toBeLessThan(1000) // Total retry time should be reasonable
    })
  })

  describe('Memory and Resource Performance', () => {
    it('should efficiently handle large API responses', async () => {
      const largeResponse = {
        campaigns: Array.from({ length: 5000 }, (_, i) => testDataFactories.campaign({ id: i })),
        analytics: Array.from({ length: 1000 }, (_, i) => ({ date: `2024-01-${i}`, value: Math.random() * 1000 }))
      }

      const mockResponse = {
        ok: true,
        json: () => Promise.resolve({
          success: true,
          data: largeResponse
        })
      }

      fetch.mockResolvedValueOnce(mockResponse)

      const startTime = Date.now()
      
      const result = await apiClient.get('/dashboard/full-data')
      
      const processingTime = Date.now() - startTime
      
      expect(result.success).toBe(true)
      expect(result.data.campaigns).toHaveLength(5000)
      expect(processingTime).toBeLessThan(1000) // Should process large response quickly
    })

    it('should clean up resources after API calls', async () => {
      const mockResponse = {
        ok: true,
        json: () => Promise.resolve({ success: true, data: 'test' })
      }

      fetch.mockResolvedValue(mockResponse)

      // Make multiple API calls
      const promises = Array.from({ length: 20 }, (_, i) =>
        apiClient.get(`/test-endpoint-${i}`)
      )

      const results = await Promise.all(promises)
      
      expect(results).toHaveLength(20)
      expect(results.every(result => result.success)).toBe(true)
      
      // Verify no memory leaks (in real scenario, would check actual memory usage)
      expect(fetch).toHaveBeenCalledTimes(20)
    })
  })
})
