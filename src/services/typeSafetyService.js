/**
 * Type Safety Service
 * Provides comprehensive type safety utilities and PropTypes definitions
 */

// Common PropTypes definitions for reuse across components
export const CommonPropTypes = {
  // Basic types
  id: (props, propName, componentName) => {
    const value = props[propName];
    if (value != null && (typeof value !== 'string' && typeof value !== 'number')) {
      return new Error(`Invalid prop \`${propName}\` of type \`${typeof value}\` supplied to \`${componentName}\`, expected \`string\` or \`number\`.`);
    }
  },

  // User object
  user: (props, propName, componentName) => {
    const user = props[propName];
    if (user == null) return null;
    
    if (typeof user !== 'object') {
      return new Error(`Invalid prop \`${propName}\` of type \`${typeof user}\` supplied to \`${componentName}\`, expected \`object\`.`);
    }
    
    const requiredFields = ['id', 'email', 'name'];
    for (const field of requiredFields) {
      if (!user[field]) {
        return new Error(`Missing required field \`${field}\` in user object supplied to \`${componentName}\`.`);
      }
    }
    
    if (user.tier && !['solopreneur', 'startup', 'sme', 'enterprise'].includes(user.tier)) {
      return new Error(`Invalid user tier \`${user.tier}\` supplied to \`${componentName}\`.`);
    }
  },

  // Campaign object
  campaign: (props, propName, componentName) => {
    const campaign = props[propName];
    if (campaign == null) return null;
    
    if (typeof campaign !== 'object') {
      return new Error(`Invalid prop \`${propName}\` of type \`${typeof campaign}\` supplied to \`${componentName}\`, expected \`object\`.`);
    }
    
    const requiredFields = ['id', 'name', 'status'];
    for (const field of requiredFields) {
      if (!campaign[field]) {
        return new Error(`Missing required field \`${field}\` in campaign object supplied to \`${componentName}\`.`);
      }
    }
  },

  // Agent object
  agent: (props, propName, componentName) => {
    const agent = props[propName];
    if (agent == null) return null;
    
    if (typeof agent !== 'object') {
      return new Error(`Invalid prop \`${propName}\` of type \`${typeof agent}\` supplied to \`${componentName}\`, expected \`object\`.`);
    }
    
    const requiredFields = ['id', 'name', 'type'];
    for (const field of requiredFields) {
      if (!agent[field]) {
        return new Error(`Missing required field \`${field}\` in agent object supplied to \`${componentName}\`.`);
      }
    }
  },

  // Event handler
  eventHandler: (props, propName, componentName) => {
    const handler = props[propName];
    if (handler != null && typeof handler !== 'function') {
      return new Error(`Invalid prop \`${propName}\` of type \`${typeof handler}\` supplied to \`${componentName}\`, expected \`function\`.`);
    }
  },

  // Children with specific types
  reactNode: (props, propName, componentName) => {
    const children = props[propName];
    if (children == null) return null;
    
    const validTypes = ['string', 'number', 'object'];
    if (!validTypes.includes(typeof children)) {
      return new Error(`Invalid prop \`${propName}\` of type \`${typeof children}\` supplied to \`${componentName}\`, expected React node.`);
    }
  },

  // Email validation
  email: (props, propName, componentName) => {
    const email = props[propName];
    if (email == null) return null;
    
    if (typeof email !== 'string') {
      return new Error(`Invalid prop \`${propName}\` of type \`${typeof email}\` supplied to \`${componentName}\`, expected \`string\`.`);
    }
    
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      return new Error(`Invalid email format in prop \`${propName}\` supplied to \`${componentName}\`.`);
    }
  },

  // URL validation
  url: (props, propName, componentName) => {
    const url = props[propName];
    if (url == null) return null;
    
    if (typeof url !== 'string') {
      return new Error(`Invalid prop \`${propName}\` of type \`${typeof url}\` supplied to \`${componentName}\`, expected \`string\`.`);
    }
    
    try {
      new URL(url);
    } catch {
      return new Error(`Invalid URL format in prop \`${propName}\` supplied to \`${componentName}\`.`);
    }
  },

  // Date validation
  date: (props, propName, componentName) => {
    const date = props[propName];
    if (date == null) return null;
    
    if (!(date instanceof Date) && typeof date !== 'string') {
      return new Error(`Invalid prop \`${propName}\` of type \`${typeof date}\` supplied to \`${componentName}\`, expected \`Date\` or \`string\`.`);
    }
    
    if (typeof date === 'string') {
      const parsedDate = new Date(date);
      if (isNaN(parsedDate.getTime())) {
        return new Error(`Invalid date string in prop \`${propName}\` supplied to \`${componentName}\`.`);
      }
    }
  },

  // Status enum
  status: (props, propName, componentName) => {
    const status = props[propName];
    if (status == null) return null;
    
    const validStatuses = ['active', 'inactive', 'pending', 'completed', 'cancelled', 'draft'];
    if (!validStatuses.includes(status)) {
      return new Error(`Invalid status \`${status}\` in prop \`${propName}\` supplied to \`${componentName}\`. Expected one of: ${validStatuses.join(', ')}.`);
    }
  },

  // Tier validation
  tier: (props, propName, componentName) => {
    const tier = props[propName];
    if (tier == null) return null;
    
    const validTiers = ['solopreneur', 'startup', 'sme', 'enterprise'];
    if (!validTiers.includes(tier)) {
      return new Error(`Invalid tier \`${tier}\` in prop \`${propName}\` supplied to \`${componentName}\`. Expected one of: ${validTiers.join(', ')}.`);
    }
  }
};

