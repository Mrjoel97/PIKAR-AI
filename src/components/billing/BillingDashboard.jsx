/**
 * Billing Dashboard Component
 * Complete billing management interface with Stripe integration
 */

import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Separator } from '@/components/ui/separator'
import { 
  CreditCard, 
  Calendar, 
  DollarSign, 
  Download, 
  Settings,
  AlertCircle,
  CheckCircle,
  Clock,
  TrendingUp,
  Receipt,
  Shield
} from 'lucide-react'
import { useTier } from '@/hooks/useTier'
import { useAuth } from '@/contexts/AuthContext'
import { paymentService } from '@/services/paymentService'
import { toast } from 'sonner'
import { formatDistanceToNow } from 'date-fns'

export default function BillingDashboard() {
  const { user } = useAuth()
  const { currentTier, usage, getUsagePercentage } = useTier()
  const [billingInfo, setBillingInfo] = useState(null)
  const [invoices, setInvoices] = useState([])
  const [paymentMethods, setPaymentMethods] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [isProcessing, setIsProcessing] = useState(false)

  useEffect(() => {
    loadBillingData()
  }, [user?.id])

  const loadBillingData = async () => {
    if (!user?.id) return

    try {
      setIsLoading(true)
      
      // Load billing information
      const billing = await getBillingInfo(user.id)
      setBillingInfo(billing)
      
      // Load invoices
      const invoiceData = await getInvoices(user.id)
      setInvoices(invoiceData)
      
      // Load payment methods
      const paymentData = await getPaymentMethods(user.id)
      setPaymentMethods(paymentData)
      
    } catch (error) {
      console.error('Failed to load billing data:', error)
      toast.error('Failed to load billing information')
    } finally {
      setIsLoading(false)
    }
  }

  const handleUpgrade = async (tierId, billingPeriod = 'monthly') => {
    try {
      setIsProcessing(true)
      
      const session = await paymentService.createCheckoutSession(
        user.id,
        tierId,
        billingPeriod,
        billingInfo?.customerId
      )
      
      // Redirect to Stripe Checkout
      window.location.href = session.url
      
    } catch (error) {
      console.error('Failed to create checkout session:', error)
      toast.error('Failed to start upgrade process')
    } finally {
      setIsProcessing(false)
    }
  }

  const handleManageBilling = async () => {
    try {
      setIsProcessing(true)
      
      if (!billingInfo?.customerId) {
        toast.error('No billing information found')
        return
      }
      
      const session = await paymentService.createPortalSession(billingInfo.customerId)
      window.location.href = session.url
      
    } catch (error) {
      console.error('Failed to open billing portal:', error)
      toast.error('Failed to open billing management')
    } finally {
      setIsProcessing(false)
    }
  }

  const handleCancelSubscription = async () => {
    if (!billingInfo?.subscriptionId) return
    
    const confirmed = window.confirm(
      'Are you sure you want to cancel your subscription? You will retain access until the end of your current billing period.'
    )
    
    if (!confirmed) return
    
    try {
      setIsProcessing(true)
      
      await paymentService.cancelSubscription(billingInfo.subscriptionId, user.id)
      toast.success('Subscription cancelled successfully')
      
      // Reload billing data
      await loadBillingData()
      
    } catch (error) {
      console.error('Failed to cancel subscription:', error)
      toast.error('Failed to cancel subscription')
    } finally {
      setIsProcessing(false)
    }
  }

  const getStatusBadge = (status) => {
    const statusConfig = {
      active: { color: 'bg-green-100 text-green-800', icon: CheckCircle, text: 'Active' },
      trialing: { color: 'bg-blue-100 text-blue-800', icon: Clock, text: 'Trial' },
      past_due: { color: 'bg-orange-100 text-orange-800', icon: AlertCircle, text: 'Past Due' },
      canceled: { color: 'bg-gray-100 text-gray-800', icon: AlertCircle, text: 'Cancelled' },
      unpaid: { color: 'bg-red-100 text-red-800', icon: AlertCircle, text: 'Unpaid' }
    }
    
    const config = statusConfig[status] || statusConfig.active
    const IconComponent = config.icon
    
    return (
      <Badge className={config.color}>
        <IconComponent className="w-3 h-3 mr-1" />
        {config.text}
      </Badge>
    )
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-32 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Billing & Subscription</h1>
          <p className="text-gray-600">Manage your subscription and billing information</p>
        </div>
        
        <Button 
          onClick={handleManageBilling}
          disabled={isProcessing || !billingInfo?.customerId}
        >
          <Settings className="w-4 h-4 mr-2" />
          Manage Billing
        </Button>
      </div>

      {/* Current Plan */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CreditCard className="w-5 h-5" />
            Current Plan
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-xl font-semibold">{currentTier?.name || 'Free'}</h3>
              <p className="text-gray-600">
                {currentTier?.price > 0 
                  ? `$${currentTier.price}/${currentTier.billingPeriod?.slice(0, -2) || 'month'}`
                  : 'No cost'
                }
              </p>
            </div>
            
            <div className="flex items-center gap-2">
              {billingInfo?.status && getStatusBadge(billingInfo.status)}
              {currentTier?.id === 'free' && (
                <Button onClick={() => handleUpgrade('pro')}>
                  <TrendingUp className="w-4 h-4 mr-2" />
                  Upgrade
                </Button>
              )}
            </div>
          </div>
          
          {billingInfo?.nextBillingDate && (
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <Calendar className="w-4 h-4" />
              Next billing: {new Date(billingInfo.nextBillingDate).toLocaleDateString()}
            </div>
          )}
          
          {billingInfo?.cancelAtPeriodEnd && (
            <div className="p-3 bg-orange-50 border border-orange-200 rounded-lg">
              <div className="flex items-center gap-2 text-orange-800">
                <AlertCircle className="w-4 h-4" />
                <span className="font-medium">Subscription Ending</span>
              </div>
              <p className="text-sm text-orange-700 mt-1">
                Your subscription will end on {new Date(billingInfo.currentPeriodEnd).toLocaleDateString()}
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Usage Overview */}
      <Card>
        <CardHeader>
          <CardTitle>Usage Overview</CardTitle>
          <CardDescription>Current usage for this billing period</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {usage && Object.entries(currentTier?.limits || {}).map(([key, limit]) => {
            const currentUsage = usage[key] || 0
            const percentage = getUsagePercentage(key)
            
            if (limit === 'unlimited') return null
            
            return (
              <div key={key} className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="capitalize">{key.replace(/([A-Z])/g, ' $1').toLowerCase()}</span>
                  <span>{currentUsage} / {limit}</span>
                </div>
                <Progress value={percentage} className="h-2" />
                {percentage >= 80 && (
                  <p className="text-xs text-orange-600">
                    You're approaching your limit. Consider upgrading for more capacity.
                  </p>
                )}
              </div>
            )
          })}
        </CardContent>
      </Card>

      {/* Upgrade Options */}
      {currentTier?.id === 'free' && (
        <Card>
          <CardHeader>
            <CardTitle>Upgrade Your Plan</CardTitle>
            <CardDescription>Unlock more features and higher limits</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-4 border rounded-lg">
                <h4 className="font-semibold">Pro Plan</h4>
                <p className="text-2xl font-bold">$49<span className="text-sm font-normal">/month</span></p>
                <ul className="text-sm text-gray-600 mt-2 space-y-1">
                  <li>• 1,000 monthly executions</li>
                  <li>• Advanced analytics</li>
                  <li>• Priority support</li>
                  <li>• Custom integrations</li>
                </ul>
                <Button 
                  className="w-full mt-4" 
                  onClick={() => handleUpgrade('pro')}
                  disabled={isProcessing}
                >
                  Upgrade to Pro
                </Button>
              </div>
              
              <div className="p-4 border rounded-lg">
                <h4 className="font-semibold">Enterprise Plan</h4>
                <p className="text-2xl font-bold">$199<span className="text-sm font-normal">/month</span></p>
                <ul className="text-sm text-gray-600 mt-2 space-y-1">
                  <li>• Unlimited executions</li>
                  <li>• White-label options</li>
                  <li>• Dedicated support</li>
                  <li>• Custom agents</li>
                </ul>
                <Button 
                  className="w-full mt-4" 
                  onClick={() => handleUpgrade('enterprise')}
                  disabled={isProcessing}
                >
                  Upgrade to Enterprise
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Payment Methods */}
      {paymentMethods.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="w-5 h-5" />
              Payment Methods
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {paymentMethods.map((method, index) => (
                <div key={index} className="flex items-center justify-between p-3 border rounded-lg">
                  <div className="flex items-center gap-3">
                    <CreditCard className="w-5 h-5 text-gray-400" />
                    <div>
                      <p className="font-medium">**** **** **** {method.last4}</p>
                      <p className="text-sm text-gray-600">{method.brand} • Expires {method.expMonth}/{method.expYear}</p>
                    </div>
                  </div>
                  {method.isDefault && (
                    <Badge variant="outline">Default</Badge>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Recent Invoices */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Receipt className="w-5 h-5" />
            Recent Invoices
          </CardTitle>
        </CardHeader>
        <CardContent>
          {invoices.length === 0 ? (
            <p className="text-gray-600 text-center py-4">No invoices found</p>
          ) : (
            <div className="space-y-3">
              {invoices.map((invoice, index) => (
                <div key={index} className="flex items-center justify-between p-3 border rounded-lg">
                  <div>
                    <p className="font-medium">${(invoice.amount / 100).toFixed(2)}</p>
                    <p className="text-sm text-gray-600">
                      {new Date(invoice.created * 1000).toLocaleDateString()} • {invoice.status}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    {getStatusBadge(invoice.status)}
                    {invoice.invoicePdf && (
                      <Button variant="outline" size="sm" asChild>
                        <a href={invoice.invoicePdf} target="_blank" rel="noopener noreferrer">
                          <Download className="w-4 h-4" />
                        </a>
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Danger Zone */}
      {billingInfo?.subscriptionId && !billingInfo?.cancelAtPeriodEnd && (
        <Card className="border-red-200">
          <CardHeader>
            <CardTitle className="text-red-600">Danger Zone</CardTitle>
            <CardDescription>
              Irreversible actions that will affect your subscription
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button 
              variant="destructive" 
              onClick={handleCancelSubscription}
              disabled={isProcessing}
            >
              Cancel Subscription
            </Button>
            <p className="text-sm text-gray-600 mt-2">
              You will retain access until the end of your current billing period.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

// Mock data functions - replace with actual API calls
async function getBillingInfo(userId) {
  // Mock billing info
  return {
    customerId: 'cus_mock123',
    subscriptionId: 'sub_mock123',
    status: 'active',
    nextBillingDate: Date.now() + (30 * 24 * 60 * 60 * 1000),
    currentPeriodEnd: Date.now() + (30 * 24 * 60 * 60 * 1000),
    cancelAtPeriodEnd: false
  }
}

async function getInvoices(userId) {
  // Mock invoices
  return [
    {
      id: 'in_mock1',
      amount: 4900,
      status: 'paid',
      created: Math.floor(Date.now() / 1000) - (30 * 24 * 60 * 60),
      invoicePdf: 'https://example.com/invoice.pdf'
    }
  ]
}

async function getPaymentMethods(userId) {
  // Mock payment methods
  return [
    {
      id: 'pm_mock1',
      brand: 'Visa',
      last4: '4242',
      expMonth: 12,
      expYear: 2025,
      isDefault: true
    }
  ]
}
