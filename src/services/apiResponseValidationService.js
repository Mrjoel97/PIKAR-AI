/**
 * API Response Validation Service
 * Comprehensive validation service for all API responses
 */

import { z } from 'zod';
import { validateApiResponse } from '@/lib/validation/middleware';
import { errorHandlingService } from './errorHandlingService';
import { auditService } from './auditService';
import * as schemas from '@/lib/validation/schemas';

class ApiResponseValidationService {
  constructor() {
    this.validationCache = new Map();
    this.validationStats = {
      totalValidations: 0,
      successfulValidations: 0,
      failedValidations: 0,
      warningValidations: 0
    };
    this.responseSchemas = new Map();
    this.validationErrors = [];
  }

  /**
   * Initialize API response validation service
   */
  async initialize() {
    try {
      console.log('🔍 Initializing API Response Validation Service...');
      
      // Register all response schemas
      await this.registerResponseSchemas();
      
      // Set up validation interceptors
      await this.setupValidationInterceptors();
      
      // Initialize validation monitoring
      await this.initializeValidationMonitoring();
      
      console.log('✅ API Response Validation Service initialized');
      auditService.logSystem.configChange(null, 'api_response_validation_initialized', null, 'initialized');
    } catch (error) {
      console.error('Failed to initialize API Response Validation Service:', error);
      auditService.logSystem.error(error, 'api_response_validation_initialization');
      throw error;
    }
  }

  /**
   * Register all response schemas
   */
  async registerResponseSchemas() {
    // Authentication response schemas
    this.registerSchema('auth.login', z.object({
      success: z.boolean(),
      data: z.object({
        user: schemas.UserSchema,
        tokens: z.object({
          accessToken: z.string(),
          refreshToken: z.string(),
          expiresIn: z.number().optional()
        })
      }).optional(),
      error: z.string().optional()
    }));

    this.registerSchema('auth.register', z.object({
      success: z.boolean(),
      data: z.object({
        user: schemas.UserSchema,
        tokens: z.object({
          accessToken: z.string(),
          refreshToken: z.string(),
          expiresIn: z.number().optional()
        })
      }).optional(),
      error: z.string().optional()
    }));

    // Entity response schemas
    this.registerSchema('entities.create', z.object({
      success: z.boolean(),
      data: z.any(), // Will be validated against specific entity schema
      error: z.string().optional(),
      id: z.string().optional()
    }));

    this.registerSchema('entities.get', z.object({
      success: z.boolean(),
      data: z.any(), // Will be validated against specific entity schema
      error: z.string().optional()
    }));

    this.registerSchema('entities.update', z.object({
      success: z.boolean(),
      data: z.any(), // Will be validated against specific entity schema
      error: z.string().optional()
    }));

    this.registerSchema('entities.delete', z.object({
      success: z.boolean(),
      message: z.string().optional(),
      error: z.string().optional()
    }));

    this.registerSchema('entities.list', z.object({
      success: z.boolean(),
      data: z.array(z.any()), // Will be validated against specific entity schema array
      pagination: z.object({
        page: z.number(),
        limit: z.number(),
        total: z.number(),
        totalPages: z.number()
      }).optional(),
      error: z.string().optional()
    }));

    // Analytics response schemas
    this.registerSchema('analytics.query', z.object({
      success: z.boolean(),
      data: z.object({
        metrics: z.record(z.number()),
        dimensions: z.record(z.any()),
        timeRange: z.object({
          start: z.string(),
          end: z.string()
        }),
        aggregations: z.record(z.number()).optional()
      }).optional(),
      error: z.string().optional()
    }));

    // Integration response schemas
    this.registerSchema('integrations.invokeLLM', z.object({
      success: z.boolean(),
      data: z.object({
        response: z.string(),
        usage: z.object({
          promptTokens: z.number(),
          completionTokens: z.number(),
          totalTokens: z.number()
        }).optional(),
        model: z.string().optional(),
        finishReason: z.string().optional()
      }).optional(),
      error: z.string().optional()
    }));

    this.registerSchema('integrations.sendEmail', z.object({
      success: z.boolean(),
      data: z.object({
        messageId: z.string(),
        status: z.enum(['sent', 'queued', 'failed'])
      }).optional(),
      error: z.string().optional()
    }));

    this.registerSchema('integrations.uploadFile', z.object({
      success: z.boolean(),
      data: z.object({
        fileId: z.string(),
        url: z.string().url(),
        filename: z.string(),
        size: z.number(),
        mimeType: z.string()
      }).optional(),
      error: z.string().optional()
    }));

    // Social media response schemas
    this.registerSchema('social.meta.post', z.object({
      success: z.boolean(),
      data: z.object({
        postId: z.string(),
        url: z.string().url().optional(),
        status: z.enum(['published', 'scheduled', 'failed'])
      }).optional(),
      error: z.string().optional()
    }));

    this.registerSchema('social.twitter.post', z.object({
      success: z.boolean(),
      data: z.object({
        tweetId: z.string(),
        url: z.string().url().optional(),
        status: z.enum(['published', 'scheduled', 'failed'])
      }).optional(),
      error: z.string().optional()
    }));

    // Error response schema (universal)
    this.registerSchema('error', z.object({
      success: z.literal(false),
      error: z.string(),
      details: z.any().optional(),
      code: z.string().optional(),
      timestamp: z.string().optional()
    }));
  }

