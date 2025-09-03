/**
 * Email Preferences Component
 * User interface for managing email notification preferences
 */

import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { 
  Mail, 
  Bell, 
  Shield, 
  CreditCard, 
  BarChart3, 
  Zap, 
  AlertTriangle,
  Info,
  Settings,
  Save,
  RefreshCw
} from 'lucide-react'
import { emailNotificationService } from '@/services/emailNotificationService'
import { useAuth } from '@/contexts/AuthContext'
import { toast } from 'sonner'

const NOTIFICATION_CATEGORIES = {
  account: {
    name: 'Account & Security',
    icon: Shield,
    color: 'text-red-600',
    description: 'Important account and security notifications'
  },
  agents: {
    name: 'Agent Activity',
    icon: Zap,
    color: 'text-blue-600',
    description: 'AI agent execution updates and results'
  },
  billing: {
    name: 'Billing & Payments',
    icon: CreditCard,
    color: 'text-green-600',
    description: 'Billing, payments, and subscription updates'
  },
  usage: {
    name: 'Usage & Quotas',
    icon: BarChart3,
    color: 'text-orange-600',
    description: 'Usage alerts and quota notifications'
  },
  marketing: {
    name: 'Marketing & Updates',
    icon: Bell,
    color: 'text-purple-600',
    description: 'Product updates and marketing communications'
  }
}

const NOTIFICATION_SETTINGS = {
  // Account & Security
  welcome: {
    category: 'account',
    name: 'Welcome Email',
    description: 'Welcome message when you join PIKAR AI',
    required: true
  },
  email_verification: {
    category: 'account',
    name: 'Email Verification',
    description: 'Email address verification requests',
    required: true
  },
  password_reset: {
    category: 'account',
    name: 'Password Reset',
    description: 'Password reset confirmation emails',
    required: true
  },
  security_alert: {
    category: 'account',
    name: 'Security Alerts',
    description: 'Suspicious activity and security warnings',
    required: true
  },
  
  // Agent Activity
  agent_execution_complete: {
    category: 'agents',
    name: 'Agent Execution Complete',
    description: 'Notifications when agent tasks finish successfully',
    required: false
  },
  agent_execution_failed: {
    category: 'agents',
    name: 'Agent Execution Failed',
    description: 'Alerts when agent tasks encounter errors',
    required: false
  },
  
  // Billing & Payments
  tier_upgraded: {
    category: 'billing',
    name: 'Tier Upgrades',
    description: 'Confirmation when you upgrade your subscription',
    required: false
  },
  tier_downgraded: {
    category: 'billing',
    name: 'Tier Downgrades',
    description: 'Confirmation when you downgrade your subscription',
    required: false
  },
  billing_reminder: {
    category: 'billing',
    name: 'Billing Reminders',
    description: 'Upcoming payment and renewal reminders',
    required: false
  },
  payment_failed: {
    category: 'billing',
    name: 'Payment Failed',
    description: 'Alerts when payments fail or are declined',
    required: true
  },
  
  // Usage & Quotas
  quota_warning: {
    category: 'usage',
    name: 'Quota Warnings',
    description: 'Alerts when approaching usage limits',
    required: false
  },
  quota_exceeded: {
    category: 'usage',
    name: 'Quota Exceeded',
    description: 'Notifications when usage limits are reached',
    required: true
  },
  
  // Marketing & Updates
  weekly_summary: {
    category: 'marketing',
    name: 'Weekly Summary',
    description: 'Weekly activity and performance summaries',
    required: false
  },
  monthly_report: {
    category: 'marketing',
    name: 'Monthly Reports',
    description: 'Monthly analytics and insights reports',
    required: false
  },
  feature_announcement: {
    category: 'marketing',
    name: 'Feature Announcements',
    description: 'New features and product updates',
    required: false
  },
  system_maintenance: {
    category: 'marketing',
    name: 'System Maintenance',
    description: 'Scheduled maintenance and downtime notices',
    required: false
  }
}

