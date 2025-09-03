/**
 * User Management Service
 * Comprehensive user management with roles, permissions, teams, and profiles
 */

import { auditService } from './auditService'
import { loggingService } from './loggingService'
import { tierService } from './tierService'
import { environmentConfig } from '@/config/environment'

class UserManagementService {
  constructor() {
    this.users = new Map()
    this.teams = new Map()
    this.roles = new Map()
    this.permissions = new Map()
    this.invitations = new Map()
    this.sessions = new Map()
    this.isInitialized = false
    
    // Default roles and permissions
    this.defaultRoles = {
      OWNER: {
        id: 'owner',
        name: 'Owner',
        description: 'Full access to all features and settings',
        permissions: ['*'], // All permissions
        isSystemRole: true,
        canBeDeleted: false
      },
      ADMIN: {
        id: 'admin',
        name: 'Administrator',
        description: 'Administrative access with user management',
        permissions: [
          'users.manage',
          'teams.manage',
          'agents.manage',
          'billing.view',
          'settings.manage',
          'analytics.view'
        ],
        isSystemRole: true,
        canBeDeleted: false
      },
      MANAGER: {
        id: 'manager',
        name: 'Manager',
        description: 'Team management and agent oversight',
        permissions: [
          'users.view',
          'teams.manage',
          'agents.manage',
          'analytics.view',
          'projects.manage'
        ],
        isSystemRole: true,
        canBeDeleted: false
      },
      MEMBER: {
        id: 'member',
        name: 'Member',
        description: 'Standard user with basic access',
        permissions: [
          'agents.execute',
          'projects.view',
          'analytics.view',
          'profile.manage'
        ],
        isSystemRole: true,
        canBeDeleted: false
      },
      VIEWER: {
        id: 'viewer',
        name: 'Viewer',
        description: 'Read-only access to projects and analytics',
        permissions: [
          'projects.view',
          'analytics.view',
          'profile.view'
        ],
        isSystemRole: true,
        canBeDeleted: false
      }
    }
    
    // All available permissions
    this.availablePermissions = {
      // User management
      'users.view': 'View users',
      'users.manage': 'Manage users',
      'users.invite': 'Invite users',
      'users.remove': 'Remove users',
      
      // Team management
      'teams.view': 'View teams',
      'teams.manage': 'Manage teams',
      'teams.create': 'Create teams',
      'teams.delete': 'Delete teams',
      
      // Agent management
      'agents.view': 'View agents',
      'agents.execute': 'Execute agents',
      'agents.manage': 'Manage agents',
      'agents.create': 'Create custom agents',
      
      // Project management
      'projects.view': 'View projects',
      'projects.manage': 'Manage projects',
      'projects.create': 'Create projects',
      'projects.delete': 'Delete projects',
      
      // Analytics and reporting
      'analytics.view': 'View analytics',
      'analytics.export': 'Export analytics',
      'reports.generate': 'Generate reports',
      
      // Billing and subscriptions
      'billing.view': 'View billing',
      'billing.manage': 'Manage billing',
      'subscriptions.manage': 'Manage subscriptions',
      
      // Settings and configuration
      'settings.view': 'View settings',
      'settings.manage': 'Manage settings',
      'integrations.manage': 'Manage integrations',
      
      // Profile management
      'profile.view': 'View own profile',
      'profile.manage': 'Manage own profile'
    }
    
    this.setupDefaultRoles()
  }

  /**
   * Initialize user management service
   */
  async initialize() {
    try {
      console.log('👥 Initializing User Management Service...')
      
      // Load users and teams
      await this.loadUsers()
      await this.loadTeams()
      
      // Setup session management
      this.setupSessionManagement()
      
      // Setup invitation cleanup
      this.setupInvitationCleanup()
      
      this.isInitialized = true
      
      console.log('✅ User Management Service initialized successfully')
      
      await auditService.logSystem.userManagement('user_management_service_initialized', {
        totalUsers: this.users.size,
        totalTeams: this.teams.size,
        totalRoles: this.roles.size
      })
      
    } catch (error) {
      console.error('❌ User Management Service initialization failed:', error)
      throw error
    }
  }

