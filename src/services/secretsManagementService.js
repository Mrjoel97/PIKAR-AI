/**
 * Secrets Management Service
 * Secure handling of sensitive configuration data and API keys
 */

import { environmentConfig } from '@/config/environment';
import { encryptionService } from './encryptionService';
import { auditService } from './auditService';

class SecretsManagementService {
  constructor() {
    this.secrets = new Map();
    this.encryptedSecrets = new Map();
    this.secretsLoaded = false;
    this.rotationSchedule = new Map();
    this.accessLog = [];
  }

  /**
   * Initialize secrets management
   */
  async initialize() {
    try {
      // Load secrets from environment
      await this.loadSecretsFromEnvironment();
      
      // Set up secret rotation monitoring
      this.setupRotationMonitoring();
      
      // Initialize access logging
      this.setupAccessLogging();
      
      this.secretsLoaded = true;
      console.log('🔐 Secrets Management Service initialized');
      
      auditService.logSystem.configChange(null, 'secrets_service_initialized', null, 'initialized');
    } catch (error) {
      console.error('Failed to initialize secrets management:', error);
      auditService.logSystem.error(error, 'secrets_initialization');
      throw error;
    }
  }

  /**
   * Load secrets from environment variables
   */
  async loadSecretsFromEnvironment() {
    const sensitiveKeys = [
      'VITE_JWT_SECRET',
      'VITE_SENTRY_DSN',
      'VITE_STRIPE_PUBLIC_KEY',
      'VITE_GOOGLE_MAPS_API_KEY',
      'VITE_RECAPTCHA_SITE_KEY',
      'VITE_FACEBOOK_APP_ID',
      'VITE_TWITTER_API_KEY',
      'VITE_LINKEDIN_CLIENT_ID',
      'VITE_INSTAGRAM_CLIENT_ID',
      'VITE_OPENAI_API_KEY',
      'VITE_ANTHROPIC_API_KEY',
      'VITE_GA_TRACKING_ID',
      'VITE_HOTJAR_ID'
    ];

    for (const key of sensitiveKeys) {
      const value = environmentConfig.get(key);
      if (value) {
        await this.storeSecret(key, value, {
          encrypted: true,
          rotationDays: this.getRotationPeriod(key)
        });
      }
    }
  }

  /**
   * Store a secret securely
   * @param {string} key - Secret key
   * @param {string} value - Secret value
   * @param {Object} options - Storage options
   */
  async storeSecret(key, value, options = {}) {
    try {
      const {
        encrypted = true,
        rotationDays = 90,
        category = 'general'
      } = options;

      // Validate secret strength
      this.validateSecretStrength(key, value);

      if (encrypted) {
        // Encrypt the secret
        const encryptionKey = await encryptionService.generateKey();
        const encryptedValue = await encryptionService.encrypt(value, encryptionKey);
        
        this.encryptedSecrets.set(key, {
          value: encryptedValue,
          key: encryptionKey,
          category,
          createdAt: new Date(),
          lastAccessed: null,
          accessCount: 0
        });
      } else {
        this.secrets.set(key, {
          value,
          category,
          createdAt: new Date(),
          lastAccessed: null,
          accessCount: 0
        });
      }

      // Set up rotation schedule
      if (rotationDays > 0) {
        const rotationDate = new Date();
        rotationDate.setDate(rotationDate.getDate() + rotationDays);
        this.rotationSchedule.set(key, rotationDate);
      }

      auditService.logSystem.configChange(null, 'secret_stored', key, category);
    } catch (error) {
      auditService.logSystem.error(error, 'secret_storage', { key });
      throw error;
    }
  }

  /**
   * Retrieve a secret
   * @param {string} key - Secret key
   * @param {Object} context - Access context
   * @returns {string|null} Secret value
   */
  async getSecret(key, context = {}) {
    try {
      let secretData = null;
      let isEncrypted = false;

      // Check encrypted secrets first
      if (this.encryptedSecrets.has(key)) {
        secretData = this.encryptedSecrets.get(key);
        isEncrypted = true;
      } else if (this.secrets.has(key)) {
        secretData = this.secrets.get(key);
      }

      if (!secretData) {
        // Log access attempt for non-existent secret
        this.logSecretAccess(key, false, context);
        return null;
      }

      // Update access tracking
      secretData.lastAccessed = new Date();
      secretData.accessCount++;

      // Decrypt if necessary
      let value = secretData.value;
      if (isEncrypted) {
        value = await encryptionService.decrypt(secretData.value, secretData.key);
      }

      // Log successful access
      this.logSecretAccess(key, true, context);

      // Check if rotation is needed
      this.checkRotationNeeded(key);

      return value;
    } catch (error) {
      auditService.logSystem.error(error, 'secret_retrieval', { key });
      this.logSecretAccess(key, false, context, error.message);
      return null;
    }
  }

