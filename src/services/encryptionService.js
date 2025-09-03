/**
 * Encryption Service
 * Provides client-side encryption for sensitive data using Web Crypto API
 */

import { auditService } from './auditService';

class EncryptionService {
  constructor() {
    this.algorithm = 'AES-GCM';
    this.keyLength = 256;
    this.ivLength = 12; // 96 bits for GCM
    this.tagLength = 128; // 128 bits for GCM
    this.keyCache = new Map();
    this.maxCacheSize = 10;
  }

  /**
   * Generate a new encryption key
   * @returns {Promise<CryptoKey>} Generated key
   */
  async generateKey() {
    try {
      const key = await crypto.subtle.generateKey(
        {
          name: this.algorithm,
          length: this.keyLength
        },
        true, // extractable
        ['encrypt', 'decrypt']
      );

      auditService.logSystem.configChange(null, 'encryption_key_generated', null, 'new_key');
      return key;
    } catch (error) {
      auditService.logSystem.error(error, 'encryption_key_generation');
      throw new Error('Failed to generate encryption key');
    }
  }

  /**
   * Derive key from password using PBKDF2
   * @param {string} password - Password to derive key from
   * @param {Uint8Array} salt - Salt for key derivation
   * @param {number} iterations - Number of iterations (default: 100000)
   * @returns {Promise<CryptoKey>} Derived key
   */
  async deriveKeyFromPassword(password, salt, iterations = 100000) {
    try {
      // Import password as key material
      const keyMaterial = await crypto.subtle.importKey(
        'raw',
        new TextEncoder().encode(password),
        'PBKDF2',
        false,
        ['deriveKey']
      );

      // Derive actual encryption key
      const key = await crypto.subtle.deriveKey(
        {
          name: 'PBKDF2',
          salt: salt,
          iterations: iterations,
          hash: 'SHA-256'
        },
        keyMaterial,
        {
          name: this.algorithm,
          length: this.keyLength
        },
        true,
        ['encrypt', 'decrypt']
      );

      auditService.logSystem.configChange(null, 'encryption_key_derived', null, 'password_derived');
      return key;
    } catch (error) {
      auditService.logSystem.error(error, 'encryption_key_derivation');
      throw new Error('Failed to derive encryption key from password');
    }
  }

  /**
   * Generate random salt
   * @param {number} length - Salt length in bytes (default: 32)
   * @returns {Uint8Array} Random salt
   */
  generateSalt(length = 32) {
    return crypto.getRandomValues(new Uint8Array(length));
  }

  /**
   * Generate random IV
   * @returns {Uint8Array} Random IV
   */
  generateIV() {
    return crypto.getRandomValues(new Uint8Array(this.ivLength));
  }

  /**
   * Encrypt data
   * @param {string|Object} data - Data to encrypt
   * @param {CryptoKey} key - Encryption key
   * @param {Uint8Array} iv - Initialization vector (optional, will generate if not provided)
   * @returns {Promise<Object>} Encrypted data with metadata
   */
  async encrypt(data, key, iv = null) {
    try {
      // Convert data to string if it's an object
      const plaintext = typeof data === 'string' ? data : JSON.stringify(data);
      const plaintextBytes = new TextEncoder().encode(plaintext);

      // Generate IV if not provided
      if (!iv) {
        iv = this.generateIV();
      }

      // Encrypt the data
      const ciphertext = await crypto.subtle.encrypt(
        {
          name: this.algorithm,
          iv: iv,
          tagLength: this.tagLength
        },
        key,
        plaintextBytes
      );

      // Return encrypted data with metadata
      const result = {
        ciphertext: Array.from(new Uint8Array(ciphertext)),
        iv: Array.from(iv),
        algorithm: this.algorithm,
        keyLength: this.keyLength,
        timestamp: new Date().toISOString()
      };

      auditService.logData.modification(null, 'data_encrypted', 'sensitive_data', {
        dataSize: plaintextBytes.length,
        algorithm: this.algorithm
      });

      return result;
    } catch (error) {
      auditService.logSystem.error(error, 'data_encryption');
      throw new Error('Failed to encrypt data');
    }
  }

