import { ZodError } from 'zod';

/**
 * Validation middleware for API requests
 * @param {Object} schema - Zod schema to validate against
 * @param {string} source - Where to get data from ('body', 'query', 'params')
 * @returns {Function} Express middleware function
 */
export const validateRequest = (schema, source = 'body') => {
  return (req, res, next) => {
    try {
      const data = req[source];
      const validatedData = schema.parse(data);
      
      // Replace the original data with validated data
      req[source] = validatedData;
      next();
    } catch (error) {
      if (error instanceof ZodError) {
        const formattedErrors = error.errors.map(err => ({
          field: err.path.join('.'),
          message: err.message,
          code: err.code,
          received: err.received
        }));

        return res.status(400).json({
          success: false,
          error: 'Validation failed',
          details: formattedErrors,
          timestamp: new Date().toISOString()
        });
      }
      
      // Handle other types of errors
      return res.status(500).json({
        success: false,
        error: 'Internal validation error',
        timestamp: new Date().toISOString()
      });
    }
  };
};

/**
 * Client-side validation helper
 * @param {Object} schema - Zod schema to validate against
 * @param {Object} data - Data to validate
 * @returns {Object} Validation result
 */
export const validateClientData = (schema, data) => {
  try {
    const validatedData = schema.parse(data);
    return {
      success: true,
      data: validatedData,
      errors: null
    };
  } catch (error) {
    if (error instanceof ZodError) {
      const formattedErrors = error.errors.reduce((acc, err) => {
        const field = err.path.join('.');
        acc[field] = err.message;
        return acc;
      }, {});

      return {
        success: false,
        data: null,
        errors: formattedErrors
      };
    }
    
    return {
      success: false,
      data: null,
      errors: { general: 'Validation failed' }
    };
  }
};

/**
 * React Hook Form resolver for Zod schemas
 * @param {Object} schema - Zod schema to validate against
 * @returns {Function} Resolver function for React Hook Form
 */
export const zodResolver = (schema) => {
  return async (data) => {
    try {
      const validatedData = schema.parse(data);
      return {
        values: validatedData,
        errors: {}
      };
    } catch (error) {
      if (error instanceof ZodError) {
        const formattedErrors = error.errors.reduce((acc, err) => {
          const field = err.path.join('.');
          acc[field] = {
            type: err.code,
            message: err.message
          };
          return acc;
        }, {});

        return {
          values: {},
          errors: formattedErrors
        };
      }
      
      return {
        values: {},
        errors: {
          root: {
            type: 'validation',
            message: 'Validation failed'
          }
        }
      };
    }
  };
};

/**
 * Sanitize and validate form data
 * @param {Object} schema - Zod schema to validate against
 * @param {Object} data - Raw form data
 * @returns {Object} Sanitized and validated data
 */
export const sanitizeAndValidate = (schema, data) => {
  try {
    // First, sanitize the data by removing any undefined values
    const sanitizedData = Object.keys(data).reduce((acc, key) => {
      if (data[key] !== undefined && data[key] !== null && data[key] !== '') {
        acc[key] = data[key];
      }
      return acc;
    }, {});

    // Then validate with the schema
    const validatedData = schema.parse(sanitizedData);
    
    return {
      success: true,
      data: validatedData,
      errors: null
    };
  } catch (error) {
    if (error instanceof ZodError) {
      return {
        success: false,
        data: null,
        errors: error.errors
      };
    }
    
    return {
      success: false,
      data: null,
      errors: [{ message: 'Validation failed' }]
    };
  }
};

/**
 * Validate API response data
 * @param {Object} schema - Zod schema to validate against
 * @param {Object} data - Response data to validate
 * @returns {Object} Validation result
 */
export const validateApiResponse = (schema, data) => {
  try {
    const validatedData = schema.parse(data);
    return {
      success: true,
      data: validatedData
    };
  } catch (error) {
    console.error('API Response validation failed:', error);
    
    // In development, throw the error to help with debugging
    if (process.env.NODE_ENV === 'development') {
      throw new Error(`API Response validation failed: ${error.message}`);
    }
    
    // In production, return the original data with a warning
    return {
      success: false,
      data: data,
      warning: 'Response validation failed'
    };
  }
};

