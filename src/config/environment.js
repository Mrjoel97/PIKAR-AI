/**
 * Environment Configuration
 * Centralized configuration management with validation and type safety
 */

import { z } from 'zod';

// Environment variable schema for validation
const EnvironmentSchema = z.object({
  // Application Environment
  NODE_ENV: z.enum(['development', 'staging', 'production']).default('development'),
  
  // API Configuration
  VITE_API_BASE_URL: z.string().url().default('https://api.pikar-ai.com'),
  VITE_APP_BASE_URL: z.string().url().default('https://pikar-ai3.vercel.app'),
  VITE_SUPABASE_URL: z.string().url().optional(),
  VITE_SUPABASE_ANON_KEY: z.string().optional(),
  VITE_API_TIMEOUT: z.string().transform(Number).pipe(z.number().positive()).default('30000'),
  VITE_API_RETRIES: z.string().transform(Number).pipe(z.number().min(0).max(5)).default('3'),
  
  // Authentication
  VITE_JWT_SECRET: z.string().min(32).optional(),
  VITE_JWT_EXPIRES_IN: z.string().default('15m'),
  VITE_REFRESH_TOKEN_EXPIRES_IN: z.string().default('7d'),
  
  // Security Configuration
  VITE_ENABLE_CSP: z.string().transform(val => val === 'true').default('true'),
  VITE_ENABLE_HSTS: z.string().transform(val => val === 'true').default('false'),
  VITE_CSP_REPORT_URI: z.string().url().optional(),
  VITE_SECURITY_HEADERS: z.string().transform(val => val === 'true').default('true'),
  
  // Encryption
  VITE_ENCRYPTION_KEY_LENGTH: z.string().transform(Number).pipe(z.number().min(128).max(512)).default('256'),
  VITE_PBKDF2_ITERATIONS: z.string().transform(Number).pipe(z.number().min(10000)).default('100000'),
  
  // File Upload
  VITE_MAX_FILE_SIZE: z.string().transform(Number).pipe(z.number().positive()).default('52428800'), // 50MB
  VITE_ALLOWED_FILE_TYPES: z.string().default('image/*,application/pdf,.doc,.docx,.txt'),
  VITE_ENABLE_VIRUS_SCAN: z.string().transform(val => val === 'true').default('true'),
  
  // Monitoring & Analytics
  VITE_SENTRY_DSN: z.string().url().optional(),
  VITE_GA_TRACKING_ID: z.string().optional(),
  VITE_HOTJAR_ID: z.string().optional(),
  VITE_ENABLE_ANALYTICS: z.string().transform(val => val === 'true').default('false'),
  
  // Feature Flags
  VITE_ENABLE_AI_AGENTS: z.string().transform(val => val === 'true').default('true'),
  VITE_ENABLE_SOCIAL_MEDIA: z.string().transform(val => val === 'true').default('true'),
  VITE_ENABLE_QMS: z.string().transform(val => val === 'true').default('true'),
  VITE_ENABLE_COMPLIANCE: z.string().transform(val => val === 'true').default('true'),
  VITE_ENABLE_BETA_FEATURES: z.string().transform(val => val === 'true').default('false'),
  
  // Performance
  VITE_ENABLE_CODE_SPLITTING: z.string().transform(val => val === 'true').default('true'),
  VITE_ENABLE_SERVICE_WORKER: z.string().transform(val => val === 'true').default('false'),
  VITE_CACHE_DURATION: z.string().transform(Number).pipe(z.number().positive()).default('3600'), // 1 hour
  
  // Development
  VITE_ENABLE_DEBUG: z.string().transform(val => val === 'true').default('false'),
  VITE_ENABLE_MOCK_DATA: z.string().transform(val => val === 'true').default('false'),
  VITE_LOG_LEVEL: z.enum(['error', 'warn', 'info', 'debug']).default('info'),
  
  // External Services
  VITE_STRIPE_PUBLIC_KEY: z.string().optional(),
  VITE_GOOGLE_MAPS_API_KEY: z.string().optional(),
  VITE_RECAPTCHA_SITE_KEY: z.string().optional(),

  // Payment Link fallbacks (optional)
  VITE_PAYMENT_LINK_SOLO_MONTHLY: z.string().url().optional(),
  VITE_PAYMENT_LINK_SOLO_YEARLY: z.string().url().optional(),
  VITE_PAYMENT_LINK_STARTUP_MONTHLY: z.string().url().optional(),
  VITE_PAYMENT_LINK_STARTUP_YEARLY: z.string().url().optional(),
  VITE_PAYMENT_LINK_SME_MONTHLY: z.string().url().optional(),
  VITE_PAYMENT_LINK_SME_YEARLY: z.string().url().optional(),
  
  // Social Media APIs
  VITE_FACEBOOK_APP_ID: z.string().optional(),
  VITE_TWITTER_API_KEY: z.string().optional(),
  VITE_LINKEDIN_CLIENT_ID: z.string().optional(),
  VITE_INSTAGRAM_CLIENT_ID: z.string().optional(),
  
  // AI Configuration
  VITE_OPENAI_API_KEY: z.string().optional(),
  VITE_ANTHROPIC_API_KEY: z.string().optional(),
  VITE_AI_MODEL_TEMPERATURE: z.string().transform(Number).pipe(z.number().min(0).max(2)).default('0.7'),
  VITE_AI_MAX_TOKENS: z.string().transform(Number).pipe(z.number().positive()).default('2000'),
  
  // Rate Limiting
  VITE_RATE_LIMIT_WINDOW: z.string().transform(Number).pipe(z.number().positive()).default('900000'), // 15 minutes
  VITE_RATE_LIMIT_MAX_REQUESTS: z.string().transform(Number).pipe(z.number().positive()).default('100'),
  
  // Compliance
  VITE_GDPR_ENABLED: z.string().transform(val => val === 'true').default('true'),
  VITE_CCPA_ENABLED: z.string().transform(val => val === 'true').default('false'),
  VITE_COOKIE_CONSENT: z.string().transform(val => val === 'true').default('true'),
  
  // Localization
  VITE_DEFAULT_LOCALE: z.string().default('en-US'),
  VITE_SUPPORTED_LOCALES: z.string().default('en-US,es-ES,fr-FR,de-DE'),
  VITE_ENABLE_RTL: z.string().transform(val => val === 'true').default('false')
});