  /**
   * Decrypt data
   * @param {Object} encryptedData - Encrypted data object
   * @param {CryptoKey} key - Decryption key
   * @returns {Promise<string>} Decrypted data
   */
  async decrypt(encryptedData, key) {
    try {
      const { ciphertext, iv, algorithm } = encryptedData;

      // Validate algorithm
      if (algorithm !== this.algorithm) {
        throw new Error('Unsupported encryption algorithm');
      }

      // Convert arrays back to Uint8Array
      const ciphertextBytes = new Uint8Array(ciphertext);
      const ivBytes = new Uint8Array(iv);

      // Decrypt the data
      const plaintextBytes = await crypto.subtle.decrypt(
        {
          name: algorithm,
          iv: ivBytes,
          tagLength: this.tagLength
        },
        key,
        ciphertextBytes
      );

      const plaintext = new TextDecoder().decode(plaintextBytes);

      auditService.logData.modification(null, 'data_decrypted', 'sensitive_data', {
        dataSize: plaintextBytes.byteLength,
        algorithm: algorithm
      });

      return plaintext;
    } catch (error) {
      auditService.logSystem.error(error, 'data_decryption');
      throw new Error('Failed to decrypt data');
    }
  }

  /**
   * Encrypt sensitive form data
   * @param {Object} formData - Form data to encrypt
   * @param {string} userPassword - User password for key derivation
   * @returns {Promise<Object>} Encrypted form data
   */
  async encryptFormData(formData, userPassword) {
    try {
      // Generate salt and derive key
      const salt = this.generateSalt();
      const key = await this.deriveKeyFromPassword(userPassword, salt);

      // Identify sensitive fields
      const sensitiveFields = ['password', 'ssn', 'creditCard', 'bankAccount', 'apiKey', 'token'];
      const encryptedData = { ...formData };

      // Encrypt sensitive fields
      for (const [fieldName, fieldValue] of Object.entries(formData)) {
        if (sensitiveFields.some(sensitive => fieldName.toLowerCase().includes(sensitive))) {
          if (fieldValue && typeof fieldValue === 'string') {
            encryptedData[fieldName] = await this.encrypt(fieldValue, key);
            encryptedData[`${fieldName}_encrypted`] = true;
          }
        }
      }

      // Store salt for later decryption
      encryptedData._encryptionSalt = Array.from(salt);
      encryptedData._encryptionTimestamp = new Date().toISOString();

      return encryptedData;
    } catch (error) {
      auditService.logSystem.error(error, 'form_data_encryption');
      throw new Error('Failed to encrypt form data');
    }
  }

  /**
   * Decrypt sensitive form data
   * @param {Object} encryptedFormData - Encrypted form data
   * @param {string} userPassword - User password for key derivation
   * @returns {Promise<Object>} Decrypted form data
   */
  async decryptFormData(encryptedFormData, userPassword) {
    try {
      const { _encryptionSalt, ...formData } = encryptedFormData;
      
      if (!_encryptionSalt) {
        throw new Error('No encryption salt found');
      }

      // Derive key from password and salt
      const salt = new Uint8Array(_encryptionSalt);
      const key = await this.deriveKeyFromPassword(userPassword, salt);

      const decryptedData = { ...formData };

      // Decrypt encrypted fields
      for (const [fieldName, fieldValue] of Object.entries(formData)) {
        if (fieldName.endsWith('_encrypted') && fieldValue === true) {
          const dataFieldName = fieldName.replace('_encrypted', '');
          if (formData[dataFieldName] && typeof formData[dataFieldName] === 'object') {
            decryptedData[dataFieldName] = await this.decrypt(formData[dataFieldName], key);
            delete decryptedData[fieldName]; // Remove encryption flag
          }
        }
      }

      return decryptedData;
    } catch (error) {
      auditService.logSystem.error(error, 'form_data_decryption');
      throw new Error('Failed to decrypt form data');
    }
  }