  /**
   * Register a response schema
   * @param {string} key - Schema key
   * @param {Object} schema - Zod schema
   */
  registerSchema(key, schema) {
    this.responseSchemas.set(key, schema);
  }

  /**
   * Validate API response
   * @param {string} endpoint - API endpoint
   * @param {Object} response - Response data
   * @param {Object} options - Validation options
   * @returns {Object} Validation result
   */
  async validateResponse(endpoint, response, options = {}) {
    const startTime = Date.now();
    
    try {
      this.validationStats.totalValidations++;
      
      // Get appropriate schema
      const schema = this.getSchemaForEndpoint(endpoint, options);
      
      if (!schema) {
        // No schema available, return response with warning
        this.validationStats.warningValidations++;
        return {
          success: true,
          data: response,
          warning: `No validation schema available for endpoint: ${endpoint}`
        };
      }

      // Perform validation
      const validationResult = validateApiResponse(schema, response);
      
      // Update statistics
      if (validationResult.success) {
        this.validationStats.successfulValidations++;
      } else {
        this.validationStats.failedValidations++;
        
        // Log validation error
        const validationError = {
          endpoint,
          error: validationResult.warning || 'Validation failed',
          response: process.env.NODE_ENV === 'development' ? response : '[REDACTED]',
          timestamp: new Date().toISOString(),
          executionTime: Date.now() - startTime
        };
        
        this.validationErrors.push(validationError);
        
        // Audit log validation failure
        auditService.logSystem.error(
          new Error(validationResult.warning || 'API response validation failed'),
          'api_response_validation_failed',
          {
            endpoint,
            executionTime: validationError.executionTime
          }
        );
      }

      // Cache successful validations
      if (validationResult.success && options.cache) {
        this.cacheValidation(endpoint, response, validationResult);
      }

      return validationResult;
    } catch (error) {
      this.validationStats.failedValidations++;
      
      // Handle validation errors
      const validationError = {
        endpoint,
        error: error.message,
        timestamp: new Date().toISOString(),
        executionTime: Date.now() - startTime
      };
      
      this.validationErrors.push(validationError);
      
      auditService.logSystem.error(error, 'api_response_validation_error', {
        endpoint,
        executionTime: validationError.executionTime
      });

      return {
        success: false,
        data: response,
        error: error.message
      };
    }
  }

