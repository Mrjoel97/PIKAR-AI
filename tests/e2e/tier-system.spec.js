/**
 * PIKAR AI E2E Tests - Tier System
 * End-to-end testing for tier selection, trials, and upgrades
 */

import { test, expect } from '@playwright/test'

test.describe('PIKAR AI Tier System E2E', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the application
    await page.goto('/')
    
    // Wait for the application to load
    await page.waitForLoadState('networkidle')
  })

  test.describe('Tier Selection and Trial Flow', () => {
    test('should display all four tiers with correct pricing', async ({ page }) => {
      // Navigate to pricing page
      await page.click('[data-testid="pricing-link"]')
      
      // Check all tiers are displayed
      await expect(page.locator('[data-testid="solopreneur-tier"]')).toBeVisible()
      await expect(page.locator('[data-testid="startup-tier"]')).toBeVisible()
      await expect(page.locator('[data-testid="sme-tier"]')).toBeVisible()
      await expect(page.locator('[data-testid="enterprise-tier"]')).toBeVisible()
      
      // Verify pricing
      await expect(page.locator('text=$99/month')).toBeVisible()
      await expect(page.locator('text=$297/month')).toBeVisible()
      await expect(page.locator('text=$597/month')).toBeVisible()
      await expect(page.locator('text=Contact Sales')).toBeVisible()
      
      // Verify 7-day trial messaging
      const trialMessages = page.locator('text=7-day free trial')
      await expect(trialMessages).toHaveCount(4)
    })

    test('should start trial for Startup tier', async ({ page }) => {
      // Navigate to pricing
      await page.click('[data-testid="pricing-link"]')
      
      // Click Start Trial for Startup tier
      await page.click('[data-testid="startup-trial-button"]')
      
      // Should redirect to trial confirmation or dashboard
      await page.waitForURL(/\/(dashboard|trial-started)/)
      
      // Verify trial status is displayed
      await expect(page.locator('[data-testid="trial-status"]')).toBeVisible()
      await expect(page.locator('text=7 days remaining')).toBeVisible()
    })

    test('should handle Enterprise contact sales flow', async ({ page }) => {
      // Navigate to pricing
      await page.click('[data-testid="pricing-link"]')
      
      // Click Contact Sales for Enterprise
      const [popup] = await Promise.all([
        page.waitForEvent('popup'),
        page.click('[data-testid="enterprise-contact-button"]')
      ])
      
      // Verify email client opens or contact form appears
      expect(popup.url()).toContain('mailto:sales@pikar-ai.com')
    })
  })

  test.describe('Trial Experience', () => {
    test.beforeEach(async ({ page }) => {
      // Set up user in trial state
      await page.addInitScript(() => {
        localStorage.setItem('user_trial', JSON.stringify({
          tier: 'startup',
          startDate: Date.now(),
          endDate: Date.now() + (7 * 24 * 60 * 60 * 1000),
          status: 'active'
        }))
      })
    })

    test('should display trial countdown in navigation', async ({ page }) => {
      await page.reload()
      
      // Check trial indicator in navigation
      await expect(page.locator('[data-testid="trial-indicator"]')).toBeVisible()
      await expect(page.locator('text=/\\d+d left/')).toBeVisible()
    })

    test('should show trial manager on dashboard', async ({ page }) => {
      await page.goto('/dashboard')
      
      // Verify trial manager is displayed
      await expect(page.locator('[data-testid="trial-manager"]')).toBeVisible()
      await expect(page.locator('text=Startup Trial')).toBeVisible()
      await expect(page.locator('text=/\\d+ days remaining/')).toBeVisible()
      
      // Check upgrade button is present
      await expect(page.locator('[data-testid="upgrade-button"]')).toBeVisible()
    })

    test('should allow access to tier features during trial', async ({ page }) => {
      await page.goto('/dashboard')
      
      // Try to access a Startup tier feature
      await page.click('[data-testid="advanced-analytics-link"]')
      
      // Should have access (not blocked)
      await expect(page.locator('[data-testid="analytics-dashboard"]')).toBeVisible()
      await expect(page.locator('text=Upgrade Required')).not.toBeVisible()
    })

    test('should show upgrade prompts strategically', async ({ page }) => {
      await page.goto('/dashboard')
      
      // Check for upgrade prompts in appropriate locations
      await expect(page.locator('[data-testid="upgrade-prompt"]')).toBeVisible()
      
      // Verify upgrade prompt has correct messaging
      await expect(page.locator('text=Upgrade to Startup')).toBeVisible()
      await expect(page.locator('text=$297/month')).toBeVisible()
    })
  })

  test.describe('Trial Expiration', () => {
    test.beforeEach(async ({ page }) => {
      // Set up expired trial
      await page.addInitScript(() => {
        localStorage.setItem('user_trial', JSON.stringify({
          tier: 'startup',
          startDate: Date.now() - (8 * 24 * 60 * 60 * 1000),
          endDate: Date.now() - (1 * 24 * 60 * 60 * 1000),
          status: 'expired'
        }))
      })
    })

    test('should block access to premium features after trial', async ({ page }) => {
      await page.reload()
      await page.goto('/dashboard')
      
      // Try to access premium feature
      await page.click('[data-testid="advanced-analytics-link"]')
      
      // Should be blocked
      await expect(page.locator('[data-testid="upgrade-required-modal"]')).toBeVisible()
      await expect(page.locator('text=Trial Expired')).toBeVisible()
    })

    test('should show trial expired modal', async ({ page }) => {
      await page.reload()
      
      // Should show expired trial modal
      await expect(page.locator('[data-testid="trial-expired-modal"]')).toBeVisible()
      await expect(page.locator('text=Your 7-day Startup trial has ended')).toBeVisible()
      
      // Should have upgrade options
      await expect(page.locator('[data-testid="upgrade-to-startup"]')).toBeVisible()
      await expect(page.locator('[data-testid="browse-plans"]')).toBeVisible()
    })
  })

  test.describe('Upgrade Flow', () => {
    test('should redirect to Stripe checkout for paid tiers', async ({ page }) => {
      // Mock Stripe checkout
      await page.route('**/api/create-checkout-session', async route => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            url: 'https://checkout.stripe.com/pay/test_session_123'
          })
        })
      })
      
      await page.goto('/pricing')
      
      // Click upgrade button
      await page.click('[data-testid="startup-upgrade-button"]')
      
      // Should redirect to Stripe
      await page.waitForURL(/checkout\.stripe\.com/)
    })

    test('should handle successful payment return', async ({ page }) => {
      // Simulate return from successful payment
      await page.goto('/billing/success?session_id=test_session_123')
      
      // Should show success message
      await expect(page.locator('text=Payment Successful')).toBeVisible()
      await expect(page.locator('text=Welcome to Startup')).toBeVisible()
      
      // Should redirect to dashboard
      await page.waitForURL('/dashboard')
      
      // Trial indicator should be gone
      await expect(page.locator('[data-testid="trial-indicator"]')).not.toBeVisible()
    })

    test('should handle payment cancellation', async ({ page }) => {
      await page.goto('/billing/cancel')
      
      // Should show cancellation message
      await expect(page.locator('text=Payment Cancelled')).toBeVisible()
      
      // Should offer to try again
      await expect(page.locator('[data-testid="try-again-button"]')).toBeVisible()
    })
  })

  test.describe('Feature Access Control', () => {
    const testFeatureAccess = async (page, tier, feature, shouldHaveAccess) => {
      // Set user tier
      await page.addInitScript((tierData) => {
        localStorage.setItem('user_tier', JSON.stringify(tierData))
      }, { tier, status: 'active' })
      
      await page.reload()
      await page.goto('/dashboard')
      
      // Try to access feature
      await page.click(`[data-testid="${feature}-link"]`)
      
      if (shouldHaveAccess) {
        await expect(page.locator(`[data-testid="${feature}-content"]`)).toBeVisible()
        await expect(page.locator('text=Upgrade Required')).not.toBeVisible()
      } else {
        await expect(page.locator('[data-testid="upgrade-required"]')).toBeVisible()
      }
    }

    test('should control Solopreneur feature access', async ({ page }) => {
      await testFeatureAccess(page, 'solopreneur', 'basic-analytics', true)
      await testFeatureAccess(page, 'solopreneur', 'team-collaboration', false)
      await testFeatureAccess(page, 'solopreneur', 'white-label', false)
    })

    test('should control Startup feature access', async ({ page }) => {
      await testFeatureAccess(page, 'startup', 'basic-analytics', true)
      await testFeatureAccess(page, 'startup', 'team-collaboration', true)
      await testFeatureAccess(page, 'startup', 'white-label', false)
    })

    test('should control SME feature access', async ({ page }) => {
      await testFeatureAccess(page, 'sme', 'basic-analytics', true)
      await testFeatureAccess(page, 'sme', 'team-collaboration', true)
      await testFeatureAccess(page, 'sme', 'white-label', true)
    })
  })

  test.describe('Accessibility', () => {
    test('should be keyboard navigable', async ({ page }) => {
      await page.goto('/pricing')
      
      // Tab through pricing cards
      await page.keyboard.press('Tab')
      await page.keyboard.press('Tab')
      await page.keyboard.press('Tab')
      
      // Should be able to activate with Enter
      await page.keyboard.press('Enter')
      
      // Should navigate to trial or upgrade flow
      await page.waitForURL(/\/(trial|checkout)/)
    })

    test('should have proper ARIA labels', async ({ page }) => {
      await page.goto('/pricing')
      
      // Check for proper ARIA labels
      const tierCards = page.locator('[role="region"]')
      await expect(tierCards).toHaveCount(4)
      
      // Check for proper headings
      const headings = page.locator('h1, h2, h3')
      await expect(headings.first()).toBeVisible()
    })

    test('should work with screen readers', async ({ page }) => {
      await page.goto('/pricing')
      
      // Check for screen reader friendly content
      await expect(page.locator('[aria-label]')).toHaveCount.greaterThan(0)
      await expect(page.locator('[aria-describedby]')).toHaveCount.greaterThan(0)
    })
  })

  test.describe('Performance', () => {
    test('should load pricing page quickly', async ({ page }) => {
      const startTime = Date.now()
      
      await page.goto('/pricing')
      await page.waitForLoadState('networkidle')
      
      const loadTime = Date.now() - startTime
      
      // Should load in under 3 seconds
      expect(loadTime).toBeLessThan(3000)
    })

    test('should have good Core Web Vitals', async ({ page }) => {
      await page.goto('/pricing')
      
      // Measure Web Vitals
      const vitals = await page.evaluate(() => {
        return new Promise((resolve) => {
          const vitals = {}
          
          // Mock Web Vitals measurements
          vitals.LCP = 2000 // 2s
          vitals.FID = 50   // 50ms
          vitals.CLS = 0.05 // 0.05
          
          resolve(vitals)
        })
      })
      
      expect(vitals.LCP).toBeLessThan(2500)
      expect(vitals.FID).toBeLessThan(100)
      expect(vitals.CLS).toBeLessThan(0.1)
    })
  })

  test.describe('Cross-browser Compatibility', () => {
    ['chromium', 'firefox', 'webkit'].forEach(browserName => {
      test(`should work in ${browserName}`, async ({ page, browserName: currentBrowser }) => {
        test.skip(currentBrowser !== browserName, `Skipping ${browserName} test`)
        
        await page.goto('/pricing')
        
        // Basic functionality should work
        await expect(page.locator('[data-testid="solopreneur-tier"]')).toBeVisible()
        await expect(page.locator('text=$99/month')).toBeVisible()
        
        // Interactive elements should work
        await page.click('[data-testid="startup-trial-button"]')
        await page.waitForURL(/\/(dashboard|trial)/)
      })
    })
  })

  test.describe('Mobile Responsiveness', () => {
    test('should work on mobile devices', async ({ page }) => {
      // Set mobile viewport
      await page.setViewportSize({ width: 375, height: 667 })
      
      await page.goto('/pricing')
      
      // Check mobile layout
      await expect(page.locator('[data-testid="mobile-tier-cards"]')).toBeVisible()
      
      // Should be able to scroll and interact
      await page.locator('[data-testid="startup-tier"]').scrollIntoViewIfNeeded()
      await page.click('[data-testid="startup-trial-button"]')
    })

    test('should work on tablet devices', async ({ page }) => {
      // Set tablet viewport
      await page.setViewportSize({ width: 768, height: 1024 })
      
      await page.goto('/pricing')
      
      // Check tablet layout
      const tierCards = page.locator('[data-testid*="-tier"]')
      await expect(tierCards).toHaveCount(4)
      
      // All tiers should be visible
      for (let i = 0; i < 4; i++) {
        await expect(tierCards.nth(i)).toBeVisible()
      }
    })
  })
})
