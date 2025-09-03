/**
 * Base44 Entity Service
 * Enhanced wrapper for all Base44 entity operations with proper error handling
 */

import { base44 } from '@/api/base44Client';
import { errorHandlingService } from './errorHandlingService';
import { auditService } from './auditService';
import { validateClientData } from '@/lib/validation/middleware';

class Base44EntityService {
  constructor() {
    this.entityCache = new Map();
    this.operationTimeout = 30000; // 30 seconds
  }

  /**
   * Enhanced entity operation wrapper
   * @param {string} entityName - Entity name
   * @param {string} operation - Operation name (create, get, update, delete, list, filter)
   * @param {Object} params - Operation parameters
   * @param {Object} options - Additional options
   * @returns {Promise<Object>} Operation result
   */
  async executeEntityOperation(entityName, operation, params = {}, options = {}) {
    const startTime = Date.now();
    
    try {
      // Validate entity exists
      const entity = this.getEntity(entityName);
      if (!entity) {
        throw new Error(`Entity '${entityName}' not found in Base44 SDK`);
      }

      // Validate operation exists
      if (typeof entity[operation] !== 'function') {
        throw new Error(`Operation '${operation}' not available for entity '${entityName}'`);
      }

      // Validate parameters if schema provided
      if (options.validationSchema) {
        const validation = options.validationSchema.safeParse(params);
        if (!validation.success) {
          throw new Error(`Invalid parameters: ${validation.error.message}`);
        }
        params = validation.data;
      }

      // Execute with timeout
      const timeoutPromise = new Promise((_, reject) => {
        setTimeout(() => reject(new Error(`Entity operation timed out after ${this.operationTimeout}ms`)), this.operationTimeout);
      });

      const operationPromise = entity[operation](params);
      const result = await Promise.race([operationPromise, timeoutPromise]);

      // Log successful operation
      const executionTime = Date.now() - startTime;
      auditService.logAccess.dataAccess(null, 'entity_operation', `${entityName}.${operation}`, {
        executionTime,
        success: true
      });

      return result;
    } catch (error) {
      // Enhanced error handling
      const executionTime = Date.now() - startTime;
      const enhancedError = errorHandlingService.handleApiError(error, {
        entity: entityName,
        operation,
        params: Object.keys(params),
        executionTime
      });

      auditService.logSystem.error(error, 'entity_operation_error', {
        entity: entityName,
        operation,
        executionTime
      });

      throw error;
    }
  }

  /**
   * Get entity with fallback creation
   * @param {string} entityName - Entity name
   * @returns {Object} Entity object
   */
  getEntity(entityName) {
    // Check if entity exists in Base44 SDK
    if (base44.entities && base44.entities[entityName]) {
      return base44.entities[entityName];
    }

    // Check cache for created entities
    if (this.entityCache.has(entityName)) {
      return this.entityCache.get(entityName);
    }

    // Create fallback entity
    const fallbackEntity = this.createFallbackEntity(entityName);
    this.entityCache.set(entityName, fallbackEntity);
    
    // Also add to base44.entities if it exists
    if (base44.entities) {
      base44.entities[entityName] = fallbackEntity;
    }

    return fallbackEntity;
  }

