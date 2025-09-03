/**
 * Secure Storage Service
 * Provides encrypted storage for sensitive data using Web Crypto API
 */

import { encryptionService } from './encryptionService';
import { auditService } from './auditService';

class SecureStorageService {
  constructor() {
    this.storagePrefix = 'pikar_secure_';
    this.keyPrefix = 'pikar_key_';
    this.sensitiveKeys = new Set([
      'auth_token',
      'refresh_token',
      'user_credentials',
      'api_keys',
      'personal_data',
      'payment_info',
      'private_keys'
    ]);
  }

  /**
   * Store data securely
   * @param {string} key - Storage key
   * @param {any} data - Data to store
   * @param {Object} options - Storage options
   * @returns {Promise<boolean>} Success status
   */
  async setItem(key, data, options = {}) {
    try {
      const {
        encrypt = this.isSensitiveKey(key),
        expiresIn = null, // milliseconds
        compress = false
      } = options;

      let processedData = {
        value: data,
        timestamp: Date.now(),
        encrypted: encrypt,
        compressed: compress
      };

      // Add expiration if specified
      if (expiresIn) {
        processedData.expiresAt = Date.now() + expiresIn;
      }

      // Compress data if requested
      if (compress && typeof data === 'string') {
        processedData.value = this.compressString(data);
      }

      // Encrypt sensitive data
      if (encrypt) {
        const encryptedValue = await encryptionService.encryptForStorage(
          JSON.stringify(processedData.value),
          key
        );
        processedData.value = encryptedValue;
      }

      // Store in localStorage
      const storageKey = this.getStorageKey(key);
      localStorage.setItem(storageKey, JSON.stringify(processedData));

      // Log storage event
      auditService.logData.modification(null, 'secure_storage_set', key, {
        encrypted: encrypt,
        size: JSON.stringify(processedData).length
      });

      return true;
    } catch (error) {
      auditService.logSystem.error(error, 'secure_storage_set');
      console.error('Failed to store data securely:', error);
      return false;
    }
  }

  /**
   * Retrieve data securely
   * @param {string} key - Storage key
   * @returns {Promise<any>} Retrieved data or null
   */
  async getItem(key) {
    try {
      const storageKey = this.getStorageKey(key);
      const storedData = localStorage.getItem(storageKey);

      if (!storedData) {
        return null;
      }

      const processedData = JSON.parse(storedData);

      // Check expiration
      if (processedData.expiresAt && Date.now() > processedData.expiresAt) {
        await this.removeItem(key);
        return null;
      }

      let value = processedData.value;

      // Decrypt if encrypted
      if (processedData.encrypted) {
        const decryptedValue = await encryptionService.decryptFromStorage(value);
        value = JSON.parse(decryptedValue);
      }

      // Decompress if compressed
      if (processedData.compressed && typeof value === 'string') {
        value = this.decompressString(value);
      }

      // Log retrieval event
      auditService.logData.modification(null, 'secure_storage_get', key, {
        encrypted: processedData.encrypted,
        age: Date.now() - processedData.timestamp
      });

      return value;
    } catch (error) {
      auditService.logSystem.error(error, 'secure_storage_get');
      console.error('Failed to retrieve data securely:', error);
      return null;
    }
  }

  /**
   * Remove item from secure storage
   * @param {string} key - Storage key
   * @returns {Promise<boolean>} Success status
   */
  async removeItem(key) {
    try {
      const storageKey = this.getStorageKey(key);
      localStorage.removeItem(storageKey);

      // Log removal event
      auditService.logData.deletion(null, 'secure_storage', key);

      return true;
    } catch (error) {
      auditService.logSystem.error(error, 'secure_storage_remove');
      console.error('Failed to remove data securely:', error);
      return false;
    }
  }

  /**
   * Check if item exists
   * @param {string} key - Storage key
   * @returns {boolean} Whether item exists
   */
  hasItem(key) {
    const storageKey = this.getStorageKey(key);
    return localStorage.getItem(storageKey) !== null;
  }

  /**
   * Clear all secure storage
   * @returns {Promise<boolean>} Success status
   */
  async clear() {
    try {
      const keys = this.getAllKeys();
      
      for (const key of keys) {
        localStorage.removeItem(key);
      }

      // Clear encryption cache
      encryptionService.clearKeyCache();

      // Log clear event
      auditService.logData.deletion(null, 'secure_storage_clear', 'all_data');

      return true;
    } catch (error) {
      auditService.logSystem.error(error, 'secure_storage_clear');
      console.error('Failed to clear secure storage:', error);
      return false;
    }
  }

