/**
 * Payment Service
 * Comprehensive payment processing with Stripe integration
 */

import Stripe from 'stripe'
import { auditService } from './auditService'
import { loggingService } from './loggingService'
import { tierService } from './tierService'
import { emailNotificationService } from './emailNotificationService'
import { environmentConfig } from '@/config/environment'

class PaymentService {
  constructor() {
    this.stripe = null
    this.webhookSecret = null
    this.isInitialized = false
    
    // Payment configuration
    this.config = {
      currency: 'usd',
      successUrl: `${environmentConfig.baseUrl}/billing/success`,
      cancelUrl: `${environmentConfig.baseUrl}/billing/cancel`,
      webhookEndpoint: `${environmentConfig.baseUrl}/api/webhooks/stripe`,
      
      // Subscription settings
      trialPeriodDays: 7,
      gracePeriodDays: 3,

      // Pricing (in cents) - PIKAR AI Blueprint Compliant
      pricing: {
        solopreneur: {
          monthly: 9900, // $99.00
          yearly: 99000  // $990.00 (2 months free)
        },
        startup: {
          monthly: 29700, // $297.00
          yearly: 297000  // $2970.00 (2 months free)
        },
        sme: {
          monthly: 59700, // $597.00
          yearly: 597000  // $5970.00 (2 months free)
        },
        enterprise: {
          // Contact sales - handled separately
          monthly: 0,
          yearly: 0
        }
      }
    }
    
    // Stripe product and price IDs (would be set from environment)
    this.stripeProducts = {
      solopreneur: {
        monthly: environmentConfig.stripe?.solopreneurPriceMonthly,
        yearly: environmentConfig.stripe?.solopreneurPriceYearly
      },
      startup: {
        monthly: environmentConfig.stripe?.startupPriceMonthly,
        yearly: environmentConfig.stripe?.startupPriceYearly
      },
      sme: {
        monthly: environmentConfig.stripe?.smePriceMonthly,
        yearly: environmentConfig.stripe?.smePriceYearly
      },
      enterprise: {
        // Enterprise is contact sales - no Stripe products
        monthly: null,
        yearly: null
      }
    }
  }

  /**
   * Initialize payment service
   */
  async initialize() {
    try {
      console.log('💳 Initializing Payment Service...')
      
      if (!environmentConfig.stripe?.secretKey) {
        throw new Error('Stripe secret key not configured')
      }
      
      this.stripe = new Stripe(environmentConfig.stripe.secretKey, {
        apiVersion: '2023-10-16'
      })
      
      this.webhookSecret = environmentConfig.stripe.webhookSecret
      
      // Verify Stripe connection
      await this.verifyStripeConnection()
      
      // Setup products and prices if needed
      await this.setupStripeProducts()
      
      this.isInitialized = true
      
      console.log('✅ Payment Service initialized successfully')
      
      await auditService.logSystem.payment('payment_service_initialized', {
        provider: 'stripe',
        currency: this.config.currency
      })
      
    } catch (error) {
      console.error('❌ Payment Service initialization failed:', error)
      throw error
    }
  }

  /**
   * Verify Stripe connection
   */
  async verifyStripeConnection() {
    try {
      const account = await this.stripe.accounts.retrieve()
      console.log('Stripe account verified:', account.id)
      return account
    } catch (error) {
      throw new Error(`Stripe connection failed: ${error.message}`)
    }
  }

  /**
   * Create customer in Stripe
   */
  async createCustomer(userId, userEmail, userName) {
    try {
      const customer = await this.stripe.customers.create({
        email: userEmail,
        name: userName,
        metadata: {
          userId: userId,
          source: 'pikar-ai'
        }
      })
      
      await auditService.logAccess.payment('stripe_customer_created', {
        userId,
        customerId: customer.id,
        email: userEmail
      })
      
      return customer
    } catch (error) {
      console.error('Failed to create Stripe customer:', error)
      throw error
    }
  }