  /**
   * Remove a secret
   * @param {string} key - Secret key
   */
  async removeSecret(key) {
    try {
      const removed = this.secrets.delete(key) || this.encryptedSecrets.delete(key);
      this.rotationSchedule.delete(key);

      if (removed) {
        auditService.logSystem.configChange(null, 'secret_removed', key, 'removed');
      }

      return removed;
    } catch (error) {
      auditService.logSystem.error(error, 'secret_removal', { key });
      throw error;
    }
  }

  /**
   * Rotate a secret
   * @param {string} key - Secret key
   * @param {string} newValue - New secret value
   */
  async rotateSecret(key, newValue) {
    try {
      const oldSecretData = this.encryptedSecrets.get(key) || this.secrets.get(key);
      
      if (!oldSecretData) {
        throw new Error(`Secret ${key} not found for rotation`);
      }

      // Store new secret with same options
      await this.storeSecret(key, newValue, {
        encrypted: this.encryptedSecrets.has(key),
        category: oldSecretData.category,
        rotationDays: this.getRotationPeriod(key)
      });

      auditService.logSystem.configChange(null, 'secret_rotated', key, 'rotated');
      console.log(`🔄 Secret ${key} rotated successfully`);
    } catch (error) {
      auditService.logSystem.error(error, 'secret_rotation', { key });
      throw error;
    }
  }

  /**
   * Validate secret strength
   * @param {string} key - Secret key
   * @param {string} value - Secret value
   */
  validateSecretStrength(key, value) {
    const requirements = {
      'VITE_JWT_SECRET': { minLength: 32, requireSpecialChars: true },
      'VITE_OPENAI_API_KEY': { minLength: 20, pattern: /^sk-/ },
      'VITE_ANTHROPIC_API_KEY': { minLength: 20 },
      'default': { minLength: 8 }
    };

    const requirement = requirements[key] || requirements.default;

    if (value.length < requirement.minLength) {
      throw new Error(`Secret ${key} must be at least ${requirement.minLength} characters long`);
    }

    if (requirement.pattern && !requirement.pattern.test(value)) {
      throw new Error(`Secret ${key} does not match required pattern`);
    }

    if (requirement.requireSpecialChars) {
      const hasSpecialChars = /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(value);
      if (!hasSpecialChars) {
        throw new Error(`Secret ${key} must contain special characters`);
      }
    }
  }

  /**
   * Get rotation period for a secret type
   * @param {string} key - Secret key
   * @returns {number} Rotation period in days
   */
  getRotationPeriod(key) {
    const rotationPeriods = {
      'VITE_JWT_SECRET': 30,
      'VITE_OPENAI_API_KEY': 90,
      'VITE_ANTHROPIC_API_KEY': 90,
      'VITE_STRIPE_PUBLIC_KEY': 180,
      'default': 90
    };

    return rotationPeriods[key] || rotationPeriods.default;
  }

  /**
   * Log secret access
   * @param {string} key - Secret key
   * @param {boolean} success - Access success
   * @param {Object} context - Access context
   * @param {string} error - Error message if failed
   */
  logSecretAccess(key, success, context = {}, error = null) {
    const logEntry = {
      key: this.maskSecretKey(key),
      success,
      timestamp: new Date(),
      context: {
        component: context.component || 'unknown',
        operation: context.operation || 'access',
        userId: context.userId || 'system'
      },
      error
    };

    this.accessLog.unshift(logEntry);
    
    // Keep only last 100 access logs
    if (this.accessLog.length > 100) {
      this.accessLog.splice(100);
    }

    // Log to audit service
    if (success) {
      auditService.logAccess.dataAccess(context.userId, 'secret_access', this.maskSecretKey(key));
    } else {
      auditService.logAccess.suspiciousActivity(context.userId, 'secret_access_failed', {
        key: this.maskSecretKey(key),
        error
      });
    }
  }

