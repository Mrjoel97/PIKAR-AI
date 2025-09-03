/**
 * Email Notification Service
 * Comprehensive email notification system with templates, preferences, and delivery tracking
 */

import { auditService } from './auditService'
import { loggingService } from './loggingService'
import { environmentConfig } from '@/config/environment'

class EmailNotificationService {
  constructor() {
    this.emailProvider = null
    this.templates = new Map()
    this.userPreferences = new Map()
    this.deliveryTracking = new Map()
    this.isInitialized = false
    
    // Email configuration
    this.config = {
      provider: environmentConfig.email?.provider || 'sendgrid',
      apiKey: environmentConfig.email?.apiKey,
      fromEmail: environmentConfig.email?.fromEmail || 'noreply@pikar-ai.com',
      fromName: environmentConfig.email?.fromName || 'PIKAR AI',
      replyTo: environmentConfig.email?.replyTo || 'support@pikar-ai.com',
      trackOpens: true,
      trackClicks: true,
      retryAttempts: 3,
      retryDelay: 5000 // 5 seconds
    }
    
    // Default notification types
    this.notificationTypes = {
      WELCOME: 'welcome',
      AGENT_EXECUTION_COMPLETE: 'agent_execution_complete',
      AGENT_EXECUTION_FAILED: 'agent_execution_failed',
      TIER_UPGRADED: 'tier_upgraded',
      TIER_DOWNGRADED: 'tier_downgraded',
      QUOTA_WARNING: 'quota_warning',
      QUOTA_EXCEEDED: 'quota_exceeded',
      SECURITY_ALERT: 'security_alert',
      BILLING_REMINDER: 'billing_reminder',
      PAYMENT_FAILED: 'payment_failed',
      WEEKLY_SUMMARY: 'weekly_summary',
      MONTHLY_REPORT: 'monthly_report',
      SYSTEM_MAINTENANCE: 'system_maintenance',
      FEATURE_ANNOUNCEMENT: 'feature_announcement',
      PASSWORD_RESET: 'password_reset',
      EMAIL_VERIFICATION: 'email_verification'
    }
    
    this.setupEmailTemplates()
  }

  /**
   * Initialize email notification service
   */
  async initialize() {
    try {
      console.log('📧 Initializing Email Notification Service...')
      
      // Initialize email provider
      await this.initializeEmailProvider()
      
      // Load user preferences
      await this.loadUserPreferences()
      
      // Setup delivery tracking
      this.setupDeliveryTracking()
      
      this.isInitialized = true
      
      console.log('✅ Email Notification Service initialized successfully')
      
      await auditService.logSystem.notification('email_service_initialized', {
        provider: this.config.provider,
        templatesLoaded: this.templates.size,
        trackingEnabled: this.config.trackOpens
      })
      
    } catch (error) {
      console.error('❌ Email Notification Service initialization failed:', error)
      throw error
    }
  }

  /**
   * Initialize email provider
   */
  async initializeEmailProvider() {
    switch (this.config.provider) {
      case 'sendgrid':
        this.emailProvider = new SendGridProvider(this.config)
        break
      case 'ses':
        this.emailProvider = new SESProvider(this.config)
        break
      case 'mailgun':
        this.emailProvider = new MailgunProvider(this.config)
        break
      case 'smtp':
        this.emailProvider = new SMTPProvider(this.config)
        break
      default:
        this.emailProvider = new MockEmailProvider(this.config)
    }
    
    await this.emailProvider.initialize()
  }

