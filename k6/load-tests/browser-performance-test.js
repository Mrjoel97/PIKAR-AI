/**
 * Browser Performance Testing with k6
 * Frontend performance testing using k6 browser module
 */

import { browser } from 'k6/experimental/browser';
import { check, sleep } from 'k6';
import { Trend, Rate } from 'k6/metrics';

// Custom metrics
const pageLoadTime = new Trend('page_load_time');
const firstContentfulPaint = new Trend('first_contentful_paint');
const largestContentfulPaint = new Trend('largest_contentful_paint');
const cumulativeLayoutShift = new Trend('cumulative_layout_shift');
const interactionToNextPaint = new Trend('interaction_to_next_paint');
const jsErrorRate = new Rate('js_error_rate');

export const options = {
  scenarios: {
    browser_performance: {
      executor: 'constant-vus',
      vus: 5, // 5 concurrent browser sessions
      duration: '10m',
      options: {
        browser: {
          type: 'chromium',
        },
      },
    },
  },
  thresholds: {
    // Core Web Vitals thresholds
    'first_contentful_paint': ['p(95)<2000'], // FCP < 2s
    'largest_contentful_paint': ['p(95)<2500'], // LCP < 2.5s
    'cumulative_layout_shift': ['p(95)<0.1'], // CLS < 0.1
    'interaction_to_next_paint': ['p(95)<200'], // INP < 200ms
    
    // Page load performance
    'page_load_time': ['p(95)<5000'], // Page load < 5s
    'js_error_rate': ['rate<0.01'], // JS error rate < 1%
  },
};

const BASE_URL = __ENV.BASE_URL || 'https://pikar-ai.com';

export default async function () {
  const page = browser.newPage();
  
  try {
    // Test different user journeys
    const journeys = [
      () => testDashboardPerformance(page),
      () => testCampaignCreationPerformance(page),
      () => testAgentInteractionPerformance(page),
      () => testAnalyticsPerformance(page),
      () => testMobilePerformance(page)
    ];

    // Randomly select a journey
    const journey = journeys[Math.floor(Math.random() * journeys.length)];
    await journey();

  } catch (error) {
    console.error('Browser test error:', error);
    jsErrorRate.add(1);
  } finally {
    page.close();
  }
}

async function testDashboardPerformance(page) {
  console.log('Testing dashboard performance...');
  
  // Navigate to login page
  const loginStartTime = Date.now();
  await page.goto(`${BASE_URL}/login`);
  await page.waitForLoadState('networkidle');
  
  // Login
  await page.fill('[data-testid="email-input"]', 'test@pikar.ai');
  await page.fill('[data-testid="password-input"]', 'TestPassword123!');
  
  const loginClickTime = Date.now();
  await page.click('[data-testid="login-button"]');
  
  // Wait for dashboard to load
  await page.waitForSelector('[data-testid="dashboard-content"]', { timeout: 10000 });
  const dashboardLoadTime = Date.now() - loginClickTime;
  
  pageLoadTime.add(dashboardLoadTime);
  
  // Measure Core Web Vitals
  const webVitals = await page.evaluate(() => {
    return new Promise((resolve) => {
      const observer = new PerformanceObserver((list) => {
        const entries = list.getEntries();
        const vitals = {};
        
        entries.forEach((entry) => {
          switch (entry.entryType) {
            case 'paint':
              if (entry.name === 'first-contentful-paint') {
                vitals.fcp = entry.startTime;
              }
              break;
            case 'largest-contentful-paint':
              vitals.lcp = entry.startTime;
              break;
            case 'layout-shift':
              if (!entry.hadRecentInput) {
                vitals.cls = (vitals.cls || 0) + entry.value;
              }
              break;
          }
        });
        
        // Resolve after collecting metrics for 3 seconds
        setTimeout(() => resolve(vitals), 3000);
      });
      
      observer.observe({ entryTypes: ['paint', 'largest-contentful-paint', 'layout-shift'] });
    });
  });
  
  if (webVitals.fcp) firstContentfulPaint.add(webVitals.fcp);
  if (webVitals.lcp) largestContentfulPaint.add(webVitals.lcp);
  if (webVitals.cls) cumulativeLayoutShift.add(webVitals.cls);
  
  // Test dashboard interactions
  await testDashboardInteractions(page);
  
  check(page, {
    'dashboard loaded successfully': () => page.locator('[data-testid="dashboard-content"]').isVisible(),
    'dashboard load time < 5s': () => dashboardLoadTime < 5000,
  });
}

