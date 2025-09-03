/**
 * PropTypes Helper Utility
 * Provides utilities for implementing PropTypes across the application
 */

import { PropTypes, CommonPropTypes, typeSafetyService } from '@/services/typeSafetyService';

/**
 * Higher-order component to add PropTypes validation
 * @param {React.Component} Component - Component to wrap
 * @param {Object} propTypes - PropTypes definition
 * @returns {React.Component} Wrapped component with validation
 */
export const withPropTypes = (Component, propTypes) => {
  const WrappedComponent = (props) => {
    // Validate props in development
    if (process.env.NODE_ENV === 'development') {
      typeSafetyService.validateProps(props, propTypes, Component.displayName || Component.name);
    }
    
    return <Component {...props} />;
  };
  
  WrappedComponent.displayName = `withPropTypes(${Component.displayName || Component.name})`;
  WrappedComponent.propTypes = propTypes;
  
  // Register component for tracking
  typeSafetyService.registerComponent(Component.displayName || Component.name, propTypes);
  
  return WrappedComponent;
};

/**
 * Common PropTypes definitions for UI components
 */
export const UIPropTypes = {
  // Button props
  button: {
    variant: PropTypes.oneOf(['default', 'destructive', 'outline', 'secondary', 'ghost', 'link']),
    size: PropTypes.oneOf(['default', 'sm', 'lg', 'icon']),
    asChild: PropTypes.bool,
    disabled: PropTypes.bool,
    onClick: PropTypes.func,
    children: PropTypes.node,
    className: PropTypes.string,
    type: PropTypes.oneOf(['button', 'submit', 'reset'])
  },

  // Input props
  input: {
    type: PropTypes.oneOf(['text', 'email', 'password', 'number', 'tel', 'url', 'search']),
    placeholder: PropTypes.string,
    value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    defaultValue: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    onChange: PropTypes.func,
    onBlur: PropTypes.func,
    onFocus: PropTypes.func,
    disabled: PropTypes.bool,
    required: PropTypes.bool,
    className: PropTypes.string,
    id: PropTypes.string,
    name: PropTypes.string
  },

  // Card props
  card: {
    children: PropTypes.node,
    className: PropTypes.string
  },

  // Modal/Dialog props
  modal: {
    open: PropTypes.bool,
    onOpenChange: PropTypes.func,
    children: PropTypes.node,
    title: PropTypes.string,
    description: PropTypes.string
  },

  // Table props
  table: {
    data: PropTypes.array.isRequired,
    columns: PropTypes.arrayOf(PropTypes.shape({
      key: PropTypes.string.isRequired,
      title: PropTypes.string.isRequired,
      render: PropTypes.func
    })).isRequired,
    loading: PropTypes.bool,
    onRowClick: PropTypes.func,
    className: PropTypes.string
  },

  // Form props
  form: {
    onSubmit: PropTypes.func.isRequired,
    children: PropTypes.node.isRequired,
    className: PropTypes.string,
    noValidate: PropTypes.bool
  }
};

/**
 * Business domain PropTypes
 */
