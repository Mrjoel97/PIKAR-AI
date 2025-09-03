import { apiClient, base44 } from '@/api/base44Client';
import { validateClientData } from '@/lib/validation/middleware';
import { LoginSchema, RegisterSchema } from '@/lib/validation/schemas';
import { auditService } from './auditService';
import { secureStorageService } from './secureStorageService';
import { encryptionService } from './encryptionService';
import { errorHandlingService } from './errorHandlingService';

// Permission definitions for each tier
const TIER_PERMISSIONS = {
  solopreneur: [
    'basic_agents',
    'basic_analytics',
    'basic_campaigns',
    'file_upload',
    'profile_management'
  ],
  startup: [
    'basic_agents',
    'basic_analytics',
    'basic_campaigns',
    'team_collaboration',
    'advanced_agents',
    'file_upload',
    'profile_management',
    'api_access'
  ],
  sme: [
    'all_agents',
    'advanced_analytics',
    'workflow_templates',
    'team_collaboration',
    'advanced_campaigns',
    'custom_reports',
    'file_upload',
    'profile_management',
    'api_access',
    'integrations'
  ],
  enterprise: [
    'all_features',
    'custom_integrations',
    'priority_support',
    'advanced_security',
    'audit_logs',
    'custom_branding',
    'sso',
    'advanced_permissions',
    'bulk_operations',
    'data_export'
  ]
};

// Token storage keys
const TOKEN_KEYS = {
  ACCESS_TOKEN: 'pikar_access_token',
  REFRESH_TOKEN: 'pikar_refresh_token',
  USER_DATA: 'pikar_user_data'
};

class AuthService {
  constructor() {
    this.baseURL = process.env.REACT_APP_API_URL || '';
    this.tokenRefreshPromise = null;
  }

  /**
   * Login user with email and password
   * @param {Object} credentials - Login credentials
   * @returns {Promise<Object>} Login response
   */
  async login(credentials) {
    try {
      // Validate input
      const validation = validateClientData(LoginSchema, credentials);
      if (!validation.success) {
        return {
          success: false,
          error: 'Invalid login credentials format',
          details: validation.errors
        };
      }

      // Use real Base44 API instead of simulation
      const response = await this.realLogin(validation.data);
      
      if (response.success) {
        // Store user data
        this.storeUserData(response.data.user);

        // Log security event
        auditService.logAuth.loginSuccess(response.data.user.id, response.data.user.email);
      } else {
        // Log failed login attempt
        auditService.logAuth.loginFailure(credentials.email, response.error);
      }

      return response;
    } catch (error) {
      console.error('Login error:', error);
      return {
        success: false,
        error: 'Login failed. Please try again.',
        details: error.message
      };
    }
  }

  /**
   * Register new user
   * @param {Object} userData - Registration data
   * @returns {Promise<Object>} Registration response
   */
  async register(userData) {
    try {
      // Validate input
      const validation = validateClientData(RegisterSchema, userData);
      if (!validation.success) {
        return {
          success: false,
          error: 'Invalid registration data format',
          details: validation.errors
        };
      }

      // Use real Base44 API instead of simulation
      const response = await this.realRegister(validation.data);
      
      if (response.success) {
        // Store user data
        this.storeUserData(response.data.user);

        // Log security event
        auditService.logAuth.loginSuccess(response.data.user.id, response.data.user.email);
      }

      return response;
    } catch (error) {
      console.error('Registration error:', error);
      return {
        success: false,
        error: 'Registration failed. Please try again.',
        details: error.message
      };
    }
  }

  /**
   * Logout user
   * @returns {Promise<void>}
   */
  async logout() {
    try {
      const user = this.getStoredUserData();
      
      // Clear stored data
      this.clearTokens();
      this.clearUserData();
      
      // Log security event
      if (user) {
        auditService.logAuth.logout(user.id);
      }
      
      // In a real implementation, you might call a logout endpoint
      // await apiClient.post('/auth/logout');
      
    } catch (error) {
      console.error('Logout error:', error);
      // Still clear local data even if server call fails
      this.clearTokens();
      this.clearUserData();
    }
  }