class EnvironmentConfig {
  constructor() {
    this.config = null;
    this.validated = false;
    this.errors = [];
  }

  /**
   * Initialize and validate environment configuration
   */
  initialize() {
    try {
      // Get environment variables
      const env = {
        NODE_ENV: process.env.NODE_ENV,
        ...import.meta.env
      };

      // Validate against schema
      const result = EnvironmentSchema.safeParse(env);
      
      if (!result.success) {
        this.errors = result.error.errors;
        console.error('Environment validation failed:', this.errors);
        
        // In development, show detailed errors
        if (process.env.NODE_ENV === 'development') {
          console.table(this.errors.map(err => ({
            field: err.path.join('.'),
            message: err.message,
            received: err.received
          })));
        }
        
        // Use partial config with defaults
        this.config = this.getDefaultConfig();
      } else {
        this.config = result.data;
        this.validated = true;
      }

      // Derive and cache base URL
      try {
        const fallback = 'https://pikar-ai3.vercel.app'
        const fromEnv = this.get('VITE_APP_BASE_URL', null)
        const fromWindow = (typeof window !== 'undefined' && window.location?.origin) ? window.location.origin : null
        this.baseUrl = fromEnv || fromWindow || fallback
      } catch (e) {
        this.baseUrl = 'https://pikar-ai3.vercel.app'
      }

      // Log configuration summary
      this.logConfigSummary();

      return this.config;
    } catch (error) {
      console.error('Failed to initialize environment config:', error);
      this.config = this.getDefaultConfig();
      return this.config;
    }
  }

  /**
   * Get configuration value
   * @param {string} key - Configuration key
   * @param {any} defaultValue - Default value if key not found
   * @returns {any} Configuration value
   */
  get(key, defaultValue = null) {
    if (!this.config) {
      this.initialize();
    }
    
    return this.config[key] ?? defaultValue;
  }

