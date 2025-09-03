/**
 * Authentication Page Object Model
 * Encapsulates authentication page interactions and elements
 */

export class AuthPage {
  constructor(page) {
    this.page = page;
    
    // Selectors
    this.selectors = {
      // Login form
      loginForm: '[data-testid="login-form"]',
      emailInput: '[data-testid="email-input"]',
      passwordInput: '[data-testid="password-input"]',
      loginButton: '[data-testid="login-button"]',
      loginError: '[data-testid="login-error"]',
      loginLoading: '[data-testid="login-loading"]',
      
      // Registration form
      registrationForm: '[data-testid="registration-form"]',
      nameInput: '[data-testid="name-input"]',
      companyInput: '[data-testid="company-input"]',
      registerButton: '[data-testid="register-button"]',
      registrationError: '[data-testid="registration-error"]',
      
      // Navigation
      signUpLink: '[data-testid="sign-up-link"]',
      signInLink: '[data-testid="sign-in-link"]',
      
      // Validation errors
      emailError: '[data-testid="email-error"]',
      passwordError: '[data-testid="password-error"]',
      nameError: '[data-testid="name-error"]',
      companyError: '[data-testid="company-error"]',
      
      // Password reset
      forgotPasswordLink: '[data-testid="forgot-password-link"]',
      resetPasswordForm: '[data-testid="reset-password-form"]',
      resetEmailInput: '[data-testid="reset-email-input"]',
      resetSubmitButton: '[data-testid="reset-submit-button"]',
      
      // Social login
      googleLoginButton: '[data-testid="google-login-button"]',
      githubLoginButton: '[data-testid="github-login-button"]',
      
      // Terms and privacy
      termsCheckbox: '[data-testid="terms-checkbox"]',
      privacyLink: '[data-testid="privacy-link"]',
      termsLink: '[data-testid="terms-link"]'
    };
  }

