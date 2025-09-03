// @ts-check
import { test, expect } from '@playwright/test'

// Assumes dev server started by playwright.config.js webServer

test('pricing page shows plans', async ({ page }) => {
  await page.goto('/pricing')
  await expect(page.getByText('Choose your plan')).toBeVisible()
  await expect(page.getByText('Solopreneur')).toBeVisible()
  await expect(page.getByText('Startup')).toBeVisible()
  await expect(page.getByText('SME')).toBeVisible()
})

