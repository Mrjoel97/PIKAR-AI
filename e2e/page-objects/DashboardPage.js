/**
 * Dashboard Page Object Model
 * Encapsulates dashboard page interactions and elements
 */

export class DashboardPage {
  constructor(page) {
    this.page = page;
    
    // Selectors
    this.selectors = {
      // Main dashboard
      dashboardTitle: '[data-testid="dashboard-title"]',
      dashboardContent: '[data-testid="dashboard-content"]',
      welcomeMessage: '[data-testid="welcome-message"]',
      
      // User menu
      userMenu: '[data-testid="user-menu"]',
      userDropdown: '[data-testid="user-dropdown"]',
      userProfile: '[data-testid="user-profile"]',
      logoutButton: '[data-testid="logout-button"]',
      settingsButton: '[data-testid="settings-button"]',
      
      // Navigation
      sidebar: '[data-testid="sidebar"]',
      navDashboard: '[data-testid="nav-dashboard"]',
      navCampaigns: '[data-testid="nav-campaigns"]',
      navAgents: '[data-testid="nav-agents"]',
      navAnalytics: '[data-testid="nav-analytics"]',
      navSettings: '[data-testid="nav-settings"]',
      
      // Campaigns section
      campaignsSection: '[data-testid="campaigns-section"]',
      campaignsList: '[data-testid="campaigns-list"]',
      campaignCard: '[data-testid="campaign-card"]',
      createCampaignButton: '[data-testid="create-campaign-button"]',
      campaignFilter: '[data-testid="campaign-filter"]',
      campaignSearch: '[data-testid="campaign-search"]',
      
      // Analytics section
      analyticsSection: '[data-testid="analytics-section"]',
      analyticsChart: '[data-testid="analytics-chart"]',
      metricsCards: '[data-testid="metrics-cards"]',
      totalUsers: '[data-testid="total-users"]',
      activeUsers: '[data-testid="active-users"]',
      totalSessions: '[data-testid="total-sessions"]',
      conversionRate: '[data-testid="conversion-rate"]',
      
      // Recent activity
      recentActivity: '[data-testid="recent-activity"]',
      activityList: '[data-testid="activity-list"]',
      activityItem: '[data-testid="activity-item"]',
      
      // Quick actions
      quickActions: '[data-testid="quick-actions"]',
      quickActionButton: '[data-testid="quick-action-button"]',
      
      // Notifications
      notificationBell: '[data-testid="notification-bell"]',
      notificationDropdown: '[data-testid="notification-dropdown"]',
      notificationItem: '[data-testid="notification-item"]',
      notificationBadge: '[data-testid="notification-badge"]',
      
      // Loading states
      dashboardLoading: '[data-testid="dashboard-loading"]',
      campaignsLoading: '[data-testid="campaigns-loading"]',
      analyticsLoading: '[data-testid="analytics-loading"]',
      
      // Error states
      dashboardError: '[data-testid="dashboard-error"]',
      campaignsError: '[data-testid="campaigns-error"]',
      analyticsError: '[data-testid="analytics-error"]',
      
      // Refresh button
      refreshButton: '[data-testid="refresh-button"]',
      
      // Search
      globalSearch: '[data-testid="global-search"]',
      searchResults: '[data-testid="search-results"]'
    };
  }

  /**
   * Navigate to dashboard
   */
  async goto() {
    await this.page.goto('/dashboard');
    await this.page.waitForLoadState('networkidle');
  }

  // Main dashboard elements
  getDashboardTitle() {
    return this.page.locator(this.selectors.dashboardTitle);
  }

  getDashboardContent() {
    return this.page.locator(this.selectors.dashboardContent);
  }

  getWelcomeMessage() {
    return this.page.locator(this.selectors.welcomeMessage);
  }

  // User menu interactions
  async clickUserMenu() {
    await this.page.locator(this.selectors.userMenu).click();
  }

  async clickLogout() {
    await this.clickUserMenu();
    await this.page.locator(this.selectors.logoutButton).click();
  }

  async clickSettings() {
    await this.clickUserMenu();
    await this.page.locator(this.selectors.settingsButton).click();
  }

  async clickUserProfile() {
    await this.clickUserMenu();
    await this.page.locator(this.selectors.userProfile).click();
  }

  getUserDropdown() {
    return this.page.locator(this.selectors.userDropdown);
  }

  // Navigation
  async clickNavDashboard() {
    await this.page.locator(this.selectors.navDashboard).click();
  }

  async clickNavCampaigns() {
    await this.page.locator(this.selectors.navCampaigns).click();
  }

  async clickNavAgents() {
    await this.page.locator(this.selectors.navAgents).click();
  }

  async clickNavAnalytics() {
    await this.page.locator(this.selectors.navAnalytics).click();
  }

  async clickNavSettings() {
    await this.page.locator(this.selectors.navSettings).click();
  }

  getSidebar() {
    return this.page.locator(this.selectors.sidebar);
  }

  // Campaigns section
  getCampaignsSection() {
    return this.page.locator(this.selectors.campaignsSection);
  }

  getCampaignsList() {
    return this.page.locator(this.selectors.campaignsList);
  }

  getCampaignCards() {
    return this.page.locator(this.selectors.campaignCard);
  }

  async clickCreateCampaign() {
    await this.page.locator(this.selectors.createCampaignButton).click();
  }

  async searchCampaigns(query) {
    await this.page.locator(this.selectors.campaignSearch).fill(query);
  }

  async filterCampaigns(status) {
    await this.page.locator(this.selectors.campaignFilter).selectOption(status);
  }

  async getCampaignByName(name) {
    return this.page.locator(this.selectors.campaignCard).filter({ hasText: name });
  }