  /**
   * Create subscription checkout session
   */
  async createCheckoutSession(userId, tierId, billingPeriod = 'monthly', customerId = null) {
    try {
      if (!this.stripeProducts[tierId]?.[billingPeriod]) {
        throw new Error(`Price not found for ${tierId} ${billingPeriod}`)
      }
      
      const priceId = this.stripeProducts[tierId][billingPeriod]
      
      // Create or get customer
      let customer = customerId
      if (!customer) {
        const user = await this.getUserById(userId) // Would get from user service
        const stripeCustomer = await this.createCustomer(userId, user.email, user.displayName)
        customer = stripeCustomer.id
      }
      
      const sessionConfig = {
        customer: customer,
        payment_method_types: ['card'],
        line_items: [{
          price: priceId,
          quantity: 1
        }],
        mode: 'subscription',
        success_url: `${this.config.successUrl}?session_id={CHECKOUT_SESSION_ID}`,
        cancel_url: this.config.cancelUrl,
        
        // Subscription settings
        subscription_data: {
          trial_period_days: this.config.trialPeriodDays,
          metadata: {
            userId: userId,
            tierId: tierId,
            billingPeriod: billingPeriod
          }
        },
        
        // Customer portal
        customer_update: {
          address: 'auto',
          name: 'auto'
        },
        
        // Metadata
        metadata: {
          userId: userId,
          tierId: tierId,
          billingPeriod: billingPeriod
        }
      }
      
      const session = await this.stripe.checkout.sessions.create(sessionConfig)
      
      await auditService.logAccess.payment('checkout_session_created', {
        userId,
        sessionId: session.id,
        tierId,
        billingPeriod,
        amount: this.config.pricing[tierId][billingPeriod]
      })
      
      return session
    } catch (error) {
      console.error('Failed to create checkout session:', error)
      throw error
    }
  }

  /**
   * Create customer portal session
   */
  async createPortalSession(customerId, returnUrl = null) {
    try {
      const session = await this.stripe.billingPortal.sessions.create({
        customer: customerId,
        return_url: returnUrl || `${environmentConfig.baseUrl}/settings/billing`
      })
      
      return session
    } catch (error) {
      console.error('Failed to create portal session:', error)
      throw error
    }
  }

  /**
   * Handle successful checkout
   */
  async handleCheckoutSuccess(sessionId) {
    try {
      const session = await this.stripe.checkout.sessions.retrieve(sessionId, {
        expand: ['subscription', 'customer']
      })
      
      if (session.payment_status === 'paid') {
        const userId = session.metadata.userId
        const tierId = session.metadata.tierId
        const billingPeriod = session.metadata.billingPeriod
        
        // Update user tier
        await tierService.setUserTier(userId, tierId, {
          customerId: session.customer.id,
          subscriptionId: session.subscription.id,
          billingPeriod: billingPeriod,
          paymentMethod: 'stripe',
          status: 'active'
        })
        
        // Send confirmation email
        await emailNotificationService.sendNotification(userId, 'tier_upgraded', {
          userName: session.customer.name,
          tierName: tierId.charAt(0).toUpperCase() + tierId.slice(1),
          billingAmount: (session.amount_total / 100).toFixed(2),
          billingPeriod: billingPeriod,
          nextBillingDate: new Date(session.subscription.current_period_end * 1000).toLocaleDateString()
        })
        
        await auditService.logAccess.payment('subscription_activated', {
          userId,
          subscriptionId: session.subscription.id,
          tierId,
          amount: session.amount_total
        })
        
        return {
          success: true,
          subscriptionId: session.subscription.id,
          customerId: session.customer.id
        }
      }
      
      return { success: false, reason: 'Payment not completed' }
    } catch (error) {
      console.error('Failed to handle checkout success:', error)
      throw error
    }
  }

