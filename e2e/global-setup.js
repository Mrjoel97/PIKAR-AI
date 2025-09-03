/**
 * Playwright Global Setup
 * Sets up test environment, authentication, and test data
 */

import { chromium } from '@playwright/test';
import path from 'path';
import fs from 'fs';

async function globalSetup() {
  console.log('🚀 Starting E2E Test Global Setup...');

  // Create test results directory
  const resultsDir = path.join(process.cwd(), 'e2e-results');
  if (!fs.existsSync(resultsDir)) {
    fs.mkdirSync(resultsDir, { recursive: true });
  }

  // Create test artifacts directory
  const artifactsDir = path.join(resultsDir, 'test-artifacts');
  if (!fs.existsSync(artifactsDir)) {
    fs.mkdirSync(artifactsDir, { recursive: true });
  }

  // Set up test environment variables
  process.env.NODE_ENV = 'test';
  process.env.PLAYWRIGHT_TEST_MODE = 'true';
  
  // Create test user authentication state
  await setupTestAuthentication();
  
  // Set up test data
  await setupTestData();
  
  console.log('✅ E2E Test Global Setup Complete');
}

/**
 * Set up test user authentication
 */
async function setupTestAuthentication() {
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    // Navigate to login page
    await page.goto(process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173');
    
    // Check if login form exists
    const loginForm = await page.locator('[data-testid="login-form"]').first();
    if (await loginForm.isVisible()) {
      // Fill login form with test credentials
      await page.fill('[data-testid="email-input"]', 'test@pikar.ai');
      await page.fill('[data-testid="password-input"]', 'TestPassword123!');
      await page.click('[data-testid="login-button"]');
      
      // Wait for successful login
      await page.waitForURL('**/dashboard', { timeout: 10000 });
      
      // Save authentication state
      await context.storageState({ path: 'e2e/auth-state.json' });
      console.log('✅ Test authentication state saved');
    } else {
      console.log('ℹ️ No login required or already authenticated');
    }
  } catch (error) {
    console.warn('⚠️ Authentication setup failed:', error.message);
    // Create empty auth state for tests that don't require authentication
    await context.storageState({ path: 'e2e/auth-state.json' });
  } finally {
    await browser.close();
  }
}

/**
 * Set up test data
 */
async function setupTestData() {
  const testData = {
    users: {
      testUser: {
        email: 'test@pikar.ai',
        password: 'TestPassword123!',
        name: 'Test User',
        company: 'PIKAR AI Test',
        tier: 'startup'
      },
      adminUser: {
        email: 'admin@pikar.ai',
        password: 'AdminPassword123!',
        name: 'Admin User',
        company: 'PIKAR AI',
        tier: 'enterprise'
      }
    },
    campaigns: {
      testCampaign: {
        name: 'E2E Test Campaign',
        description: 'Campaign created during E2E testing',
        type: 'social-media',
        budget: 5000,
        status: 'draft'
      },
      socialCampaign: {
        name: 'Social Media Test Campaign',
        description: 'Social media campaign for E2E testing',
        type: 'social-media',
        budget: 3000,
        platforms: ['facebook', 'twitter', 'linkedin']
      }
    },
    agents: {
      contentAgent: {
        type: 'content-creation',
        name: 'Content Creation Agent',
        description: 'AI agent for content generation'
      },
      strategicAgent: {
        type: 'strategic-planning',
        name: 'Strategic Planning Agent',
        description: 'AI agent for strategic analysis'
      }
    },
    content: {
      blogPost: {
        title: 'E2E Test Blog Post',
        content: 'This is a test blog post created during E2E testing.',
        tags: ['test', 'e2e', 'automation'],
        status: 'draft'
      },
      socialPost: {
        content: 'Test social media post for E2E testing #test #automation',
        platform: 'twitter',
        scheduledTime: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString()
      }
    }
  };

  // Save test data to file
  const testDataPath = path.join(process.cwd(), 'e2e', 'test-data.json');
  fs.writeFileSync(testDataPath, JSON.stringify(testData, null, 2));
  console.log('✅ Test data prepared');
}

export default globalSetup;