  /**
   * Mask secret key for logging
   * @param {string} key - Secret key
   * @returns {string} Masked key
   */
  maskSecretKey(key) {
    if (key.length <= 8) {
      return '*'.repeat(key.length);
    }
    return key.substring(0, 4) + '*'.repeat(key.length - 8) + key.substring(key.length - 4);
  }

  /**
   * Check if secret rotation is needed
   * @param {string} key - Secret key
   */
  checkRotationNeeded(key) {
    const rotationDate = this.rotationSchedule.get(key);
    if (rotationDate && new Date() > rotationDate) {
      console.warn(`⚠️ Secret ${key} needs rotation (due: ${rotationDate.toISOString()})`);
      
      auditService.logSystem.configChange(null, 'secret_rotation_needed', key, rotationDate.toISOString());
    }
  }

  /**
   * Set up rotation monitoring
   */
  setupRotationMonitoring() {
    // Check for rotation needs every hour
    setInterval(() => {
      this.checkAllRotations();
    }, 60 * 60 * 1000);
  }

  /**
   * Check all secrets for rotation needs
   */
  checkAllRotations() {
    for (const [key, rotationDate] of this.rotationSchedule.entries()) {
      if (new Date() > rotationDate) {
        console.warn(`⚠️ Secret ${key} requires rotation`);
        
        auditService.logSystem.configChange(null, 'secret_rotation_overdue', key, rotationDate.toISOString());
      }
    }
  }

  /**
   * Set up access logging
   */
  setupAccessLogging() {
    // Log access patterns every 24 hours
    setInterval(() => {
      this.analyzeAccessPatterns();
    }, 24 * 60 * 60 * 1000);
  }

  /**
   * Analyze access patterns for security monitoring
   */
  analyzeAccessPatterns() {
    const last24Hours = new Date(Date.now() - 24 * 60 * 60 * 1000);
    const recentAccess = this.accessLog.filter(log => log.timestamp > last24Hours);
    
    const stats = {
      totalAccess: recentAccess.length,
      failedAccess: recentAccess.filter(log => !log.success).length,
      uniqueKeys: new Set(recentAccess.map(log => log.key)).size,
      topKeys: this.getTopAccessedKeys(recentAccess)
    };

    // Alert on suspicious patterns
    if (stats.failedAccess > 10) {
      console.warn(`⚠️ High number of failed secret access attempts: ${stats.failedAccess}`);
      auditService.logAccess.suspiciousActivity(null, 'high_failed_secret_access', stats);
    }

    auditService.logSystem.configChange(null, 'secret_access_analysis', null, JSON.stringify(stats));
  }

  /**
   * Get top accessed secret keys
   * @param {Array} accessLogs - Access log entries
   * @returns {Array} Top accessed keys
   */
  getTopAccessedKeys(accessLogs) {
    const keyCount = {};
    accessLogs.forEach(log => {
      keyCount[log.key] = (keyCount[log.key] || 0) + 1;
    });

    return Object.entries(keyCount)
      .sort(([,a], [,b]) => b - a)
      .slice(0, 5)
      .map(([key, count]) => ({ key, count }));
  }

  /**
   * Get secrets management status
   * @returns {Object} Status information
   */
  getStatus() {
    const now = new Date();
    const rotationNeeded = Array.from(this.rotationSchedule.entries())
      .filter(([, date]) => now > date)
      .map(([key]) => key);

    return {
      secretsLoaded: this.secretsLoaded,
      totalSecrets: this.secrets.size + this.encryptedSecrets.size,
      encryptedSecrets: this.encryptedSecrets.size,
      rotationNeeded: rotationNeeded.length,
      recentAccessCount: this.accessLog.filter(log => 
        log.timestamp > new Date(Date.now() - 60 * 60 * 1000)
      ).length
    };
  }

  /**
   * Clear all secrets (for testing or emergency)
   */
  clearAllSecrets() {
    this.secrets.clear();
    this.encryptedSecrets.clear();
    this.rotationSchedule.clear();
    this.accessLog = [];
    
    auditService.logSystem.configChange(null, 'all_secrets_cleared', null, 'emergency_clear');
    console.warn('🚨 All secrets cleared');
  }
}

// Create and export singleton instance
export const secretsManagementService = new SecretsManagementService();

export default secretsManagementService;