export const DomainPropTypes = {
  // User props
  user: {
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
    email: CommonPropTypes.email.isRequired,
    name: PropTypes.string.isRequired,
    tier: CommonPropTypes.tier,
    company: PropTypes.string,
    avatar: PropTypes.string,
    createdAt: CommonPropTypes.date,
    updatedAt: CommonPropTypes.date
  },

  // Campaign props
  campaign: {
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
    name: PropTypes.string.isRequired,
    status: CommonPropTypes.status.isRequired,
    type: PropTypes.oneOf(['social', 'email', 'content', 'ads']),
    description: PropTypes.string,
    startDate: CommonPropTypes.date,
    endDate: CommonPropTypes.date,
    budget: PropTypes.number,
    createdBy: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    createdAt: CommonPropTypes.date,
    updatedAt: CommonPropTypes.date
  },

  // Agent props
  agent: {
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
    name: PropTypes.string.isRequired,
    type: PropTypes.oneOf([
      'strategic-planning',
      'content-creation',
      'data-analysis',
      'sales-intelligence',
      'customer-support',
      'operations-optimization',
      'financial-analysis',
      'marketing-automation',
      'hr-management',
      'custom'
    ]).isRequired,
    description: PropTypes.string,
    capabilities: PropTypes.arrayOf(PropTypes.string),
    tier: CommonPropTypes.tier,
    status: CommonPropTypes.status,
    usageCount: PropTypes.number,
    rating: PropTypes.number
  },

  // Ticket props
  ticket: {
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
    title: PropTypes.string.isRequired,
    description: PropTypes.string,
    status: PropTypes.oneOf(['open', 'in-progress', 'resolved', 'closed']).isRequired,
    priority: PropTypes.oneOf(['low', 'medium', 'high', 'urgent']),
    category: PropTypes.string,
    assignedTo: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    createdBy: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    createdAt: CommonPropTypes.date,
    updatedAt: CommonPropTypes.date,
    resolvedAt: CommonPropTypes.date
  },

  // Analytics props
  analytics: {
    metrics: PropTypes.shape({
      totalUsers: PropTypes.number,
      activeUsers: PropTypes.number,
      totalSessions: PropTypes.number,
      avgSessionDuration: PropTypes.number,
      bounceRate: PropTypes.number,
      conversionRate: PropTypes.number
    }),
    timeRange: PropTypes.oneOf(['7d', '30d', '90d', '1y']),
    data: PropTypes.array,
    loading: PropTypes.bool
  },

  // Report props
  report: {
    id: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
    title: PropTypes.string.isRequired,
    type: PropTypes.oneOf(['performance', 'usage', 'financial', 'custom']).isRequired,
    data: PropTypes.object,
    generatedAt: CommonPropTypes.date,
    generatedBy: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    format: PropTypes.oneOf(['pdf', 'excel', 'csv', 'json'])
  }
};

/**
 * Page-specific PropTypes
 */
export const PagePropTypes = {
  // Dashboard props
  dashboard: {
    user: PropTypes.shape(DomainPropTypes.user).isRequired,
    analytics: PropTypes.shape(DomainPropTypes.analytics),
    recentCampaigns: PropTypes.arrayOf(PropTypes.shape(DomainPropTypes.campaign)),
    recentTickets: PropTypes.arrayOf(PropTypes.shape(DomainPropTypes.ticket)),
    loading: PropTypes.bool
  },

  // Agent Directory props
  agentDirectory: {
    agents: PropTypes.arrayOf(PropTypes.shape(DomainPropTypes.agent)).isRequired,
    categories: PropTypes.arrayOf(PropTypes.string),
    selectedCategory: PropTypes.string,
    onCategoryChange: PropTypes.func,
    onAgentSelect: PropTypes.func,
    loading: PropTypes.bool
  },

  // Campaign Manager props
  campaignManager: {
    campaigns: PropTypes.arrayOf(PropTypes.shape(DomainPropTypes.campaign)).isRequired,
    onCreateCampaign: PropTypes.func.isRequired,
    onEditCampaign: PropTypes.func.isRequired,
    onDeleteCampaign: PropTypes.func.isRequired,
    loading: PropTypes.bool,
    filters: PropTypes.shape({
      status: PropTypes.string,
      type: PropTypes.string,
      dateRange: PropTypes.string
    })
  },

  // Analytics Page props
  analyticsPage: {
    data: PropTypes.shape(DomainPropTypes.analytics).isRequired,
    timeRange: PropTypes.string,
    onTimeRangeChange: PropTypes.func,
    charts: PropTypes.arrayOf(PropTypes.shape({
      id: PropTypes.string.isRequired,
      title: PropTypes.string.isRequired,
      type: PropTypes.oneOf(['line', 'bar', 'pie', 'area']).isRequired,
      data: PropTypes.array.isRequired
    })),
    loading: PropTypes.bool
  }
};

/**
 * Component PropTypes
 */