  /**
   * Check if environment is production
   * @returns {boolean}
   */
  isProduction() {
    return this.get('NODE_ENV') === 'production';
  }

  /**
   * Check if environment is development
   * @returns {boolean}
   */
  isDevelopment() {
    return this.get('NODE_ENV') === 'development';
  }

  /**
   * Check if environment is staging
   * @returns {boolean}
   */
  isStaging() {
    return this.get('NODE_ENV') === 'staging';
  }

  /**
   * Check if feature is enabled
   * @param {string} feature - Feature name
   * @returns {boolean}
   */
  isFeatureEnabled(feature) {
    const featureKey = `VITE_ENABLE_${feature.toUpperCase()}`;
    return this.get(featureKey, false);
  }

  /**
   * Get API configuration
   * @returns {Object} API configuration
   */
  getApiConfig() {
    return {
      baseURL: this.get('VITE_API_BASE_URL'),
      timeout: this.get('VITE_API_TIMEOUT'),
      retries: this.get('VITE_API_RETRIES')
    };
  }

  /**
   * Get security configuration
   * @returns {Object} Security configuration
   */
  getSecurityConfig() {
    return {
      enableCSP: this.get('VITE_ENABLE_CSP'),
      enableHSTS: this.get('VITE_ENABLE_HSTS'),
      cspReportUri: this.get('VITE_CSP_REPORT_URI'),
      securityHeaders: this.get('VITE_SECURITY_HEADERS'),
      encryptionKeyLength: this.get('VITE_ENCRYPTION_KEY_LENGTH'),
      pbkdf2Iterations: this.get('VITE_PBKDF2_ITERATIONS')
    };
  }

  /**
   * Get performance configuration
   */
  getPerformanceConfig() {
    return {
      enableCodeSplitting: this.get('VITE_ENABLE_CODE_SPLITTING', true),
      enableServiceWorker: this.get('VITE_ENABLE_SERVICE_WORKER', false),
      cacheDuration: this.get('VITE_CACHE_DURATION', 3600)
    };
  }

  /**
   * Get feature flags
   * @returns {Object} Feature flags
   */
  getFeatureFlags() {
    return {
      aiAgents: this.get('VITE_ENABLE_AI_AGENTS'),
      socialMedia: this.get('VITE_ENABLE_SOCIAL_MEDIA'),
      qms: this.get('VITE_ENABLE_QMS'),
      compliance: this.get('VITE_ENABLE_COMPLIANCE'),
      betaFeatures: this.get('VITE_ENABLE_BETA_FEATURES'),
      codeSplitting: this.get('VITE_ENABLE_CODE_SPLITTING'),
      serviceWorker: this.get('VITE_ENABLE_SERVICE_WORKER'),
      analytics: this.get('VITE_ENABLE_ANALYTICS'),
      debug: this.get('VITE_ENABLE_DEBUG'),
      mockData: this.get('VITE_ENABLE_MOCK_DATA')
    };
  }

  /**
   * Get monitoring configuration
   * @returns {Object} Monitoring configuration
   */
  getMonitoringConfig() {
    return {
      sentryDsn: this.get('VITE_SENTRY_DSN'),
      gaTrackingId: this.get('VITE_GA_TRACKING_ID'),
      hotjarId: this.get('VITE_HOTJAR_ID'),
      enableAnalytics: this.get('VITE_ENABLE_ANALYTICS')
    };
  }