async function testDashboardInteractions(page) {
  // Test campaign card interactions
  const campaignCards = page.locator('[data-testid="campaign-card"]');
  const cardCount = await campaignCards.count();
  
  if (cardCount > 0) {
    const interactionStart = Date.now();
    await campaignCards.first().click();
    
    // Wait for campaign details to load
    await page.waitForSelector('[data-testid="campaign-details"]', { timeout: 5000 });
    const interactionTime = Date.now() - interactionStart;
    
    interactionToNextPaint.add(interactionTime);
    
    // Go back to dashboard
    await page.goBack();
    await page.waitForSelector('[data-testid="dashboard-content"]');
  }
  
  // Test search functionality
  const searchInput = page.locator('[data-testid="global-search"]');
  if (await searchInput.isVisible()) {
    const searchStart = Date.now();
    await searchInput.fill('test campaign');
    
    // Wait for search results
    await page.waitForSelector('[data-testid="search-results"]', { timeout: 3000 });
    const searchTime = Date.now() - searchStart;
    
    interactionToNextPaint.add(searchTime);
    
    // Clear search
    await searchInput.fill('');
  }
}

async function testCampaignCreationPerformance(page) {
  console.log('Testing campaign creation performance...');
  
  // Navigate to campaign creation
  const navStart = Date.now();
  await page.goto(`${BASE_URL}/campaigns/create`);
  await page.waitForLoadState('networkidle');
  const navTime = Date.now() - navStart;
  
  pageLoadTime.add(navTime);
  
  // Fill campaign form
  const formStart = Date.now();
  await page.fill('[data-testid="campaign-name-input"]', 'Performance Test Campaign');
  await page.fill('[data-testid="campaign-description-input"]', 'Testing campaign creation performance');
  await page.selectOption('[data-testid="campaign-type-select"]', 'social-media');
  await page.fill('[data-testid="campaign-budget-input"]', '5000');
  
  // Test form validation performance
  const validationStart = Date.now();
  await page.click('[data-testid="create-button"]');
  
  // Wait for either success or validation errors
  try {
    await page.waitForSelector('[data-testid="success-message"], [data-testid="validation-error"]', { timeout: 5000 });
    const validationTime = Date.now() - validationStart;
    interactionToNextPaint.add(validationTime);
  } catch (error) {
    console.warn('Form submission timeout');
    jsErrorRate.add(1);
  }
  
  const formTime = Date.now() - formStart;
  
  check(page, {
    'campaign form loaded quickly': () => navTime < 3000,
    'form submission responsive': () => formTime < 2000,
  });
}

async function testAgentInteractionPerformance(page) {
  console.log('Testing agent interaction performance...');
  
  // Navigate to agent page
  await page.goto(`${BASE_URL}/agents/content-creation`);
  await page.waitForLoadState('networkidle');
  
  // Test agent execution
  const agentStart = Date.now();
  await page.fill('[data-testid="agent-prompt-input"]', 'Create a social media post about AI innovation');
  await page.click('[data-testid="execute-agent-button"]');
  
  // Wait for agent response
  try {
    await page.waitForSelector('[data-testid="agent-response"]', { timeout: 15000 });
    const agentTime = Date.now() - agentStart;
    
    interactionToNextPaint.add(agentTime);
    
    check(page, {
      'agent execution completed': () => page.locator('[data-testid="agent-response"]').isVisible(),
      'agent response time acceptable': () => agentTime < 15000,
    });
  } catch (error) {
    console.warn('Agent execution timeout');
    jsErrorRate.add(1);
  }
}

async function testAnalyticsPerformance(page) {
  console.log('Testing analytics performance...');
  
  // Navigate to analytics
  const analyticsStart = Date.now();
  await page.goto(`${BASE_URL}/analytics`);
  await page.waitForLoadState('networkidle');
  
  // Wait for charts to load
  await page.waitForSelector('[data-testid="analytics-chart"]', { timeout: 10000 });
  const analyticsTime = Date.now() - analyticsStart;
  
  pageLoadTime.add(analyticsTime);
  
  // Test date range filter
  const filterStart = Date.now();
  await page.selectOption('[data-testid="date-range-select"]', '30d');
  
  // Wait for chart update
  await page.waitForTimeout(2000); // Wait for chart animation
  const filterTime = Date.now() - filterStart;
  
  interactionToNextPaint.add(filterTime);
  
  // Test export functionality
  const exportStart = Date.now();
  await page.click('[data-testid="export-button"]');
  
  try {
    await page.waitForSelector('[data-testid="export-modal"]', { timeout: 3000 });
    const exportTime = Date.now() - exportStart;
    interactionToNextPaint.add(exportTime);
  } catch (error) {
    console.warn('Export modal timeout');
  }
  
  check(page, {
    'analytics loaded successfully': () => analyticsTime < 8000,
    'date filter responsive': () => filterTime < 3000,
  });
}

