import { useState, useCallback, useMemo } from 'react';
import { validateClientData, sanitizeAndValidate } from '@/lib/validation/middleware';

/**
 * Custom hook for form validation using Zod schemas
 * @param {Object} schema - Zod schema for validation
 * @param {Object} initialData - Initial form data
 * @param {Object} options - Validation options
 * @returns {Object} Validation utilities and state
 */
export const useValidation = (schema, initialData = {}, options = {}) => {
  const {
    validateOnChange = false,
    validateOnBlur = true,
    sanitize = true
  } = options;

  const [data, setData] = useState(initialData);
  const [errors, setErrors] = useState({});
  const [touched, setTouched] = useState({});
  const [isValidating, setIsValidating] = useState(false);

  // Validate a single field
  const validateField = useCallback((fieldName, value) => {
    try {
      // Create a partial schema for the specific field
      const fieldSchema = schema.pick({ [fieldName]: true });
      const result = validateClientData(fieldSchema, { [fieldName]: value });
      
      if (result.success) {
        setErrors(prev => {
          const newErrors = { ...prev };
          delete newErrors[fieldName];
          return newErrors;
        });
        return null;
      } else {
        const fieldError = result.errors[fieldName];
        setErrors(prev => ({
          ...prev,
          [fieldName]: fieldError
        }));
        return fieldError;
      }
    } catch (error) {
      const errorMessage = 'Validation error';
      setErrors(prev => ({
        ...prev,
        [fieldName]: errorMessage
      }));
      return errorMessage;
    }
  }, [schema]);

  // Validate all data
  const validateAll = useCallback(async () => {
    setIsValidating(true);
    
    try {
      const validationFn = sanitize ? sanitizeAndValidate : validateClientData;
      const result = validationFn(schema, data);
      
      if (result.success) {
        setErrors({});
        return { success: true, data: result.data };
      } else {
        const formattedErrors = Array.isArray(result.errors) 
          ? result.errors.reduce((acc, err) => {
              const field = err.path?.join('.') || 'general';
              acc[field] = err.message;
              return acc;
            }, {})
          : result.errors || {};
        
        setErrors(formattedErrors);
        return { success: false, errors: formattedErrors };
      }
    } catch (error) {
      const generalError = { general: 'Validation failed' };
      setErrors(generalError);
      return { success: false, errors: generalError };
    } finally {
      setIsValidating(false);
    }
  }, [schema, data, sanitize]);

  // Update field value
  const updateField = useCallback((fieldName, value) => {
    setData(prev => ({
      ...prev,
      [fieldName]: value
    }));

    if (validateOnChange) {
      validateField(fieldName, value);
    }
  }, [validateOnChange, validateField]);

  // Handle field blur
  const handleBlur = useCallback((fieldName) => {
    setTouched(prev => ({
      ...prev,
      [fieldName]: true
    }));

    if (validateOnBlur) {
      validateField(fieldName, data[fieldName]);
    }
  }, [validateOnBlur, validateField, data]);

  // Reset form
  const reset = useCallback((newData = initialData) => {
    setData(newData);
    setErrors({});
    setTouched({});
    setIsValidating(false);
  }, [initialData]);

  // Set multiple fields at once
  const setFields = useCallback((newFields) => {
    setData(prev => ({
      ...prev,
      ...newFields
    }));
  }, []);

  // Check if form is valid
  const isValid = useMemo(() => {
    return Object.keys(errors).length === 0;
  }, [errors]);

  // Check if form has been touched
  const isDirty = useMemo(() => {
    return Object.keys(touched).length > 0;
  }, [touched]);

  // Get field error
  const getFieldError = useCallback((fieldName) => {
    return errors[fieldName] || null;
  }, [errors]);

  // Check if field has error
  const hasFieldError = useCallback((fieldName) => {
    return Boolean(errors[fieldName]);
  }, [errors]);

  // Check if field is touched
  const isFieldTouched = useCallback((fieldName) => {
    return Boolean(touched[fieldName]);
  }, [touched]);

  return {
    // Data
    data,
    errors,
    touched,
    
    // State
    isValid,
    isDirty,
    isValidating,
    
    // Actions
    updateField,
    handleBlur,
    validateField,
    validateAll,
    reset,
    setFields,
    
    // Utilities
    getFieldError,
    hasFieldError,
    isFieldTouched
  };
};