  /**
   * Cancel subscription
   */
  async cancelSubscription(subscriptionId, userId, reason = 'user_requested') {
    try {
      const subscription = await this.stripe.subscriptions.update(subscriptionId, {
        cancel_at_period_end: true,
        metadata: {
          cancellation_reason: reason,
          cancelled_by: userId
        }
      })
      
      await auditService.logAccess.payment('subscription_cancelled', {
        userId,
        subscriptionId,
        reason,
        cancelAt: subscription.cancel_at
      })
      
      // Send cancellation email
      await emailNotificationService.sendNotification(userId, 'subscription_cancelled', {
        cancelDate: new Date(subscription.cancel_at * 1000).toLocaleDateString()
      })
      
      return subscription
    } catch (error) {
      console.error('Failed to cancel subscription:', error)
      throw error
    }
  }

  /**
   * Reactivate subscription
   */
  async reactivateSubscription(subscriptionId, userId) {
    try {
      const subscription = await this.stripe.subscriptions.update(subscriptionId, {
        cancel_at_period_end: false,
        metadata: {
          reactivated_by: userId,
          reactivated_at: Math.floor(Date.now() / 1000)
        }
      })
      
      await auditService.logAccess.payment('subscription_reactivated', {
        userId,
        subscriptionId
      })
      
      return subscription
    } catch (error) {
      console.error('Failed to reactivate subscription:', error)
      throw error
    }
  }

  /**
   * Handle webhook events
   */
  async handleWebhook(payload, signature) {
    try {
      const event = this.stripe.webhooks.constructEvent(
        payload,
        signature,
        this.webhookSecret
      )
      
      console.log('Processing Stripe webhook:', event.type)
      
      switch (event.type) {
        case 'checkout.session.completed':
          await this.handleCheckoutCompleted(event.data.object)
          break
          
        case 'invoice.payment_succeeded':
          await this.handlePaymentSucceeded(event.data.object)
          break
          
        case 'invoice.payment_failed':
          await this.handlePaymentFailed(event.data.object)
          break
          
        case 'customer.subscription.updated':
          await this.handleSubscriptionUpdated(event.data.object)
          break
          
        case 'customer.subscription.deleted':
          await this.handleSubscriptionDeleted(event.data.object)
          break
          
        case 'invoice.upcoming':
          await this.handleUpcomingInvoice(event.data.object)
          break
          
        default:
          console.log('Unhandled webhook event:', event.type)
      }
      
      await auditService.logSystem.payment('webhook_processed', {
        eventType: event.type,
        eventId: event.id
      })
      
      return { received: true }
    } catch (error) {
      console.error('Webhook processing failed:', error)
      throw error
    }
  }

  /**
   * Handle checkout completed
   */
  async handleCheckoutCompleted(session) {
    if (session.mode === 'subscription') {
      await this.handleCheckoutSuccess(session.id)
    }
  }

  /**
   * Handle payment succeeded
   */
  async handlePaymentSucceeded(invoice) {
    const subscriptionId = invoice.subscription
    const customerId = invoice.customer
    
    if (subscriptionId) {
      const subscription = await this.stripe.subscriptions.retrieve(subscriptionId)
      const userId = subscription.metadata.userId
      
      if (userId) {
        await emailNotificationService.sendNotification(userId, 'payment_successful', {
          amount: (invoice.amount_paid / 100).toFixed(2),
          invoiceUrl: invoice.hosted_invoice_url,
          nextBillingDate: new Date(subscription.current_period_end * 1000).toLocaleDateString()
        })
      }
    }
  }

  /**
   * Handle payment failed
   */
  async handlePaymentFailed(invoice) {
    const subscriptionId = invoice.subscription
    
    if (subscriptionId) {
      const subscription = await this.stripe.subscriptions.retrieve(subscriptionId)
      const userId = subscription.metadata.userId
      
      if (userId) {
        await emailNotificationService.sendNotification(userId, 'payment_failed', {
          amount: (invoice.amount_due / 100).toFixed(2),
          invoiceUrl: invoice.hosted_invoice_url,
          retryDate: new Date(invoice.next_payment_attempt * 1000).toLocaleDateString()
        })
        
        // Handle dunning management
        await this.handleDunningManagement(userId, invoice)
      }
    }
  }