  /**
   * Refresh access token
   * @param {string} refreshToken - Refresh token
   * @returns {Promise<Object>} Refresh response
   */
  async refreshToken(refreshToken) {
    try {
      // Prevent multiple simultaneous refresh attempts
      if (this.tokenRefreshPromise) {
        return await this.tokenRefreshPromise;
      }

      this.tokenRefreshPromise = this.performTokenRefresh(refreshToken);
      const result = await this.tokenRefreshPromise;
      this.tokenRefreshPromise = null;
      
      return result;
    } catch (error) {
      this.tokenRefreshPromise = null;
      throw error;
    }
  }

  /**
   * Perform actual token refresh
   * @param {string} refreshToken - Refresh token
   * @returns {Promise<Object>} Refresh response
   */
  async performTokenRefresh(refreshToken) {
    try {
      // For now, simulate token refresh
      // In a real implementation, this would call the refresh endpoint
      const response = await this.simulateTokenRefresh(refreshToken);
      
      if (response.success) {
        const userData = this.getStoredUserData();
        auditService.logAuth.tokenRefresh(userData?.id, true);
      }
      
      return response;
    } catch (error) {
      console.error('Token refresh error:', error);
      return {
        success: false,
        error: 'Token refresh failed'
      };
    }
  }

  /**
   * Verify access token
   * @param {string} accessToken - Access token to verify
   * @returns {Promise<Object|null>} User data if valid, null if invalid
   */
  async verifyToken(accessToken) {
    try {
      // For now, simulate token verification
      // In a real implementation, this would call the verify endpoint
      const response = await this.simulateTokenVerification(accessToken);
      return response.success ? response.data.user : null;
    } catch (error) {
      console.error('Token verification error:', error);
      return null;
    }
  }

  /**
   * Check if user has specific permission
   * @param {string} userTier - User's tier
   * @param {string} permission - Permission to check
   * @returns {boolean} Whether user has permission
   */
  hasPermission(userTier, permission) {
    const tierPermissions = TIER_PERMISSIONS[userTier] || [];
    return tierPermissions.includes(permission) || tierPermissions.includes('all_features');
  }

  /**
   * Get all permissions for a tier
   * @param {string} userTier - User's tier
   * @returns {Array<string>} Array of permissions
   */
  getTierPermissions(userTier) {
    return TIER_PERMISSIONS[userTier] || [];
  }

  /**
   * Store tokens securely using encrypted storage
   * @param {Object} tokens - Access and refresh tokens
   */
  async storeTokens(tokens) {
    try {
      // Store tokens with encryption and expiration
      await secureStorageService.setItem('auth_token', tokens.accessToken, {
        encrypt: true,
        expiresIn: 15 * 60 * 1000 // 15 minutes
      });

      await secureStorageService.setItem('refresh_token', tokens.refreshToken, {
        encrypt: true,
        expiresIn: 7 * 24 * 60 * 60 * 1000 // 7 days
      });

      auditService.logAuth.tokenRefresh(null, true);
    } catch (error) {
      console.error('Error storing tokens:', error);
      auditService.logSystem.error(error, 'token_storage');
    }
  }

  /**
   * Get stored tokens from secure storage
   * @returns {Promise<Object>} Stored tokens
   */
  async getStoredTokens() {
    try {
      const [accessToken, refreshToken] = await Promise.all([
        secureStorageService.getItem('auth_token'),
        secureStorageService.getItem('refresh_token')
      ]);

      return {
        accessToken,
        refreshToken
      };
    } catch (error) {
      console.error('Error retrieving tokens:', error);
      auditService.logSystem.error(error, 'token_retrieval');
      return { accessToken: null, refreshToken: null };
    }
  }

