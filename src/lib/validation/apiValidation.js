import { validateApiResponse, validateClientData } from './middleware';
import * as schemas from './schemas';
import { errorHandlingService } from '@/services/errorHandlingService';

/**
 * API validation wrapper for Base44 SDK calls
 * Provides input validation, response validation, and error handling
 */
export class ApiValidator {
  constructor(base44Client) {
    this.client = base44Client;
    this.schemas = schemas;
  }

  /**
   * Validate and execute a Base44 entity operation
   * @param {string} entityName - Name of the entity (e.g., 'campaigns', 'tickets')
   * @param {string} operation - Operation to perform ('create', 'update', 'list', 'get', 'delete')
   * @param {Object} data - Data to send with the request
   * @param {Object} options - Additional options
   * @returns {Promise<Object>} Validated response
   */
  async executeEntityOperation(entityName, operation, data = {}, options = {}) {
    const { validateInput = true, validateOutput = true, schema } = options;

    try {
      // Input validation
      if (validateInput && data && Object.keys(data).length > 0) {
        const inputSchema = this.getInputSchema(entityName, operation, schema);
        if (inputSchema) {
          const validation = validateClientData(inputSchema, data);
          if (!validation.success) {
            throw new ValidationError('Input validation failed', validation.errors);
          }
          data = validation.data; // Use sanitized data
        }
      }

      // Execute the operation
      const entity = this.client.entities[entityName];
      if (!entity || !entity[operation]) {
        throw new Error(`Invalid entity operation: ${entityName}.${operation}`);
      }

      const response = await entity[operation](data);

      // Output validation
      if (validateOutput && response) {
        const outputSchema = this.getOutputSchema(entityName, operation, schema);
        if (outputSchema) {
          const validation = validateApiResponse(outputSchema, response);
          if (!validation.success && validation.warning) {
            console.warn(`Response validation warning for ${entityName}.${operation}:`, validation.warning);
          }
          return validation.data;
        }
      }

      return response;
    } catch (error) {
      // Enhanced error handling with error handling service
      if (error instanceof ValidationError) {
        errorHandlingService.handleValidationError({
          errors: error.errors || [{ message: error.message }],
          field: error.path?.[0],
          value: error.value
        }, {
          entityName,
          operation,
          data
        });
        throw error;
      }

      // Handle API errors through error handling service
      const apiErrorResult = errorHandlingService.handleApiError(error, {
        endpoint: `${entityName}.${operation}`,
        method: operation.toUpperCase(),
        data,
        entityName,
        operation
      });

      // Wrap other errors with context
      const enhancedError = new Error(`API operation failed: ${entityName}.${operation}`);
      enhancedError.originalError = error;
      enhancedError.entityName = entityName;
      enhancedError.operation = operation;
      enhancedError.data = data;
      enhancedError.errorId = apiErrorResult.id;

      throw enhancedError;
    }
  }

  /**
   * Get input validation schema for an entity operation
   * @param {string} entityName - Entity name
   * @param {string} operation - Operation name
   * @param {Object} customSchema - Custom schema override
   * @returns {Object|null} Zod schema or null
   */
  getInputSchema(entityName, operation, customSchema) {
    if (customSchema) return customSchema;

    const schemaMap = {
      campaigns: {
        create: schemas.CampaignCreateSchema,
        update: schemas.CampaignUpdateSchema
      },
      tickets: {
        create: schemas.TicketCreateSchema,
        update: schemas.TicketUpdateSchema
      },
      users: {
        create: schemas.UserSchema,
        update: schemas.UserUpdateSchema
      },
      reports: {
        create: schemas.ReportCreateSchema,
        update: schemas.ReportUpdateSchema
      },
      agents: {
        create: schemas.AgentCreateSchema,
        update: schemas.AgentUpdateSchema
      },
      correctiveActions: {
        create: schemas.CorrectiveActionCreateSchema,
        update: schemas.CorrectiveActionUpdateSchema
      },
      documents: {
        create: schemas.DocumentCreateSchema,
        update: schemas.DocumentUpdateSchema
      },
      learningPaths: {
        create: schemas.LearningPathCreateSchema,
        update: schemas.LearningPathUpdateSchema
      },
      migrations: {
        create: schemas.DatabaseMigrationCreateSchema,
        update: schemas.DatabaseMigrationUpdateSchema
      }
    };

    return schemaMap[entityName]?.[operation] || null;
  }