  /**
   * Setup email templates
   */
  setupEmailTemplates() {
    // Welcome email template
    this.templates.set(this.notificationTypes.WELCOME, {
      subject: 'Welcome to PIKAR AI! 🚀',
      template: 'welcome',
      variables: ['userName', 'activationLink', 'supportEmail'],
      category: 'onboarding'
    })
    
    // Agent execution complete
    this.templates.set(this.notificationTypes.AGENT_EXECUTION_COMPLETE, {
      subject: 'Agent Execution Complete - {{agentType}}',
      template: 'agent_execution_complete',
      variables: ['userName', 'agentType', 'executionId', 'duration', 'results', 'dashboardLink'],
      category: 'agent_activity'
    })
    
    // Agent execution failed
    this.templates.set(this.notificationTypes.AGENT_EXECUTION_FAILED, {
      subject: 'Agent Execution Failed - {{agentType}}',
      template: 'agent_execution_failed',
      variables: ['userName', 'agentType', 'executionId', 'errorMessage', 'supportLink'],
      category: 'agent_activity'
    })
    
    // Tier upgraded
    this.templates.set(this.notificationTypes.TIER_UPGRADED, {
      subject: 'Welcome to {{tierName}}! 🎉',
      template: 'tier_upgraded',
      variables: ['userName', 'tierName', 'newFeatures', 'billingAmount', 'nextBillingDate'],
      category: 'billing'
    })
    
    // Quota warning
    this.templates.set(this.notificationTypes.QUOTA_WARNING, {
      subject: 'Quota Warning - {{quotaType}}',
      template: 'quota_warning',
      variables: ['userName', 'quotaType', 'currentUsage', 'limit', 'percentage', 'upgradeLink'],
      category: 'usage'
    })
    
    // Security alert
    this.templates.set(this.notificationTypes.SECURITY_ALERT, {
      subject: '🔒 Security Alert - PIKAR AI',
      template: 'security_alert',
      variables: ['userName', 'alertType', 'timestamp', 'ipAddress', 'location', 'actionRequired'],
      category: 'security'
    })
    
    // Weekly summary
    this.templates.set(this.notificationTypes.WEEKLY_SUMMARY, {
      subject: 'Your Weekly PIKAR AI Summary',
      template: 'weekly_summary',
      variables: ['userName', 'weekStart', 'weekEnd', 'agentExecutions', 'topAgents', 'achievements'],
      category: 'summary'
    })
    
    // Password reset
    this.templates.set(this.notificationTypes.PASSWORD_RESET, {
      subject: 'Reset Your PIKAR AI Password',
      template: 'password_reset',
      variables: ['userName', 'resetLink', 'expirationTime'],
      category: 'security'
    })
  }

  /**
   * Send email notification
   */
  async sendNotification(userId, notificationType, variables = {}, options = {}) {
    try {
      // Check if user has opted out of this notification type
      if (!this.canSendNotification(userId, notificationType)) {
        loggingService.info('Notification blocked by user preferences', {
          userId,
          notificationType
        })
        return { success: false, reason: 'User opted out' }
      }
      
      const template = this.templates.get(notificationType)
      if (!template) {
        throw new Error(`Template not found for notification type: ${notificationType}`)
      }
      
      // Get user email and preferences
      const userEmail = await this.getUserEmail(userId)
      if (!userEmail) {
        throw new Error(`Email not found for user: ${userId}`)
      }
      
      // Prepare email data
      const emailData = {
        to: userEmail,
        from: {
          email: this.config.fromEmail,
          name: this.config.fromName
        },
        replyTo: this.config.replyTo,
        subject: this.processTemplate(template.subject, variables),
        templateId: template.template,
        dynamicTemplateData: {
          ...variables,
          baseUrl: environmentConfig.baseUrl,
          supportEmail: this.config.replyTo,
          unsubscribeUrl: this.generateUnsubscribeUrl(userId, notificationType)
        },
        categories: [template.category, 'pikar-ai'],
        customArgs: {
          userId,
          notificationType,
          timestamp: Date.now().toString()
        },
        trackingSettings: {
          clickTracking: { enable: this.config.trackClicks },
          openTracking: { enable: this.config.trackOpens }
        },
        ...options
      }
      
      // Send email
      const result = await this.emailProvider.send(emailData)
      
      // Track delivery
      await this.trackDelivery(userId, notificationType, result)
      
      // Log successful send
      await auditService.logSystem.notification('email_sent', {
        userId,
        notificationType,
        messageId: result.messageId,
        recipient: userEmail
      })
      
      return {
        success: true,
        messageId: result.messageId,
        deliveryId: result.deliveryId
      }
      
    } catch (error) {
      console.error('Failed to send email notification:', error)
      
      await auditService.logSystem.error(error, 'email_send_failed', {
        userId,
        notificationType
      })
      
      // Retry logic
      if (options.retryCount < this.config.retryAttempts) {
        setTimeout(() => {
          this.sendNotification(userId, notificationType, variables, {
            ...options,
            retryCount: (options.retryCount || 0) + 1
          })
        }, this.config.retryDelay * (options.retryCount + 1))
      }
      
      throw error
    }
  }

  /**
   * Send bulk notifications
   */
  async sendBulkNotifications(notifications) {
    const results = []
    const batchSize = 100 // Process in batches to avoid rate limits
    
    for (let i = 0; i < notifications.length; i += batchSize) {
      const batch = notifications.slice(i, i + batchSize)
      
      const batchPromises = batch.map(async (notification) => {
        try {
          const result = await this.sendNotification(
            notification.userId,
            notification.type,
            notification.variables,
            notification.options
          )
          return { ...notification, result, success: true }
        } catch (error) {
          return { ...notification, error: error.message, success: false }
        }
      })
      
      const batchResults = await Promise.allSettled(batchPromises)
      results.push(...batchResults.map(r => r.value || r.reason))
      
      // Add delay between batches to respect rate limits
      if (i + batchSize < notifications.length) {
        await new Promise(resolve => setTimeout(resolve, 1000))
      }
    }
    
    return results
  }

