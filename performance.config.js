/**
 * Performance Testing Configuration
 * Configuration for all performance testing tools and thresholds
 */

export default {
  // Test environment configuration
  environment: {
    baseUrl: process.env.VITE_API_BASE_URL || 'http://localhost:3000',
    apiUrl: process.env.VITE_API_BASE_URL || 'http://localhost:3001/api',
    testUser: {
      email: process.env.PERF_TEST_EMAIL || 'test@pikar.ai',
      password: process.env.PERF_TEST_PASSWORD || 'TestPassword123!'
    }
  },

  // Performance thresholds
  thresholds: {
    // Frontend performance (milliseconds)
    frontend: {
      componentRender: 100,
      pageLoad: 3000,
      userInteraction: 200,
      bundleSize: 1024 * 1024, // 1MB
      chunkSize: 250 * 1024,   // 250KB
      
      // Core Web Vitals
      firstContentfulPaint: 2000,
      largestContentfulPaint: 2500,
      cumulativeLayoutShift: 0.1,
      interactionToNextPaint: 200,
      firstInputDelay: 100
    },

    // API performance (milliseconds)
    api: {
      authentication: 500,
      campaigns: 1000,
      agents: 10000,
      analytics: 2000,
      fileUpload: 5000,
      
      // Database queries
      simpleQuery: 100,
      complexQuery: 500,
      aggregation: 1000
    },

    // Memory thresholds (bytes)
    memory: {
      maxUsage: 100 * 1024 * 1024,    // 100MB
      maxLeak: 10 * 1024 * 1024,      // 10MB
      maxIncrease: 50 * 1024 * 1024   // 50MB
    },

    // Load testing thresholds
    load: {
      maxUsers: 1000,
      requestsPerSecond: 500,
      errorRate: 0.05,        // 5%
      avgResponseTime: 1000,  // 1s
      p95ResponseTime: 2000,  // 2s
      p99ResponseTime: 5000   // 5s
    },

    // Browser performance
    browser: {
      domContentLoaded: 2000,
      loadComplete: 5000,
      timeToInteractive: 3000,
      speedIndex: 2500
    }
  },

  // Test scenarios configuration
  scenarios: {
    // Frontend performance scenarios
    frontend: {
      componentRender: {
        enabled: true,
        components: [
          'Dashboard',
          'CampaignCreation',
          'ContentCreation',
          'Analytics',
          'AgentExecution'
        ]
      },
      
      pageLoad: {
        enabled: true,
        pages: [
          { path: '/', name: 'Landing' },
          { path: '/dashboard', name: 'Dashboard' },
          { path: '/campaigns', name: 'Campaigns' },
          { path: '/campaigns/create', name: 'Campaign Creation' },
          { path: '/agents', name: 'Agents' },
          { path: '/analytics', name: 'Analytics' }
        ]
      },

      userInteraction: {
        enabled: true,
        interactions: [
          'button-click',
          'form-input',
          'navigation',
          'search',
          'filter',
          'sort'
        ]
      }
    },

    // API performance scenarios
    api: {
      crud: {
        enabled: true,
        endpoints: [
          { method: 'POST', path: '/auth/login', name: 'Login' },
          { method: 'GET', path: '/campaigns', name: 'List Campaigns' },
          { method: 'POST', path: '/campaigns', name: 'Create Campaign' },
          { method: 'GET', path: '/campaigns/:id', name: 'Get Campaign' },
          { method: 'PUT', path: '/campaigns/:id', name: 'Update Campaign' },
          { method: 'DELETE', path: '/campaigns/:id', name: 'Delete Campaign' }
        ]
      },

      agents: {
        enabled: true,
        types: [
          'strategic_planning',
          'content_creation',
          'data_analysis',
          'customer_support',
          'sales_intelligence'
        ]
      },

      analytics: {
        enabled: true,
        queries: [
          'dashboard-metrics',
          'campaign-performance',
          'user-engagement',
          'agent-usage',
          'system-health'
        ]
      }
    },

    // Load testing scenarios
    load: {
      smoke: {
        enabled: true,
        vus: 5,
        duration: '2m',
        description: 'Smoke test with minimal load'
      },

      average: {
        enabled: true,
        vus: 50,
        duration: '10m',
        description: 'Average load simulation'
      },

      stress: {
        enabled: false, // Disabled by default
        vus: 200,
        duration: '15m',
        description: 'Stress test with high load'
      },

      spike: {
        enabled: false, // Disabled by default
        stages: [
          { duration: '2m', target: 10 },
          { duration: '1m', target: 100 },
          { duration: '2m', target: 10 }
        ],
        description: 'Spike test with sudden load increase'
      }
    }
  },

  // Reporting configuration
  reporting: {
    outputDir: './performance-results',
    formats: ['json', 'html', 'csv'],
    
    // Report sections to include
    sections: {
      summary: true,
      detailed: true,
      charts: true,
      recommendations: true,
      comparison: true
    },

    // Notification settings
    notifications: {
      enabled: process.env.NODE_ENV === 'production',
      webhook: process.env.PERF_WEBHOOK_URL,
      email: process.env.PERF_EMAIL_RECIPIENTS?.split(',') || [],
      
      // Notification triggers
      triggers: {
        testFailure: true,
        thresholdBreach: true,
        performanceRegression: true
      }
    }
  },

  // Tool-specific configurations
  tools: {
    // Vitest configuration for performance tests
    vitest: {
      testTimeout: 30000,
      hookTimeout: 10000,
      teardownTimeout: 5000,
      
      // Performance test specific settings
      performance: {
        warmupRuns: 3,
        measurementRuns: 10,
        maxVariation: 0.1 // 10% variation allowed
      }
    },

    // k6 configuration
    k6: {
      // Default options for all k6 tests
      options: {
        summaryTrendStats: ['avg', 'min', 'med', 'max', 'p(90)', 'p(95)', 'p(99)'],
        summaryTimeUnit: 'ms',
        
        // HTTP configuration
        http: {
          timeout: '30s',
          responseCallback: null
        },

        // Browser configuration (for browser tests)
        browser: {
          type: 'chromium',
          headless: true,
          args: ['--no-sandbox', '--disable-dev-shm-usage']
        }
      },

      // Environment variables for k6
      env: {
        BASE_URL: process.env.VITE_API_BASE_URL || 'http://localhost:3000',
        API_URL: process.env.VITE_API_BASE_URL || 'http://localhost:3001/api',
        TEST_EMAIL: process.env.PERF_TEST_EMAIL || 'test@pikar.ai',
        TEST_PASSWORD: process.env.PERF_TEST_PASSWORD || 'TestPassword123!'
      }
    },

    // Playwright configuration for browser performance
    playwright: {
      use: {
        // Browser settings
        headless: true,
        viewport: { width: 1280, height: 720 },
        ignoreHTTPSErrors: true,
        
        // Performance settings
        launchOptions: {
          args: [
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-web-security',
            '--disable-features=TranslateUI'
          ]
        }
      },

      // Test configuration
      timeout: 30000,
      expect: { timeout: 5000 },
      
      // Performance specific settings
      performance: {
        tracing: true,
        video: 'retain-on-failure',
        screenshot: 'only-on-failure'
      }
    }
  },

  // Monitoring and alerting
  monitoring: {
    enabled: true,
    
    // Metrics to track
    metrics: [
      'response_time',
      'throughput',
      'error_rate',
      'memory_usage',
      'cpu_usage',
      'core_web_vitals'
    ],

    // Alert conditions
    alerts: {
      responseTimeP95: { threshold: 2000, severity: 'warning' },
      responseTimeP99: { threshold: 5000, severity: 'critical' },
      errorRate: { threshold: 0.05, severity: 'critical' },
      memoryUsage: { threshold: 0.8, severity: 'warning' },
      coreWebVitals: {
        fcp: { threshold: 2000, severity: 'warning' },
        lcp: { threshold: 2500, severity: 'warning' },
        cls: { threshold: 0.1, severity: 'warning' }
      }
    }
  },

  // CI/CD integration
  ci: {
    enabled: process.env.CI === 'true',
    
    // Performance gates for CI/CD
    gates: {
      // Fail build if these thresholds are exceeded
      failOn: {
        errorRate: 0.1,        // 10% error rate
        p95ResponseTime: 5000, // 5s response time
        performanceScore: 50   // Performance score below 50
      },

      // Warn but don't fail build
      warnOn: {
        errorRate: 0.05,       // 5% error rate
        p95ResponseTime: 2000, // 2s response time
        performanceScore: 70   // Performance score below 70
      }
    },

    // Test selection for CI
    testSuites: {
      pullRequest: ['smoke', 'api-basic'],
      staging: ['smoke', 'api-full', 'frontend-basic'],
      production: ['smoke', 'load-average', 'api-full', 'frontend-full']
    }
  }
}