export default function EmailPreferences() {
  const { user } = useAuth()
  const [preferences, setPreferences] = useState({})
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [hasChanges, setHasChanges] = useState(false)

  useEffect(() => {
    loadPreferences()
  }, [user?.id])

  const loadPreferences = async () => {
    if (!user?.id) return

    try {
      setIsLoading(true)
      const userPreferences = emailNotificationService.getUserPreferences(user.id)
      setPreferences(userPreferences)
    } catch (error) {
      console.error('Failed to load email preferences:', error)
      toast.error('Failed to load email preferences')
    } finally {
      setIsLoading(false)
    }
  }

  const handlePreferenceChange = (notificationType, enabled) => {
    setPreferences(prev => ({
      ...prev,
      [notificationType]: enabled
    }))
    setHasChanges(true)
  }

  const handleFrequencyChange = (frequency) => {
    setPreferences(prev => ({
      ...prev,
      emailFrequency: frequency
    }))
    setHasChanges(true)
  }

  const savePreferences = async () => {
    if (!user?.id) return

    try {
      setIsSaving(true)
      await emailNotificationService.updateUserPreferences(user.id, preferences)
      setHasChanges(false)
      toast.success('Email preferences saved successfully')
    } catch (error) {
      console.error('Failed to save email preferences:', error)
      toast.error('Failed to save email preferences')
    } finally {
      setIsSaving(false)
    }
  }

  const resetToDefaults = () => {
    const defaultPreferences = emailNotificationService.getDefaultPreferences()
    setPreferences(defaultPreferences)
    setHasChanges(true)
    toast.info('Preferences reset to defaults')
  }

  const toggleCategoryPreferences = (category, enabled) => {
    const categorySettings = Object.entries(NOTIFICATION_SETTINGS)
      .filter(([_, setting]) => setting.category === category && !setting.required)
      .map(([key]) => key)

    const updates = {}
    categorySettings.forEach(key => {
      updates[key] = enabled
    })

    setPreferences(prev => ({
      ...prev,
      ...updates
    }))
    setHasChanges(true)
  }

  const getCategoryStatus = (category) => {
    const categorySettings = Object.entries(NOTIFICATION_SETTINGS)
      .filter(([_, setting]) => setting.category === category && !setting.required)
      .map(([key]) => key)

    if (categorySettings.length === 0) return 'none'

    const enabledCount = categorySettings.filter(key => preferences[key]).length
    
    if (enabledCount === 0) return 'none'
    if (enabledCount === categorySettings.length) return 'all'
    return 'partial'
  }

  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center p-8">
          <RefreshCw className="w-6 h-6 animate-spin mr-2" />
          Loading preferences...
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Mail className="w-5 h-5" />
            Email Notification Preferences
          </CardTitle>
          <CardDescription>
            Manage when and how you receive email notifications from PIKAR AI
          </CardDescription>
        </CardHeader>
      </Card>

      {/* Global Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="w-5 h-5" />
            Global Settings
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium">Email Frequency</label>
              <p className="text-sm text-gray-600">
                How often you want to receive non-urgent notifications
              </p>
            </div>
            <Select
              value={preferences.emailFrequency || 'immediate'}
              onValueChange={handleFrequencyChange}
            >
              <SelectTrigger className="w-40">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="immediate">Immediate</SelectItem>
                <SelectItem value="daily">Daily Digest</SelectItem>
                <SelectItem value="weekly">Weekly Digest</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Notification Categories */}
      {Object.entries(NOTIFICATION_CATEGORIES).map(([categoryKey, category]) => {
        const categorySettings = Object.entries(NOTIFICATION_SETTINGS)
          .filter(([_, setting]) => setting.category === categoryKey)
        
        const categoryStatus = getCategoryStatus(categoryKey)
        const IconComponent = category.icon

        return (
          <Card key={categoryKey}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <IconComponent className={`w-5 h-5 ${category.color}`} />
                  <div>
                    <CardTitle className="text-lg">{category.name}</CardTitle>
                    <CardDescription>{category.description}</CardDescription>
                  </div>
                </div>
                
                {categoryStatus !== 'none' && (
                  <div className="flex items-center gap-2">
                    <Badge variant={categoryStatus === 'all' ? 'default' : 'secondary'}>
                      {categoryStatus === 'all' ? 'All On' : 
                       categoryStatus === 'partial' ? 'Partial' : 'All Off'}
                    </Badge>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => toggleCategoryPreferences(categoryKey, categoryStatus !== 'all')}
                    >
                      {categoryStatus === 'all' ? 'Disable All' : 'Enable All'}
                    </Button>
                  </div>
                )}
              </div>
            </CardHeader>
            
            <CardContent className="space-y-4">
              {categorySettings.map(([settingKey, setting]) => (
                <div key={settingKey} className="flex items-center justify-between py-2">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <label className="text-sm font-medium">{setting.name}</label>
                      {setting.required && (
                        <Badge variant="outline" className="text-xs">
                          Required
                        </Badge>
                      )}
                    </div>
                    <p className="text-sm text-gray-600">{setting.description}</p>
                  </div>
                  
                  <Switch
                    checked={preferences[settingKey] !== false}
                    onCheckedChange={(checked) => handlePreferenceChange(settingKey, checked)}
                    disabled={setting.required}
                  />
                </div>
              ))}
            </CardContent>
          </Card>
        )
      })}

      {/* Actions */}
      <Card>
        <CardContent className="flex items-center justify-between p-6">
          <div className="flex items-center gap-2">
            {hasChanges && (
              <div className="flex items-center gap-2 text-orange-600">
                <AlertTriangle className="w-4 h-4" />
                <span className="text-sm">You have unsaved changes</span>
              </div>
            )}
          </div>
          
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              onClick={resetToDefaults}
              disabled={isSaving}
            >
              Reset to Defaults
            </Button>
            
            <Button
              onClick={savePreferences}
              disabled={!hasChanges || isSaving}
            >
              {isSaving ? (
                <>
                  <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="w-4 h-4 mr-2" />
                  Save Preferences
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Help Text */}
      <Card className="bg-blue-50 border-blue-200">
        <CardContent className="p-4">
          <div className="flex items-start gap-3">
            <Info className="w-5 h-5 text-blue-600 mt-0.5" />
            <div className="text-sm text-blue-800">
              <p className="font-medium mb-1">About Email Notifications</p>
              <ul className="space-y-1 text-blue-700">
                <li>• Required notifications cannot be disabled for security and compliance reasons</li>
                <li>• Daily and weekly digests combine multiple notifications into single emails</li>
                <li>• You can unsubscribe from individual emails using the link at the bottom</li>
                <li>• Changes take effect immediately for new notifications</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