  /**
   * Get default configuration for fallback
   * @returns {Object} Default configuration
   */
  getDefaultConfig() {
    return {
      NODE_ENV: 'development',
      VITE_API_BASE_URL: 'https://api.pikar-ai.com',
      VITE_APP_BASE_URL: 'https://pikar-ai3.vercel.app',
      // Base44 removed
      VITE_API_TIMEOUT: 30000,
      VITE_API_RETRIES: 3,
      VITE_ENABLE_CSP: true,
      VITE_ENABLE_HSTS: false,
      VITE_SECURITY_HEADERS: true,
      VITE_ENCRYPTION_KEY_LENGTH: 256,
      VITE_PBKDF2_ITERATIONS: 100000,
      VITE_MAX_FILE_SIZE: 52428800,
      VITE_ENABLE_VIRUS_SCAN: true,
      VITE_ENABLE_AI_AGENTS: true,
      VITE_ENABLE_SOCIAL_MEDIA: true,
      VITE_ENABLE_QMS: true,
      VITE_ENABLE_COMPLIANCE: true,
      VITE_ENABLE_BETA_FEATURES: false,
      VITE_ENABLE_CODE_SPLITTING: true,
      VITE_ENABLE_SERVICE_WORKER: false,
      VITE_CACHE_DURATION: 3600,
      VITE_ENABLE_DEBUG: false,
      VITE_ENABLE_MOCK_DATA: false,
      VITE_LOG_LEVEL: 'info',
      VITE_AI_MODEL_TEMPERATURE: 0.7,
      VITE_AI_MAX_TOKENS: 2000,
      VITE_RATE_LIMIT_WINDOW: 900000,
      VITE_RATE_LIMIT_MAX_REQUESTS: 100,
      VITE_GDPR_ENABLED: true,
      VITE_CCPA_ENABLED: false,
      VITE_COOKIE_CONSENT: true,
      VITE_DEFAULT_LOCALE: 'en-US',
      VITE_SUPPORTED_LOCALES: 'en-US,es-ES,fr-FR,de-DE',
      VITE_ENABLE_RTL: false
    };
  }

  /**
   * Log configuration summary
   */
  logConfigSummary() {
    if (this.isDevelopment()) {
      console.log('🔧 Environment Configuration Loaded');
      console.log(`Environment: ${this.get('NODE_ENV')}`);
      console.log(`API Base URL: ${this.get('VITE_API_BASE_URL')}`);
      console.log(`Security Headers: ${this.get('VITE_SECURITY_HEADERS') ? 'Enabled' : 'Disabled'}`);
      console.log(`Feature Flags:`, this.getFeatureFlags());
      
      if (!this.validated) {
        console.warn('⚠️ Environment validation failed, using defaults');
      }
    }
  }

  /**
   * Validate required secrets for production
   * @returns {Object} Validation result
   */
  validateProductionSecrets() {
    if (!this.isProduction()) {
      return { valid: true, missing: [] };
    }

    const requiredSecrets = [
      'VITE_API_BASE_URL'
    ];

    const missing = requiredSecrets.filter(secret => !this.get(secret));
    
    return {
      valid: missing.length === 0,
      missing: missing
    };
  }

  /**
   * Get configuration for specific environment
   * @param {string} environment - Environment name
   * @returns {Object} Environment-specific configuration
   */
  getEnvironmentConfig(environment = null) {
    const env = environment || this.get('NODE_ENV');
    
    const baseConfig = this.config || this.getDefaultConfig();
    
    // Environment-specific overrides
    const environmentOverrides = {
      development: {
        VITE_ENABLE_DEBUG: true,
        VITE_LOG_LEVEL: 'debug',
        VITE_ENABLE_MOCK_DATA: true
      },
      staging: {
        VITE_ENABLE_DEBUG: false,
        VITE_LOG_LEVEL: 'info',
        VITE_ENABLE_MOCK_DATA: false,
        VITE_ENABLE_ANALYTICS: true
      },
      production: {
        VITE_ENABLE_DEBUG: false,
        VITE_LOG_LEVEL: 'error',
        VITE_ENABLE_MOCK_DATA: false,
        VITE_ENABLE_HSTS: true,
        VITE_ENABLE_ANALYTICS: true,
        VITE_ENABLE_SERVICE_WORKER: true
      }
    };

    return {
      ...baseConfig,
      ...(environmentOverrides[env] || {})
    };
  }
}

// Create and export singleton instance
export const environmentConfig = new EnvironmentConfig();

// Initialize on import
environmentConfig.initialize();

// Export convenience functions
export const isProduction = () => environmentConfig.isProduction();
export const isDevelopment = () => environmentConfig.isDevelopment();
export const isStaging = () => environmentConfig.isStaging();
export const getConfig = (key, defaultValue) => environmentConfig.get(key, defaultValue);
export const isFeatureEnabled = (feature) => environmentConfig.isFeatureEnabled(feature);

export default environmentConfig;