  /**
   * Get all secure storage keys
   * @returns {Array<string>} Array of storage keys
   */
  getAllKeys() {
    const keys = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && key.startsWith(this.storagePrefix)) {
        keys.push(key);
      }
    }
    return keys;
  }

  /**
   * Get storage statistics
   * @returns {Object} Storage statistics
   */
  getStorageStats() {
    const keys = this.getAllKeys();
    let totalSize = 0;
    let encryptedCount = 0;
    let expiredCount = 0;

    keys.forEach(key => {
      try {
        const data = localStorage.getItem(key);
        if (data) {
          totalSize += data.length;
          const parsed = JSON.parse(data);
          
          if (parsed.encrypted) {
            encryptedCount++;
          }
          
          if (parsed.expiresAt && Date.now() > parsed.expiresAt) {
            expiredCount++;
          }
        }
      } catch (error) {
        // Skip invalid entries
      }
    });

    return {
      totalItems: keys.length,
      totalSize: totalSize,
      encryptedItems: encryptedCount,
      expiredItems: expiredCount,
      averageSize: keys.length > 0 ? Math.round(totalSize / keys.length) : 0
    };
  }

  /**
   * Clean up expired items
   * @returns {Promise<number>} Number of items cleaned up
   */
  async cleanup() {
    try {
      const keys = this.getAllKeys();
      let cleanedCount = 0;

      for (const storageKey of keys) {
        try {
          const data = localStorage.getItem(storageKey);
          if (data) {
            const parsed = JSON.parse(data);
            if (parsed.expiresAt && Date.now() > parsed.expiresAt) {
              localStorage.removeItem(storageKey);
              cleanedCount++;
            }
          }
        } catch (error) {
          // Remove invalid entries
          localStorage.removeItem(storageKey);
          cleanedCount++;
        }
      }

      if (cleanedCount > 0) {
        auditService.logData.deletion(null, 'secure_storage_cleanup', `${cleanedCount}_items`);
      }

      return cleanedCount;
    } catch (error) {
      auditService.logSystem.error(error, 'secure_storage_cleanup');
      console.error('Failed to cleanup secure storage:', error);
      return 0;
    }
  }

  /**
   * Store user session data
   * @param {Object} sessionData - Session data
   * @param {number} expiresIn - Expiration time in milliseconds
   * @returns {Promise<boolean>} Success status
   */
  async storeSession(sessionData, expiresIn = 24 * 60 * 60 * 1000) {
    return await this.setItem('user_session', sessionData, {
      encrypt: true,
      expiresIn: expiresIn
    });
  }

  /**
   * Retrieve user session data
   * @returns {Promise<Object|null>} Session data or null
   */
  async getSession() {
    return await this.getItem('user_session');
  }

  /**
   * Clear user session
   * @returns {Promise<boolean>} Success status
   */
  async clearSession() {
    return await this.removeItem('user_session');
  }

  /**
   * Store API credentials
   * @param {Object} credentials - API credentials
   * @returns {Promise<boolean>} Success status
   */
  async storeCredentials(credentials) {
    return await this.setItem('api_credentials', credentials, {
      encrypt: true
    });
  }

  /**
   * Retrieve API credentials
   * @returns {Promise<Object|null>} Credentials or null
   */
  async getCredentials() {
    return await this.getItem('api_credentials');
  }

  // Private methods

  /**
   * Get full storage key with prefix
   * @param {string} key - Original key
   * @returns {string} Prefixed key
   */
  getStorageKey(key) {
    return `${this.storagePrefix}${key}`;
  }

  /**
   * Check if key is sensitive
   * @param {string} key - Storage key
   * @returns {boolean} Whether key is sensitive
   */
  isSensitiveKey(key) {
    return this.sensitiveKeys.has(key) || 
           Array.from(this.sensitiveKeys).some(sensitive => key.includes(sensitive));
  }

  /**
   * Simple string compression (placeholder)
   * @param {string} str - String to compress
   * @returns {string} Compressed string
   */
  compressString(str) {
    // In a real implementation, you might use a compression library
    // For now, just return the original string
    return str;
  }

  /**
   * Simple string decompression (placeholder)
   * @param {string} str - String to decompress
   * @returns {string} Decompressed string
   */
  decompressString(str) {
    // In a real implementation, you would decompress the string
    // For now, just return the original string
    return str;
  }

  /**
   * Initialize secure storage
   */
  async initialize() {
    try {
      // Clean up expired items on initialization
      await this.cleanup();

      // Set up periodic cleanup
      setInterval(() => {
        this.cleanup();
      }, 60 * 60 * 1000); // Clean up every hour

      auditService.logSystem.configChange(null, 'secure_storage_initialized', null, 'initialized');
    } catch (error) {
      auditService.logSystem.error(error, 'secure_storage_initialization');
      console.error('Failed to initialize secure storage:', error);
    }
  }
}

// Create and export singleton instance
export const secureStorageService = new SecureStorageService();
