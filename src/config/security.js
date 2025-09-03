/**
 * Security Configuration
 * Comprehensive security settings and policies for PIKAR AI
 */

import { environmentConfig } from './environment'

export const securityConfig = {
  // Authentication Configuration
  authentication: {
    // JWT Configuration
    jwt: {
      secret: process.env.JWT_SECRET || 'your-super-secret-jwt-key-change-in-production',
      expiresIn: '24h',
      refreshExpiresIn: '7d',
      algorithm: 'HS256',
      issuer: 'pikar-ai',
      audience: 'pikar-ai-users'
    },
    
    // Session Configuration
    session: {
      secret: process.env.SESSION_SECRET || 'your-super-secret-session-key-change-in-production',
      name: 'pikar-ai-session',
      maxAge: 24 * 60 * 60 * 1000, // 24 hours
      secure: environmentConfig.environment === 'production',
      httpOnly: true,
      sameSite: 'strict',
      rolling: true
    },
    
    // Multi-Factor Authentication
    mfa: {
      enabled: true,
      issuer: 'PIKAR AI',
      window: 2, // Allow 2 time steps before/after current
      digits: 6,
      period: 30,
      algorithm: 'sha1'
    },
    
    // OAuth Configuration
    oauth: {
      google: {
        clientId: process.env.GOOGLE_CLIENT_ID,
        clientSecret: process.env.GOOGLE_CLIENT_SECRET,
        scope: ['profile', 'email']
      },
      microsoft: {
        clientId: process.env.MICROSOFT_CLIENT_ID,
        clientSecret: process.env.MICROSOFT_CLIENT_SECRET,
        scope: ['user.read']
      }
    }
  },

  // Password Policy
  passwordPolicy: {
    minLength: 12,
    maxLength: 128,
    requireUppercase: true,
    requireLowercase: true,
    requireNumbers: true,
    requireSpecialChars: true,
    specialChars: '!@#$%^&*()_+-=[]{}|;:,.<>?',
    preventCommonPasswords: true,
    preventUserInfo: true,
    maxAge: 90 * 24 * 60 * 60 * 1000, // 90 days
    historyCount: 12, // Remember last 12 passwords
    lockoutThreshold: 5,
    lockoutDuration: 30 * 60 * 1000 // 30 minutes
  },

  // Rate Limiting Configuration
  rateLimiting: {
    // General API rate limiting
    api: {
      windowMs: 15 * 60 * 1000, // 15 minutes
      max: 1000, // Limit each IP to 1000 requests per windowMs
      message: 'Too many requests from this IP, please try again later',
      standardHeaders: true,
      legacyHeaders: false
    },
    
    // Authentication rate limiting
    auth: {
      windowMs: 15 * 60 * 1000, // 15 minutes
      max: 10, // Limit each IP to 10 login attempts per windowMs
      skipSuccessfulRequests: true,
      message: 'Too many login attempts, please try again later'
    },
    
    // Agent execution rate limiting
    agents: {
      windowMs: 60 * 1000, // 1 minute
      max: 50, // Limit each user to 50 agent executions per minute
      keyGenerator: (req) => req.user?.id || req.ip,
      message: 'Agent execution rate limit exceeded'
    },
    
    // File upload rate limiting
    uploads: {
      windowMs: 60 * 60 * 1000, // 1 hour
      max: 100, // Limit each user to 100 uploads per hour
      keyGenerator: (req) => req.user?.id || req.ip,
      message: 'Upload rate limit exceeded'
    }
  },

  // CORS Configuration
  cors: {
    origin: function (origin, callback) {
      const allowedOrigins = [
        'https://pikar-ai.com',
        'https://www.pikar-ai.com',
        'https://app.pikar-ai.com',
        'https://admin.pikar-ai.com'
      ]
      
      // Allow requests with no origin (mobile apps, etc.)
      if (!origin) return callback(null, true)
      
      if (environmentConfig.environment === 'development') {
        allowedOrigins.push('http://localhost:3000', 'http://localhost:5173')
      }
      
      if (allowedOrigins.includes(origin)) {
        callback(null, true)
      } else {
        callback(new Error('Not allowed by CORS'))
      }
    },
    credentials: true,
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'],
    allowedHeaders: [
      'Origin',
      'X-Requested-With',
      'Content-Type',
      'Accept',
      'Authorization',
      'X-API-Key',
      'X-Request-ID'
    ],
    exposedHeaders: ['X-Request-ID', 'X-Rate-Limit-Remaining'],
    maxAge: 86400 // 24 hours
  },

  // Content Security Policy
  csp: {
    directives: {
      defaultSrc: ["'self'"],
      scriptSrc: [
        "'self'",
        "'unsafe-inline'", // Required for some React functionality
        'https://cdn.jsdelivr.net',
        'https://unpkg.com'
      ],
      styleSrc: [
        "'self'",
        "'unsafe-inline'", // Required for styled-components
        'https://fonts.googleapis.com'
      ],
      fontSrc: [
        "'self'",
        'https://fonts.gstatic.com'
      ],
      imgSrc: [
        "'self'",
        'data:',
        'https:',
        'blob:'
      ],
      connectSrc: [
        "'self'",
        'https://api.pikar-ai.com',
        'https://api.base44.com',
        'wss://pikar-ai.com'
      ],
      frameSrc: ["'none'"],
      objectSrc: ["'none'"],
      mediaSrc: ["'self'"],
      workerSrc: ["'self'", 'blob:'],
      childSrc: ["'self'"],
      formAction: ["'self'"],
      upgradeInsecureRequests: environmentConfig.environment === 'production'
    },
    reportOnly: environmentConfig.environment === 'development'
  },

  // Security Headers
  headers: {
    // Strict Transport Security
    hsts: {
      maxAge: 31536000, // 1 year
      includeSubDomains: true,
      preload: true
    },
    
    // X-Frame-Options
    frameOptions: 'DENY',
    
    // X-Content-Type-Options
    noSniff: true,
    
    // X-XSS-Protection
    xssFilter: true,
    
    // Referrer Policy
    referrerPolicy: 'strict-origin-when-cross-origin',
    
    // Permissions Policy
    permissionsPolicy: {
      camera: [],
      microphone: [],
      geolocation: [],
      payment: [],
      usb: [],
      magnetometer: [],
      gyroscope: [],
      accelerometer: []
    }
  },

  // Encryption Configuration
  encryption: {
    // Data at rest encryption
    dataAtRest: {
      algorithm: 'aes-256-gcm',
      keyDerivation: 'pbkdf2',
      iterations: 100000,
      saltLength: 32,
      tagLength: 16
    },
    
    // Data in transit encryption
    dataInTransit: {
      minTlsVersion: '1.2',
      cipherSuites: [
        'ECDHE-RSA-AES128-GCM-SHA256',
        'ECDHE-RSA-AES256-GCM-SHA384',
        'ECDHE-RSA-AES128-SHA256',
        'ECDHE-RSA-AES256-SHA384'
      ],
      honorCipherOrder: true,
      sessionTimeout: 300 // 5 minutes
    },
    
    // Field-level encryption
    fieldLevel: {
      algorithm: 'aes-256-gcm',
      keyRotationInterval: 90 * 24 * 60 * 60 * 1000, // 90 days
      encryptedFields: [
        'email',
        'phone',
        'address',
        'ssn',
        'creditCard',
        'bankAccount'
      ]
    }
  },

  // Input Validation and Sanitization
  validation: {
    // Maximum request size
    maxRequestSize: '10mb',
    
    // File upload restrictions
    fileUpload: {
      maxSize: 50 * 1024 * 1024, // 50MB
      allowedTypes: [
        'image/jpeg',
        'image/png',
        'image/gif',
        'image/webp',
        'application/pdf',
        'text/plain',
        'text/csv',
        'application/json'
      ],
      maxFiles: 10,
      virusScanEnabled: true
    },
    
    // Input sanitization rules
    sanitization: {
      stripHtml: true,
      trimWhitespace: true,
      normalizeUnicode: true,
      maxStringLength: 10000,
      allowedHtmlTags: [], // No HTML allowed by default
      sqlInjectionProtection: true,
      xssProtection: true
    }
  },

  // Audit and Logging
  audit: {
    // Events to audit
    events: [
      'user_login',
      'user_logout',
      'user_registration',
      'password_change',
      'mfa_setup',
      'mfa_disable',
      'role_change',
      'permission_change',
      'data_access',
      'data_modification',
      'data_deletion',
      'agent_execution',
      'file_upload',
      'file_download',
      'security_violation',
      'failed_login',
      'account_lockout'
    ],
    
    // Audit log retention
    retention: {
      days: 2555, // 7 years for compliance
      compressionEnabled: true,
      encryptionEnabled: true
    },
    
    // Real-time monitoring
    realTimeMonitoring: {
      enabled: true,
      alertThresholds: {
        failedLogins: 10,
        suspiciousActivity: 5,
        dataExfiltration: 1,
        privilegeEscalation: 1
      }
    }
  },

  // API Security
  api: {
    // API Key configuration
    apiKeys: {
      length: 64,
      prefix: 'pk_',
      expirationDays: 365,
      rotationWarningDays: 30,
      maxKeysPerUser: 10
    },
    
    // Request signing
    requestSigning: {
      enabled: true,
      algorithm: 'hmac-sha256',
      timestampTolerance: 300, // 5 minutes
      nonceLength: 32
    },
    
    // API versioning
    versioning: {
      strategy: 'header', // 'header', 'url', 'query'
      headerName: 'API-Version',
      currentVersion: 'v1',
      supportedVersions: ['v1'],
      deprecationWarningDays: 90
    }
  },

  // Data Loss Prevention
  dlp: {
    enabled: true,
    
    // Sensitive data patterns
    patterns: {
      creditCard: /\b(?:\d{4}[-\s]?){3}\d{4}\b/g,
      ssn: /\b\d{3}-\d{2}-\d{4}\b/g,
      email: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g,
      phone: /\b\d{3}-\d{3}-\d{4}\b/g,
      ipAddress: /\b(?:\d{1,3}\.){3}\d{1,3}\b/g
    },
    
    // Actions for detected sensitive data
    actions: {
      log: true,
      alert: true,
      block: false, // Set to true for strict blocking
      redact: true
    },
    
    // Whitelist for allowed sensitive data contexts
    whitelist: [
      '/api/v1/users/profile', // Allow email in profile updates
      '/api/v1/payments' // Allow credit card in payment processing
    ]
  },

  // Security Monitoring
  monitoring: {
    // Intrusion detection
    intrusionDetection: {
      enabled: true,
      rules: [
        {
          name: 'SQL Injection Attempt',
          pattern: /(union|select|insert|update|delete|drop|create|alter)\s+/i,
          severity: 'high'
        },
        {
          name: 'XSS Attempt',
          pattern: /<script|javascript:|on\w+\s*=/i,
          severity: 'high'
        },
        {
          name: 'Path Traversal Attempt',
          pattern: /\.\.[\/\\]/,
          severity: 'medium'
        },
        {
          name: 'Command Injection Attempt',
          pattern: /[;&|`$()]/,
          severity: 'high'
        }
      ]
    },
    
    // Anomaly detection
    anomalyDetection: {
      enabled: true,
      baselineWindow: 7 * 24 * 60 * 60 * 1000, // 7 days
      alertThreshold: 3, // Standard deviations
      metrics: [
        'request_rate',
        'error_rate',
        'response_time',
        'data_volume',
        'login_frequency'
      ]
    }
  },

  // Incident Response
  incidentResponse: {
    // Automatic response actions
    autoResponse: {
      enabled: true,
      actions: {
        blockIp: {
          enabled: true,
          duration: 60 * 60 * 1000, // 1 hour
          threshold: 10 // violations
        },
        lockAccount: {
          enabled: true,
          duration: 30 * 60 * 1000, // 30 minutes
          threshold: 5 // failed attempts
        },
        alertTeam: {
          enabled: true,
          channels: ['email', 'slack', 'sms'],
          severity: 'medium'
        }
      }
    },
    
    // Incident classification
    classification: {
      low: {
        responseTime: 24 * 60 * 60 * 1000, // 24 hours
        escalation: false
      },
      medium: {
        responseTime: 4 * 60 * 60 * 1000, // 4 hours
        escalation: true
      },
      high: {
        responseTime: 60 * 60 * 1000, // 1 hour
        escalation: true
      },
      critical: {
        responseTime: 15 * 60 * 1000, // 15 minutes
        escalation: true
      }
    }
  },

  // Compliance Settings
  compliance: {
    frameworks: ['SOC2', 'GDPR', 'ISO27001'],
    
    // Data retention policies
    dataRetention: {
      userProfiles: 7 * 365 * 24 * 60 * 60 * 1000, // 7 years
      auditLogs: 7 * 365 * 24 * 60 * 60 * 1000, // 7 years
      sessionData: 30 * 24 * 60 * 60 * 1000, // 30 days
      temporaryFiles: 24 * 60 * 60 * 1000, // 24 hours
      backups: 90 * 24 * 60 * 60 * 1000 // 90 days
    },
    
    // Privacy settings
    privacy: {
      dataMinimization: true,
      purposeLimitation: true,
      consentRequired: true,
      rightToErasure: true,
      dataPortability: true,
      privacyByDesign: true
    }
  }
}

// Environment-specific overrides
if (environmentConfig.environment === 'development') {
  // Relax some security settings for development
  securityConfig.csp.reportOnly = true
  securityConfig.headers.hsts.maxAge = 0
  securityConfig.rateLimiting.api.max = 10000
  securityConfig.passwordPolicy.minLength = 8
}

if (environmentConfig.environment === 'production') {
  // Strengthen security settings for production
  securityConfig.session.secure = true
  securityConfig.dlp.actions.block = true
  securityConfig.monitoring.intrusionDetection.enabled = true
  securityConfig.incidentResponse.autoResponse.enabled = true
}

export default securityConfig
