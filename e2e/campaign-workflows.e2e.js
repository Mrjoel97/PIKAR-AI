/**
 * Campaign Workflows E2E Tests
 * Complete end-to-end testing of campaign creation and management workflows
 */

import { test, expect } from '@playwright/test';
import { AuthPage } from './page-objects/AuthPage';
import { DashboardPage } from './page-objects/DashboardPage';
import { CampaignPage } from './page-objects/CampaignPage';
import testData from './test-data.json';

test.describe('Campaign Workflows E2E', () => {
  let authPage;
  let dashboardPage;
  let campaignPage;

  test.beforeEach(async ({ page }) => {
    authPage = new AuthPage(page);
    dashboardPage = new DashboardPage(page);
    campaignPage = new CampaignPage(page);
    
    // Login before each test
    await authPage.goto();
    const user = testData.users.testUser;
    await authPage.submitLoginForm(user.email, user.password);
    await expect(page).toHaveURL(/.*\/dashboard/);
  });

  test.describe('Campaign Creation', () => {
    test('creates a complete social media campaign', async ({ page }) => {
      await test.step('Navigate to campaign creation', async () => {
        await dashboardPage.clickCreateCampaign();
        await expect(page).toHaveURL(/.*\/campaigns\/create/);
        await expect(campaignPage.getCampaignForm()).toBeVisible();
      });

      await test.step('Fill campaign basic information', async () => {
        const campaign = testData.campaigns.socialCampaign;
        await campaignPage.fillCampaignName(campaign.name);
        await campaignPage.fillCampaignDescription(campaign.description);
        await campaignPage.selectCampaignType(campaign.type);
        await campaignPage.fillBudget(campaign.budget);
      });

      await test.step('Configure campaign settings', async () => {
        // Set campaign dates
        const startDate = new Date();
        const endDate = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000); // 30 days from now
        
        await campaignPage.setStartDate(startDate);
        await campaignPage.setEndDate(endDate);
        
        // Select target platforms
        await campaignPage.selectPlatforms(['facebook', 'twitter', 'linkedin']);
        
        // Configure audience targeting
        await campaignPage.setAudienceTargeting({
          ageRange: '25-45',
          interests: ['technology', 'business', 'marketing'],
          location: 'United States'
        });
      });

      await test.step('Review and create campaign', async () => {
        await campaignPage.clickReviewButton();
        await expect(campaignPage.getCampaignReview()).toBeVisible();
        
        // Verify campaign details in review
        await expect(page.locator('[data-testid="review-campaign-name"]')).toContainText(testData.campaigns.socialCampaign.name);
        await expect(page.locator('[data-testid="review-campaign-budget"]')).toContainText('$3,000');
        
        await campaignPage.clickCreateButton();
      });

      await test.step('Verify campaign creation success', async () => {
        // Should redirect to campaign details or dashboard
        await expect(page).toHaveURL(/.*\/(campaigns|dashboard)/);
        
        // Should show success message
        await expect(page.locator('[data-testid="success-message"]')).toBeVisible();
        await expect(page.locator('[data-testid="success-message"]')).toContainText(/campaign.*created.*successfully/i);
        
        // Campaign should appear in campaigns list
        if (page.url().includes('dashboard')) {
          await expect(dashboardPage.getCampaignByName(testData.campaigns.socialCampaign.name)).toBeVisible();
        }
      });
    });

    test('validates campaign form fields', async ({ page }) => {
      await dashboardPage.clickCreateCampaign();
      await expect(page).toHaveURL(/.*\/campaigns\/create/);

      await test.step('Test empty form validation', async () => {
        await campaignPage.clickCreateButton();
        
        // Should show validation errors
        await expect(campaignPage.getNameError()).toBeVisible();
        await expect(campaignPage.getBudgetError()).toBeVisible();
        await expect(campaignPage.getTypeError()).toBeVisible();
      });

      await test.step('Test invalid budget validation', async () => {
        await campaignPage.fillCampaignName('Test Campaign');
        await campaignPage.fillBudget(-100); // Negative budget
        await campaignPage.clickCreateButton();
        
        await expect(campaignPage.getBudgetError()).toContainText(/budget.*must.*be.*positive/i);
      });

      await test.step('Test date validation', async () => {
        const pastDate = new Date(Date.now() - 24 * 60 * 60 * 1000); // Yesterday
        const startDate = new Date();
        
        await campaignPage.setStartDate(startDate);
        await campaignPage.setEndDate(pastDate); // End date before start date
        await campaignPage.clickCreateButton();
        
        await expect(campaignPage.getDateError()).toContainText(/end.*date.*must.*be.*after.*start.*date/i);
      });
    });

    test('handles campaign creation errors', async ({ page }) => {
      await dashboardPage.clickCreateCampaign();
      
      // Fill form with data that might cause server error
      await campaignPage.fillCampaignName('Test Campaign');
      await campaignPage.fillBudget(1000000); // Very high budget that might exceed limits
      await campaignPage.selectCampaignType('social-media');
      
      await campaignPage.clickCreateButton();
      
      // Should handle error gracefully
      await expect(page.locator('[data-testid="error-message"]')).toBeVisible();
      await expect(page.locator('[data-testid="error-message"]')).toContainText(/error.*creating.*campaign/i);
      
      // Should remain on creation page
      await expect(page).toHaveURL(/.*\/campaigns\/create/);
    });
  });

  test.describe('Campaign Management', () => {
    test.beforeEach(async ({ page }) => {
      // Create a test campaign first
      await dashboardPage.clickCreateCampaign();
      const campaign = testData.campaigns.testCampaign;
      await campaignPage.fillCampaignName(campaign.name);
      await campaignPage.fillCampaignDescription(campaign.description);
      await campaignPage.selectCampaignType(campaign.type);
      await campaignPage.fillBudget(campaign.budget);
      await campaignPage.clickCreateButton();
      
      // Wait for creation success
      await expect(page.locator('[data-testid="success-message"]')).toBeVisible();
    });

    test('views campaign details', async ({ page }) => {
      await test.step('Navigate to campaigns list', async () => {
        await dashboardPage.clickNavCampaigns();
        await expect(page).toHaveURL(/.*\/campaigns/);
        await dashboardPage.waitForCampaignsLoad();
      });

      await test.step('Click on campaign to view details', async () => {
        await dashboardPage.clickCampaign(testData.campaigns.testCampaign.name);
        await expect(page).toHaveURL(/.*\/campaigns\/[^\/]+/);
        
        // Should show campaign details
        await expect(campaignPage.getCampaignDetails()).toBeVisible();
        await expect(campaignPage.getCampaignTitle()).toContainText(testData.campaigns.testCampaign.name);
      });

      await test.step('Verify campaign information', async () => {
        // Check campaign status
        await expect(campaignPage.getCampaignStatus()).toBeVisible();
        
        // Check campaign metrics
        await expect(campaignPage.getCampaignMetrics()).toBeVisible();
        
        // Check campaign timeline
        await expect(campaignPage.getCampaignTimeline()).toBeVisible();
      });
    });

    test('edits campaign information', async ({ page }) => {
      await dashboardPage.clickNavCampaigns();
      await dashboardPage.clickCampaign(testData.campaigns.testCampaign.name);
      
      await test.step('Enter edit mode', async () => {
        await campaignPage.clickEditButton();
        await expect(campaignPage.getCampaignEditForm()).toBeVisible();
      });

      await test.step('Update campaign details', async () => {
        const updatedName = 'Updated E2E Test Campaign';
        const updatedBudget = 7500;
        
        await campaignPage.fillCampaignName(updatedName);
        await campaignPage.fillBudget(updatedBudget);
        await campaignPage.clickSaveButton();
      });

      await test.step('Verify updates', async () => {
        await expect(page.locator('[data-testid="success-message"]')).toBeVisible();
        await expect(campaignPage.getCampaignTitle()).toContainText('Updated E2E Test Campaign');
        await expect(campaignPage.getCampaignBudget()).toContainText('$7,500');
      });
    });

    test('manages campaign status', async ({ page }) => {
      await dashboardPage.clickNavCampaigns();
      await dashboardPage.clickCampaign(testData.campaigns.testCampaign.name);

      await test.step('Activate campaign', async () => {
        await campaignPage.clickStatusButton();
        await campaignPage.selectStatus('active');
        await campaignPage.confirmStatusChange();
        
        await expect(campaignPage.getCampaignStatus()).toContainText('Active');
        await expect(page.locator('[data-testid="success-message"]')).toContainText(/campaign.*activated/i);
      });

      await test.step('Pause campaign', async () => {
        await campaignPage.clickStatusButton();
        await campaignPage.selectStatus('paused');
        await campaignPage.confirmStatusChange();
        
        await expect(campaignPage.getCampaignStatus()).toContainText('Paused');
      });

      await test.step('Complete campaign', async () => {
        await campaignPage.clickStatusButton();
        await campaignPage.selectStatus('completed');
        await campaignPage.confirmStatusChange();
        
        await expect(campaignPage.getCampaignStatus()).toContainText('Completed');
      });
    });

    test('deletes campaign', async ({ page }) => {
      await dashboardPage.clickNavCampaigns();
      await dashboardPage.clickCampaign(testData.campaigns.testCampaign.name);

      await test.step('Delete campaign', async () => {
        await campaignPage.clickDeleteButton();
        
        // Should show confirmation dialog
        await expect(page.locator('[data-testid="delete-confirmation"]')).toBeVisible();
        await expect(page.locator('[data-testid="delete-confirmation"]')).toContainText(/are.*you.*sure/i);
        
        await page.locator('[data-testid="confirm-delete"]').click();
      });

      await test.step('Verify deletion', async () => {
        // Should redirect to campaigns list
        await expect(page).toHaveURL(/.*\/campaigns$/);
        
        // Should show success message
        await expect(page.locator('[data-testid="success-message"]')).toContainText(/campaign.*deleted/i);
        
        // Campaign should not appear in list
        await expect(dashboardPage.getCampaignByName(testData.campaigns.testCampaign.name)).not.toBeVisible();
      });
    });
  });

  test.describe('Campaign Analytics', () => {
    test('views campaign performance metrics', async ({ page }) => {
      // Navigate to campaigns and select one
      await dashboardPage.clickNavCampaigns();
      await dashboardPage.clickCampaign(testData.campaigns.testCampaign.name);

      await test.step('View analytics tab', async () => {
        await campaignPage.clickAnalyticsTab();
        await expect(campaignPage.getAnalyticsSection()).toBeVisible();
      });

      await test.step('Check performance metrics', async () => {
        // Should show key metrics
        await expect(campaignPage.getImpressionsMetric()).toBeVisible();
        await expect(campaignPage.getClicksMetric()).toBeVisible();
        await expect(campaignPage.getConversionsMetric()).toBeVisible();
        await expect(campaignPage.getCTRMetric()).toBeVisible();
        
        // Should show charts
        await expect(campaignPage.getPerformanceChart()).toBeVisible();
      });

      await test.step('Filter analytics by date range', async () => {
        await campaignPage.selectDateRange('last-7-days');
        
        // Should update metrics
        await expect(campaignPage.getAnalyticsSection()).toBeVisible();
        
        // Should show loading state during update
        await expect(campaignPage.getAnalyticsLoading()).toBeVisible();
        await expect(campaignPage.getAnalyticsLoading()).not.toBeVisible({ timeout: 10000 });
      });
    });

    test('exports campaign data', async ({ page }) => {
      await dashboardPage.clickNavCampaigns();
      await dashboardPage.clickCampaign(testData.campaigns.testCampaign.name);
      await campaignPage.clickAnalyticsTab();

      await test.step('Export analytics data', async () => {
        // Set up download handler
        const downloadPromise = page.waitForEvent('download');
        
        await campaignPage.clickExportButton();
        await campaignPage.selectExportFormat('csv');
        await campaignPage.confirmExport();
        
        const download = await downloadPromise;
        
        // Verify download
        expect(download.suggestedFilename()).toMatch(/campaign.*analytics.*\.csv$/);
      });
    });
  });

  test.describe('Campaign Collaboration', () => {
    test('shares campaign with team members', async ({ page }) => {
      await dashboardPage.clickNavCampaigns();
      await dashboardPage.clickCampaign(testData.campaigns.testCampaign.name);

      await test.step('Open sharing dialog', async () => {
        await campaignPage.clickShareButton();
        await expect(page.locator('[data-testid="share-dialog"]')).toBeVisible();
      });

      await test.step('Add team member', async () => {
        await page.locator('[data-testid="share-email-input"]').fill('teammate@pikar.ai');
        await page.locator('[data-testid="share-role-select"]').selectOption('editor');
        await page.locator('[data-testid="send-invite-button"]').click();
        
        await expect(page.locator('[data-testid="success-message"]')).toContainText(/invitation.*sent/i);
      });

      await test.step('Verify team member added', async () => {
        await expect(page.locator('[data-testid="team-member-list"]')).toContainText('teammate@pikar.ai');
        await expect(page.locator('[data-testid="team-member-role"]')).toContainText('Editor');
      });
    });
  });

  test.describe('Performance & Accessibility', () => {
    test('campaign creation performs well', async ({ page }) => {
      const startTime = Date.now();
      
      await dashboardPage.clickCreateCampaign();
      
      const campaign = testData.campaigns.testCampaign;
      await campaignPage.fillCampaignName(campaign.name);
      await campaignPage.fillCampaignDescription(campaign.description);
      await campaignPage.selectCampaignType(campaign.type);
      await campaignPage.fillBudget(campaign.budget);
      await campaignPage.clickCreateButton();
      
      await expect(page.locator('[data-testid="success-message"]')).toBeVisible();
      
      const endTime = Date.now();
      const duration = endTime - startTime;
      
      // Campaign creation should complete within 10 seconds
      expect(duration).toBeLessThan(10000);
    });

    test('campaign form is keyboard accessible', async ({ page }) => {
      await dashboardPage.clickCreateCampaign();
      
      // Test tab navigation through form
      await page.keyboard.press('Tab'); // Campaign name
      await expect(page.locator('[data-testid="campaign-name-input"]')).toBeFocused();
      
      await page.keyboard.press('Tab'); // Description
      await expect(page.locator('[data-testid="campaign-description-input"]')).toBeFocused();
      
      await page.keyboard.press('Tab'); // Type select
      await expect(page.locator('[data-testid="campaign-type-select"]')).toBeFocused();
      
      await page.keyboard.press('Tab'); // Budget
      await expect(page.locator('[data-testid="campaign-budget-input"]')).toBeFocused();
      
      // Test form submission with Enter key
      await page.locator('[data-testid="campaign-name-input"]').fill('Keyboard Test Campaign');
      await page.locator('[data-testid="campaign-budget-input"]').fill('1000');
      await page.keyboard.press('Enter');
      
      // Should show validation errors for missing fields
      await expect(campaignPage.getTypeError()).toBeVisible();
    });

    test('campaign list handles large datasets', async ({ page }) => {
      await dashboardPage.clickNavCampaigns();
      
      // Should load campaigns efficiently
      const startTime = Date.now();
      await dashboardPage.waitForCampaignsLoad();
      const loadTime = Date.now() - startTime;
      
      // Should load within 5 seconds
      expect(loadTime).toBeLessThan(5000);
      
      // Should show campaigns or empty state
      const campaignsList = dashboardPage.getCampaignsList();
      const emptyState = page.locator('[data-testid="campaigns-empty-state"]');
      await expect(campaignsList.or(emptyState)).toBeVisible();
    });
  });
});