export const ComponentPropTypes = {
  // Navigation props
  navigation: {
    items: PropTypes.arrayOf(PropTypes.shape({
      id: PropTypes.string.isRequired,
      label: PropTypes.string.isRequired,
      href: PropTypes.string,
      icon: PropTypes.elementType,
      children: PropTypes.array
    })).isRequired,
    activeItem: PropTypes.string,
    onItemClick: PropTypes.func,
    collapsed: PropTypes.bool
  },

  // Header props
  header: {
    title: PropTypes.string,
    user: PropTypes.shape(DomainPropTypes.user),
    onUserMenuClick: PropTypes.func,
    notifications: PropTypes.arrayOf(PropTypes.shape({
      id: PropTypes.string.isRequired,
      title: PropTypes.string.isRequired,
      message: PropTypes.string,
      type: PropTypes.oneOf(['info', 'success', 'warning', 'error']),
      read: PropTypes.bool,
      createdAt: CommonPropTypes.date
    })),
    onNotificationClick: PropTypes.func
  },

  // Footer props
  footer: {
    links: PropTypes.arrayOf(PropTypes.shape({
      label: PropTypes.string.isRequired,
      href: PropTypes.string.isRequired
    })),
    copyright: PropTypes.string,
    version: PropTypes.string
  },

  // Error Boundary props
  errorBoundary: {
    children: PropTypes.node.isRequired,
    fallback: PropTypes.elementType,
    onError: PropTypes.func,
    resetOnPropsChange: PropTypes.array
  }
};

/**
 * Validation utilities
 */
export const ValidationUtils = {
  /**
   * Create a required version of a PropType
   * @param {Function} propType - PropType validator
   * @returns {Function} Required PropType validator
   */
  required: (propType) => {
    const validator = (props, propName, componentName) => {
      if (props[propName] == null) {
        return new Error(`Required prop \`${propName}\` was not specified in \`${componentName}\`.`);
      }
      return propType(props, propName, componentName);
    };
    validator.isRequired = validator;
    return validator;
  },

  /**
   * Create a conditional PropType (required if condition is met)
   * @param {Function} condition - Condition function
   * @param {Function} propType - PropType validator
   * @returns {Function} Conditional PropType validator
   */
  requiredIf: (condition, propType) => (props, propName, componentName) => {
    if (condition(props)) {
      if (props[propName] == null) {
        return new Error(`Prop \`${propName}\` is required in \`${componentName}\` when condition is met.`);
      }
    }
    return propType(props, propName, componentName);
  },

  /**
   * Create a deprecated PropType warning
   * @param {Function} propType - PropType validator
   * @param {string} message - Deprecation message
   * @returns {Function} Deprecated PropType validator
   */
  deprecated: (propType, message) => (props, propName, componentName) => {
    if (props[propName] != null) {
      console.warn(`Warning: Prop \`${propName}\` in \`${componentName}\` is deprecated. ${message}`);
    }
    return propType(props, propName, componentName);
  }
};

/**
 * Development-only PropTypes validation
 * @param {React.Component} Component - Component to validate
 * @param {Object} propTypes - PropTypes definition
 */
export const addPropTypes = (Component, propTypes) => {
  if (process.env.NODE_ENV === 'development') {
    Component.propTypes = propTypes;
    
    // Register with type safety service
    typeSafetyService.registerComponent(
      Component.displayName || Component.name,
      propTypes
    );
  }
};

/**
 * Get PropTypes for a specific domain
 * @param {string} domain - Domain name
 * @returns {Object} PropTypes for the domain
 */
export const getPropTypesForDomain = (domain) => {
  const domains = {
    ui: UIPropTypes,
    domain: DomainPropTypes,
    page: PagePropTypes,
    component: ComponentPropTypes
  };
  
  return domains[domain] || {};
};

export default {
  PropTypes,
  CommonPropTypes,
  UIPropTypes,
  DomainPropTypes,
  PagePropTypes,
  ComponentPropTypes,
  ValidationUtils,
  withPropTypes,
  addPropTypes,
  getPropTypesForDomain
};
