/**
 * API Integration Service
 * Centralized management for all social media API integrations
 */

import { getAllPlatformFunctions, checkFunctionAvailability, executeWithRetry } from '@/api/functions';
import { errorHandlingService } from './errorHandlingService';
import { auditService } from './auditService';
import { environmentConfig } from '@/config/environment';

class ApiIntegrationService {
  constructor() {
    this.platforms = ['meta', 'twitter', 'linkedin', 'youtube', 'tiktok'];
    this.functionStatus = new Map();
    this.connectionStatus = new Map();
    this.lastHealthCheck = null;
    this.healthCheckInterval = null;
  }

  /**
   * Initialize API integration service
   */
  async initialize() {
    try {
      console.log('🔗 Initializing API Integration Service...');
      
      // Check all function availability
      await this.checkAllFunctions();
      
      // Initialize platform connections
      await this.initializePlatformConnections();
      
      // Set up health monitoring
      this.setupHealthMonitoring();
      
      console.log('✅ API Integration Service initialized');
      auditService.logSystem.configChange(null, 'api_integration_initialized', null, 'initialized');
    } catch (error) {
      console.error('Failed to initialize API Integration Service:', error);
      auditService.logSystem.error(error, 'api_integration_initialization');
      throw error;
    }
  }

  /**
   * Check availability of all API functions
   */
  async checkAllFunctions() {
    const platformFunctions = getAllPlatformFunctions();
    
    for (const [platform, functions] of Object.entries(platformFunctions)) {
      const platformStatus = {};
      
      for (const functionName of functions) {
        const status = await checkFunctionAvailability(functionName);
        platformStatus[functionName] = status;
      }
      
      this.functionStatus.set(platform, platformStatus);
    }
    
    console.log('📊 Function availability check completed');
  }

  /**
   * Initialize platform connections
   */
  async initializePlatformConnections() {
    for (const platform of this.platforms) {
      try {
        const status = await this.checkPlatformConnection(platform);
        this.connectionStatus.set(platform, status);
      } catch (error) {
        console.warn(`Failed to check ${platform} connection:`, error);
        this.connectionStatus.set(platform, {
          connected: false,
          error: error.message,
          lastChecked: new Date().toISOString()
        });
      }
    }
  }

  /**
   * Check platform connection status
   * @param {string} platform - Platform name
   * @returns {Object} Connection status
   */
  async checkPlatformConnection(platform) {
    try {
      const validateFunction = `${platform}ValidateSecrets`;
      const result = await executeWithRetry(validateFunction, {}, 1);
      
      return {
        connected: result?.data?.ok || false,
        lastChecked: new Date().toISOString(),
        details: result?.data
      };
    } catch (error) {
      return {
        connected: false,
        error: error.message,
        lastChecked: new Date().toISOString()
      };
    }
  }

  /**
   * Execute platform function with enhanced error handling
   * @param {string} platform - Platform name
   * @param {string} functionName - Function name
   * @param {Object} params - Function parameters
   * @param {Object} options - Execution options
   * @returns {Promise<Object>} Function result
   */
  async executePlatformFunction(platform, functionName, params = {}, options = {}) {
    const { retries = 3, timeout = 30000 } = options;
    
    try {
      // Check if function is available
      const platformStatus = this.functionStatus.get(platform);
      if (!platformStatus || !platformStatus[functionName]?.available) {
        throw new Error(`Function ${functionName} not available for platform ${platform}`);
      }

      // Check platform connection
      const connectionStatus = this.connectionStatus.get(platform);
      if (!connectionStatus?.connected && !functionName.includes('Oauth') && !functionName.includes('Validate')) {
        throw new Error(`Platform ${platform} not connected. Please authenticate first.`);
      }

      // Execute with timeout
      const timeoutPromise = new Promise((_, reject) => {
        setTimeout(() => reject(new Error(`Function ${functionName} timed out after ${timeout}ms`)), timeout);
      });

      const executionPromise = executeWithRetry(functionName, params, retries);
      const result = await Promise.race([executionPromise, timeoutPromise]);

      // Log successful execution
      auditService.logAccess.dataAccess(null, 'platform_function_executed', functionName, {
        platform,
        success: true,
        executionTime: Date.now()
      });

      return result;
    } catch (error) {
      // Enhanced error handling
      const enhancedError = errorHandlingService.handleApiError(error, {
        platform,
        functionName,
        params
      });

      auditService.logSystem.error(error, 'platform_function_error', {
        platform,
        functionName
      });

      throw error;
    }
  }

  /**
   * Batch execute multiple functions
   * @param {Array} operations - Array of operations to execute
   * @returns {Promise<Array>} Results array
   */
  async batchExecute(operations) {
    const results = [];
    
    for (const operation of operations) {
      try {
        const result = await this.executePlatformFunction(
          operation.platform,
          operation.functionName,
          operation.params,
          operation.options
        );
        results.push({ success: true, result, operation });
      } catch (error) {
        results.push({ success: false, error: error.message, operation });
      }
    }
    
    return results;
  }

