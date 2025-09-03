/**
 * User Repository
 * Database operations for user management
 */

import { db } from '../connection.js'
import { loggingService } from '@/services/loggingService'

class UserRepository {
  /**
   * Create a new user
   */
  async create(userData) {
    const query = `
      INSERT INTO users (
        email, first_name, last_name, display_name, avatar_url,
        status, role_id, custom_permissions, team_ids, primary_team_id,
        profile, two_factor_enabled, created_by
      ) VALUES (
        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13
      ) RETURNING *
    `
    
    const values = [
      userData.email,
      userData.firstName,
      userData.lastName,
      userData.displayName,
      userData.avatar,
      userData.status || 'active',
      userData.roleId || 'member',
      JSON.stringify(userData.customPermissions || []),
      JSON.stringify(userData.teamIds || []),
      userData.primaryTeamId,
      JSON.stringify(userData.profile || {}),
      userData.twoFactorEnabled || false,
      userData.createdBy
    ]
    
    try {
      const result = await db.query(query, values)
      return this.mapUserFromDb(result.rows[0])
    } catch (error) {
      loggingService.error('Failed to create user', error, { email: userData.email })
      throw error
    }
  }

  /**
   * Find user by ID
   */
  async findById(userId) {
    const query = 'SELECT * FROM users WHERE id = $1 AND status != $2'
    
    try {
      const result = await db.query(query, [userId, 'deleted'])
      return result.rows[0] ? this.mapUserFromDb(result.rows[0]) : null
    } catch (error) {
      loggingService.error('Failed to find user by ID', error, { userId })
      throw error
    }
  }

  /**
   * Find user by email
   */
  async findByEmail(email) {
    const query = 'SELECT * FROM users WHERE LOWER(email) = LOWER($1) AND status != $2'
    
    try {
      const result = await db.query(query, [email, 'deleted'])
      return result.rows[0] ? this.mapUserFromDb(result.rows[0]) : null
    } catch (error) {
      loggingService.error('Failed to find user by email', error, { email })
      throw error
    }
  }

  /**
   * Update user
   */
  async update(userId, updates) {
    const allowedFields = [
      'first_name', 'last_name', 'display_name', 'avatar_url',
      'status', 'email_verified', 'last_login', 'login_count',
      'role_id', 'custom_permissions', 'team_ids', 'primary_team_id',
      'profile', 'two_factor_enabled', 'failed_login_attempts', 'locked_until'
    ]
    
    const updateFields = []
    const values = []
    let paramIndex = 1
    
    for (const [key, value] of Object.entries(updates)) {
      const dbField = this.camelToSnake(key)
      if (allowedFields.includes(dbField)) {
        updateFields.push(`${dbField} = $${paramIndex}`)
        
        // Handle JSON fields
        if (['custom_permissions', 'team_ids', 'profile'].includes(dbField)) {
          values.push(JSON.stringify(value))
        } else {
          values.push(value)
        }
        paramIndex++
      }
    }
    
    if (updateFields.length === 0) {
      throw new Error('No valid fields to update')
    }
    
    updateFields.push(`updated_at = CURRENT_TIMESTAMP`)
    values.push(userId)
    
    const query = `
      UPDATE users 
      SET ${updateFields.join(', ')}
      WHERE id = $${paramIndex}
      RETURNING *
    `
    
    try {
      const result = await db.query(query, values)
      return result.rows[0] ? this.mapUserFromDb(result.rows[0]) : null
    } catch (error) {
      loggingService.error('Failed to update user', error, { userId, updates: Object.keys(updates) })
      throw error
    }
  }

  /**
   * Soft delete user
   */
  async delete(userId, deletedBy) {
    const query = `
      UPDATE users 
      SET status = 'deleted', 
          team_ids = '[]',
          primary_team_id = NULL,
          updated_at = CURRENT_TIMESTAMP
      WHERE id = $1
      RETURNING *
    `
    
    try {
      const result = await db.query(query, [userId])
      
      // Log the deletion
      if (result.rows[0]) {
        await this.logAuditEvent(userId, 'user_deleted', 'user', userId, {
          deletedBy,
          email: result.rows[0].email
        })
      }
      
      return result.rows[0] ? this.mapUserFromDb(result.rows[0]) : null
    } catch (error) {
      loggingService.error('Failed to delete user', error, { userId, deletedBy })
      throw error
    }
  }

  /**
   * Find users by role
   */
  async findByRole(roleId, limit = 100, offset = 0) {
    const query = `
      SELECT * FROM users 
      WHERE role_id = $1 AND status = 'active'
      ORDER BY created_at DESC
      LIMIT $2 OFFSET $3
    `
    
    try {
      const result = await db.query(query, [roleId, limit, offset])
      return result.rows.map(row => this.mapUserFromDb(row))
    } catch (error) {
      loggingService.error('Failed to find users by role', error, { roleId })
      throw error
    }
  }

  /**
   * Find users by team
   */
  async findByTeam(teamId, limit = 100, offset = 0) {
    const query = `
      SELECT u.* FROM users u
      JOIN team_members tm ON u.id = tm.user_id
      WHERE tm.team_id = $1 AND u.status = 'active'
      ORDER BY tm.joined_at DESC
      LIMIT $2 OFFSET $3
    `
    
    try {
      const result = await db.query(query, [teamId, limit, offset])
      return result.rows.map(row => this.mapUserFromDb(row))
    } catch (error) {
      loggingService.error('Failed to find users by team', error, { teamId })
      throw error
    }
  }