  /**
   * Create fallback entity with standard CRUD operations
   * @param {string} entityName - Entity name
   * @returns {Object} Fallback entity
   */
  createFallbackEntity(entityName) {
    const baseUrl = `/api/entities/${entityName.toLowerCase()}`;
    
    return {
      create: async (data) => {
        const response = await fetch(baseUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${await this.getAuthToken()}`
          },
          body: JSON.stringify(data)
        });
        
        if (!response.ok) {
          throw new Error(`Failed to create ${entityName}: ${response.statusText}`);
        }
        
        return await response.json();
      },

      get: async (id) => {
        const response = await fetch(`${baseUrl}/${id}`, {
          headers: {
            'Authorization': `Bearer ${await this.getAuthToken()}`
          }
        });
        
        if (!response.ok) {
          throw new Error(`Failed to get ${entityName}: ${response.statusText}`);
        }
        
        return await response.json();
      },

      update: async (id, data) => {
        const response = await fetch(`${baseUrl}/${id}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${await this.getAuthToken()}`
          },
          body: JSON.stringify(data)
        });
        
        if (!response.ok) {
          throw new Error(`Failed to update ${entityName}: ${response.statusText}`);
        }
        
        return await response.json();
      },

      delete: async (id) => {
        const response = await fetch(`${baseUrl}/${id}`, {
          method: 'DELETE',
          headers: {
            'Authorization': `Bearer ${await this.getAuthToken()}`
          }
        });
        
        if (!response.ok) {
          throw new Error(`Failed to delete ${entityName}: ${response.statusText}`);
        }
        
        return response.ok;
      },

      list: async (orderBy = 'id', limit = 50) => {
        const params = new URLSearchParams({ orderBy, limit: limit.toString() });
        const response = await fetch(`${baseUrl}?${params}`, {
          headers: {
            'Authorization': `Bearer ${await this.getAuthToken()}`
          }
        });
        
        if (!response.ok) {
          throw new Error(`Failed to list ${entityName}: ${response.statusText}`);
        }
        
        return await response.json();
      },

      filter: async (filters) => {
        const response = await fetch(`${baseUrl}/filter`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${await this.getAuthToken()}`
          },
          body: JSON.stringify(filters)
        });
        
        if (!response.ok) {
          throw new Error(`Failed to filter ${entityName}: ${response.statusText}`);
        }
        
        return await response.json();
      }
    };
  }

  /**
   * Get authentication token
   * @returns {Promise<string>} Auth token
   */
  async getAuthToken() {
    try {
      // Try to get token from secure storage
      const { authService } = await import('./authService');
      const token = await authService.getAccessToken();
      return token || '';
    } catch (error) {
      console.warn('Failed to get auth token:', error);
      return '';
    }
  }

  /**
   * Enhanced create operation
   * @param {string} entityName - Entity name
   * @param {Object} data - Entity data
   * @param {Object} options - Options
   * @returns {Promise<Object>} Created entity
   */
  async create(entityName, data, options = {}) {
    return this.executeEntityOperation(entityName, 'create', data, options);
  }

  /**
   * Enhanced get operation
   * @param {string} entityName - Entity name
   * @param {string} id - Entity ID
   * @param {Object} options - Options
   * @returns {Promise<Object>} Entity data
   */
  async get(entityName, id, options = {}) {
    return this.executeEntityOperation(entityName, 'get', id, options);
  }

  /**
   * Enhanced update operation
   * @param {string} entityName - Entity name
   * @param {string} id - Entity ID
   * @param {Object} data - Update data
   * @param {Object} options - Options
   * @returns {Promise<Object>} Updated entity
   */
  async update(entityName, id, data, options = {}) {
    return this.executeEntityOperation(entityName, 'update', { id, ...data }, options);
  }

  /**
   * Enhanced delete operation
   * @param {string} entityName - Entity name
   * @param {string} id - Entity ID
   * @param {Object} options - Options
   * @returns {Promise<boolean>} Success status
   */
  async delete(entityName, id, options = {}) {
    return this.executeEntityOperation(entityName, 'delete', id, options);
  }

  /**
   * Enhanced list operation
   * @param {string} entityName - Entity name
   * @param {string} orderBy - Order by field
   * @param {number} limit - Result limit
   * @param {Object} options - Options
   * @returns {Promise<Array>} Entity list
   */
  async list(entityName, orderBy = 'id', limit = 50, options = {}) {
    return this.executeEntityOperation(entityName, 'list', { orderBy, limit }, options);
  }

  /**
   * Enhanced filter operation
   * @param {string} entityName - Entity name
   * @param {Object} filters - Filter criteria
   * @param {Object} options - Options
   * @returns {Promise<Array>} Filtered entities
   */
  async filter(entityName, filters, options = {}) {
    return this.executeEntityOperation(entityName, 'filter', filters, options);
  }

  /**
   * Batch operations
   * @param {Array} operations - Array of operations
   * @returns {Promise<Array>} Results array
   */
  async batchExecute(operations) {
    const results = [];
    
    for (const operation of operations) {
      try {
        const result = await this.executeEntityOperation(
          operation.entity,
          operation.operation,
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
   * Get entity operation statistics
   * @returns {Object} Statistics
   */
  getStatistics() {
    return {
      cachedEntities: this.entityCache.size,
      operationTimeout: this.operationTimeout,
      lastUpdated: new Date().toISOString()
    };
  }

  /**
   * Clear entity cache
   */
  clearCache() {
    this.entityCache.clear();
    auditService.logSystem.configChange(null, 'entity_cache_cleared', null, 'cleared');
  }
}

// Create and export singleton instance
export const base44EntityService = new Base44EntityService();

export default base44EntityService;