  /**
   * Create new user
   */
  async createUser(userData, createdBy = null) {
    try {
      // Validate user data
      this.validateUserData(userData)
      
      // Check if email already exists
      if (this.getUserByEmail(userData.email)) {
        throw new Error('User with this email already exists')
      }
      
      const userId = this.generateUserId()
      const user = {
        id: userId,
        email: userData.email,
        firstName: userData.firstName,
        lastName: userData.lastName,
        displayName: userData.displayName || `${userData.firstName} ${userData.lastName}`,
        avatar: userData.avatar || null,
        
        // Account status
        status: 'active',
        emailVerified: false,
        lastLogin: null,
        loginCount: 0,
        
        // Role and permissions
        roleId: userData.roleId || 'member',
        customPermissions: userData.customPermissions || [],
        
        // Team membership
        teamIds: userData.teamIds || [],
        primaryTeamId: userData.primaryTeamId || null,
        
        // Profile information
        profile: {
          bio: userData.bio || '',
          timezone: userData.timezone || 'UTC',
          language: userData.language || 'en',
          notifications: userData.notifications || this.getDefaultNotificationSettings(),
          preferences: userData.preferences || {}
        },
        
        // Security
        twoFactorEnabled: false,
        lastPasswordChange: Date.now(),
        failedLoginAttempts: 0,
        lockedUntil: null,
        
        // Metadata
        createdAt: Date.now(),
        updatedAt: Date.now(),
        createdBy: createdBy
      }
      
      this.users.set(userId, user)
      
      // Send welcome email
      await this.sendWelcomeEmail(user)
      
      await auditService.logAccess.userManagement('user_created', {
        userId,
        email: user.email,
        roleId: user.roleId,
        createdBy
      })
      
      return user
      
    } catch (error) {
      console.error('Failed to create user:', error)
      throw error
    }
  }

  /**
   * Update user
   */
  async updateUser(userId, updates, updatedBy = null) {
    const user = this.users.get(userId)
    if (!user) {
      throw new Error('User not found')
    }
    
    // Validate updates
    if (updates.email && updates.email !== user.email) {
      if (this.getUserByEmail(updates.email)) {
        throw new Error('Email already in use')
      }
      updates.emailVerified = false // Require re-verification
    }
    
    // Update user data
    const updatedUser = {
      ...user,
      ...updates,
      updatedAt: Date.now()
    }
    
    // Handle profile updates
    if (updates.profile) {
      updatedUser.profile = {
        ...user.profile,
        ...updates.profile
      }
    }
    
    this.users.set(userId, updatedUser)
    
    await auditService.logAccess.userManagement('user_updated', {
      userId,
      updates: Object.keys(updates),
      updatedBy
    })
    
    return updatedUser
  }

  /**
   * Delete user
   */
  async deleteUser(userId, deletedBy = null) {
    const user = this.users.get(userId)
    if (!user) {
      throw new Error('User not found')
    }
    
    // Check if user is the only owner
    if (user.roleId === 'owner') {
      const ownerCount = Array.from(this.users.values())
        .filter(u => u.roleId === 'owner' && u.status === 'active').length
      
      if (ownerCount <= 1) {
        throw new Error('Cannot delete the last owner')
      }
    }
    
    // Soft delete - mark as deleted but keep data for audit
    user.status = 'deleted'
    user.deletedAt = Date.now()
    user.deletedBy = deletedBy
    user.updatedAt = Date.now()
    
    // Remove from teams
    user.teamIds = []
    user.primaryTeamId = null
    
    await auditService.logAccess.userManagement('user_deleted', {
      userId,
      email: user.email,
      deletedBy
    })
    
    return user
  }

  /**
   * Create team
   */
  async createTeam(teamData, createdBy) {
    try {
      this.validateTeamData(teamData)
      
      const teamId = this.generateTeamId()
      const team = {
        id: teamId,
        name: teamData.name,
        description: teamData.description || '',
        avatar: teamData.avatar || null,
        
        // Team settings
        settings: {
          visibility: teamData.visibility || 'private', // private, public
          joinPolicy: teamData.joinPolicy || 'invite_only', // open, invite_only, closed
          defaultRole: teamData.defaultRole || 'member'
        },
        
        // Members
        members: [{
          userId: createdBy,
          roleId: 'owner',
          joinedAt: Date.now(),
          invitedBy: null
        }],
        
        // Statistics
        stats: {
          memberCount: 1,
          projectCount: 0,
          agentExecutions: 0
        },
        
        // Metadata
        createdAt: Date.now(),
        updatedAt: Date.now(),
        createdBy
      }
      
      this.teams.set(teamId, team)
      
      // Add team to creator's profile
      const creator = this.users.get(createdBy)
      if (creator) {
        creator.teamIds.push(teamId)
        if (!creator.primaryTeamId) {
          creator.primaryTeamId = teamId
        }
        creator.updatedAt = Date.now()
      }
      
      await auditService.logAccess.userManagement('team_created', {
        teamId,
        teamName: team.name,
        createdBy
      })
      
      return team
      
    } catch (error) {
      console.error('Failed to create team:', error)
      throw error
    }
  }