/**
 * Create a validation error response
 * @param {Array} errors - Array of validation errors
 * @param {string} message - Custom error message
 * @returns {Object} Formatted error response
 */
export const createValidationError = (errors, message = 'Validation failed') => {
  return {
    success: false,
    error: message,
    details: errors,
    timestamp: new Date().toISOString()
  };
};

/**
 * Batch validate multiple data objects
 * @param {Array} validations - Array of {schema, data} objects
 * @returns {Object} Batch validation result
 */
export const batchValidate = (validations) => {
  const results = [];
  let hasErrors = false;

  for (let i = 0; i < validations.length; i++) {
    const { schema, data, name } = validations[i];
    const result = validateClientData(schema, data);
    
    results.push({
      name: name || `item_${i}`,
      ...result
    });
    
    if (!result.success) {
      hasErrors = true;
    }
  }

  return {
    success: !hasErrors,
    results: results,
    errors: hasErrors ? results.filter(r => !r.success) : null
  };
};

/**
 * Enhanced file upload validation with security integration
 * @param {File} file - File object to validate
 * @param {Object} options - Validation options
 * @returns {Promise<Object>} Validation result
 */
export const validateFileUpload = async (file, options = {}) => {
  const {
    maxSize = 50 * 1024 * 1024, // 50MB default
    allowedTypes = [
      'image/jpeg', 'image/png', 'image/gif', 'image/webp',
      'application/pdf', 'text/csv', 'application/json'
    ],
    maxFilenameLength = 255,
    purpose = 'general',
    userId = null,
    enableSecurityScan = true
  } = options;

  const errors = [];

  // Basic validation
  if (file.size === 0) {
    errors.push({
      field: 'size',
      message: 'File is empty'
    });
  }

  if (file.size > maxSize) {
    errors.push({
      field: 'size',
      message: `File size must be less than ${Math.round(maxSize / 1024 / 1024)}MB`
    });
  }

  // Check file type
  if (!allowedTypes.includes(file.type)) {
    errors.push({
      field: 'type',
      message: `File type ${file.type} is not allowed`
    });
  }

  // Check filename length
  if (file.name.length > maxFilenameLength) {
    errors.push({
      field: 'filename',
      message: `Filename must be less than ${maxFilenameLength} characters`
    });
  }

  // Check for potentially dangerous filenames
  const dangerousPatterns = [
    /\.\./,  // Directory traversal
    /[<>:"|?*]/,  // Invalid filename characters
    /^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])$/i  // Reserved Windows names
  ];

  if (dangerousPatterns.some(pattern => pattern.test(file.name))) {
    errors.push({
      field: 'filename',
      message: 'Filename contains invalid characters'
    });
  }

  // If basic validation fails, return early
  if (errors.length > 0) {
    return {
      success: false,
      errors: errors,
      file: null
    };
  }

  // Enhanced security scan
  let scanResult = null;
  if (enableSecurityScan) {
    try {
      const { fileSecurityService } = await import('@/services/fileSecurityService');
      scanResult = await fileSecurityService.scanFile(file, {
        purpose,
        userId,
        deepScan: true
      });

      if (!scanResult.allowed) {
        errors.push({
          field: 'security',
          message: `Security scan failed: ${scanResult.threats.join(', ')}`
        });
      }
    } catch (error) {
      console.error('Security scan failed:', error);
      errors.push({
        field: 'security',
        message: 'Security scan failed - file rejected for safety'
      });
    }
  }

  return {
    success: errors.length === 0,
    errors: errors.length > 0 ? errors : null,
    scanResult,
    file: errors.length === 0 ? {
      name: file.name,
      size: file.size,
      type: file.type,
      lastModified: file.lastModified
    } : null
  };
};
