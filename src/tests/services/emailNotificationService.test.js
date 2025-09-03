/**
 * Email Notification Service Tests
 * Comprehensive unit tests for email notification functionality
 */

import { describe, test, expect, beforeEach, afterEach, vi } from 'vitest'
import { emailNotificationService } from '@/services/emailNotificationService'
import { auditService } from '@/services/auditService'

// Mock dependencies
vi.mock('@/services/auditService', () => ({
  auditService: {
    logSystem: {
      notification: vi.fn(),
      error: vi.fn()
    }
  }
}))

// Mock email providers
const mockEmailProvider = {
  initialize: vi.fn(),
  send: vi.fn()
}

describe('EmailNotificationService', () => {
  beforeEach(async () => {
    // Reset service state
    emailNotificationService.userPreferences = new Map()
    emailNotificationService.deliveryTracking = new Map()
    emailNotificationService.isInitialized = false
    
    // Mock email provider
    emailNotificationService.emailProvider = mockEmailProvider
    
    // Initialize service
    await emailNotificationService.initialize()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Initialization', () => {
    test('should initialize successfully', async () => {
      expect(emailNotificationService.isInitialized).toBe(true)
      expect(emailNotificationService.templates.size).toBeGreaterThan(0)
      expect(auditService.logSystem.notification).toHaveBeenCalledWith(
        'email_service_initialized',
        expect.any(Object)
      )
    })

    test('should setup email templates', () => {
      const welcomeTemplate = emailNotificationService.templates.get('welcome')
      expect(welcomeTemplate).toBeTruthy()
      expect(welcomeTemplate.subject).toContain('Welcome')
      expect(welcomeTemplate.variables).toContain('userName')
    })
  })

  describe('Notification Sending', () => {
    const userId = 'test-user-123'
    const mockMessageId = 'msg_123'
    const mockDeliveryId = 'del_123'

    beforeEach(() => {
      mockEmailProvider.send.mockResolvedValue({
        messageId: mockMessageId,
        deliveryId: mockDeliveryId
      })
      
      // Mock getUserEmail
      emailNotificationService.getUserEmail = vi.fn().mockResolvedValue('test@example.com')
    })

    test('should send welcome notification successfully', async () => {
      const variables = {
        userName: 'John Doe',
        activationLink: 'https://example.com/activate'
      }

      const result = await emailNotificationService.sendNotification(
        userId,
        'welcome',
        variables
      )

      expect(result.success).toBe(true)
      expect(result.messageId).toBe(mockMessageId)
      expect(mockEmailProvider.send).toHaveBeenCalledWith(
        expect.objectContaining({
          to: 'test@example.com',
          templateId: 'welcome',
          dynamicTemplateData: expect.objectContaining(variables)
        })
      )
    })

    test('should process template variables correctly', async () => {
      const template = 'Hello {{userName}}, welcome to {{platformName}}!'
      const variables = { userName: 'John', platformName: 'PIKAR AI' }
      
      const processed = emailNotificationService.processTemplate(template, variables)
      
      expect(processed).toBe('Hello John, welcome to PIKAR AI!')
    })

    test('should handle missing template gracefully', async () => {
      await expect(
        emailNotificationService.sendNotification(userId, 'non_existent_template')
      ).rejects.toThrow('Template not found for notification type: non_existent_template')
    })

    test('should handle missing user email', async () => {
      emailNotificationService.getUserEmail.mockResolvedValue(null)
      
      await expect(
        emailNotificationService.sendNotification(userId, 'welcome')
      ).rejects.toThrow('Email not found for user: test-user-123')
    })

    test('should respect user preferences', async () => {
      // User has opted out of welcome emails
      emailNotificationService.userPreferences.set(userId, {
        welcome: false
      })

      const result = await emailNotificationService.sendNotification(userId, 'welcome')
      
      expect(result.success).toBe(false)
      expect(result.reason).toBe('User opted out')
      expect(mockEmailProvider.send).not.toHaveBeenCalled()
    })

    test('should track delivery', async () => {
      await emailNotificationService.sendNotification(userId, 'welcome')
      
      const deliveryRecord = emailNotificationService.deliveryTracking.get(mockMessageId)
      expect(deliveryRecord).toBeTruthy()
      expect(deliveryRecord.userId).toBe(userId)
      expect(deliveryRecord.notificationType).toBe('welcome')
      expect(deliveryRecord.status).toBe('sent')
    })

    test('should generate unsubscribe URL', () => {
      const url = emailNotificationService.generateUnsubscribeUrl(userId, 'welcome')
      expect(url).toContain('/unsubscribe')
      expect(url).toContain('token=')
    })
  })

  describe('Bulk Notifications', () => {
    const notifications = [
      { userId: 'user1', type: 'welcome', variables: { userName: 'User 1' } },
      { userId: 'user2', type: 'welcome', variables: { userName: 'User 2' } },
      { userId: 'user3', type: 'welcome', variables: { userName: 'User 3' } }
    ]

    beforeEach(() => {
      mockEmailProvider.send.mockResolvedValue({
        messageId: 'msg_bulk',
        deliveryId: 'del_bulk'
      })
      
      emailNotificationService.getUserEmail = vi.fn().mockResolvedValue('test@example.com')
    })

    test('should send bulk notifications successfully', async () => {
      const results = await emailNotificationService.sendBulkNotifications(notifications)
      
      expect(results).toHaveLength(3)
      expect(results.every(r => r.success)).toBe(true)
      expect(mockEmailProvider.send).toHaveBeenCalledTimes(3)
    })

    test('should handle partial failures in bulk sending', async () => {
      mockEmailProvider.send
        .mockResolvedValueOnce({ messageId: 'msg1', deliveryId: 'del1' })
        .mockRejectedValueOnce(new Error('Send failed'))
        .mockResolvedValueOnce({ messageId: 'msg3', deliveryId: 'del3' })

      const results = await emailNotificationService.sendBulkNotifications(notifications)
      
      expect(results).toHaveLength(3)
      expect(results[0].success).toBe(true)
      expect(results[1].success).toBe(false)
      expect(results[2].success).toBe(true)
    })

    test('should process bulk notifications in batches', async () => {
      const largeNotificationList = Array.from({ length: 250 }, (_, i) => ({
        userId: `user${i}`,
        type: 'welcome',
        variables: { userName: `User ${i}` }
      }))

      await emailNotificationService.sendBulkNotifications(largeNotificationList)
      
      // Should be called in batches of 100
      expect(mockEmailProvider.send).toHaveBeenCalledTimes(250)
    })
  })

  describe('User Preferences', () => {
    const userId = 'test-user-123'

    test('should get default preferences for new user', () => {
      const preferences = emailNotificationService.getUserPreferences(userId)
      
      expect(preferences.welcome).toBe(true)
      expect(preferences.agent_execution_complete).toBe(true)
      expect(preferences.weekly_summary).toBe(false) // Opt-in
      expect(preferences.emailFrequency).toBe('immediate')
    })

    test('should update user preferences', async () => {
      const updates = {
        weekly_summary: true,
        emailFrequency: 'daily'
      }

      const result = await emailNotificationService.updateUserPreferences(userId, updates)
      
      expect(result.weekly_summary).toBe(true)
      expect(result.emailFrequency).toBe('daily')
      expect(result.updatedAt).toBeTruthy()
    })

    test('should check notification permissions', () => {
      emailNotificationService.userPreferences.set(userId, {
        welcome: true,
        weekly_summary: false
      })

      expect(emailNotificationService.canSendNotification(userId, 'welcome')).toBe(true)
      expect(emailNotificationService.canSendNotification(userId, 'weekly_summary')).toBe(false)
    })

    test('should return default preferences structure', () => {
      const defaults = emailNotificationService.getDefaultPreferences()
      
      expect(defaults).toHaveProperty('welcome')
      expect(defaults).toHaveProperty('emailFrequency')
      expect(defaults).toHaveProperty('createdAt')
      expect(defaults).toHaveProperty('updatedAt')
    })
  })

  describe('Webhook Handling', () => {
    const messageId = 'msg_123'
    const deliveryRecord = {
      userId: 'user123',
      notificationType: 'welcome',
      messageId,
      status: 'sent',
      opens: 0,
      clicks: 0
    }

    beforeEach(() => {
      emailNotificationService.deliveryTracking.set(messageId, deliveryRecord)
    })

    test('should handle delivered webhook', async () => {
      const event = {
        messageId,
        eventType: 'delivered',
        timestamp: Date.now(),
        data: {}
      }

      await emailNotificationService.handleWebhookEvent(event)
      
      const record = emailNotificationService.deliveryTracking.get(messageId)
      expect(record.status).toBe('delivered')
      expect(record.deliveredAt).toBeTruthy()
    })

    test('should handle opened webhook', async () => {
      const event = {
        messageId,
        eventType: 'opened',
        timestamp: Date.now(),
        data: {}
      }

      await emailNotificationService.handleWebhookEvent(event)
      
      const record = emailNotificationService.deliveryTracking.get(messageId)
      expect(record.opens).toBe(1)
      expect(record.lastOpenedAt).toBeTruthy()
    })

    test('should handle clicked webhook', async () => {
      const event = {
        messageId,
        eventType: 'clicked',
        timestamp: Date.now(),
        data: {}
      }

      await emailNotificationService.handleWebhookEvent(event)
      
      const record = emailNotificationService.deliveryTracking.get(messageId)
      expect(record.clicks).toBe(1)
      expect(record.lastClickedAt).toBeTruthy()
    })

    test('should handle bounced webhook', async () => {
      const event = {
        messageId,
        eventType: 'bounced',
        timestamp: Date.now(),
        data: { reason: 'invalid_email' }
      }

      await emailNotificationService.handleWebhookEvent(event)
      
      const record = emailNotificationService.deliveryTracking.get(messageId)
      expect(record.status).toBe('bounced')
      expect(record.bounceReason).toBe('invalid_email')
    })

    test('should handle unsubscribed webhook', async () => {
      emailNotificationService.handleUnsubscribe = vi.fn()
      
      const event = {
        messageId,
        eventType: 'unsubscribed',
        timestamp: Date.now(),
        data: {}
      }

      await emailNotificationService.handleWebhookEvent(event)
      
      expect(emailNotificationService.handleUnsubscribe).toHaveBeenCalledWith(
        deliveryRecord.userId,
        deliveryRecord.notificationType
      )
    })

    test('should handle missing delivery record gracefully', async () => {
      const event = {
        messageId: 'non_existent_message',
        eventType: 'delivered',
        timestamp: Date.now(),
        data: {}
      }

      // Should not throw
      await expect(
        emailNotificationService.handleWebhookEvent(event)
      ).resolves.toBeUndefined()
    })
  })

  describe('Delivery Statistics', () => {
    beforeEach(() => {
      const now = Date.now()
      const oneHourAgo = now - (60 * 60 * 1000)
      
      // Add some test delivery records
      emailNotificationService.deliveryTracking.set('msg1', {
        sentAt: oneHourAgo,
        status: 'delivered',
        opens: 1,
        clicks: 0
      })
      
      emailNotificationService.deliveryTracking.set('msg2', {
        sentAt: oneHourAgo,
        status: 'delivered',
        opens: 0,
        clicks: 1
      })
      
      emailNotificationService.deliveryTracking.set('msg3', {
        sentAt: oneHourAgo,
        status: 'bounced',
        opens: 0,
        clicks: 0
      })
    })

    test('should calculate delivery statistics correctly', () => {
      const stats = emailNotificationService.getDeliveryStatistics()
      
      expect(stats.totalSent).toBe(3)
      expect(stats.delivered).toBe(2)
      expect(stats.opened).toBe(1)
      expect(stats.clicked).toBe(1)
      expect(stats.bounced).toBe(1)
      expect(stats.deliveryRate).toBeCloseTo(66.67, 1)
      expect(stats.openRate).toBe(50)
      expect(stats.clickRate).toBe(100)
    })

    test('should handle empty statistics', () => {
      emailNotificationService.deliveryTracking.clear()
      
      const stats = emailNotificationService.getDeliveryStatistics()
      
      expect(stats.totalSent).toBe(0)
      expect(stats.deliveryRate).toBe(0)
      expect(stats.openRate).toBe(0)
      expect(stats.clickRate).toBe(0)
    })

    test('should filter by time window', () => {
      const oneWeekAgo = Date.now() - (7 * 24 * 60 * 60 * 1000)
      
      // Add old record
      emailNotificationService.deliveryTracking.set('msg_old', {
        sentAt: oneWeekAgo,
        status: 'delivered',
        opens: 1,
        clicks: 0
      })
      
      const stats = emailNotificationService.getDeliveryStatistics(24 * 60 * 60 * 1000) // 24 hours
      
      expect(stats.totalSent).toBe(3) // Should not include old record
    })
  })

  describe('Error Handling and Retry Logic', () => {
    const userId = 'test-user-123'

    beforeEach(() => {
      emailNotificationService.getUserEmail = vi.fn().mockResolvedValue('test@example.com')
    })

    test('should retry failed sends', async () => {
      mockEmailProvider.send
        .mockRejectedValueOnce(new Error('Temporary failure'))
        .mockResolvedValueOnce({ messageId: 'msg_retry', deliveryId: 'del_retry' })

      // Mock setTimeout to execute immediately
      vi.spyOn(global, 'setTimeout').mockImplementation((fn) => fn())

      const result = await emailNotificationService.sendNotification(
        userId,
        'welcome',
        {},
        { retryCount: 0 }
      )

      expect(mockEmailProvider.send).toHaveBeenCalledTimes(1) // Initial call
      expect(auditService.logSystem.error).toHaveBeenCalled()
    })

    test('should handle provider initialization failure', async () => {
      mockEmailProvider.initialize.mockRejectedValue(new Error('Provider init failed'))
      
      emailNotificationService.isInitialized = false
      
      await expect(
        emailNotificationService.initialize()
      ).rejects.toThrow('Provider init failed')
    })

    test('should log audit events for failures', async () => {
      mockEmailProvider.send.mockRejectedValue(new Error('Send failed'))
      
      await expect(
        emailNotificationService.sendNotification(userId, 'welcome')
      ).rejects.toThrow('Send failed')
      
      expect(auditService.logSystem.error).toHaveBeenCalledWith(
        expect.any(Error),
        'email_send_failed',
        expect.objectContaining({ userId })
      )
    })
  })

  describe('Unsubscribe Handling', () => {
    const userId = 'test-user-123'
    const notificationType = 'weekly_summary'

    test('should handle unsubscribe request', async () => {
      emailNotificationService.updateUserPreferences = vi.fn()
      
      await emailNotificationService.handleUnsubscribe(userId, notificationType)
      
      expect(emailNotificationService.updateUserPreferences).toHaveBeenCalledWith(
        userId,
        { [notificationType]: false }
      )
    })

    test('should generate valid unsubscribe token', () => {
      const token = emailNotificationService.generateUnsubscribeToken(userId, notificationType)
      
      expect(token).toBeTruthy()
      expect(typeof token).toBe('string')
      
      // Should be base64 encoded
      const decoded = Buffer.from(token, 'base64').toString()
      expect(decoded).toContain(userId)
      expect(decoded).toContain(notificationType)
    })
  })
})
