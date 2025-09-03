/**
 * Enhanced Dashboard Component
 * Integrated dashboard with all new services and features
 */

import React, { useState, useEffect, Suspense, lazy } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { 
  BarChart3, 
  Users, 
  Zap, 
  TrendingUp, 
  Bell, 
  CreditCard,
  TestTube,
  Shield,
  Activity,
  AlertTriangle,
  CheckCircle,
  Clock
} from 'lucide-react'
import { useTier } from '@/hooks/useTier'
import { useAuth } from '@/contexts/AuthContext'
import { toast } from 'sonner'

// Lazy load heavy components for better performance
const TierPricingCard = lazy(() => import('@/components/TierPricingCard'))
const NotificationCenter = lazy(() => import('@/components/notifications/NotificationCenter'))
const BillingDashboard = lazy(() => import('@/components/billing/BillingDashboard'))

// Loading component
const ComponentLoader = ({ children }) => (
  <Suspense fallback={
    <div className="flex items-center justify-center p-8">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
    </div>
  }>
    {children}
  </Suspense>
)

export default function EnhancedDashboard() {
  const { user } = useAuth()
  const { 
    currentTier, 
    usage, 
    getUsagePercentage, 
    hasFeatureAccess,
    upgradeOptions 
  } = useTier()
  
  const [dashboardData, setDashboardData] = useState({
    stats: {},
    recentActivity: [],
    notifications: [],
    abTests: [],
    teamMembers: []
  })
  const [isLoading, setIsLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('overview')

  useEffect(() => {
    loadDashboardData()
  }, [user?.id])

  const loadDashboardData = async () => {
    if (!user?.id) return

    try {
      setIsLoading(true)
      
      // Load dashboard statistics
      const stats = await getDashboardStats(user.id)
      
      // Load recent activity
      const activity = await getRecentActivity(user.id)
      
      // Load notifications
      const notifications = await getRecentNotifications(user.id)
      
      // Load A/B tests if user has access
      let abTests = []
      if (hasFeatureAccess('abTesting')) {
        abTests = await getActiveABTests(user.id)
      }
      
      // Load team members
      const teamMembers = await getTeamMembers(user.id)
      
      setDashboardData({
        stats,
        recentActivity: activity,
        notifications,
        abTests,
        teamMembers
      })
      
    } catch (error) {
      console.error('Failed to load dashboard data:', error)
      toast.error('Failed to load dashboard data')
    } finally {
      setIsLoading(false)
    }
  }

  const getUsageAlerts = () => {
    const alerts = []
    
    if (usage && currentTier?.limits) {
      Object.entries(currentTier.limits).forEach(([key, limit]) => {
        if (limit !== 'unlimited') {
          const percentage = getUsagePercentage(key)
          const currentUsage = usage[key] || 0
          
          if (percentage >= 90) {
            alerts.push({
              type: 'error',
              message: `${key} usage at ${percentage}% (${currentUsage}/${limit})`,
              action: 'upgrade'
            })
          } else if (percentage >= 75) {
            alerts.push({
              type: 'warning',
              message: `${key} usage at ${percentage}% (${currentUsage}/${limit})`,
              action: 'monitor'
            })
          }
        }
      })
    }
    
    return alerts
  }

  const handleUpgrade = () => {
    setActiveTab('billing')
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="h-32 bg-gray-200 rounded"></div>
            ))}
          </div>
          <div className="h-96 bg-gray-200 rounded"></div>
        </div>
      </div>
    )
  }

  const usageAlerts = getUsageAlerts()

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <p className="text-gray-600">
            Welcome back, {user?.firstName || 'User'}! Here's your PIKAR AI overview.
          </p>
        </div>
        
        <div className="flex items-center gap-2">
          <Badge className={currentTier?.id === 'free' ? 'bg-gray-100 text-gray-800' : 'bg-blue-100 text-blue-800'}>
            {currentTier?.name || 'Free'} Plan
          </Badge>
          {upgradeOptions.length > 0 && (
            <Button onClick={handleUpgrade}>
              <TrendingUp className="w-4 h-4 mr-2" />
              Upgrade
            </Button>
          )}
        </div>
      </div>

      {/* Usage Alerts */}
      {usageAlerts.length > 0 && (
        <div className="space-y-2">
          {usageAlerts.map((alert, index) => (
            <div
              key={index}
              className={`p-4 rounded-lg border ${
                alert.type === 'error' 
                  ? 'bg-red-50 border-red-200 text-red-800' 
                  : 'bg-orange-50 border-orange-200 text-orange-800'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4" />
                  <span className="font-medium">{alert.message}</span>
                </div>
                {alert.action === 'upgrade' && (
                  <Button size="sm" onClick={handleUpgrade}>
                    Upgrade Now
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Agent Executions</p>
                <p className="text-2xl font-bold">{dashboardData.stats.totalExecutions || 0}</p>
                <p className="text-xs text-gray-500">This month</p>
              </div>
              <div className="p-3 bg-blue-100 rounded-full">
                <Zap className="w-6 h-6 text-blue-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Success Rate</p>
                <p className="text-2xl font-bold">{dashboardData.stats.successRate || 0}%</p>
                <p className="text-xs text-gray-500">Last 30 days</p>
              </div>
              <div className="p-3 bg-green-100 rounded-full">
                <CheckCircle className="w-6 h-6 text-green-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Team Members</p>
                <p className="text-2xl font-bold">{dashboardData.teamMembers.length}</p>
                <p className="text-xs text-gray-500">Active users</p>
              </div>
              <div className="p-3 bg-purple-100 rounded-full">
                <Users className="w-6 h-6 text-purple-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Active Tests</p>
                <p className="text-2xl font-bold">{dashboardData.abTests.length}</p>
                <p className="text-xs text-gray-500">A/B experiments</p>
              </div>
              <div className="p-3 bg-orange-100 rounded-full">
                <TestTube className="w-6 h-6 text-orange-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="usage">Usage</TabsTrigger>
          <TabsTrigger value="tests">A/B Tests</TabsTrigger>
          <TabsTrigger value="notifications">Notifications</TabsTrigger>
          <TabsTrigger value="billing">Billing</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Recent Activity */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="w-5 h-5" />
                  Recent Activity
                </CardTitle>
              </CardHeader>
              <CardContent>
                {dashboardData.recentActivity.length === 0 ? (
                  <p className="text-gray-500 text-center py-4">No recent activity</p>
                ) : (
                  <div className="space-y-3">
                    {dashboardData.recentActivity.slice(0, 5).map((activity, index) => (
                      <div key={index} className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50">
                        <div className={`p-2 rounded-full ${getActivityIconBg(activity.type)}`}>
                          {getActivityIcon(activity.type)}
                        </div>
                        <div className="flex-1">
                          <p className="text-sm font-medium">{activity.title}</p>
                          <p className="text-xs text-gray-500">{activity.timestamp}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Quick Actions */}
            <Card>
              <CardHeader>
                <CardTitle>Quick Actions</CardTitle>
                <CardDescription>Common tasks and shortcuts</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <Button className="w-full justify-start" variant="outline">
                  <Zap className="w-4 h-4 mr-2" />
                  Execute Agent
                </Button>
                
                {hasFeatureAccess('abTesting') && (
                  <Button className="w-full justify-start" variant="outline">
                    <TestTube className="w-4 h-4 mr-2" />
                    Create A/B Test
                  </Button>
                )}
                
                <Button className="w-full justify-start" variant="outline">
                  <Users className="w-4 h-4 mr-2" />
                  Invite Team Member
                </Button>
                
                <Button className="w-full justify-start" variant="outline">
                  <BarChart3 className="w-4 h-4 mr-2" />
                  View Analytics
                </Button>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Usage Tab */}
        <TabsContent value="usage" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Usage Overview</CardTitle>
              <CardDescription>Current usage for your {currentTier?.name} plan</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {usage && currentTier?.limits && Object.entries(currentTier.limits).map(([key, limit]) => {
                const currentUsage = usage[key] || 0
                const percentage = getUsagePercentage(key)
                
                return (
                  <div key={key} className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="capitalize font-medium">
                        {key.replace(/([A-Z])/g, ' $1').toLowerCase()}
                      </span>
                      <span>
                        {currentUsage} / {limit === 'unlimited' ? '∞' : limit}
                      </span>
                    </div>
                    <Progress 
                      value={limit === 'unlimited' ? 0 : percentage} 
                      className="h-2"
                    />
                    {percentage >= 80 && limit !== 'unlimited' && (
                      <p className="text-xs text-orange-600">
                        You're approaching your limit. Consider upgrading for more capacity.
                      </p>
                    )}
                  </div>
                )
              })}
              
              {upgradeOptions.length > 0 && (
                <div className="pt-4 border-t">
                  <p className="text-sm text-gray-600 mb-3">Need more capacity?</p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {upgradeOptions.slice(0, 2).map((option) => (
                      <ComponentLoader key={option.tierId}>
                        <TierPricingCard 
                          tier={option}
                          showUsage={false}
                          className="h-auto"
                        />
                      </ComponentLoader>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* A/B Tests Tab */}
        <TabsContent value="tests" className="space-y-6">
          {!hasFeatureAccess('abTesting') ? (
            <Card>
              <CardContent className="text-center py-8">
                <TestTube className="w-12 h-12 mx-auto text-gray-400 mb-4" />
                <h3 className="text-lg font-semibold mb-2">A/B Testing Available</h3>
                <p className="text-gray-600 mb-4">
                  Upgrade to Pro or Enterprise to access A/B testing features
                </p>
                <Button onClick={handleUpgrade}>
                  <TrendingUp className="w-4 h-4 mr-2" />
                  Upgrade Now
                </Button>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardHeader>
                <CardTitle>Active A/B Tests</CardTitle>
                <CardDescription>Monitor your running experiments</CardDescription>
              </CardHeader>
              <CardContent>
                {dashboardData.abTests.length === 0 ? (
                  <div className="text-center py-8">
                    <TestTube className="w-12 h-12 mx-auto text-gray-400 mb-4" />
                    <p className="text-gray-600 mb-4">No active A/B tests</p>
                    <Button>Create Your First Test</Button>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {dashboardData.abTests.map((test, index) => (
                      <div key={index} className="p-4 border rounded-lg">
                        <div className="flex items-center justify-between mb-2">
                          <h4 className="font-medium">{test.name}</h4>
                          <Badge variant={test.status === 'running' ? 'default' : 'secondary'}>
                            {test.status}
                          </Badge>
                        </div>
                        <p className="text-sm text-gray-600 mb-3">{test.description}</p>
                        <div className="flex items-center gap-4 text-xs text-gray-500">
                          <span>Variants: {test.variantCount}</span>
                          <span>Traffic: {test.trafficAllocation * 100}%</span>
                          <span>Started: {test.startDate}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Notifications Tab */}
        <TabsContent value="notifications">
          <ComponentLoader>
            <NotificationCenter />
          </ComponentLoader>
        </TabsContent>

        {/* Billing Tab */}
        <TabsContent value="billing">
          <ComponentLoader>
            <BillingDashboard />
          </ComponentLoader>
        </TabsContent>
      </Tabs>
    </div>
  )
}

// Helper functions
function getActivityIcon(type) {
  const icons = {
    execution: <Zap className="w-4 h-4" />,
    upgrade: <TrendingUp className="w-4 h-4" />,
    test: <TestTube className="w-4 h-4" />,
    notification: <Bell className="w-4 h-4" />,
    user: <Users className="w-4 h-4" />
  }
  return icons[type] || <Activity className="w-4 h-4" />
}

function getActivityIconBg(type) {
  const backgrounds = {
    execution: 'bg-blue-100 text-blue-600',
    upgrade: 'bg-green-100 text-green-600',
    test: 'bg-orange-100 text-orange-600',
    notification: 'bg-purple-100 text-purple-600',
    user: 'bg-gray-100 text-gray-600'
  }
  return backgrounds[type] || 'bg-gray-100 text-gray-600'
}

// Mock data functions - replace with actual API calls
async function getDashboardStats(userId) {
  return {
    totalExecutions: 1247,
    successRate: 94.2,
    avgExecutionTime: 2.3
  }
}

async function getRecentActivity(userId) {
  return [
    {
      type: 'execution',
      title: 'Strategic Planning Agent completed',
      timestamp: '2 minutes ago'
    },
    {
      type: 'test',
      title: 'Button Color A/B test started',
      timestamp: '1 hour ago'
    },
    {
      type: 'user',
      title: 'New team member joined',
      timestamp: '3 hours ago'
    }
  ]
}

async function getRecentNotifications(userId) {
  return []
}

async function getActiveABTests(userId) {
  return [
    {
      name: 'Homepage CTA Button',
      description: 'Testing different button colors for conversion',
      status: 'running',
      variantCount: 2,
      trafficAllocation: 0.5,
      startDate: '2 days ago'
    }
  ]
}

async function getTeamMembers(userId) {
  return [
    { id: '1', name: 'John Doe', role: 'Admin' },
    { id: '2', name: 'Jane Smith', role: 'Member' }
  ]
}