  async clickCampaign(name) {
    const campaign = await this.getCampaignByName(name);
    await campaign.click();
  }

  // Analytics section
  getAnalyticsSection() {
    return this.page.locator(this.selectors.analyticsSection);
  }

  getAnalyticsChart() {
    return this.page.locator(this.selectors.analyticsChart);
  }

  getMetricsCards() {
    return this.page.locator(this.selectors.metricsCards);
  }

  async getTotalUsers() {
    return await this.page.locator(this.selectors.totalUsers).textContent();
  }

  async getActiveUsers() {
    return await this.page.locator(this.selectors.activeUsers).textContent();
  }

  async getTotalSessions() {
    return await this.page.locator(this.selectors.totalSessions).textContent();
  }

  async getConversionRate() {
    return await this.page.locator(this.selectors.conversionRate).textContent();
  }

  // Recent activity
  getRecentActivity() {
    return this.page.locator(this.selectors.recentActivity);
  }

  getActivityList() {
    return this.page.locator(this.selectors.activityList);
  }

  getActivityItems() {
    return this.page.locator(this.selectors.activityItem);
  }

  // Quick actions
  getQuickActions() {
    return this.page.locator(this.selectors.quickActions);
  }

  async clickQuickAction(action) {
    await this.page.locator(this.selectors.quickActionButton).filter({ hasText: action }).click();
  }

  // Notifications
  async clickNotificationBell() {
    await this.page.locator(this.selectors.notificationBell).click();
  }

  getNotificationDropdown() {
    return this.page.locator(this.selectors.notificationDropdown);
  }

  getNotificationItems() {
    return this.page.locator(this.selectors.notificationItem);
  }

  async getNotificationCount() {
    const badge = this.page.locator(this.selectors.notificationBadge);
    if (await badge.isVisible()) {
      return await badge.textContent();
    }
    return '0';
  }

  // Loading states
  getDashboardLoading() {
    return this.page.locator(this.selectors.dashboardLoading);
  }

  getCampaignsLoading() {
    return this.page.locator(this.selectors.campaignsLoading);
  }

  getAnalyticsLoading() {
    return this.page.locator(this.selectors.analyticsLoading);
  }

  // Error states
  getDashboardError() {
    return this.page.locator(this.selectors.dashboardError);
  }

  getCampaignsError() {
    return this.page.locator(this.selectors.campaignsError);
  }

  getAnalyticsError() {
    return this.page.locator(this.selectors.analyticsError);
  }

  // Actions
  async refreshDashboard() {
    await this.page.locator(this.selectors.refreshButton).click();
  }

  async globalSearch(query) {
    await this.page.locator(this.selectors.globalSearch).fill(query);
    await this.page.keyboard.press('Enter');
  }

  getSearchResults() {
    return this.page.locator(this.selectors.searchResults);
  }

  // Utility methods
  async waitForDashboardLoad() {
    await this.page.waitForSelector(this.selectors.dashboardContent, { state: 'visible' });
    
    // Wait for loading states to disappear
    await this.page.waitForSelector(this.selectors.dashboardLoading, { state: 'hidden', timeout: 10000 });
  }

  async waitForCampaignsLoad() {
    await this.page.waitForSelector(this.selectors.campaignsSection, { state: 'visible' });
    await this.page.waitForSelector(this.selectors.campaignsLoading, { state: 'hidden', timeout: 10000 });
  }

  async waitForAnalyticsLoad() {
    await this.page.waitForSelector(this.selectors.analyticsSection, { state: 'visible' });
    await this.page.waitForSelector(this.selectors.analyticsLoading, { state: 'hidden', timeout: 10000 });
  }

  async isDashboardLoaded() {
    try {
      await this.waitForDashboardLoad();
      return true;
    } catch {
      return false;
    }
  }

  async getCampaignCount() {
    const campaigns = await this.getCampaignCards();
    return await campaigns.count();
  }

  async getVisibleSections() {
    const sections = [];
    
    if (await this.getCampaignsSection().isVisible()) {
      sections.push('campaigns');
    }
    
    if (await this.getAnalyticsSection().isVisible()) {
      sections.push('analytics');
    }
    
    if (await this.getRecentActivity().isVisible()) {
      sections.push('activity');
    }
    
    if (await this.getQuickActions().isVisible()) {
      sections.push('quickActions');
    }
    
    return sections;
  }

  async takeScreenshot(name) {
    await this.page.screenshot({ 
      path: `e2e-results/screenshots/dashboard-${name}-${Date.now()}.png`,
      fullPage: true 
    });
  }

  // Accessibility helpers
  async checkDashboardAccessibility() {
    // Check if main content has proper landmarks
    const main = this.page.locator('main');
    if (!(await main.isVisible())) {
      throw new Error('Dashboard missing main landmark');
    }
    
    // Check if navigation has proper role
    const nav = this.getSidebar();
    const navRole = await nav.getAttribute('role');
    if (navRole !== 'navigation') {
      throw new Error('Sidebar missing navigation role');
    }
    
    // Check if headings are properly structured
    const headings = this.page.locator('h1, h2, h3, h4, h5, h6');
    const headingCount = await headings.count();
    if (headingCount === 0) {
      throw new Error('Dashboard missing heading structure');
    }
    
    return true;
  }

  async testKeyboardNavigation() {
    // Test tab navigation through main elements
    await this.page.keyboard.press('Tab'); // User menu
    await this.page.keyboard.press('Tab'); // Notification bell
    await this.page.keyboard.press('Tab'); // Global search
    await this.page.keyboard.press('Tab'); // First campaign or quick action
    
    // Test arrow key navigation in sidebar
    await this.getSidebar().focus();
    await this.page.keyboard.press('ArrowDown');
    await this.page.keyboard.press('ArrowDown');
    
    return true;
  }
}