  /**
   * Hash data using SHA-256
   * @param {string} data - Data to hash
   * @returns {Promise<string>} Hex-encoded hash
   */
  async hash(data) {
    try {
      const dataBytes = new TextEncoder().encode(data);
      const hashBuffer = await crypto.subtle.digest('SHA-256', dataBytes);
      const hashArray = Array.from(new Uint8Array(hashBuffer));
      return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    } catch (error) {
      auditService.logSystem.error(error, 'data_hashing');
      throw new Error('Failed to hash data');
    }
  }

  /**
   * Generate secure random string
   * @param {number} length - Length of random string
   * @returns {string} Random string
   */
  generateSecureRandom(length = 32) {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    const randomBytes = crypto.getRandomValues(new Uint8Array(length));
    return Array.from(randomBytes, byte => chars[byte % chars.length]).join('');
  }

  /**
   * Encrypt data for storage
   * @param {string} data - Data to encrypt
   * @param {string} keyId - Key identifier
   * @returns {Promise<string>} Base64 encoded encrypted data
   */
  async encryptForStorage(data, keyId = 'default') {
    try {
      let key = this.keyCache.get(keyId);
      
      if (!key) {
        key = await this.generateKey();
        this.cacheKey(keyId, key);
      }

      const encrypted = await this.encrypt(data, key);
      
      // Convert to base64 for storage
      const storageData = {
        ...encrypted,
        keyId: keyId
      };

      return btoa(JSON.stringify(storageData));
    } catch (error) {
      auditService.logSystem.error(error, 'storage_encryption');
      throw new Error('Failed to encrypt data for storage');
    }
  }

  /**
   * Decrypt data from storage
   * @param {string} encryptedData - Base64 encoded encrypted data
   * @returns {Promise<string>} Decrypted data
   */
  async decryptFromStorage(encryptedData) {
    try {
      const storageData = JSON.parse(atob(encryptedData));
      const { keyId, ...encrypted } = storageData;

      let key = this.keyCache.get(keyId);
      if (!key) {
        throw new Error('Decryption key not found');
      }

      return await this.decrypt(encrypted, key);
    } catch (error) {
      auditService.logSystem.error(error, 'storage_decryption');
      throw new Error('Failed to decrypt data from storage');
    }
  }

  /**
   * Cache encryption key
   * @param {string} keyId - Key identifier
   * @param {CryptoKey} key - Encryption key
   */
  cacheKey(keyId, key) {
    if (this.keyCache.size >= this.maxCacheSize) {
      const firstKey = this.keyCache.keys().next().value;
      this.keyCache.delete(firstKey);
    }
    this.keyCache.set(keyId, key);
  }

  /**
   * Clear key cache
   */
  clearKeyCache() {
    this.keyCache.clear();
    auditService.logSystem.configChange(null, 'encryption_cache_cleared', null, 'cache_cleared');
  }

  /**
   * Export key for backup (development only)
   * @param {CryptoKey} key - Key to export
   * @returns {Promise<string>} Base64 encoded key
   */
  async exportKey(key) {
    if (process.env.NODE_ENV === 'production') {
      throw new Error('Key export not allowed in production');
    }

    try {
      const exported = await crypto.subtle.exportKey('raw', key);
      return btoa(String.fromCharCode(...new Uint8Array(exported)));
    } catch (error) {
      throw new Error('Failed to export key');
    }
  }

  /**
   * Import key from backup (development only)
   * @param {string} keyData - Base64 encoded key
   * @returns {Promise<CryptoKey>} Imported key
   */
  async importKey(keyData) {
    if (process.env.NODE_ENV === 'production') {
      throw new Error('Key import not allowed in production');
    }

    try {
      const keyBytes = Uint8Array.from(atob(keyData), c => c.charCodeAt(0));
      return await crypto.subtle.importKey(
        'raw',
        keyBytes,
        { name: this.algorithm },
        true,
        ['encrypt', 'decrypt']
      );
    } catch (error) {
      throw new Error('Failed to import key');
    }
  }
}

// Create and export singleton instance
export const encryptionService = new EncryptionService();