  /**
   * Get platform status
   * @param {string} platform - Platform name
   * @returns {Object} Platform status
   */
  getPlatformStatus(platform) {
    return {
      functions: this.functionStatus.get(platform) || {},
      connection: this.connectionStatus.get(platform) || { connected: false },
      lastHealthCheck: this.lastHealthCheck
    };
  }

  /**
   * Get all platforms status
   * @returns {Object} All platforms status
   */
  getAllPlatformsStatus() {
    const status = {};
    
    for (const platform of this.platforms) {
      status[platform] = this.getPlatformStatus(platform);
    }
    
    return {
      platforms: status,
      lastHealthCheck: this.lastHealthCheck,
      overallHealth: this.calculateOverallHealth()
    };
  }

  /**
   * Calculate overall health score
   * @returns {Object} Health score and details
   */
  calculateOverallHealth() {
    let totalFunctions = 0;
    let availableFunctions = 0;
    let connectedPlatforms = 0;
    
    for (const platform of this.platforms) {
      const platformStatus = this.functionStatus.get(platform) || {};
      const connectionStatus = this.connectionStatus.get(platform) || {};
      
      const functions = Object.values(platformStatus);
      totalFunctions += functions.length;
      availableFunctions += functions.filter(f => f.available).length;
      
      if (connectionStatus.connected) {
        connectedPlatforms++;
      }
    }
    
    const functionHealthScore = totalFunctions > 0 ? (availableFunctions / totalFunctions) * 100 : 0;
    const connectionHealthScore = (connectedPlatforms / this.platforms.length) * 100;
    const overallScore = (functionHealthScore + connectionHealthScore) / 2;
    
    return {
      score: Math.round(overallScore),
      functionHealth: Math.round(functionHealthScore),
      connectionHealth: Math.round(connectionHealthScore),
      totalFunctions,
      availableFunctions,
      connectedPlatforms,
      totalPlatforms: this.platforms.length
    };
  }

  /**
   * Setup health monitoring
   */
  setupHealthMonitoring() {
    // Check health every 5 minutes
    this.healthCheckInterval = setInterval(async () => {
      await this.performHealthCheck();
    }, 5 * 60 * 1000);
    
    // Initial health check
    this.performHealthCheck();
  }

  /**
   * Perform comprehensive health check
   */
  async performHealthCheck() {
    try {
      this.lastHealthCheck = new Date().toISOString();
      
      // Check function availability
      await this.checkAllFunctions();
      
      // Check platform connections
      await this.initializePlatformConnections();
      
      // Calculate health metrics
      const health = this.calculateOverallHealth();
      
      // Log health status
      auditService.logSystem.configChange(null, 'api_health_check', null, JSON.stringify(health));
      
      // Alert on poor health
      if (health.score < 70) {
        console.warn('⚠️ API Integration health is poor:', health);
        auditService.logSystem.error(new Error('Poor API health'), 'api_health_warning', health);
      }
      
    } catch (error) {
      console.error('Health check failed:', error);
      auditService.logSystem.error(error, 'api_health_check_failed');
    }
  }

  /**
   * Refresh platform connection
   * @param {string} platform - Platform name
   * @returns {Promise<Object>} Connection status
   */
  async refreshPlatformConnection(platform) {
    try {
      const status = await this.checkPlatformConnection(platform);
      this.connectionStatus.set(platform, status);
      
      auditService.logSystem.configChange(null, 'platform_connection_refreshed', platform, status.connected ? 'connected' : 'disconnected');
      
      return status;
    } catch (error) {
      auditService.logSystem.error(error, 'platform_connection_refresh', { platform });
      throw error;
    }
  }

  /**
   * Get function execution statistics
   * @returns {Object} Execution statistics
   */
  getExecutionStatistics() {
    // This would typically come from a more persistent store
    // For now, return basic metrics
    return {
      totalExecutions: 0, // Would track this in real implementation
      successRate: 0,
      averageExecutionTime: 0,
      topFunctions: [],
      errorRate: 0,
      lastUpdated: new Date().toISOString()
    };
  }

  /**
   * Cleanup and shutdown
   */
  shutdown() {
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval);
      this.healthCheckInterval = null;
    }
    
    this.functionStatus.clear();
    this.connectionStatus.clear();
    
    auditService.logSystem.configChange(null, 'api_integration_shutdown', null, 'shutdown');
    console.log('🔗 API Integration Service shut down');
  }
}

// Create and export singleton instance
export const apiIntegrationService = new ApiIntegrationService();

export default apiIntegrationService;