  /**
   * Handle subscription updated
   */
  async handleSubscriptionUpdated(subscription) {
    const userId = subscription.metadata.userId
    
    if (userId) {
      // Update tier if plan changed
      const newTierId = this.getTierFromPriceId(subscription.items.data[0].price.id)
      if (newTierId) {
        await tierService.setUserTier(userId, newTierId, {
          subscriptionId: subscription.id,
          status: subscription.status
        })
      }
    }
  }

  /**
   * Handle subscription deleted
   */
  async handleSubscriptionDeleted(subscription) {
    const userId = subscription.metadata.userId
    
    if (userId) {
      // Downgrade to free tier
      await tierService.setUserTier(userId, 'FREE')
      
      await emailNotificationService.sendNotification(userId, 'subscription_ended', {
        tierName: 'Free',
        endDate: new Date(subscription.ended_at * 1000).toLocaleDateString()
      })
    }
  }

  /**
   * Handle upcoming invoice
   */
  async handleUpcomingInvoice(invoice) {
    const subscriptionId = invoice.subscription
    
    if (subscriptionId) {
      const subscription = await this.stripe.subscriptions.retrieve(subscriptionId)
      const userId = subscription.metadata.userId
      
      if (userId) {
        await emailNotificationService.sendNotification(userId, 'billing_reminder', {
          amount: (invoice.amount_due / 100).toFixed(2),
          dueDate: new Date(invoice.due_date * 1000).toLocaleDateString()
        })
      }
    }
  }

  /**
   * Handle dunning management
   */
  async handleDunningManagement(userId, invoice) {
    const attemptCount = invoice.attempt_count
    
    if (attemptCount >= 3) {
      // Suspend user after 3 failed attempts
      await this.suspendUserForNonPayment(userId)
    }
  }

  /**
   * Suspend user for non-payment
   */
  async suspendUserForNonPayment(userId) {
    // This would integrate with user management service
    console.log(`Suspending user ${userId} for non-payment`)
    
    await auditService.logAccess.payment('user_suspended_nonpayment', {
      userId,
      reason: 'payment_failed_multiple_attempts'
    })
  }

  /**
   * Get tier from Stripe price ID
   */
  getTierFromPriceId(priceId) {
    for (const [tier, prices] of Object.entries(this.stripeProducts)) {
      if (prices.monthly === priceId || prices.yearly === priceId) {
        return tier.toUpperCase()
      }
    }
    return null
  }

  /**
   * Setup Stripe products and prices
   */
  async setupStripeProducts() {
    // This would create products and prices in Stripe if they don't exist
    // For production, these should be created manually or via Stripe CLI
    console.log('Stripe products configured')
  }

  /**
   * Get payment statistics
   */
  async getPaymentStatistics(timeWindow = 30) {
    try {
      const startDate = Math.floor((Date.now() - (timeWindow * 24 * 60 * 60 * 1000)) / 1000)
      
      const charges = await this.stripe.charges.list({
        created: { gte: startDate },
        limit: 100
      })
      
      const subscriptions = await this.stripe.subscriptions.list({
        created: { gte: startDate },
        limit: 100
      })
      
      const stats = {
        totalRevenue: charges.data.reduce((sum, charge) => sum + charge.amount, 0) / 100,
        totalCharges: charges.data.length,
        successfulCharges: charges.data.filter(c => c.status === 'succeeded').length,
        newSubscriptions: subscriptions.data.length,
        activeSubscriptions: subscriptions.data.filter(s => s.status === 'active').length,
        timeWindow: `${timeWindow} days`
      }
      
      return stats
    } catch (error) {
      console.error('Failed to get payment statistics:', error)
      throw error
    }
  }

  // Placeholder method - would integrate with user service
  async getUserById(userId) {
    return {
      id: userId,
      email: `user${userId}@example.com`,
      displayName: `User ${userId}`
    }
  }
}

export const paymentService = new PaymentService()
export default paymentService
