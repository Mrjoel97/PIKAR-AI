/**
 * Authentication Flow E2E Tests
 * Complete end-to-end testing of authentication workflows
 */

import { test, expect } from '@playwright/test';
import { AuthPage } from './page-objects/AuthPage';
import { DashboardPage } from './page-objects/DashboardPage';
import testData from './test-data.json';

test.describe('Authentication Flow E2E', () => {
  let authPage;
  let dashboardPage;

  test.beforeEach(async ({ page }) => {
    authPage = new AuthPage(page);
    dashboardPage = new DashboardPage(page);
    
    // Start from clean state
    await page.context().clearCookies();
    await page.context().clearPermissions();
  });

  test.describe('User Registration', () => {
    test('completes full registration workflow', async ({ page }) => {
      await test.step('Navigate to registration page', async () => {
        await authPage.goto();
        await authPage.clickSignUpLink();
        await expect(page).toHaveURL(/.*\/register/);
      });

      await test.step('Fill registration form', async () => {
        const newUser = {
          email: `test-${Date.now()}@pikar.ai`,
          password: 'TestPassword123!',
          name: 'E2E Test User',
          company: 'PIKAR AI Test'
        };

        await authPage.fillRegistrationForm(newUser);
        await authPage.clickRegisterButton();
      });

      await test.step('Verify successful registration', async () => {
        // Should redirect to dashboard after successful registration
        await expect(page).toHaveURL(/.*\/dashboard/, { timeout: 10000 });
        
        // Should show welcome message or user info
        await expect(page.locator('[data-testid="user-welcome"]')).toBeVisible();
        
        // Should show dashboard content
        await expect(dashboardPage.getDashboardTitle()).toBeVisible();
      });
    });

    test('validates registration form fields', async ({ page }) => {
      await authPage.goto();
      await authPage.clickSignUpLink();

      await test.step('Test empty form validation', async () => {
        await authPage.clickRegisterButton();
        
        // Should show validation errors
        await expect(page.locator('[data-testid="email-error"]')).toBeVisible();
        await expect(page.locator('[data-testid="password-error"]')).toBeVisible();
        await expect(page.locator('[data-testid="name-error"]')).toBeVisible();
      });

      await test.step('Test invalid email format', async () => {
        await authPage.fillEmail('invalid-email');
        await authPage.clickRegisterButton();
        
        await expect(page.locator('[data-testid="email-error"]')).toContainText('Invalid email format');
      });

      await test.step('Test weak password', async () => {
        await authPage.fillEmail('test@example.com');
        await authPage.fillPassword('123');
        await authPage.clickRegisterButton();
        
        await expect(page.locator('[data-testid="password-error"]')).toContainText('Password must be at least');
      });
    });

    test('handles registration errors gracefully', async ({ page }) => {
      await authPage.goto();
      await authPage.clickSignUpLink();

      // Try to register with existing email
      const existingUser = testData.users.testUser;
      await authPage.fillRegistrationForm(existingUser);
      await authPage.clickRegisterButton();

      // Should show error message
      await expect(page.locator('[data-testid="registration-error"]')).toBeVisible();
      await expect(page.locator('[data-testid="registration-error"]')).toContainText(/email.*already.*exists/i);
      
      // Should remain on registration page
      await expect(page).toHaveURL(/.*\/register/);
    });
  });

  test.describe('User Login', () => {
    test('completes full login workflow', async ({ page }) => {
      await test.step('Navigate to login page', async () => {
        await authPage.goto();
        await expect(authPage.getLoginForm()).toBeVisible();
      });

      await test.step('Fill login credentials', async () => {
        const user = testData.users.testUser;
        await authPage.fillEmail(user.email);
        await authPage.fillPassword(user.password);
        await authPage.clickLoginButton();
      });

      await test.step('Verify successful login', async () => {
        // Should redirect to dashboard
        await expect(page).toHaveURL(/.*\/dashboard/, { timeout: 10000 });
        
        // Should show user information
        await expect(page.locator('[data-testid="user-menu"]')).toBeVisible();
        
        // Should show dashboard content
        await expect(dashboardPage.getDashboardTitle()).toBeVisible();
        
        // Should show user's campaigns or welcome message
        const campaignsSection = page.locator('[data-testid="campaigns-section"]');
        const welcomeMessage = page.locator('[data-testid="welcome-message"]');
        await expect(campaignsSection.or(welcomeMessage)).toBeVisible();
      });
    });

    test('handles invalid login credentials', async ({ page }) => {
      await authPage.goto();

      await test.step('Test invalid email', async () => {
        await authPage.fillEmail('nonexistent@example.com');
        await authPage.fillPassword('password123');
        await authPage.clickLoginButton();
        
        await expect(page.locator('[data-testid="login-error"]')).toBeVisible();
        await expect(page.locator('[data-testid="login-error"]')).toContainText(/invalid.*credentials/i);
      });

      await test.step('Test invalid password', async () => {
        const user = testData.users.testUser;
        await authPage.fillEmail(user.email);
        await authPage.fillPassword('wrongpassword');
        await authPage.clickLoginButton();
        
        await expect(page.locator('[data-testid="login-error"]')).toBeVisible();
        await expect(page.locator('[data-testid="login-error"]')).toContainText(/invalid.*credentials/i);
      });
    });

    test('validates login form fields', async ({ page }) => {
      await authPage.goto();

      await test.step('Test empty form submission', async () => {
        await authPage.clickLoginButton();
        
        await expect(page.locator('[data-testid="email-error"]')).toBeVisible();
        await expect(page.locator('[data-testid="password-error"]')).toBeVisible();
      });

      await test.step('Test invalid email format', async () => {
        await authPage.fillEmail('invalid-email');
        await authPage.clickLoginButton();
        
        await expect(page.locator('[data-testid="email-error"]')).toContainText('Invalid email format');
      });
    });

    test('shows loading state during login', async ({ page }) => {
      await authPage.goto();
      
      const user = testData.users.testUser;
      await authPage.fillEmail(user.email);
      await authPage.fillPassword(user.password);
      
      // Click login and immediately check for loading state
      await authPage.clickLoginButton();
      
      // Should show loading indicator
      await expect(page.locator('[data-testid="login-loading"]')).toBeVisible();
      
      // Loading should disappear after login completes
      await expect(page.locator('[data-testid="login-loading"]')).not.toBeVisible({ timeout: 10000 });
    });
  });

  test.describe('User Logout', () => {
    test.beforeEach(async ({ page }) => {
      // Login before each logout test
      await authPage.goto();
      const user = testData.users.testUser;
      await authPage.fillEmail(user.email);
      await authPage.fillPassword(user.password);
      await authPage.clickLoginButton();
      await expect(page).toHaveURL(/.*\/dashboard/);
    });

    test('completes full logout workflow', async ({ page }) => {
      await test.step('Access user menu', async () => {
        await page.locator('[data-testid="user-menu"]').click();
        await expect(page.locator('[data-testid="user-dropdown"]')).toBeVisible();
      });

      await test.step('Click logout', async () => {
        await page.locator('[data-testid="logout-button"]').click();
      });

      await test.step('Verify successful logout', async () => {
        // Should redirect to login page
        await expect(page).toHaveURL(/.*\/(login|$)/, { timeout: 10000 });
        
        // Should show login form
        await expect(authPage.getLoginForm()).toBeVisible();
        
        // Should not show user menu
        await expect(page.locator('[data-testid="user-menu"]')).not.toBeVisible();
      });
    });

    test('clears session data on logout', async ({ page }) => {
      // Logout
      await page.locator('[data-testid="user-menu"]').click();
      await page.locator('[data-testid="logout-button"]').click();
      
      // Try to access protected route directly
      await page.goto('/dashboard');
      
      // Should redirect to login
      await expect(page).toHaveURL(/.*\/(login|$)/);
      await expect(authPage.getLoginForm()).toBeVisible();
    });
  });

  test.describe('Session Management', () => {
    test('persists session across page reloads', async ({ page }) => {
      // Login
      await authPage.goto();
      const user = testData.users.testUser;
      await authPage.fillEmail(user.email);
      await authPage.fillPassword(user.password);
      await authPage.clickLoginButton();
      await expect(page).toHaveURL(/.*\/dashboard/);

      // Reload page
      await page.reload();
      
      // Should remain logged in
      await expect(page).toHaveURL(/.*\/dashboard/);
      await expect(page.locator('[data-testid="user-menu"]')).toBeVisible();
    });

    test('persists session across browser tabs', async ({ context }) => {
      const page1 = await context.newPage();
      const page2 = await context.newPage();
      
      // Login in first tab
      const authPage1 = new AuthPage(page1);
      await authPage1.goto();
      const user = testData.users.testUser;
      await authPage1.fillEmail(user.email);
      await authPage1.fillPassword(user.password);
      await authPage1.clickLoginButton();
      await expect(page1).toHaveURL(/.*\/dashboard/);

      // Navigate to dashboard in second tab
      await page2.goto('/dashboard');
      
      // Should be logged in automatically
      await expect(page2).toHaveURL(/.*\/dashboard/);
      await expect(page2.locator('[data-testid="user-menu"]')).toBeVisible();
    });

    test('handles expired session gracefully', async ({ page }) => {
      // Login
      await authPage.goto();
      const user = testData.users.testUser;
      await authPage.fillEmail(user.email);
      await authPage.fillPassword(user.password);
      await authPage.clickLoginButton();
      await expect(page).toHaveURL(/.*\/dashboard/);

      // Simulate expired session by clearing storage
      await page.evaluate(() => {
        localStorage.removeItem('accessToken');
        localStorage.removeItem('refreshToken');
      });

      // Try to access protected resource
      await page.goto('/campaigns');
      
      // Should redirect to login
      await expect(page).toHaveURL(/.*\/(login|$)/);
      await expect(authPage.getLoginForm()).toBeVisible();
    });
  });

  test.describe('Protected Routes', () => {
    test('redirects unauthenticated users to login', async ({ page }) => {
      const protectedRoutes = ['/dashboard', '/campaigns', '/agents', '/analytics'];
      
      for (const route of protectedRoutes) {
        await test.step(`Test protection for ${route}`, async () => {
          await page.goto(route);
          
          // Should redirect to login
          await expect(page).toHaveURL(/.*\/(login|$)/);
          await expect(authPage.getLoginForm()).toBeVisible();
        });
      }
    });

    test('allows authenticated users to access protected routes', async ({ page }) => {
      // Login first
      await authPage.goto();
      const user = testData.users.testUser;
      await authPage.fillEmail(user.email);
      await authPage.fillPassword(user.password);
      await authPage.clickLoginButton();
      await expect(page).toHaveURL(/.*\/dashboard/);

      const protectedRoutes = [
        { path: '/dashboard', testId: 'dashboard-content' },
        { path: '/campaigns', testId: 'campaigns-content' },
        { path: '/agents', testId: 'agents-content' }
      ];
      
      for (const route of protectedRoutes) {
        await test.step(`Test access to ${route.path}`, async () => {
          await page.goto(route.path);
          
          // Should stay on the route
          await expect(page).toHaveURL(new RegExp(`.*${route.path.replace('/', '\\/')}`));
          
          // Should show content (not redirect to login)
          await expect(page.locator(`[data-testid="${route.testId}"]`).or(
            page.locator('main')
          )).toBeVisible();
        });
      }
    });
  });

  test.describe('Accessibility', () => {
    test('login form is keyboard accessible', async ({ page }) => {
      await authPage.goto();
      
      // Tab through form elements
      await page.keyboard.press('Tab'); // Email field
      await expect(page.locator('[data-testid="email-input"]')).toBeFocused();
      
      await page.keyboard.press('Tab'); // Password field
      await expect(page.locator('[data-testid="password-input"]')).toBeFocused();
      
      await page.keyboard.press('Tab'); // Login button
      await expect(page.locator('[data-testid="login-button"]')).toBeFocused();
      
      // Submit form with Enter key
      const user = testData.users.testUser;
      await page.locator('[data-testid="email-input"]').fill(user.email);
      await page.locator('[data-testid="password-input"]').fill(user.password);
      await page.keyboard.press('Enter');
      
      // Should login successfully
      await expect(page).toHaveURL(/.*\/dashboard/);
    });

    test('has proper ARIA labels and roles', async ({ page }) => {
      await authPage.goto();
      
      // Check form accessibility
      await expect(page.locator('[data-testid="login-form"]')).toHaveAttribute('role', 'form');
      await expect(page.locator('[data-testid="email-input"]')).toHaveAttribute('aria-label');
      await expect(page.locator('[data-testid="password-input"]')).toHaveAttribute('aria-label');
      
      // Check error message accessibility
      await authPage.clickLoginButton(); // Trigger validation
      await expect(page.locator('[data-testid="email-error"]')).toHaveAttribute('role', 'alert');
    });
  });
});