  /**
   * Update user notification preferences
   */
  async updateUserPreferences(userId, preferences) {
    const currentPreferences = this.userPreferences.get(userId) || this.getDefaultPreferences()
    
    const updatedPreferences = {
      ...currentPreferences,
      ...preferences,
      updatedAt: Date.now()
    }
    
    this.userPreferences.set(userId, updatedPreferences)
    
    // Save to database
    await this.saveUserPreferences(userId, updatedPreferences)
    
    await auditService.logAccess.preferences('notification_preferences_updated', {
      userId,
      preferences: Object.keys(preferences)
    })
    
    return updatedPreferences
  }

  /**
   * Get user notification preferences
   */
  getUserPreferences(userId) {
    return this.userPreferences.get(userId) || this.getDefaultPreferences()
  }

  /**
   * Get default notification preferences
   */
  getDefaultPreferences() {
    return {
      [this.notificationTypes.WELCOME]: true,
      [this.notificationTypes.AGENT_EXECUTION_COMPLETE]: true,
      [this.notificationTypes.AGENT_EXECUTION_FAILED]: true,
      [this.notificationTypes.TIER_UPGRADED]: true,
      [this.notificationTypes.TIER_DOWNGRADED]: true,
      [this.notificationTypes.QUOTA_WARNING]: true,
      [this.notificationTypes.QUOTA_EXCEEDED]: true,
      [this.notificationTypes.SECURITY_ALERT]: true,
      [this.notificationTypes.BILLING_REMINDER]: true,
      [this.notificationTypes.PAYMENT_FAILED]: true,
      [this.notificationTypes.WEEKLY_SUMMARY]: false, // Opt-in
      [this.notificationTypes.MONTHLY_REPORT]: false, // Opt-in
      [this.notificationTypes.SYSTEM_MAINTENANCE]: true,
      [this.notificationTypes.FEATURE_ANNOUNCEMENT]: false, // Opt-in
      [this.notificationTypes.PASSWORD_RESET]: true,
      [this.notificationTypes.EMAIL_VERIFICATION]: true,
      emailFrequency: 'immediate', // immediate, daily, weekly
      createdAt: Date.now(),
      updatedAt: Date.now()
    }
  }

  /**
   * Check if notification can be sent to user
   */
  canSendNotification(userId, notificationType) {
    const preferences = this.getUserPreferences(userId)
    return preferences[notificationType] !== false
  }

  /**
   * Process template with variables
   */
  processTemplate(template, variables) {
    let processed = template
    
    for (const [key, value] of Object.entries(variables)) {
      const regex = new RegExp(`{{${key}}}`, 'g')
      processed = processed.replace(regex, value)
    }
    
    return processed
  }

  /**
   * Generate unsubscribe URL
   */
  generateUnsubscribeUrl(userId, notificationType) {
    const token = this.generateUnsubscribeToken(userId, notificationType)
    return `${environmentConfig.baseUrl}/unsubscribe?token=${token}`
  }

  /**
   * Generate unsubscribe token
   */
  generateUnsubscribeToken(userId, notificationType) {
    // This would use proper JWT or similar secure token generation
    return Buffer.from(`${userId}:${notificationType}:${Date.now()}`).toString('base64')
  }

  /**
   * Track email delivery
   */
  async trackDelivery(userId, notificationType, result) {
    const deliveryRecord = {
      userId,
      notificationType,
      messageId: result.messageId,
      deliveryId: result.deliveryId,
      status: 'sent',
      sentAt: Date.now(),
      opens: 0,
      clicks: 0,
      lastActivity: Date.now()
    }
    
    this.deliveryTracking.set(result.messageId, deliveryRecord)
    
    // Save to database for persistence
    await this.saveDeliveryRecord(deliveryRecord)
  }

  /**
   * Handle webhook events from email provider
   */
  async handleWebhookEvent(event) {
    const { messageId, eventType, timestamp, data } = event
    
    const deliveryRecord = this.deliveryTracking.get(messageId)
    if (!deliveryRecord) {
      console.warn('Delivery record not found for message:', messageId)
      return
    }
    
    switch (eventType) {
      case 'delivered':
        deliveryRecord.status = 'delivered'
        deliveryRecord.deliveredAt = timestamp
        break
        
      case 'opened':
        deliveryRecord.opens += 1
        deliveryRecord.lastOpenedAt = timestamp
        break
        
      case 'clicked':
        deliveryRecord.clicks += 1
        deliveryRecord.lastClickedAt = timestamp
        break
        
      case 'bounced':
        deliveryRecord.status = 'bounced'
        deliveryRecord.bounceReason = data.reason
        break
        
      case 'spam':
        deliveryRecord.status = 'spam'
        break
        
      case 'unsubscribed':
        deliveryRecord.status = 'unsubscribed'
        await this.handleUnsubscribe(deliveryRecord.userId, deliveryRecord.notificationType)
        break
    }
    
    deliveryRecord.lastActivity = timestamp
    await this.updateDeliveryRecord(deliveryRecord)
    
    await auditService.logSystem.notification('email_webhook_processed', {
      messageId,
      eventType,
      userId: deliveryRecord.userId
    })
  }