/**
 * Hook for validating API responses
 * @param {Object} schema - Zod schema for validation
 * @returns {Function} Validation function
 */
export const useApiValidation = (schema) => {
  const validateResponse = useCallback(async (data) => {
    try {
      const validatedData = schema.parse(data);
      return {
        success: true,
        data: validatedData,
        errors: null
      };
    } catch (error) {
      console.error('API validation failed:', error);
      
      return {
        success: false,
        data: null,
        errors: error.errors || [{ message: 'Validation failed' }]
      };
    }
  }, [schema]);

  return validateResponse;
};

/**
 * Hook for batch validation of multiple items
 * @param {Array} schemas - Array of schemas to validate against
 * @returns {Function} Batch validation function
 */
export const useBatchValidation = (schemas) => {
  const [isValidating, setIsValidating] = useState(false);
  const [results, setResults] = useState([]);

  const validateBatch = useCallback(async (dataArray) => {
    setIsValidating(true);
    
    try {
      const validationPromises = dataArray.map(async (data, index) => {
        const schema = schemas[index] || schemas[0]; // Use first schema as fallback
        const result = validateClientData(schema, data);
        
        return {
          index,
          ...result
        };
      });

      const batchResults = await Promise.all(validationPromises);
      setResults(batchResults);
      
      const hasErrors = batchResults.some(result => !result.success);
      
      return {
        success: !hasErrors,
        results: batchResults,
        errors: hasErrors ? batchResults.filter(r => !r.success) : null
      };
    } catch (error) {
      const errorResult = {
        success: false,
        results: [],
        errors: [{ message: 'Batch validation failed' }]
      };
      
      setResults([]);
      return errorResult;
    } finally {
      setIsValidating(false);
    }
  }, [schemas]);

  return {
    validateBatch,
    isValidating,
    results
  };
};

/**
 * Hook for real-time validation with debouncing
 * @param {Object} schema - Zod schema for validation
 * @param {number} debounceMs - Debounce delay in milliseconds
 * @returns {Object} Validation utilities
 */
export const useRealtimeValidation = (schema, debounceMs = 300) => {
  const [data, setData] = useState({});
  const [errors, setErrors] = useState({});
  const [isValidating, setIsValidating] = useState(false);

  // Debounced validation function
  const debouncedValidate = useMemo(() => {
    let timeoutId;
    
    return (fieldName, value) => {
      clearTimeout(timeoutId);
      setIsValidating(true);
      
      timeoutId = setTimeout(() => {
        try {
          const fieldSchema = schema.pick({ [fieldName]: true });
          const result = validateClientData(fieldSchema, { [fieldName]: value });
          
          if (result.success) {
            setErrors(prev => {
              const newErrors = { ...prev };
              delete newErrors[fieldName];
              return newErrors;
            });
          } else {
            setErrors(prev => ({
              ...prev,
              [fieldName]: result.errors[fieldName]
            }));
          }
        } catch (error) {
          setErrors(prev => ({
            ...prev,
            [fieldName]: 'Validation error'
          }));
        } finally {
          setIsValidating(false);
        }
      }, debounceMs);
    };
  }, [schema, debounceMs]);

  const updateField = useCallback((fieldName, value) => {
    setData(prev => ({
      ...prev,
      [fieldName]: value
    }));
    
    debouncedValidate(fieldName, value);
  }, [debouncedValidate]);

  return {
    data,
    errors,
    isValidating,
    updateField
  };
};