  /**
   * Add user to team
   */
  async addUserToTeam(teamId, userId, roleId = 'member', invitedBy = null) {
    const team = this.teams.get(teamId)
    const user = this.users.get(userId)
    
    if (!team) throw new Error('Team not found')
    if (!user) throw new Error('User not found')
    
    // Check if user is already a member
    const existingMember = team.members.find(m => m.userId === userId)
    if (existingMember) {
      throw new Error('User is already a team member')
    }
    
    // Check team size limits based on tier
    const teamOwner = this.users.get(team.createdBy)
    if (teamOwner) {
      const userTier = tierService.getUserTier(teamOwner.id)
      const maxTeamMembers = userTier.features.maxTeamMembers
      
      if (maxTeamMembers !== 'unlimited' && team.members.length >= maxTeamMembers) {
        throw new Error(`Team size limit reached. Upgrade to add more members.`)
      }
    }
    
    // Add member to team
    team.members.push({
      userId,
      roleId,
      joinedAt: Date.now(),
      invitedBy
    })
    
    team.stats.memberCount = team.members.length
    team.updatedAt = Date.now()
    
    // Add team to user's profile
    user.teamIds.push(teamId)
    if (!user.primaryTeamId) {
      user.primaryTeamId = teamId
    }
    user.updatedAt = Date.now()
    
    await auditService.logAccess.userManagement('user_added_to_team', {
      teamId,
      userId,
      roleId,
      invitedBy
    })
    
    return team
  }

  /**
   * Remove user from team
   */
  async removeUserFromTeam(teamId, userId, removedBy = null) {
    const team = this.teams.get(teamId)
    const user = this.users.get(userId)
    
    if (!team) throw new Error('Team not found')
    if (!user) throw new Error('User not found')
    
    // Check if user is a member
    const memberIndex = team.members.findIndex(m => m.userId === userId)
    if (memberIndex === -1) {
      throw new Error('User is not a team member')
    }
    
    const member = team.members[memberIndex]
    
    // Check if removing the last owner
    if (member.roleId === 'owner') {
      const ownerCount = team.members.filter(m => m.roleId === 'owner').length
      if (ownerCount <= 1) {
        throw new Error('Cannot remove the last team owner')
      }
    }
    
    // Remove member from team
    team.members.splice(memberIndex, 1)
    team.stats.memberCount = team.members.length
    team.updatedAt = Date.now()
    
    // Remove team from user's profile
    user.teamIds = user.teamIds.filter(id => id !== teamId)
    if (user.primaryTeamId === teamId) {
      user.primaryTeamId = user.teamIds[0] || null
    }
    user.updatedAt = Date.now()
    
    await auditService.logAccess.userManagement('user_removed_from_team', {
      teamId,
      userId,
      removedBy
    })
    
    return team
  }

  /**
   * Send team invitation
   */
  async sendTeamInvitation(teamId, email, roleId, invitedBy) {
    const team = this.teams.get(teamId)
    if (!team) throw new Error('Team not found')
    
    const inviter = this.users.get(invitedBy)
    if (!inviter) throw new Error('Inviter not found')
    
    // Check if user already exists
    const existingUser = this.getUserByEmail(email)
    if (existingUser && existingUser.teamIds.includes(teamId)) {
      throw new Error('User is already a team member')
    }
    
    const invitationId = this.generateInvitationId()
    const invitation = {
      id: invitationId,
      teamId,
      email,
      roleId,
      invitedBy,
      status: 'pending',
      expiresAt: Date.now() + (7 * 24 * 60 * 60 * 1000), // 7 days
      createdAt: Date.now()
    }
    
    this.invitations.set(invitationId, invitation)
    
    // Send invitation email
    await this.sendInvitationEmail(invitation, team, inviter)
    
    await auditService.logAccess.userManagement('team_invitation_sent', {
      invitationId,
      teamId,
      email,
      roleId,
      invitedBy
    })
    
    return invitation
  }

  /**
   * Accept team invitation
   */
  async acceptInvitation(invitationId, userId) {
    const invitation = this.invitations.get(invitationId)
    if (!invitation) throw new Error('Invitation not found')
    
    if (invitation.status !== 'pending') {
      throw new Error('Invitation is no longer valid')
    }
    
    if (Date.now() > invitation.expiresAt) {
      throw new Error('Invitation has expired')
    }
    
    const user = this.users.get(userId)
    if (!user) throw new Error('User not found')
    
    if (user.email !== invitation.email) {
      throw new Error('Invitation email does not match user email')
    }
    
    // Add user to team
    await this.addUserToTeam(invitation.teamId, userId, invitation.roleId, invitation.invitedBy)
    
    // Mark invitation as accepted
    invitation.status = 'accepted'
    invitation.acceptedAt = Date.now()
    invitation.acceptedBy = userId
    
    await auditService.logAccess.userManagement('team_invitation_accepted', {
      invitationId,
      teamId: invitation.teamId,
      userId
    })
    
    return invitation
  }