  /**
   * Get output validation schema for an entity operation
   * @param {string} entityName - Entity name
   * @param {string} operation - Operation name
   * @param {Object} customSchema - Custom schema override
   * @returns {Object|null} Zod schema or null
   */
  getOutputSchema(entityName, operation, customSchema) {
    if (customSchema) return customSchema;

    // For now, we'll use the base schemas for output validation
    // In a real implementation, you might have separate response schemas
    const schemaMap = {
      campaigns: schemas.CampaignSchema,
      tickets: schemas.TicketSchema,
      users: schemas.UserSchema,
      reports: schemas.ReportSchema,
      agents: schemas.AgentSchema,
      correctiveActions: schemas.CorrectiveActionSchema,
      documents: schemas.DocumentSchema,
      learningPaths: schemas.LearningPathSchema,
      migrations: schemas.DatabaseMigrationSchema
    };

    // For list operations, wrap in array
    if (operation === 'list') {
      const baseSchema = schemaMap[entityName];
      return baseSchema ? baseSchema.array() : null;
    }

    return schemaMap[entityName] || null;
  }

  /**
   * Validate file upload
   * @param {File} file - File to validate
   * @param {Object} options - Validation options
   * @returns {Object} Validation result
   */
  async validateFileUpload(file, options = {}) {
    const { validateFileUpload } = await import('./middleware');
    return validateFileUpload(file, options);
  }

  /**
   * Validate authentication data
   * @param {Object} authData - Authentication data
   * @param {string} type - Type of auth ('login', 'register', 'reset', 'change')
   * @returns {Object} Validation result
   */
  validateAuth(authData, type) {
    const schemaMap = {
      login: schemas.LoginSchema,
      register: schemas.RegisterSchema,
      reset: schemas.PasswordResetSchema,
      change: schemas.PasswordChangeSchema
    };

    const schema = schemaMap[type];
    if (!schema) {
      throw new Error(`Invalid auth type: ${type}`);
    }

    return validateClientData(schema, authData);
  }

  /**
   * Validate analytics query
   * @param {Object} queryData - Analytics query data
   * @returns {Object} Validation result
   */
  validateAnalyticsQuery(queryData) {
    return validateClientData(schemas.AnalyticsQuerySchema, queryData);
  }

  /**
   * Validate workflow data
   * @param {Object} workflowData - Workflow data
   * @param {string} operation - Operation type
   * @returns {Object} Validation result
   */
  validateWorkflow(workflowData, operation = 'create') {
    const schema = operation === 'create' 
      ? schemas.WorkflowCreateSchema 
      : schemas.WorkflowUpdateSchema;
    
    return validateClientData(schema, workflowData);
  }

  /**
   * Validate social media post data
   * @param {Object} postData - Social media post data
   * @param {string} operation - Operation type
   * @returns {Object} Validation result
   */
  validateSocialPost(postData, operation = 'create') {
    const schema = operation === 'create' 
      ? schemas.SocialPostCreateSchema 
      : schemas.SocialPostUpdateSchema;
    
    return validateClientData(schema, postData);
  }

  /**
   * Validate agent invocation data
   * @param {Object} invocationData - Agent invocation data
   * @returns {Object} Validation result
   */
  validateAgentInvocation(invocationData) {
    return validateClientData(schemas.AgentInvocationCreateSchema, invocationData);
  }
}

/**
 * Custom validation error class
 */
export class ValidationError extends Error {
  constructor(message, errors = {}) {
    super(message);
    this.name = 'ValidationError';
    this.errors = errors;
    this.isValidationError = true;
  }
}

/**
 * Create a validated API client wrapper
 * @param {Object} base44Client - Base44 SDK client
 * @returns {ApiValidator} Validated API client
 */
export function createValidatedApiClient(base44Client) {
  return new ApiValidator(base44Client);
}

/**
 * Utility function to handle API errors consistently
 * @param {Error} error - Error to handle
 * @param {string} context - Context where error occurred
 * @returns {Object} Formatted error response
 */
export function handleApiError(error, context = 'API operation') {
  if (error instanceof ValidationError) {
    return {
      success: false,
      error: 'Validation failed',
      details: error.errors,
      context
    };
  }

  // Log the error for debugging
  console.error(`${context} failed:`, error);

  return {
    success: false,
    error: error.message || 'An unexpected error occurred',
    details: process.env.NODE_ENV === 'development' ? {
      stack: error.stack,
      originalError: error.originalError
    } : null,
    context
  };
}
