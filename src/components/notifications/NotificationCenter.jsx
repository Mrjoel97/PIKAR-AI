/**
 * Notification Center Component
 * Centralized notification management and history
 */

import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { 
  Bell, 
  Mail, 
  Search, 
  Filter, 
  MarkAsRead, 
  Trash2, 
  Settings,
  CheckCircle,
  AlertCircle,
  Info,
  Zap,
  Shield,
  CreditCard,
  BarChart3,
  RefreshCw,
  Eye,
  EyeOff
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { useAuth } from '@/contexts/AuthContext'
import { toast } from 'sonner'

const NOTIFICATION_TYPES = {
  info: {
    icon: Info,
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200'
  },
  success: {
    icon: CheckCircle,
    color: 'text-green-600',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200'
  },
  warning: {
    icon: AlertCircle,
    color: 'text-orange-600',
    bgColor: 'bg-orange-50',
    borderColor: 'border-orange-200'
  },
  error: {
    icon: AlertCircle,
    color: 'text-red-600',
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200'
  },
  agent: {
    icon: Zap,
    color: 'text-purple-600',
    bgColor: 'bg-purple-50',
    borderColor: 'border-purple-200'
  },
  security: {
    icon: Shield,
    color: 'text-red-600',
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200'
  },
  billing: {
    icon: CreditCard,
    color: 'text-green-600',
    bgColor: 'bg-green-50',
    borderColor: 'border-green-200'
  },
  usage: {
    icon: BarChart3,
    color: 'text-orange-600',
    bgColor: 'bg-orange-50',
    borderColor: 'border-orange-200'
  }
}

export default function NotificationCenter() {
  const { user } = useAuth()
  const [notifications, setNotifications] = useState([])
  const [filteredNotifications, setFilteredNotifications] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [filterType, setFilterType] = useState('all')
  const [filterStatus, setFilterStatus] = useState('all')
  const [selectedNotifications, setSelectedNotifications] = useState(new Set())

  useEffect(() => {
    loadNotifications()
  }, [user?.id])

  useEffect(() => {
    filterNotifications()
  }, [notifications, searchQuery, filterType, filterStatus])

  const loadNotifications = async () => {
    if (!user?.id) return

    try {
      setIsLoading(true)
      // Mock notifications - replace with actual API call
      const mockNotifications = generateMockNotifications()
      setNotifications(mockNotifications)
    } catch (error) {
      console.error('Failed to load notifications:', error)
      toast.error('Failed to load notifications')
    } finally {
      setIsLoading(false)
    }
  }

  const filterNotifications = () => {
    let filtered = [...notifications]

    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      filtered = filtered.filter(notification =>
        notification.title.toLowerCase().includes(query) ||
        notification.message.toLowerCase().includes(query)
      )
    }

    // Type filter
    if (filterType !== 'all') {
      filtered = filtered.filter(notification => notification.type === filterType)
    }

    // Status filter
    if (filterStatus !== 'all') {
      if (filterStatus === 'read') {
        filtered = filtered.filter(notification => notification.read)
      } else if (filterStatus === 'unread') {
        filtered = filtered.filter(notification => !notification.read)
      }
    }

    // Sort by timestamp (newest first)
    filtered.sort((a, b) => b.timestamp - a.timestamp)

    setFilteredNotifications(filtered)
  }

  const markAsRead = async (notificationIds) => {
    try {
      const updatedNotifications = notifications.map(notification => {
        if (notificationIds.includes(notification.id)) {
          return { ...notification, read: true }
        }
        return notification
      })
      
      setNotifications(updatedNotifications)
      toast.success(`Marked ${notificationIds.length} notification(s) as read`)
    } catch (error) {
      console.error('Failed to mark notifications as read:', error)
      toast.error('Failed to mark notifications as read')
    }
  }

  const markAsUnread = async (notificationIds) => {
    try {
      const updatedNotifications = notifications.map(notification => {
        if (notificationIds.includes(notification.id)) {
          return { ...notification, read: false }
        }
        return notification
      })
      
      setNotifications(updatedNotifications)
      toast.success(`Marked ${notificationIds.length} notification(s) as unread`)
    } catch (error) {
      console.error('Failed to mark notifications as unread:', error)
      toast.error('Failed to mark notifications as unread')
    }
  }

  const deleteNotifications = async (notificationIds) => {
    try {
      const updatedNotifications = notifications.filter(
        notification => !notificationIds.includes(notification.id)
      )
      
      setNotifications(updatedNotifications)
      setSelectedNotifications(new Set())
      toast.success(`Deleted ${notificationIds.length} notification(s)`)
    } catch (error) {
      console.error('Failed to delete notifications:', error)
      toast.error('Failed to delete notifications')
    }
  }

  const toggleNotificationSelection = (notificationId) => {
    const newSelection = new Set(selectedNotifications)
    if (newSelection.has(notificationId)) {
      newSelection.delete(notificationId)
    } else {
      newSelection.add(notificationId)
    }
    setSelectedNotifications(newSelection)
  }

  const selectAllVisible = () => {
    const visibleIds = filteredNotifications.map(n => n.id)
    setSelectedNotifications(new Set(visibleIds))
  }

  const clearSelection = () => {
    setSelectedNotifications(new Set())
  }

  const getUnreadCount = () => {
    return notifications.filter(n => !n.read).length
  }

  const getNotificationStats = () => {
    const stats = {
      total: notifications.length,
      unread: notifications.filter(n => !n.read).length,
      today: notifications.filter(n => 
        new Date(n.timestamp).toDateString() === new Date().toDateString()
      ).length
    }

    const typeStats = {}
    notifications.forEach(n => {
      typeStats[n.type] = (typeStats[n.type] || 0) + 1
    })

    return { ...stats, byType: typeStats }
  }

  const generateMockNotifications = () => {
    return [
      {
        id: '1',
        type: 'agent',
        title: 'Agent Execution Complete',
        message: 'Strategic Planning Agent completed successfully. Generated 5 strategic recommendations.',
        timestamp: Date.now() - 1000 * 60 * 30, // 30 minutes ago
        read: false,
        actionUrl: '/agents/executions/123'
      },
      {
        id: '2',
        type: 'usage',
        title: 'Quota Warning',
        message: 'You have used 85% of your monthly agent executions. Consider upgrading to Pro.',
        timestamp: Date.now() - 1000 * 60 * 60 * 2, // 2 hours ago
        read: false,
        actionUrl: '/settings/billing'
      },
      {
        id: '3',
        type: 'billing',
        title: 'Payment Successful',
        message: 'Your Pro subscription has been renewed for $49.00.',
        timestamp: Date.now() - 1000 * 60 * 60 * 24, // 1 day ago
        read: true,
        actionUrl: '/settings/billing'
      },
      {
        id: '4',
        type: 'security',
        title: 'New Login Detected',
        message: 'New login from Chrome on Windows in New York, NY.',
        timestamp: Date.now() - 1000 * 60 * 60 * 24 * 2, // 2 days ago
        read: true,
        actionUrl: '/settings/security'
      },
      {
        id: '5',
        type: 'info',
        title: 'New Feature Available',
        message: 'A/B Testing is now available for Pro users. Start optimizing your campaigns today!',
        timestamp: Date.now() - 1000 * 60 * 60 * 24 * 3, // 3 days ago
        read: false,
        actionUrl: '/features/ab-testing'
      }
    ]
  }

  const stats = getNotificationStats()

  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center p-8">
          <RefreshCw className="w-6 h-6 animate-spin mr-2" />
          Loading notifications...
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Bell className="w-5 h-5" />
                Notification Center
                {stats.unread > 0 && (
                  <Badge variant="destructive" className="ml-2">
                    {stats.unread} unread
                  </Badge>
                )}
              </CardTitle>
              <CardDescription>
                Manage your notifications and stay updated with PIKAR AI
              </CardDescription>
            </div>
            
            <Button variant="outline" onClick={loadNotifications}>
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh
            </Button>
          </div>
        </CardHeader>
      </Card>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold">{stats.total}</div>
            <div className="text-sm text-gray-600">Total</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-blue-600">{stats.unread}</div>
            <div className="text-sm text-gray-600">Unread</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-green-600">{stats.today}</div>
            <div className="text-sm text-gray-600">Today</div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-purple-600">
              {stats.byType.agent || 0}
            </div>
            <div className="text-sm text-gray-600">Agent Updates</div>
          </CardContent>
        </Card>
      </div>

      {/* Filters and Search */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                <Input
                  placeholder="Search notifications..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            
            <Select value={filterType} onValueChange={setFilterType}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Filter by type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                <SelectItem value="agent">Agent</SelectItem>
                <SelectItem value="usage">Usage</SelectItem>
                <SelectItem value="billing">Billing</SelectItem>
                <SelectItem value="security">Security</SelectItem>
                <SelectItem value="info">Info</SelectItem>
              </SelectContent>
            </Select>
            
            <Select value={filterStatus} onValueChange={setFilterStatus}>
              <SelectTrigger className="w-32">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                <SelectItem value="unread">Unread</SelectItem>
                <SelectItem value="read">Read</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Bulk Actions */}
      {selectedNotifications.size > 0 && (
        <Card className="bg-blue-50 border-blue-200">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">
                  {selectedNotifications.size} notification(s) selected
                </span>
              </div>
              
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => markAsRead(Array.from(selectedNotifications))}
                >
                  <Eye className="w-4 h-4 mr-1" />
                  Mark Read
                </Button>
                
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => markAsUnread(Array.from(selectedNotifications))}
                >
                  <EyeOff className="w-4 h-4 mr-1" />
                  Mark Unread
                </Button>
                
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => deleteNotifications(Array.from(selectedNotifications))}
                >
                  <Trash2 className="w-4 h-4 mr-1" />
                  Delete
                </Button>
                
                <Button variant="outline" size="sm" onClick={clearSelection}>
                  Clear
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Notifications List */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">
              Notifications ({filteredNotifications.length})
            </CardTitle>
            
            {filteredNotifications.length > 0 && (
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={selectedNotifications.size === filteredNotifications.length ? clearSelection : selectAllVisible}
                >
                  {selectedNotifications.size === filteredNotifications.length ? 'Deselect All' : 'Select All'}
                </Button>
              </div>
            )}
          </div>
        </CardHeader>
        
        <CardContent className="p-0">
          {filteredNotifications.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <Bell className="w-12 h-12 mx-auto mb-4 text-gray-300" />
              <p>No notifications found</p>
              <p className="text-sm">Try adjusting your filters or search query</p>
            </div>
          ) : (
            <div className="divide-y">
              {filteredNotifications.map((notification) => {
                const typeConfig = NOTIFICATION_TYPES[notification.type] || NOTIFICATION_TYPES.info
                const IconComponent = typeConfig.icon
                const isSelected = selectedNotifications.has(notification.id)
                
                return (
                  <div
                    key={notification.id}
                    className={`p-4 hover:bg-gray-50 transition-colors ${
                      !notification.read ? 'bg-blue-50/50' : ''
                    } ${isSelected ? 'bg-blue-100' : ''}`}
                  >
                    <div className="flex items-start gap-3">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleNotificationSelection(notification.id)}
                        className="mt-1"
                      />
                      
                      <div className={`p-2 rounded-full ${typeConfig.bgColor}`}>
                        <IconComponent className={`w-4 h-4 ${typeConfig.color}`} />
                      </div>
                      
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <h4 className={`font-medium ${!notification.read ? 'text-gray-900' : 'text-gray-700'}`}>
                            {notification.title}
                          </h4>
                          {!notification.read && (
                            <div className="w-2 h-2 bg-blue-600 rounded-full"></div>
                          )}
                        </div>
                        
                        <p className="text-sm text-gray-600 mb-2">
                          {notification.message}
                        </p>
                        
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-gray-500">
                            {formatDistanceToNow(new Date(notification.timestamp), { addSuffix: true })}
                          </span>
                          
                          <div className="flex items-center gap-2">
                            {notification.actionUrl && (
                              <Button variant="outline" size="sm">
                                View Details
                              </Button>
                            )}
                            
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => markAsRead([notification.id])}
                            >
                              {notification.read ? (
                                <EyeOff className="w-4 h-4" />
                              ) : (
                                <Eye className="w-4 h-4" />
                              )}
                            </Button>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
