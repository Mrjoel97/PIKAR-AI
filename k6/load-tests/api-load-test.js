/**
 * API Load Testing with k6
 * Comprehensive load testing for PIKAR AI API endpoints
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('error_rate');
const responseTime = new Trend('response_time');
const requestCount = new Counter('request_count');

// Test configuration
export const options = {
  stages: [
    // Ramp up
    { duration: '2m', target: 10 },   // Ramp up to 10 users over 2 minutes
    { duration: '5m', target: 50 },   // Stay at 50 users for 5 minutes
    { duration: '3m', target: 100 },  // Ramp up to 100 users over 3 minutes
    { duration: '10m', target: 100 }, // Stay at 100 users for 10 minutes
    { duration: '2m', target: 200 },  // Spike to 200 users
    { duration: '1m', target: 200 },  // Stay at spike for 1 minute
    { duration: '5m', target: 0 },    // Ramp down to 0 users
  ],
  thresholds: {
    // API response time thresholds
    'http_req_duration': ['p(95)<2000', 'p(99)<5000'], // 95% < 2s, 99% < 5s
    'http_req_failed': ['rate<0.05'], // Error rate < 5%
    
    // Custom metric thresholds
    'error_rate': ['rate<0.05'],
    'response_time': ['p(95)<2000'],
    
    // Specific endpoint thresholds
    'http_req_duration{endpoint:auth}': ['p(95)<500'],
    'http_req_duration{endpoint:campaigns}': ['p(95)<1000'],
    'http_req_duration{endpoint:agents}': ['p(95)<3000'],
    'http_req_duration{endpoint:analytics}': ['p(95)<2000'],
  },
};

// Test data
const BASE_URL = __ENV.BASE_URL || 'https://api.pikar-ai.com';
const TEST_USER = {
  email: 'loadtest@pikar.ai',
  password: 'LoadTest123!'
};

let authToken = '';

// Setup function - runs once per VU
export function setup() {
  console.log('Starting load test setup...');
  
  // Authenticate and get token
  const loginResponse = http.post(`${BASE_URL}/auth/login`, JSON.stringify(TEST_USER), {
    headers: { 'Content-Type': 'application/json' },
    tags: { endpoint: 'auth' }
  });
  
  if (loginResponse.status === 200) {
    const loginData = JSON.parse(loginResponse.body);
    return { authToken: loginData.data.token };
  }
  
  console.error('Setup failed: Unable to authenticate');
  return { authToken: null };
}

// Main test function
export default function(data) {
  if (!data.authToken) {
    console.error('No auth token available, skipping test');
    return;
  }

  const headers = {
    'Authorization': `Bearer ${data.authToken}`,
    'Content-Type': 'application/json'
  };

  // Test different user scenarios
  const scenarios = [
    () => testDashboardLoad(headers),
    () => testCampaignOperations(headers),
    () => testAgentExecution(headers),
    () => testAnalyticsQueries(headers),
    () => testUserProfile(headers)
  ];

  // Randomly select a scenario (simulating different user behaviors)
  const scenario = scenarios[Math.floor(Math.random() * scenarios.length)];
  scenario();

  // Think time between requests
  sleep(Math.random() * 3 + 1); // 1-4 seconds
}

function testDashboardLoad(headers) {
  group('Dashboard Load Test', () => {
    // Load dashboard metrics
    const metricsResponse = http.get(`${BASE_URL}/dashboard/metrics`, {
      headers,
      tags: { endpoint: 'dashboard' }
    });

    const metricsCheck = check(metricsResponse, {
      'dashboard metrics status is 200': (r) => r.status === 200,
      'dashboard metrics response time < 1s': (r) => r.timings.duration < 1000,
      'dashboard metrics has data': (r) => {
        try {
          const data = JSON.parse(r.body);
          return data.success && data.data;
        } catch {
          return false;
        }
      }
    });

    errorRate.add(!metricsCheck);
    responseTime.add(metricsResponse.timings.duration);
    requestCount.add(1);

    // Load recent campaigns
    const campaignsResponse = http.get(`${BASE_URL}/campaigns?limit=10&sort=recent`, {
      headers,
      tags: { endpoint: 'campaigns' }
    });

    check(campaignsResponse, {
      'recent campaigns status is 200': (r) => r.status === 200,
      'recent campaigns response time < 800ms': (r) => r.timings.duration < 800
    });

    // Load recent activity
    const activityResponse = http.get(`${BASE_URL}/activity/recent?limit=20`, {
      headers,
      tags: { endpoint: 'activity' }
    });

    check(activityResponse, {
      'recent activity status is 200': (r) => r.status === 200,
      'recent activity response time < 500ms': (r) => r.timings.duration < 500
    });
  });
}

function testCampaignOperations(headers) {
  group('Campaign Operations Test', () => {
    // List campaigns
    const listResponse = http.get(`${BASE_URL}/campaigns?page=1&limit=50`, {
      headers,
      tags: { endpoint: 'campaigns' }
    });

    check(listResponse, {
      'campaign list status is 200': (r) => r.status === 200,
      'campaign list response time < 1s': (r) => r.timings.duration < 1000,
      'campaign list has pagination': (r) => {
        try {
          const data = JSON.parse(r.body);
          return data.data && data.pagination;
        } catch {
          return false;
        }
      }
    });

    // Create new campaign (10% of users)
    if (Math.random() < 0.1) {
      const newCampaign = {
        name: `Load Test Campaign ${Date.now()}`,
        description: 'Campaign created during load testing',
        type: 'social-media',
        budget: Math.floor(Math.random() * 10000) + 1000,
        platforms: ['facebook', 'twitter']
      };

      const createResponse = http.post(`${BASE_URL}/campaigns`, JSON.stringify(newCampaign), {
        headers,
        tags: { endpoint: 'campaigns' }
      });

      check(createResponse, {
        'campaign create status is 201': (r) => r.status === 201,
        'campaign create response time < 2s': (r) => r.timings.duration < 2000
      });

      // If campaign created successfully, try to update it
      if (createResponse.status === 201) {
        try {
          const createdCampaign = JSON.parse(createResponse.body);
          const campaignId = createdCampaign.data.id;

          const updateData = {
            name: `Updated ${newCampaign.name}`,
            budget: newCampaign.budget + 500
          };

          const updateResponse = http.put(`${BASE_URL}/campaigns/${campaignId}`, JSON.stringify(updateData), {
            headers,
            tags: { endpoint: 'campaigns' }
          });

          check(updateResponse, {
            'campaign update status is 200': (r) => r.status === 200,
            'campaign update response time < 1.5s': (r) => r.timings.duration < 1500
          });
        } catch (e) {
          console.error('Failed to update campaign:', e.message);
        }
      }
    }

    // View campaign details (30% of users)
    if (Math.random() < 0.3) {
      // Simulate viewing a random campaign
      const campaignId = Math.floor(Math.random() * 100) + 1;
      
      const detailResponse = http.get(`${BASE_URL}/campaigns/${campaignId}`, {
        headers,
        tags: { endpoint: 'campaigns' }
      });

      check(detailResponse, {
        'campaign detail response time < 800ms': (r) => r.timings.duration < 800
      });
    }
  });
}

function testAgentExecution(headers) {
  group('AI Agent Execution Test', () => {
    const agentTypes = [
      'strategic_planning',
      'content_creation',
      'data_analysis',
      'customer_support',
      'sales_intelligence'
    ];

    const randomAgent = agentTypes[Math.floor(Math.random() * agentTypes.length)];
    
    const agentRequest = {
      agentType: randomAgent,
      task: 'load-test-task',
      parameters: {
        complexity: 'medium',
        loadTest: true,
        timestamp: Date.now()
      }
    };

    const agentResponse = http.post(`${BASE_URL}/agents/execute`, JSON.stringify(agentRequest), {
      headers,
      tags: { endpoint: 'agents' },
      timeout: '30s' // Agents can take longer
    });

    const agentCheck = check(agentResponse, {
      'agent execution status is 200': (r) => r.status === 200,
      'agent execution response time < 10s': (r) => r.timings.duration < 10000,
      'agent execution has result': (r) => {
        try {
          const data = JSON.parse(r.body);
          return data.success && data.data && data.data.result;
        } catch {
          return false;
        }
      }
    });

    errorRate.add(!agentCheck);
    responseTime.add(agentResponse.timings.duration);
    requestCount.add(1);

    // Check agent status (20% of users)
    if (Math.random() < 0.2) {
      const statusResponse = http.get(`${BASE_URL}/agents/status`, {
        headers,
        tags: { endpoint: 'agents' }
      });

      check(statusResponse, {
        'agent status response time < 300ms': (r) => r.timings.duration < 300
      });
    }
  });
}

function testAnalyticsQueries(headers) {
  group('Analytics Queries Test', () => {
    const timeRanges = ['7d', '30d', '90d'];
    const randomRange = timeRanges[Math.floor(Math.random() * timeRanges.length)];

    // Campaign analytics
    const campaignAnalyticsResponse = http.get(`${BASE_URL}/analytics/campaigns?range=${randomRange}`, {
      headers,
      tags: { endpoint: 'analytics' }
    });

    check(campaignAnalyticsResponse, {
      'campaign analytics status is 200': (r) => r.status === 200,
      'campaign analytics response time < 2s': (r) => r.timings.duration < 2000
    });

    // User engagement analytics
    const engagementResponse = http.get(`${BASE_URL}/analytics/engagement?range=${randomRange}`, {
      headers,
      tags: { endpoint: 'analytics' }
    });

    check(engagementResponse, {
      'engagement analytics status is 200': (r) => r.status === 200,
      'engagement analytics response time < 1.5s': (r) => r.timings.duration < 1500
    });

    // Performance metrics (15% of users)
    if (Math.random() < 0.15) {
      const performanceResponse = http.get(`${BASE_URL}/analytics/performance?range=${randomRange}&detailed=true`, {
        headers,
        tags: { endpoint: 'analytics' }
      });

      check(performanceResponse, {
        'performance analytics response time < 3s': (r) => r.timings.duration < 3000
      });
    }
  });
}

function testUserProfile(headers) {
  group('User Profile Test', () => {
    // Get user profile
    const profileResponse = http.get(`${BASE_URL}/user/profile`, {
      headers,
      tags: { endpoint: 'user' }
    });

    check(profileResponse, {
      'user profile status is 200': (r) => r.status === 200,
      'user profile response time < 400ms': (r) => r.timings.duration < 400
    });

    // Update profile (5% of users)
    if (Math.random() < 0.05) {
      const updateData = {
        preferences: {
          notifications: Math.random() > 0.5,
          theme: Math.random() > 0.5 ? 'dark' : 'light',
          language: 'en'
        }
      };

      const updateResponse = http.put(`${BASE_URL}/user/profile`, JSON.stringify(updateData), {
        headers,
        tags: { endpoint: 'user' }
      });

      check(updateResponse, {
        'profile update status is 200': (r) => r.status === 200,
        'profile update response time < 600ms': (r) => r.timings.duration < 600
      });
    }

    // Get user activity (25% of users)
    if (Math.random() < 0.25) {
      const activityResponse = http.get(`${BASE_URL}/user/activity?limit=50`, {
        headers,
        tags: { endpoint: 'user' }
      });

      check(activityResponse, {
        'user activity response time < 800ms': (r) => r.timings.duration < 800
      });
    }
  });
}

// Teardown function - runs once after all VUs finish
export function teardown(data) {
  console.log('Load test completed');
  
  if (data.authToken) {
    // Logout
    http.post(`${BASE_URL}/auth/logout`, null, {
      headers: {
        'Authorization': `Bearer ${data.authToken}`,
        'Content-Type': 'application/json'
      }
    });
  }
}

// Handle summary - custom summary output
export function handleSummary(data) {
  return {
    'load-test-results.json': JSON.stringify(data, null, 2),
    'load-test-summary.html': generateHTMLReport(data),
    stdout: generateConsoleReport(data)
  };
}

function generateConsoleReport(data) {
  const report = `
=== PIKAR AI Load Test Results ===

Test Duration: ${data.state.testRunDurationMs / 1000}s
Virtual Users: ${data.metrics.vus_max.values.max}
Total Requests: ${data.metrics.http_reqs.values.count}

Response Times:
- Average: ${data.metrics.http_req_duration.values.avg.toFixed(2)}ms
- 95th percentile: ${data.metrics.http_req_duration.values['p(95)'].toFixed(2)}ms
- 99th percentile: ${data.metrics.http_req_duration.values['p(99)'].toFixed(2)}ms

Error Rate: ${(data.metrics.http_req_failed.values.rate * 100).toFixed(2)}%
Requests/sec: ${data.metrics.http_reqs.values.rate.toFixed(2)}

Thresholds:
${Object.entries(data.thresholds).map(([key, value]) => 
  `- ${key}: ${value.ok ? '✓ PASS' : '✗ FAIL'}`
).join('\n')}

=== End Report ===
  `;
  
  return report;
}

function generateHTMLReport(data) {
  return `
<!DOCTYPE html>
<html>
<head>
    <title>PIKAR AI Load Test Results</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .metric { margin: 10px 0; }
        .pass { color: green; }
        .fail { color: red; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <h1>PIKAR AI Load Test Results</h1>
    
    <h2>Test Summary</h2>
    <div class="metric">Test Duration: ${data.state.testRunDurationMs / 1000}s</div>
    <div class="metric">Max Virtual Users: ${data.metrics.vus_max.values.max}</div>
    <div class="metric">Total Requests: ${data.metrics.http_reqs.values.count}</div>
    <div class="metric">Requests/sec: ${data.metrics.http_reqs.values.rate.toFixed(2)}</div>
    
    <h2>Performance Metrics</h2>
    <table>
        <tr><th>Metric</th><th>Value</th></tr>
        <tr><td>Average Response Time</td><td>${data.metrics.http_req_duration.values.avg.toFixed(2)}ms</td></tr>
        <tr><td>95th Percentile</td><td>${data.metrics.http_req_duration.values['p(95)'].toFixed(2)}ms</td></tr>
        <tr><td>99th Percentile</td><td>${data.metrics.http_req_duration.values['p(99)'].toFixed(2)}ms</td></tr>
        <tr><td>Error Rate</td><td>${(data.metrics.http_req_failed.values.rate * 100).toFixed(2)}%</td></tr>
    </table>
    
    <h2>Threshold Results</h2>
    <ul>
        ${Object.entries(data.thresholds).map(([key, value]) => 
          `<li class="${value.ok ? 'pass' : 'fail'}">${key}: ${value.ok ? 'PASS' : 'FAIL'}</li>`
        ).join('')}
    </ul>
</body>
</html>
  `;
}