  /**
   * Clear stored tokens from secure storage
   */
  async clearTokens() {
    try {
      await Promise.all([
        secureStorageService.removeItem('auth_token'),
        secureStorageService.removeItem('refresh_token')
      ]);
    } catch (error) {
      console.error('Error clearing tokens:', error);
      auditService.logSystem.error(error, 'token_clearing');
    }
  }

  /**
   * Store user data securely
   * @param {Object} userData - User data to store
   */
  async storeUserData(userData) {
    try {
      // Encrypt sensitive user data
      const sensitiveFields = ['email', 'phone', 'address', 'paymentInfo'];
      const encryptedUserData = { ...userData };

      for (const field of sensitiveFields) {
        if (userData[field]) {
          encryptedUserData[field] = await encryptionService.encrypt(
            userData[field],
            await encryptionService.generateKey()
          );
        }
      }

      await secureStorageService.setItem('user_data', encryptedUserData, {
        encrypt: true
      });
    } catch (error) {
      console.error('Error storing user data:', error);
      auditService.logSystem.error(error, 'user_data_storage');
    }
  }

  /**
   * Get stored user data
   * @returns {Promise<Object|null>} Stored user data
   */
  async getStoredUserData() {
    try {
      const userData = await secureStorageService.getItem('user_data');
      if (!userData) return null;

      // Decrypt sensitive fields if they exist
      const decryptedUserData = { ...userData };
      const sensitiveFields = ['email', 'phone', 'address', 'paymentInfo'];

      for (const field of sensitiveFields) {
        if (userData[field] && typeof userData[field] === 'object' && userData[field].ciphertext) {
          try {
            const key = await encryptionService.generateKey(); // In real app, retrieve the correct key
            decryptedUserData[field] = await encryptionService.decrypt(userData[field], key);
          } catch (decryptError) {
            console.warn(`Failed to decrypt ${field}, using encrypted value`);
          }
        }
      }

      return decryptedUserData;
    } catch (error) {
      console.error('Error retrieving user data:', error);
      auditService.logSystem.error(error, 'user_data_retrieval');
      return null;
    }
  }

  /**
   * Clear stored user data
   */
  async clearUserData() {
    try {
      await secureStorageService.removeItem('user_data');
    } catch (error) {
      console.error('Error clearing user data:', error);
      auditService.logSystem.error(error, 'user_data_clearing');
    }
  }



  // Simulation methods (replace with real API calls in production)

  /**
   * Real login using Base44 API
   * @param {Object} credentials - Login credentials
   * @returns {Promise<Object>} Login response
   */
  async realLogin(credentials) {
    try {
      // Validate credentials first
      const validation = LoginSchema.safeParse(credentials);
      if (!validation.success) {
        return {
          success: false,
          error: 'Invalid credentials format',
          validationErrors: validation.error.errors
        };
      }

      // Call Base44 auth API with proper error handling
      const response = await this.callBase44AuthMethod('login', {
        email: credentials.email,
        password: credentials.password
      });

      if (response && response.data) {
        const { user, tokens } = response.data;

        // Store tokens securely
        await this.storeTokens(tokens);
        await this.storeUserData(user);

        // Log successful login
        auditService.logAuth.login(user.id, true, {
          email: user.email,
          loginMethod: 'email_password'
        });

        return {
          success: true,
          data: { user, tokens }
        };
      } else {
        throw new Error('Invalid response from authentication service');
      }
    } catch (error) {
      // Log failed login attempt
      auditService.logAuth.login(null, false, {
        email: credentials.email,
        error: error.message,
        loginMethod: 'email_password'
      });

      // Handle specific error types
      if (error.status === 401) {
        return {
          success: false,
          error: 'Invalid email or password'
        };
      } else if (error.status === 429) {
        return {
          success: false,
          error: 'Too many login attempts. Please try again later.'
        };
      } else if (error.status === 403) {
        return {
          success: false,
          error: 'Account is locked or suspended. Please contact support.'
        };
      }

      return {
        success: false,
        error: error.message || 'Login failed. Please try again.'
      };
    }
  }