// PropTypes factory functions
export const createPropTypes = {
  // Array of specific type
  arrayOf: (validator) => (props, propName, componentName) => {
    const array = props[propName];
    if (array == null) return null;
    
    if (!Array.isArray(array)) {
      return new Error(`Invalid prop \`${propName}\` of type \`${typeof array}\` supplied to \`${componentName}\`, expected \`array\`.`);
    }
    
    for (let i = 0; i < array.length; i++) {
      const error = validator({ [propName]: array[i] }, propName, `${componentName}[${i}]`);
      if (error) return error;
    }
  },

  // Object with specific shape
  shape: (shape) => (props, propName, componentName) => {
    const obj = props[propName];
    if (obj == null) return null;
    
    if (typeof obj !== 'object') {
      return new Error(`Invalid prop \`${propName}\` of type \`${typeof obj}\` supplied to \`${componentName}\`, expected \`object\`.`);
    }
    
    for (const [key, validator] of Object.entries(shape)) {
      const error = validator({ [key]: obj[key] }, key, componentName);
      if (error) return error;
    }
  },

  // One of specific values
  oneOf: (values) => (props, propName, componentName) => {
    const value = props[propName];
    if (value == null) return null;
    
    if (!values.includes(value)) {
      return new Error(`Invalid prop \`${propName}\` of value \`${value}\` supplied to \`${componentName}\`, expected one of: ${values.join(', ')}.`);
    }
  },

  // One of specific types
  oneOfType: (validators) => (props, propName, componentName) => {
    const value = props[propName];
    if (value == null) return null;
    
    for (const validator of validators) {
      const error = validator(props, propName, componentName);
      if (!error) return null;
    }
    
    return new Error(`Invalid prop \`${propName}\` supplied to \`${componentName}\`, none of the expected types matched.`);
  }
};

