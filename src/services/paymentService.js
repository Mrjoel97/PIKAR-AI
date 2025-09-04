/**
 * Payment Service
 * Comprehensive payment processing with Stripe integration
 */

 fix/stripe-client-safe-payments


import { supabase } from '@/lib/supabase'
 main
import { auditService } from './auditService'
fix/auth-register-routing-v2

main
import { tierService } from './tierService'
import { emailNotificationService } from './emailNotificationService'
import { environmentConfig } from '@/config/environment'

import { supabase } from '@/lib/supabase'

class PaymentService {
  constructor() {
    this.stripe = null
    this.webhookSecret = null
    this.isInitialized = false
    
    // Payment configuration
    const base = environmentConfig.baseUrl || environmentConfig.get('VITE_APP_BASE_URL', 'https://pikar-ai3.vercel.app')
    this.config = {
      currency: 'usd',
      successUrl: `${base}/billing/success`,
      cancelUrl: `${base}/billing/cancel`,
      webhookEndpoint: `${base}/api/webhooks/stripe`,
      
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
    // Client-safe no-op; server-side Stripe operations are handled by webhooks/edge functions
    this.isInitialized = true
    return true
  }

  /**
   * Verify Stripe connection
   */
  async verifyStripeConnection() {
    // Not applicable on client; verification happens server-side if needed
    return null
  }

  /**
   * Create customer in Stripe
   */
  async createCustomer() {
    // Not supported in client for Payment Links flow
    return null
  }

  /**
   * Create subscription checkout session
   */
  async createCheckoutSession(userId, tierId, billingPeriod = 'monthly', customerId = null) {
    try {
 fix/stripe-client-safe-payments
      // Client-safe: use Supabase payment links instead of Stripe SDK in the browser (domain base is pikar-ai3.vercel.app)

      // Client-safe: use Supabase payment links instead of Stripe SDK in the browser
 main
      const nameMap = { solopreneur: 'Solopreneur', startup: 'Startup', sme: 'SME' }
      const productName = nameMap[tierId]
      if (!productName) throw new Error(`Unsupported tier: ${tierId}`)

      const interval = billingPeriod === 'yearly' ? 'year' : 'month'

      fix/stripe-client-safe-payments
      const { data, error } = await supabase
        .from('billing_prices')
        .select('payment_link_url, interval, active, product:billing_products(name)')
        .eq('active', true)
        .eq('interval', interval)
        .limit(1)
        .maybeSingle()

      if (error) throw error
      if (!data?.payment_link_url || data?.product?.name !== productName) {
        // Fallback: query with explicit join filter
        const { data: rows, error: err2 } = await supabase
          .from('billing_prices')
          .select('payment_link_url, interval, active, product:billing_products(name)')
          .eq('active', true)
          .eq('interval', interval)
        if (err2) throw err2
        const row = (rows || []).find(r => r.product?.name === productName && !!r.payment_link_url)
        if (!row) throw new Error('No payment link configured for selected plan')
        await auditService.logAccess.payment('checkout_link_resolved', { userId, tierId, billingPeriod, via: 'fallback' })
        return { url: row.payment_link_url }
      }

 fix/remove-stripe-from-client
      // 1) Env-based fallback for payment links to support deployments without DB
      const envLinks = {
        solopreneur: {
          month: environmentConfig.get('VITE_PAYMENT_LINK_SOLO_MONTHLY', null),
          year: environmentConfig.get('VITE_PAYMENT_LINK_SOLO_YEARLY', null),
        },
        startup: {
          month: environmentConfig.get('VITE_PAYMENT_LINK_STARTUP_MONTHLY', null),
          year: environmentConfig.get('VITE_PAYMENT_LINK_STARTUP_YEARLY', null),
        },
        sme: {
          month: environmentConfig.get('VITE_PAYMENT_LINK_SME_MONTHLY', null),
          year: environmentConfig.get('VITE_PAYMENT_LINK_SME_YEARLY', null),
        },
      }
      const envUrl = envLinks[tierId]?.[interval]
      if (envUrl) {
        await auditService.logAccess.payment('checkout_link_resolved_env', { userId, tierId, billingPeriod })
        return { url: envUrl }
      }

      // 2) Supabase-driven lookup
      const { data, error } = await supabase
        .from('billing_prices')
        .select('payment_link_url, interval, active, product:billing_products(name)')
        .eq('active', true)
        .eq('interval', interval)
        .limit(1)
        .maybeSingle()

      if (error) throw error
      if (!data?.payment_link_url || data?.product?.name !== productName) {
        const { data: rows, error: err2 } = await supabase
          .from('billing_prices')
          .select('payment_link_url, interval, active, product:billing_products(name)')
          .eq('active', true)
          .eq('interval', interval)
        if (err2) throw err2
        const row = (rows || []).find(r => r.product?.name === productName && !!r.payment_link_url)
        if (!row) throw new Error('No payment link configured for selected plan')
        await auditService.logAccess.payment('checkout_link_resolved', { userId, tierId, billingPeriod, via: 'fallback' })
        return { url: row.payment_link_url }
      }

      const { data, error } = await supabase
        .from('billing_prices')
        .select('payment_link_url, interval, active, product:billing_products(name)')
        .eq('active', true)
        .eq('interval', interval)
        .limit(1)
        .maybeSingle()

      if (error) throw error
      if (!data?.payment_link_url || data?.product?.name !== productName) {
        const { data: rows, error: err2 } = await supabase
          .from('billing_prices')
          .select('payment_link_url, interval, active, product:billing_products(name)')
          .eq('active', true)
          .eq('interval', interval)
        if (err2) throw err2
        const row = (rows || []).find(r => r.product?.name === productName && !!r.payment_link_url)
        if (!row) throw new Error('No payment link configured for selected plan')
        await auditService.logAccess.payment('checkout_link_resolved', { userId, tierId, billingPeriod, via: 'fallback' })
        return { url: row.payment_link_url }
      }
main
 main

      await auditService.logAccess.payment('checkout_link_resolved', { userId, tierId, billingPeriod })
      return { url: data.payment_link_url }
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
fix/stripe-client-safe-payments
      // Client-safe fallback: send user to internal billing page

main
      const base = environmentConfig.baseUrl || environmentConfig.get('VITE_APP_BASE_URL', 'https://pikar-ai3.vercel.app')
      const url = returnUrl || `${base}/billing`
      await auditService.logAccess.payment('billing_portal_fallback', { customerId, url })
      return { url }
    } catch (error) {
      console.error('Failed to create portal session:', error)
      throw error
    }
  }

  /**
   * Handle successful checkout
   */
  async handleCheckoutSuccess() {
    // For Payment Links + webhooks, client does not confirm session; server updates state.
    return { success: true }
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