  /**
   * Navigate to authentication page
   */
  async goto() {
    await this.page.goto('/');
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Navigate to login page specifically
   */
  async gotoLogin() {
    await this.page.goto('/login');
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Navigate to registration page specifically
   */
  async gotoRegister() {
    await this.page.goto('/register');
    await this.page.waitForLoadState('networkidle');
  }

  // Login form interactions
  getLoginForm() {
    return this.page.locator(this.selectors.loginForm);
  }

  async fillEmail(email) {
    await this.page.locator(this.selectors.emailInput).fill(email);
  }

  async fillPassword(password) {
    await this.page.locator(this.selectors.passwordInput).fill(password);
  }

  async clickLoginButton() {
    await this.page.locator(this.selectors.loginButton).click();
  }

  async submitLoginForm(email, password) {
    await this.fillEmail(email);
    await this.fillPassword(password);
    await this.clickLoginButton();
  }

  getLoginError() {
    return this.page.locator(this.selectors.loginError);
  }

  getLoginLoading() {
    return this.page.locator(this.selectors.loginLoading);
  }

  // Registration form interactions
  getRegistrationForm() {
    return this.page.locator(this.selectors.registrationForm);
  }

  async fillName(name) {
    await this.page.locator(this.selectors.nameInput).fill(name);
  }

  async fillCompany(company) {
    await this.page.locator(this.selectors.companyInput).fill(company);
  }

  async clickRegisterButton() {
    await this.page.locator(this.selectors.registerButton).click();
  }

  async fillRegistrationForm(userData) {
    await this.fillEmail(userData.email);
    await this.fillPassword(userData.password);
    await this.fillName(userData.name);
    if (userData.company) {
      await this.fillCompany(userData.company);
    }
    
    // Accept terms if checkbox exists
    const termsCheckbox = this.page.locator(this.selectors.termsCheckbox);
    if (await termsCheckbox.isVisible()) {
      await termsCheckbox.check();
    }
  }

  async submitRegistrationForm(userData) {
    await this.fillRegistrationForm(userData);
    await this.clickRegisterButton();
  }

  getRegistrationError() {
    return this.page.locator(this.selectors.registrationError);
  }

  // Navigation
  async clickSignUpLink() {
    await this.page.locator(this.selectors.signUpLink).click();
  }

  async clickSignInLink() {
    await this.page.locator(this.selectors.signInLink).click();
  }

  // Validation errors
  getEmailError() {
    return this.page.locator(this.selectors.emailError);
  }

  getPasswordError() {
    return this.page.locator(this.selectors.passwordError);
  }

  getNameError() {
    return this.page.locator(this.selectors.nameError);
  }

  getCompanyError() {
    return this.page.locator(this.selectors.companyError);
  }

  // Password reset
  async clickForgotPasswordLink() {
    await this.page.locator(this.selectors.forgotPasswordLink).click();
  }

  async fillResetEmail(email) {
    await this.page.locator(this.selectors.resetEmailInput).fill(email);
  }

  async submitPasswordReset(email) {
    await this.fillResetEmail(email);
    await this.page.locator(this.selectors.resetSubmitButton).click();
  }

  getResetPasswordForm() {
    return this.page.locator(this.selectors.resetPasswordForm);
  }

  // Social login
  async clickGoogleLogin() {
    await this.page.locator(this.selectors.googleLoginButton).click();
  }

  async clickGithubLogin() {
    await this.page.locator(this.selectors.githubLoginButton).click();
  }

  // Terms and privacy
  async acceptTerms() {
    await this.page.locator(this.selectors.termsCheckbox).check();
  }

  async clickPrivacyLink() {
    await this.page.locator(this.selectors.privacyLink).click();
  }

  async clickTermsLink() {
    await this.page.locator(this.selectors.termsLink).click();
  }

  // Utility methods
  async waitForLoginSuccess() {
    await this.page.waitForURL(/.*\/dashboard/, { timeout: 10000 });
  }

  async waitForRegistrationSuccess() {
    await this.page.waitForURL(/.*\/dashboard/, { timeout: 10000 });
  }

  async isLoggedIn() {
    try {
      await this.page.waitForURL(/.*\/dashboard/, { timeout: 5000 });
      return true;
    } catch {
      return false;
    }
  }

  async getValidationErrors() {
    const errors = {};
    
    const emailError = this.page.locator(this.selectors.emailError);
    if (await emailError.isVisible()) {
      errors.email = await emailError.textContent();
    }
    
    const passwordError = this.page.locator(this.selectors.passwordError);
    if (await passwordError.isVisible()) {
      errors.password = await passwordError.textContent();
    }
    
    const nameError = this.page.locator(this.selectors.nameError);
    if (await nameError.isVisible()) {
      errors.name = await nameError.textContent();
    }
    
    const companyError = this.page.locator(this.selectors.companyError);
    if (await companyError.isVisible()) {
      errors.company = await companyError.textContent();
    }
    
    return errors;
  }

  async takeScreenshot(name) {
    await this.page.screenshot({ 
      path: `e2e-results/screenshots/auth-${name}-${Date.now()}.png`,
      fullPage: true 
    });
  }

  // Accessibility helpers
  async checkFormAccessibility() {
    const form = this.getLoginForm();
    
    // Check if form has proper role
    const role = await form.getAttribute('role');
    if (role !== 'form') {
      throw new Error('Login form missing proper role attribute');
    }
    
    // Check if inputs have labels
    const emailInput = this.page.locator(this.selectors.emailInput);
    const emailLabel = await emailInput.getAttribute('aria-label');
    if (!emailLabel) {
      throw new Error('Email input missing aria-label');
    }
    
    const passwordInput = this.page.locator(this.selectors.passwordInput);
    const passwordLabel = await passwordInput.getAttribute('aria-label');
    if (!passwordLabel) {
      throw new Error('Password input missing aria-label');
    }
    
    return true;
  }

  async testKeyboardNavigation() {
    await this.page.keyboard.press('Tab');
    const emailFocused = await this.page.locator(this.selectors.emailInput).evaluate(el => el === document.activeElement);
    
    await this.page.keyboard.press('Tab');
    const passwordFocused = await this.page.locator(this.selectors.passwordInput).evaluate(el => el === document.activeElement);
    
    await this.page.keyboard.press('Tab');
    const buttonFocused = await this.page.locator(this.selectors.loginButton).evaluate(el => el === document.activeElement);
    
    return emailFocused && passwordFocused && buttonFocused;
  }
}