  /**
   * Check user permissions
   */
  hasPermission(userId, permission) {
    const user = this.users.get(userId)
    if (!user || user.status !== 'active') return false
    
    const role = this.roles.get(user.roleId)
    if (!role) return false
    
    // Check for wildcard permission (owner)
    if (role.permissions.includes('*')) return true
    
    // Check role permissions
    if (role.permissions.includes(permission)) return true
    
    // Check custom permissions
    if (user.customPermissions.includes(permission)) return true
    
    return false
  }

  /**
   * Get user's effective permissions
   */
  getUserPermissions(userId) {
    const user = this.users.get(userId)
    if (!user || user.status !== 'active') return []
    
    const role = this.roles.get(user.roleId)
    if (!role) return user.customPermissions
    
    // If user has wildcard permission, return all permissions
    if (role.permissions.includes('*')) {
      return Object.keys(this.availablePermissions)
    }
    
    // Combine role and custom permissions
    const permissions = new Set([...role.permissions, ...user.customPermissions])
    return Array.from(permissions)
  }

  /**
   * Get user by email
   */
  getUserByEmail(email) {
    return Array.from(this.users.values()).find(user => 
      user.email.toLowerCase() === email.toLowerCase() && user.status !== 'deleted'
    )
  }

  /**
   * Get team members
   */
  getTeamMembers(teamId) {
    const team = this.teams.get(teamId)
    if (!team) return []
    
    return team.members.map(member => {
      const user = this.users.get(member.userId)
      return {
        ...member,
        user: user ? {
          id: user.id,
          email: user.email,
          firstName: user.firstName,
          lastName: user.lastName,
          displayName: user.displayName,
          avatar: user.avatar,
          status: user.status
        } : null
      }
    }).filter(member => member.user)
  }

  /**
   * Get user's teams
   */
  getUserTeams(userId) {
    const user = this.users.get(userId)
    if (!user) return []
    
    return user.teamIds.map(teamId => this.teams.get(teamId)).filter(Boolean)
  }

  // Utility methods
  generateUserId() {
    return `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  generateTeamId() {
    return `team_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  generateInvitationId() {
    return `inv_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  validateUserData(userData) {
    if (!userData.email) throw new Error('Email is required')
    if (!userData.firstName) throw new Error('First name is required')
    if (!userData.lastName) throw new Error('Last name is required')
    
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRegex.test(userData.email)) {
      throw new Error('Invalid email format')
    }
  }

  validateTeamData(teamData) {
    if (!teamData.name) throw new Error('Team name is required')
    if (teamData.name.length < 2) throw new Error('Team name must be at least 2 characters')
    if (teamData.name.length > 50) throw new Error('Team name must be less than 50 characters')
  }

  setupDefaultRoles() {
    for (const [key, role] of Object.entries(this.defaultRoles)) {
      this.roles.set(key.toLowerCase(), role)
    }
  }

  setupSessionManagement() {
    // Clean up expired sessions every hour
    setInterval(() => {
      this.cleanupExpiredSessions()
    }, 60 * 60 * 1000)
  }

  setupInvitationCleanup() {
    // Clean up expired invitations daily
    setInterval(() => {
      this.cleanupExpiredInvitations()
    }, 24 * 60 * 60 * 1000)
  }

  cleanupExpiredSessions() {
    const now = Date.now()
    for (const [sessionId, session] of this.sessions.entries()) {
      if (session.expiresAt < now) {
        this.sessions.delete(sessionId)
      }
    }
  }

  cleanupExpiredInvitations() {
    const now = Date.now()
    for (const [invitationId, invitation] of this.invitations.entries()) {
      if (invitation.expiresAt < now && invitation.status === 'pending') {
        invitation.status = 'expired'
      }
    }
  }

  getDefaultNotificationSettings() {
    return {
      email: true,
      push: true,
      agentUpdates: true,
      teamUpdates: true,
      billingUpdates: true,
      securityAlerts: true
    }
  }

  // Placeholder methods for email sending
  async sendWelcomeEmail(user) {
    console.log(`Sending welcome email to ${user.email}`)
  }

  async sendInvitationEmail(invitation, team, inviter) {
    console.log(`Sending team invitation to ${invitation.email} for team ${team.name}`)
  }

  // Placeholder methods for database operations
  async loadUsers() {
    console.log('Loading users from database...')
  }

  async loadTeams() {
    console.log('Loading teams from database...')
  }
}

export const userManagementService = new UserManagementService()
