/**
 * Campaign Page Object Model
 * Encapsulates campaign page interactions and elements
 */

export class CampaignPage {
  constructor(page) {
    this.page = page;
    
    // Selectors
    this.selectors = {
      // Campaign form
      campaignForm: '[data-testid="campaign-form"]',
      campaignNameInput: '[data-testid="campaign-name-input"]',
      campaignDescriptionInput: '[data-testid="campaign-description-input"]',
      campaignTypeSelect: '[data-testid="campaign-type-select"]',
      campaignBudgetInput: '[data-testid="campaign-budget-input"]',
      startDateInput: '[data-testid="start-date-input"]',
      endDateInput: '[data-testid="end-date-input"]',
      
      // Platform selection
      platformCheckboxes: '[data-testid="platform-checkbox"]',
      facebookCheckbox: '[data-testid="platform-facebook"]',
      twitterCheckbox: '[data-testid="platform-twitter"]',
      linkedinCheckbox: '[data-testid="platform-linkedin"]',
      instagramCheckbox: '[data-testid="platform-instagram"]',
      
      // Audience targeting
      audienceSection: '[data-testid="audience-section"]',
      ageRangeSelect: '[data-testid="age-range-select"]',
      interestsInput: '[data-testid="interests-input"]',
      locationInput: '[data-testid="location-input"]',
      
      // Form actions
      reviewButton: '[data-testid="review-button"]',
      createButton: '[data-testid="create-button"]',
      saveButton: '[data-testid="save-button"]',
      cancelButton: '[data-testid="cancel-button"]',
      
      // Campaign review
      campaignReview: '[data-testid="campaign-review"]',
      reviewCampaignName: '[data-testid="review-campaign-name"]',
      reviewCampaignBudget: '[data-testid="review-campaign-budget"]',
      reviewCampaignType: '[data-testid="review-campaign-type"]',
      
      // Validation errors
      nameError: '[data-testid="name-error"]',
      budgetError: '[data-testid="budget-error"]',
      typeError: '[data-testid="type-error"]',
      dateError: '[data-testid="date-error"]',
      
      // Campaign details
      campaignDetails: '[data-testid="campaign-details"]',
      campaignTitle: '[data-testid="campaign-title"]',
      campaignStatus: '[data-testid="campaign-status"]',
      campaignBudget: '[data-testid="campaign-budget"]',
      campaignMetrics: '[data-testid="campaign-metrics"]',
      campaignTimeline: '[data-testid="campaign-timeline"]',
      
      // Campaign actions
      editButton: '[data-testid="edit-button"]',
      deleteButton: '[data-testid="delete-button"]',
      shareButton: '[data-testid="share-button"]',
      statusButton: '[data-testid="status-button"]',
      
      // Edit form
      campaignEditForm: '[data-testid="campaign-edit-form"]',
      
      // Status management
      statusSelect: '[data-testid="status-select"]',
      confirmStatusButton: '[data-testid="confirm-status-button"]',
      
      // Delete confirmation
      deleteConfirmation: '[data-testid="delete-confirmation"]',
      confirmDeleteButton: '[data-testid="confirm-delete"]',
      cancelDeleteButton: '[data-testid="cancel-delete"]',
      
      // Analytics
      analyticsTab: '[data-testid="analytics-tab"]',
      analyticsSection: '[data-testid="analytics-section"]',
      analyticsLoading: '[data-testid="analytics-loading"]',
      performanceChart: '[data-testid="performance-chart"]',
      impressionsMetric: '[data-testid="impressions-metric"]',
      clicksMetric: '[data-testid="clicks-metric"]',
      conversionsMetric: '[data-testid="conversions-metric"]',
      ctrMetric: '[data-testid="ctr-metric"]',
      
      // Date range filter
      dateRangeSelect: '[data-testid="date-range-select"]',
      
      // Export
      exportButton: '[data-testid="export-button"]',
      exportFormatSelect: '[data-testid="export-format-select"]',
      confirmExportButton: '[data-testid="confirm-export-button"]',
      
      // Sharing
      shareDialog: '[data-testid="share-dialog"]',
      shareEmailInput: '[data-testid="share-email-input"]',
      shareRoleSelect: '[data-testid="share-role-select"]',
      sendInviteButton: '[data-testid="send-invite-button"]',
      teamMemberList: '[data-testid="team-member-list"]',
      teamMemberRole: '[data-testid="team-member-role"]'
    };
  }