  /**
   * Real registration using Base44 API
   * @param {Object} userData - Registration data
   * @returns {Promise<Object>} Registration response
   */
  async realRegister(userData) {
    try {
      // Validate registration data
      const validation = RegisterSchema.safeParse(userData);
      if (!validation.success) {
        return {
          success: false,
          error: 'Invalid registration data',
          validationErrors: validation.error.errors
        };
      }

      // Call Base44 auth API with proper error handling
      const response = await this.callBase44AuthMethod('register', {
        email: userData.email,
        password: userData.password,
        name: userData.name,
        company: userData.company,
        tier: userData.tier || 'startup'
      });

      if (response && response.data) {
        const { user, tokens } = response.data;

        // Store tokens securely
        await this.storeTokens(tokens);
        await this.storeUserData(user);

        // Log successful registration
        auditService.logAuth.register(user.id, true, {
          email: user.email,
          tier: user.tier,
          company: user.company
        });

        return {
          success: true,
          data: { user, tokens }
        };
      } else {
        throw new Error('Invalid response from registration service');
      }
    } catch (error) {
      // Log failed registration attempt
      auditService.logAuth.register(null, false, {
        email: userData.email,
        error: error.message
      });

      // Handle specific error types
      if (error.status === 409) {
        return {
          success: false,
          error: 'Email address is already registered'
        };
      } else if (error.status === 400) {
        return {
          success: false,
          error: 'Invalid registration data. Please check your information.'
        };
      } else if (error.status === 429) {
        return {
          success: false,
          error: 'Too many registration attempts. Please try again later.'
        };
      }

      return {
        success: false,
        error: error.message || 'Registration failed. Please try again.'
      };
    }
  }

  /**
   * Simulate token refresh (replace with real API call)
   * @param {string} refreshToken - Refresh token
   * @returns {Promise<Object>} Simulated refresh response
   */
  async simulateTokenRefresh(refreshToken) {
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 500));

    // Check if refresh token is valid (mock check)
    if (!refreshToken || !refreshToken.startsWith('mock_refresh_token_')) {
      return {
        success: false,
        error: 'Invalid refresh token'
      };
    }

    // Generate new tokens
    const tokens = {
      accessToken: `mock_access_token_${Date.now()}`,
      refreshToken: `mock_refresh_token_${Date.now()}`
    };

    return {
      success: true,
      data: { tokens }
    };
  }

  /**
   * Simulate token verification (replace with real API call)
   * @param {string} accessToken - Access token
   * @returns {Promise<Object>} Simulated verification response
   */
  async simulateTokenVerification(accessToken) {
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 300));

    // Check if token is valid (mock check)
    if (!accessToken || !accessToken.startsWith('mock_access_token_')) {
      return {
        success: false,
        error: 'Invalid access token'
      };
    }

    // Get stored user data
    const userData = this.getStoredUserData();
    if (!userData) {
      return {
        success: false,
        error: 'User data not found'
      };
    }

    return {
      success: true,
      data: { user: userData }
    };
  }

  /**
   * Call Base44 auth method with proper error handling
   * @param {string} method - Auth method name
   * @param {Object} params - Method parameters
   * @returns {Promise<Object>} API response
   */
  async callBase44AuthMethod(method, params) {
    try {
      // Check if Base44 auth method exists
      if (!base44.auth || typeof base44.auth[method] !== 'function') {
        throw new Error(`Base44 auth method '${method}' not available`);
      }

      // Call the method with timeout
      const timeoutPromise = new Promise((_, reject) => {
        setTimeout(() => reject(new Error(`Auth method '${method}' timed out`)), 30000);
      });

      const methodPromise = base44.auth[method](params);
      const response = await Promise.race([methodPromise, timeoutPromise]);

      return response;
    } catch (error) {
      // Enhanced error handling for Base44 auth methods
      const enhancedError = errorHandlingService.handleApiError(error, {
        method: `base44.auth.${method}`,
        params: Object.keys(params),
        component: 'AuthService'
      });

      throw error;
    }
  }
}

// Create and export singleton instance
export const authService = new AuthService();