  /**
   * Get schema for endpoint
   * @param {string} endpoint - API endpoint
   * @param {Object} options - Options
   * @returns {Object} Zod schema
   */
  getSchemaForEndpoint(endpoint, options = {}) {
    // Direct schema lookup
    if (this.responseSchemas.has(endpoint)) {
      return this.responseSchemas.get(endpoint);
    }

    // Pattern matching for endpoints
    const patterns = [
      { pattern: /^auth\./, schema: 'auth.login' },
      { pattern: /^entities\..*\.create$/, schema: 'entities.create' },
      { pattern: /^entities\..*\.get$/, schema: 'entities.get' },
      { pattern: /^entities\..*\.update$/, schema: 'entities.update' },
      { pattern: /^entities\..*\.delete$/, schema: 'entities.delete' },
      { pattern: /^entities\..*\.list$/, schema: 'entities.list' },
      { pattern: /^analytics\./, schema: 'analytics.query' },
      { pattern: /^integrations\.invokeLLM/, schema: 'integrations.invokeLLM' },
      { pattern: /^integrations\.sendEmail/, schema: 'integrations.sendEmail' },
      { pattern: /^integrations\.uploadFile/, schema: 'integrations.uploadFile' },
      { pattern: /^social\.meta\./, schema: 'social.meta.post' },
      { pattern: /^social\.twitter\./, schema: 'social.twitter.post' }
    ];

    for (const { pattern, schema } of patterns) {
      if (pattern.test(endpoint)) {
        return this.responseSchemas.get(schema);
      }
    }

    // Custom schema from options
    if (options.schema) {
      return options.schema;
    }

    return null;
  }

  /**
   * Cache validation result
   * @param {string} endpoint - Endpoint
   * @param {Object} response - Response
   * @param {Object} validationResult - Validation result
   */
  cacheValidation(endpoint, response, validationResult) {
    const cacheKey = `${endpoint}:${JSON.stringify(response).substring(0, 100)}`;
    this.validationCache.set(cacheKey, {
      result: validationResult,
      timestamp: Date.now()
    });

    // Clean old cache entries (keep last 1000)
    if (this.validationCache.size > 1000) {
      const entries = Array.from(this.validationCache.entries());
      entries.sort((a, b) => b[1].timestamp - a[1].timestamp);
      
      this.validationCache.clear();
      entries.slice(0, 1000).forEach(([key, value]) => {
        this.validationCache.set(key, value);
      });
    }
  }

  /**
   * Setup validation interceptors
   */
  async setupValidationInterceptors() {
    // This would integrate with the API client to automatically validate responses
    // Implementation depends on the specific HTTP client being used
  }

  /**
   * Initialize validation monitoring
   */
  async initializeValidationMonitoring() {
    // Set up periodic monitoring of validation statistics
    setInterval(() => {
      this.logValidationStats();
    }, 300000); // Every 5 minutes
  }

  /**
   * Log validation statistics
   */
  logValidationStats() {
    const stats = this.getValidationStats();
    
    if (stats.failureRate > 10) {
      console.warn('⚠️ High API response validation failure rate:', stats.failureRate + '%');
    }
    
    auditService.logSystem.info('api_response_validation_stats', stats);
  }

  /**
   * Get validation statistics
   * @returns {Object} Validation statistics
   */
  getValidationStats() {
    const total = this.validationStats.totalValidations;
    const successful = this.validationStats.successfulValidations;
    const failed = this.validationStats.failedValidations;
    const warnings = this.validationStats.warningValidations;

    return {
      totalValidations: total,
      successfulValidations: successful,
      failedValidations: failed,
      warningValidations: warnings,
      successRate: total > 0 ? Math.round((successful / total) * 100) : 0,
      failureRate: total > 0 ? Math.round((failed / total) * 100) : 0,
      warningRate: total > 0 ? Math.round((warnings / total) * 100) : 0,
      recentErrors: this.validationErrors.slice(-10),
      cacheSize: this.validationCache.size,
      registeredSchemas: this.responseSchemas.size
    };
  }

  /**
   * Clear validation cache and errors
   */
  clearCache() {
    this.validationCache.clear();
    this.validationErrors = [];
    auditService.logSystem.configChange(null, 'api_response_validation_cache_cleared', null, 'cleared');
  }

  /**
   * Validate batch responses
   * @param {Array} responses - Array of response objects with endpoint info
   * @returns {Array} Validation results
   */
  async validateBatch(responses) {
    const results = [];
    
    for (const { endpoint, response, options } of responses) {
      try {
        const result = await this.validateResponse(endpoint, response, options);
        results.push({ endpoint, result });
      } catch (error) {
        results.push({ 
          endpoint, 
          result: { 
            success: false, 
            error: error.message,
            data: response 
          } 
        });
      }
    }
    
    return results;
  }
}

// Create and export singleton instance
export const apiResponseValidationService = new ApiResponseValidationService();

export default apiResponseValidationService;