async function testMobilePerformance(page) {
  console.log('Testing mobile performance...');
  
  // Set mobile viewport
  await page.setViewportSize({ width: 375, height: 667 });
  
  // Navigate to mobile dashboard
  const mobileStart = Date.now();
  await page.goto(`${BASE_URL}/dashboard`);
  await page.waitForLoadState('networkidle');
  const mobileTime = Date.now() - mobileStart;
  
  pageLoadTime.add(mobileTime);
  
  // Test mobile navigation
  const navStart = Date.now();
  await page.click('[data-testid="mobile-menu-button"]');
  await page.waitForSelector('[data-testid="mobile-menu"]', { timeout: 2000 });
  const navTime = Date.now() - navStart;
  
  interactionToNextPaint.add(navTime);
  
  // Test touch interactions
  const touchStart = Date.now();
  await page.tap('[data-testid="campaign-card"]');
  await page.waitForSelector('[data-testid="campaign-details"]', { timeout: 5000 });
  const touchTime = Date.now() - touchStart;
  
  interactionToNextPaint.add(touchTime);
  
  check(page, {
    'mobile dashboard loaded': () => mobileTime < 6000,
    'mobile navigation responsive': () => navTime < 1000,
    'touch interactions smooth': () => touchTime < 3000,
  });
}

// Performance monitoring function
async function measurePerformanceMetrics(page) {
  const metrics = await page.evaluate(() => {
    const navigation = performance.getEntriesByType('navigation')[0];
    const paint = performance.getEntriesByType('paint');
    
    return {
      domContentLoaded: navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart,
      loadComplete: navigation.loadEventEnd - navigation.loadEventStart,
      firstPaint: paint.find(p => p.name === 'first-paint')?.startTime || 0,
      firstContentfulPaint: paint.find(p => p.name === 'first-contentful-paint')?.startTime || 0,
      memoryUsage: performance.memory ? {
        used: performance.memory.usedJSHeapSize,
        total: performance.memory.totalJSHeapSize,
        limit: performance.memory.jsHeapSizeLimit
      } : null
    };
  });
  
  return metrics;
}

// Error monitoring
export function handleSummary(data) {
  const report = {
    testDuration: data.state.testRunDurationMs / 1000,
    browserSessions: data.metrics.browser_web_vital_fcp ? data.metrics.browser_web_vital_fcp.values.count : 0,
    
    coreWebVitals: {
      fcp: data.metrics.first_contentful_paint ? {
        avg: data.metrics.first_contentful_paint.values.avg,
        p95: data.metrics.first_contentful_paint.values['p(95)']
      } : null,
      lcp: data.metrics.largest_contentful_paint ? {
        avg: data.metrics.largest_contentful_paint.values.avg,
        p95: data.metrics.largest_contentful_paint.values['p(95)']
      } : null,
      cls: data.metrics.cumulative_layout_shift ? {
        avg: data.metrics.cumulative_layout_shift.values.avg,
        p95: data.metrics.cumulative_layout_shift.values['p(95)']
      } : null,
      inp: data.metrics.interaction_to_next_paint ? {
        avg: data.metrics.interaction_to_next_paint.values.avg,
        p95: data.metrics.interaction_to_next_paint.values['p(95)']
      } : null
    },
    
    performance: {
      pageLoadTime: data.metrics.page_load_time ? {
        avg: data.metrics.page_load_time.values.avg,
        p95: data.metrics.page_load_time.values['p(95)']
      } : null,
      jsErrorRate: data.metrics.js_error_rate ? data.metrics.js_error_rate.values.rate : 0
    },
    
    thresholds: data.thresholds
  };
  
  return {
    'browser-performance-results.json': JSON.stringify(report, null, 2),
    stdout: `
=== Browser Performance Test Results ===

Test Duration: ${report.testDuration}s
Browser Sessions: ${report.browserSessions}

Core Web Vitals:
- First Contentful Paint: ${report.coreWebVitals.fcp ? `${report.coreWebVitals.fcp.avg.toFixed(0)}ms (p95: ${report.coreWebVitals.fcp.p95.toFixed(0)}ms)` : 'N/A'}
- Largest Contentful Paint: ${report.coreWebVitals.lcp ? `${report.coreWebVitals.lcp.avg.toFixed(0)}ms (p95: ${report.coreWebVitals.lcp.p95.toFixed(0)}ms)` : 'N/A'}
- Cumulative Layout Shift: ${report.coreWebVitals.cls ? `${report.coreWebVitals.cls.avg.toFixed(3)} (p95: ${report.coreWebVitals.cls.p95.toFixed(3)})` : 'N/A'}
- Interaction to Next Paint: ${report.coreWebVitals.inp ? `${report.coreWebVitals.inp.avg.toFixed(0)}ms (p95: ${report.coreWebVitals.inp.p95.toFixed(0)}ms)` : 'N/A'}

Performance:
- Page Load Time: ${report.performance.pageLoadTime ? `${report.performance.pageLoadTime.avg.toFixed(0)}ms (p95: ${report.performance.pageLoadTime.p95.toFixed(0)}ms)` : 'N/A'}
- JS Error Rate: ${(report.performance.jsErrorRate * 100).toFixed(2)}%

Thresholds:
${Object.entries(report.thresholds).map(([key, value]) => 
  `- ${key}: ${value.ok ? '✓ PASS' : '✗ FAIL'}`
).join('\n')}

=== End Report ===
    `
  };
}