  /**
   * Search users
   */
  async search(searchTerm, limit = 50, offset = 0) {
    const query = `
      SELECT * FROM users 
      WHERE (
        LOWER(first_name) LIKE LOWER($1) OR 
        LOWER(last_name) LIKE LOWER($1) OR 
        LOWER(email) LIKE LOWER($1) OR
        LOWER(display_name) LIKE LOWER($1)
      ) AND status = 'active'
      ORDER BY 
        CASE 
          WHEN LOWER(email) = LOWER($2) THEN 1
          WHEN LOWER(email) LIKE LOWER($1) THEN 2
          WHEN LOWER(display_name) LIKE LOWER($1) THEN 3
          ELSE 4
        END,
        created_at DESC
      LIMIT $3 OFFSET $4
    `
    
    const searchPattern = `%${searchTerm}%`
    
    try {
      const result = await db.query(query, [searchPattern, searchTerm, limit, offset])
      return result.rows.map(row => this.mapUserFromDb(row))
    } catch (error) {
      loggingService.error('Failed to search users', error, { searchTerm })
      throw error
    }
  }

  /**
   * Get user statistics
   */
  async getStatistics() {
    const query = `
      SELECT 
        COUNT(*) as total_users,
        COUNT(CASE WHEN status = 'active' THEN 1 END) as active_users,
        COUNT(CASE WHEN status = 'inactive' THEN 1 END) as inactive_users,
        COUNT(CASE WHEN email_verified = true THEN 1 END) as verified_users,
        COUNT(CASE WHEN two_factor_enabled = true THEN 1 END) as two_factor_users,
        COUNT(CASE WHEN role_id = 'owner' THEN 1 END) as owners,
        COUNT(CASE WHEN role_id = 'admin' THEN 1 END) as admins,
        COUNT(CASE WHEN role_id = 'member' THEN 1 END) as members,
        COUNT(CASE WHEN created_at >= CURRENT_DATE - INTERVAL '30 days' THEN 1 END) as new_users_30d,
        COUNT(CASE WHEN last_login >= CURRENT_DATE - INTERVAL '30 days' THEN 1 END) as active_users_30d
      FROM users 
      WHERE status != 'deleted'
    `
    
    try {
      const result = await db.query(query)
      return result.rows[0]
    } catch (error) {
      loggingService.error('Failed to get user statistics', error)
      throw error
    }
  }

  /**
   * Update last login
   */
  async updateLastLogin(userId, ipAddress = null, userAgent = null) {
    const query = `
      UPDATE users 
      SET last_login = CURRENT_TIMESTAMP,
          login_count = login_count + 1,
          failed_login_attempts = 0,
          locked_until = NULL
      WHERE id = $1
      RETURNING last_login, login_count
    `
    
    try {
      const result = await db.query(query, [userId])
      
      // Log the login
      await this.logAuditEvent(userId, 'user_login', 'user', userId, {
        ipAddress,
        userAgent
      })
      
      return result.rows[0]
    } catch (error) {
      loggingService.error('Failed to update last login', error, { userId })
      throw error
    }
  }

  /**
   * Handle failed login attempt
   */
  async handleFailedLogin(userId, maxAttempts = 5, lockDuration = 30) {
    const query = `
      UPDATE users 
      SET failed_login_attempts = failed_login_attempts + 1,
          locked_until = CASE 
            WHEN failed_login_attempts + 1 >= $2 
            THEN CURRENT_TIMESTAMP + INTERVAL '${lockDuration} minutes'
            ELSE locked_until
          END
      WHERE id = $1
      RETURNING failed_login_attempts, locked_until
    `
    
    try {
      const result = await db.query(query, [userId, maxAttempts])
      
      if (result.rows[0]) {
        const { failed_login_attempts, locked_until } = result.rows[0]
        
        await this.logAuditEvent(userId, 'failed_login_attempt', 'user', userId, {
          attemptCount: failed_login_attempts,
          isLocked: !!locked_until
        })
        
        return {
          failedAttempts: failed_login_attempts,
          isLocked: !!locked_until,
          lockedUntil: locked_until
        }
      }
      
      return null
    } catch (error) {
      loggingService.error('Failed to handle failed login', error, { userId })
      throw error
    }
  }

  /**
   * Map database row to user object
   */
  mapUserFromDb(row) {
    return {
      id: row.id,
      email: row.email,
      firstName: row.first_name,
      lastName: row.last_name,
      displayName: row.display_name,
      avatar: row.avatar_url,
      status: row.status,
      emailVerified: row.email_verified,
      lastLogin: row.last_login,
      loginCount: row.login_count,
      roleId: row.role_id,
      customPermissions: row.custom_permissions || [],
      teamIds: row.team_ids || [],
      primaryTeamId: row.primary_team_id,
      profile: row.profile || {},
      twoFactorEnabled: row.two_factor_enabled,
      lastPasswordChange: row.last_password_change,
      failedLoginAttempts: row.failed_login_attempts,
      lockedUntil: row.locked_until,
      createdAt: row.created_at,
      updatedAt: row.updated_at,
      createdBy: row.created_by
    }
  }

  /**
   * Convert camelCase to snake_case
   */
  camelToSnake(str) {
    return str.replace(/[A-Z]/g, letter => `_${letter.toLowerCase()}`)
  }

  /**
   * Log audit event
   */
  async logAuditEvent(userId, action, resourceType, resourceId, details = {}) {
    const query = `
      INSERT INTO audit_logs (user_id, action, resource_type, resource_id, details)
      VALUES ($1, $2, $3, $4, $5)
    `
    
    try {
      await db.query(query, [
        userId,
        action,
        resourceType,
        resourceId,
        JSON.stringify(details)
      ])
    } catch (error) {
      loggingService.error('Failed to log audit event', error, {
        userId, action, resourceType, resourceId
      })
      // Don't throw - audit logging shouldn't break main operations
    }
  }
}

export const userRepository = new UserRepository()
export default userRepository