  /**
   * Handle unsubscribe request
   */
  async handleUnsubscribe(userId, notificationType) {
    const preferences = this.getUserPreferences(userId)
    preferences[notificationType] = false
    preferences.updatedAt = Date.now()
    
    await this.updateUserPreferences(userId, { [notificationType]: false })
    
    await auditService.logAccess.preferences('user_unsubscribed', {
      userId,
      notificationType
    })
  }

  /**
   * Get delivery statistics
   */
  getDeliveryStatistics(timeWindow = 24 * 60 * 60 * 1000) { // 24 hours
    const cutoff = Date.now() - timeWindow
    const recentDeliveries = Array.from(this.deliveryTracking.values())
      .filter(record => record.sentAt > cutoff)
    
    const stats = {
      totalSent: recentDeliveries.length,
      delivered: recentDeliveries.filter(r => r.status === 'delivered').length,
      opened: recentDeliveries.filter(r => r.opens > 0).length,
      clicked: recentDeliveries.filter(r => r.clicks > 0).length,
      bounced: recentDeliveries.filter(r => r.status === 'bounced').length,
      spam: recentDeliveries.filter(r => r.status === 'spam').length,
      unsubscribed: recentDeliveries.filter(r => r.status === 'unsubscribed').length
    }
    
    stats.deliveryRate = stats.totalSent > 0 ? (stats.delivered / stats.totalSent) * 100 : 0
    stats.openRate = stats.delivered > 0 ? (stats.opened / stats.delivered) * 100 : 0
    stats.clickRate = stats.opened > 0 ? (stats.clicked / stats.opened) * 100 : 0
    stats.bounceRate = stats.totalSent > 0 ? (stats.bounced / stats.totalSent) * 100 : 0
    
    return stats
  }

  // Placeholder methods for database operations
  async loadUserPreferences() {
    // Load from database
    console.log('Loading user preferences from database...')
  }

  async saveUserPreferences(userId, preferences) {
    // Save to database
    console.log('Saving user preferences to database...', { userId })
  }

  async getUserEmail(userId) {
    // Get user email from database
    return `user${userId}@example.com` // Placeholder
  }

  async saveDeliveryRecord(record) {
    // Save to database
    console.log('Saving delivery record to database...', record.messageId)
  }

  async updateDeliveryRecord(record) {
    // Update in database
    console.log('Updating delivery record in database...', record.messageId)
  }

  setupDeliveryTracking() {
    // Setup webhook endpoint for email provider callbacks
    console.log('Setting up delivery tracking...')
  }
}

// Email provider implementations (simplified)
class MockEmailProvider {
  constructor(config) {
    this.config = config
  }

  async initialize() {
    console.log('Mock email provider initialized')
  }

  async send(emailData) {
    console.log('Mock email sent:', emailData.subject, 'to', emailData.to)
    return {
      messageId: `mock_${Date.now()}`,
      deliveryId: `delivery_${Date.now()}`
    }
  }
}

class SendGridProvider {
  constructor(config) {
    this.config = config
  }

  async initialize() {
    // Initialize SendGrid client
    console.log('SendGrid provider initialized')
  }

  async send(emailData) {
    // Send via SendGrid API
    return {
      messageId: `sg_${Date.now()}`,
      deliveryId: `sg_delivery_${Date.now()}`
    }
  }
}

class SESProvider {
  constructor(config) {
    this.config = config
  }

  async initialize() {
    // Initialize AWS SES client
    console.log('SES provider initialized')
  }

  async send(emailData) {
    // Send via AWS SES
    return {
      messageId: `ses_${Date.now()}`,
      deliveryId: `ses_delivery_${Date.now()}`
    }
  }
}

class MailgunProvider {
  constructor(config) {
    this.config = config
  }

  async initialize() {
    // Initialize Mailgun client
    console.log('Mailgun provider initialized')
  }

  async send(emailData) {
    // Send via Mailgun API
    return {
      messageId: `mg_${Date.now()}`,
      deliveryId: `mg_delivery_${Date.now()}`
    }
  }
}

class SMTPProvider {
  constructor(config) {
    this.config = config
  }

  async initialize() {
    // Initialize SMTP client
    console.log('SMTP provider initialized')
  }

  async send(emailData) {
    // Send via SMTP
    return {
      messageId: `smtp_${Date.now()}`,
      deliveryId: `smtp_delivery_${Date.now()}`
    }
  }
}

export const emailNotificationService = new EmailNotificationService()