// Basic PropTypes (similar to React PropTypes)
export const PropTypes = {
  any: () => null,
  array: (props, propName, componentName) => {
    const value = props[propName];
    if (value != null && !Array.isArray(value)) {
      return new Error(`Invalid prop \`${propName}\` of type \`${typeof value}\` supplied to \`${componentName}\`, expected \`array\`.`);
    }
  },
  bool: (props, propName, componentName) => {
    const value = props[propName];
    if (value != null && typeof value !== 'boolean') {
      return new Error(`Invalid prop \`${propName}\` of type \`${typeof value}\` supplied to \`${componentName}\`, expected \`boolean\`.`);
    }
  },
  func: (props, propName, componentName) => {
    const value = props[propName];
    if (value != null && typeof value !== 'function') {
      return new Error(`Invalid prop \`${propName}\` of type \`${typeof value}\` supplied to \`${componentName}\`, expected \`function\`.`);
    }
  },
  number: (props, propName, componentName) => {
    const value = props[propName];
    if (value != null && typeof value !== 'number') {
      return new Error(`Invalid prop \`${propName}\` of type \`${typeof value}\` supplied to \`${componentName}\`, expected \`number\`.`);
    }
  },
  object: (props, propName, componentName) => {
    const value = props[propName];
    if (value != null && (typeof value !== 'object' || Array.isArray(value))) {
      return new Error(`Invalid prop \`${propName}\` of type \`${typeof value}\` supplied to \`${componentName}\`, expected \`object\`.`);
    }
  },
  string: (props, propName, componentName) => {
    const value = props[propName];
    if (value != null && typeof value !== 'string') {
      return new Error(`Invalid prop \`${propName}\` of type \`${typeof value}\` supplied to \`${componentName}\`, expected \`string\`.`);
    }
  },
  symbol: (props, propName, componentName) => {
    const value = props[propName];
    if (value != null && typeof value !== 'symbol') {
      return new Error(`Invalid prop \`${propName}\` of type \`${typeof value}\` supplied to \`${componentName}\`, expected \`symbol\`.`);
    }
  },
  node: CommonPropTypes.reactNode,
  element: (props, propName, componentName) => {
    const value = props[propName];
    if (value != null && (!value || typeof value.type !== 'string' && typeof value.type !== 'function')) {
      return new Error(`Invalid prop \`${propName}\` supplied to \`${componentName}\`, expected a React element.`);
    }
  },
  instanceOf: (expectedClass) => (props, propName, componentName) => {
    const value = props[propName];
    if (value != null && !(value instanceof expectedClass)) {
      return new Error(`Invalid prop \`${propName}\` supplied to \`${componentName}\`, expected instance of \`${expectedClass.name}\`.`);
    }
  },
  oneOf: createPropTypes.oneOf,
  oneOfType: createPropTypes.oneOfType,
  arrayOf: createPropTypes.arrayOf,
  objectOf: (validator) => (props, propName, componentName) => {
    const obj = props[propName];
    if (obj == null) return null;
    
    if (typeof obj !== 'object' || Array.isArray(obj)) {
      return new Error(`Invalid prop \`${propName}\` of type \`${typeof obj}\` supplied to \`${componentName}\`, expected \`object\`.`);
    }
    
    for (const [key, value] of Object.entries(obj)) {
      const error = validator({ [key]: value }, key, componentName);
      if (error) return error;
    }
  },
  shape: createPropTypes.shape,
  exact: (shape) => (props, propName, componentName) => {
    const obj = props[propName];
    if (obj == null) return null;
    
    if (typeof obj !== 'object' || Array.isArray(obj)) {
      return new Error(`Invalid prop \`${propName}\` of type \`${typeof obj}\` supplied to \`${componentName}\`, expected \`object\`.`);
    }
    
    // Check for extra properties
    const shapeKeys = Object.keys(shape);
    const objKeys = Object.keys(obj);
    const extraKeys = objKeys.filter(key => !shapeKeys.includes(key));
    
    if (extraKeys.length > 0) {
      return new Error(`Invalid prop \`${propName}\` supplied to \`${componentName}\`, unexpected properties: ${extraKeys.join(', ')}.`);
    }
    
    // Validate shape
    return createPropTypes.shape(shape)(props, propName, componentName);
  }
};

// Add isRequired to all PropTypes
Object.keys(PropTypes).forEach(key => {
  const validator = PropTypes[key];
  PropTypes[key].isRequired = (props, propName, componentName) => {
    if (props[propName] == null) {
      return new Error(`Required prop \`${propName}\` was not specified in \`${componentName}\`.`);
    }
    return validator(props, propName, componentName);
  };
});

// Type safety validation service
class TypeSafetyService {
  constructor() {
    this.validationErrors = [];
    this.componentValidations = new Map();
  }

  /**
   * Validate component props
   * @param {Object} props - Component props
   * @param {Object} propTypes - PropTypes definition
   * @param {string} componentName - Component name
   */
  validateProps(props, propTypes, componentName) {
    if (!propTypes || typeof propTypes !== 'object') {
      return;
    }

    const errors = [];
    
    for (const [propName, validator] of Object.entries(propTypes)) {
      if (typeof validator === 'function') {
        const error = validator(props, propName, componentName);
        if (error) {
          errors.push(error);
          this.validationErrors.push({
            component: componentName,
            prop: propName,
            error: error.message,
            timestamp: new Date().toISOString()
          });
        }
      }
    }

    if (errors.length > 0) {
      console.group(`PropTypes validation failed for ${componentName}`);
      errors.forEach(error => console.error(error.message));
      console.groupEnd();
    }

    return errors;
  }

  /**
   * Register component validation
   * @param {string} componentName - Component name
   * @param {Object} propTypes - PropTypes definition
   */
  registerComponent(componentName, propTypes) {
    this.componentValidations.set(componentName, propTypes);
  }

  /**
   * Get validation statistics
   */
  getValidationStats() {
    return {
      totalErrors: this.validationErrors.length,
      componentsRegistered: this.componentValidations.size,
      recentErrors: this.validationErrors.slice(-10),
      errorsByComponent: this.validationErrors.reduce((acc, error) => {
        acc[error.component] = (acc[error.component] || 0) + 1;
        return acc;
      }, {})
    };
  }

  /**
   * Clear validation errors
   */
  clearErrors() {
    this.validationErrors = [];
  }
}

// Create and export singleton instance
export const typeSafetyService = new TypeSafetyService();

// Export everything
export default {
  PropTypes,
  CommonPropTypes,
  createPropTypes,
  typeSafetyService
};