  /**
   * Navigate to campaign creation page
   */
  async gotoCreate() {
    await this.page.goto('/campaigns/create');
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Navigate to specific campaign
   */
  async gotoCampaign(campaignId) {
    await this.page.goto(`/campaigns/${campaignId}`);
    await this.page.waitForLoadState('networkidle');
  }

  // Campaign form interactions
  getCampaignForm() {
    return this.page.locator(this.selectors.campaignForm);
  }

  async fillCampaignName(name) {
    await this.page.locator(this.selectors.campaignNameInput).fill(name);
  }

  async fillCampaignDescription(description) {
    await this.page.locator(this.selectors.campaignDescriptionInput).fill(description);
  }

  async selectCampaignType(type) {
    await this.page.locator(this.selectors.campaignTypeSelect).selectOption(type);
  }

  async fillBudget(budget) {
    await this.page.locator(this.selectors.campaignBudgetInput).fill(budget.toString());
  }

  async setStartDate(date) {
    const dateString = date.toISOString().split('T')[0];
    await this.page.locator(this.selectors.startDateInput).fill(dateString);
  }

  async setEndDate(date) {
    const dateString = date.toISOString().split('T')[0];
    await this.page.locator(this.selectors.endDateInput).fill(dateString);
  }

  // Platform selection
  async selectPlatforms(platforms) {
    for (const platform of platforms) {
      await this.page.locator(`[data-testid="platform-${platform}"]`).check();
    }
  }

  async selectPlatform(platform) {
    await this.page.locator(`[data-testid="platform-${platform}"]`).check();
  }

  async unselectPlatform(platform) {
    await this.page.locator(`[data-testid="platform-${platform}"]`).uncheck();
  }

  // Audience targeting
  async setAudienceTargeting(targeting) {
    if (targeting.ageRange) {
      await this.page.locator(this.selectors.ageRangeSelect).selectOption(targeting.ageRange);
    }
    
    if (targeting.interests) {
      const interestsString = targeting.interests.join(', ');
      await this.page.locator(this.selectors.interestsInput).fill(interestsString);
    }
    
    if (targeting.location) {
      await this.page.locator(this.selectors.locationInput).fill(targeting.location);
    }
  }

  // Form actions
  async clickReviewButton() {
    await this.page.locator(this.selectors.reviewButton).click();
  }

  async clickCreateButton() {
    await this.page.locator(this.selectors.createButton).click();
  }

  async clickSaveButton() {
    await this.page.locator(this.selectors.saveButton).click();
  }

  async clickCancelButton() {
    await this.page.locator(this.selectors.cancelButton).click();
  }

  // Campaign review
  getCampaignReview() {
    return this.page.locator(this.selectors.campaignReview);
  }

  // Validation errors
  getNameError() {
    return this.page.locator(this.selectors.nameError);
  }

  getBudgetError() {
    return this.page.locator(this.selectors.budgetError);
  }

  getTypeError() {
    return this.page.locator(this.selectors.typeError);
  }

  getDateError() {
    return this.page.locator(this.selectors.dateError);
  }

  // Campaign details
  getCampaignDetails() {
    return this.page.locator(this.selectors.campaignDetails);
  }

  getCampaignTitle() {
    return this.page.locator(this.selectors.campaignTitle);
  }

  getCampaignStatus() {
    return this.page.locator(this.selectors.campaignStatus);
  }

  getCampaignBudget() {
    return this.page.locator(this.selectors.campaignBudget);
  }

  getCampaignMetrics() {
    return this.page.locator(this.selectors.campaignMetrics);
  }

  getCampaignTimeline() {
    return this.page.locator(this.selectors.campaignTimeline);
  }

  // Campaign actions
  async clickEditButton() {
    await this.page.locator(this.selectors.editButton).click();
  }

  async clickDeleteButton() {
    await this.page.locator(this.selectors.deleteButton).click();
  }

  async clickShareButton() {
    await this.page.locator(this.selectors.shareButton).click();
  }

  async clickStatusButton() {
    await this.page.locator(this.selectors.statusButton).click();
  }

  getCampaignEditForm() {
    return this.page.locator(this.selectors.campaignEditForm);
  }

  // Status management
  async selectStatus(status) {
    await this.page.locator(this.selectors.statusSelect).selectOption(status);
  }

  async confirmStatusChange() {
    await this.page.locator(this.selectors.confirmStatusButton).click();
  }

  // Delete confirmation
  async confirmDelete() {
    await this.page.locator(this.selectors.confirmDeleteButton).click();
  }

  async cancelDelete() {
    await this.page.locator(this.selectors.cancelDeleteButton).click();
  }

  // Analytics
  async clickAnalyticsTab() {
    await this.page.locator(this.selectors.analyticsTab).click();
  }

  getAnalyticsSection() {
    return this.page.locator(this.selectors.analyticsSection);
  }

  getAnalyticsLoading() {
    return this.page.locator(this.selectors.analyticsLoading);
  }

  getPerformanceChart() {
    return this.page.locator(this.selectors.performanceChart);
  }

  getImpressionsMetric() {
    return this.page.locator(this.selectors.impressionsMetric);
  }

  getClicksMetric() {
    return this.page.locator(this.selectors.clicksMetric);
  }

  getConversionsMetric() {
    return this.page.locator(this.selectors.conversionsMetric);
  }

  getCTRMetric() {
    return this.page.locator(this.selectors.ctrMetric);
  }

  async selectDateRange(range) {
    await this.page.locator(this.selectors.dateRangeSelect).selectOption(range);
  }

  // Export
  async clickExportButton() {
    await this.page.locator(this.selectors.exportButton).click();
  }

  async selectExportFormat(format) {
    await this.page.locator(this.selectors.exportFormatSelect).selectOption(format);
  }

  async confirmExport() {
    await this.page.locator(this.selectors.confirmExportButton).click();
  }

  // Sharing
  getShareDialog() {
    return this.page.locator(this.selectors.shareDialog);
  }

  async fillShareEmail(email) {
    await this.page.locator(this.selectors.shareEmailInput).fill(email);
  }

  async selectShareRole(role) {
    await this.page.locator(this.selectors.shareRoleSelect).selectOption(role);
  }

  async clickSendInvite() {
    await this.page.locator(this.selectors.sendInviteButton).click();
  }

  getTeamMemberList() {
    return this.page.locator(this.selectors.teamMemberList);
  }

  // Utility methods
  async fillBasicCampaignInfo(campaign) {
    await this.fillCampaignName(campaign.name);
    await this.fillCampaignDescription(campaign.description);
    await this.selectCampaignType(campaign.type);
    await this.fillBudget(campaign.budget);
  }

  async waitForCampaignLoad() {
    await this.page.waitForSelector(this.selectors.campaignDetails, { state: 'visible' });
  }

  async waitForAnalyticsLoad() {
    await this.page.waitForSelector(this.selectors.analyticsSection, { state: 'visible' });
    await this.page.waitForSelector(this.selectors.analyticsLoading, { state: 'hidden', timeout: 10000 });
  }

  async takeScreenshot(name) {
    await this.page.screenshot({ 
      path: `e2e-results/screenshots/campaign-${name}-${Date.now()}.png`,
      fullPage: true 
    });
  }

  // Validation helpers
  async getFormErrors() {
    const errors = {};
    
    if (await this.getNameError().isVisible()) {
      errors.name = await this.getNameError().textContent();
    }
    
    if (await this.getBudgetError().isVisible()) {
      errors.budget = await this.getBudgetError().textContent();
    }
    
    if (await this.getTypeError().isVisible()) {
      errors.type = await this.getTypeError().textContent();
    }
    
    if (await this.getDateError().isVisible()) {
      errors.date = await this.getDateError().textContent();
    }
    
    return errors;
  }

  async isFormValid() {
    const errors = await this.getFormErrors();
    return Object.keys(errors).length === 0;
  }
}
