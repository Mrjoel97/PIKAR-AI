/**
 * Database Connection Manager
 * Handles PostgreSQL connections with connection pooling and error handling
 */

import { Pool } from 'pg'
import { environmentConfig } from '@/config/environment'
import { loggingService } from '@/services/loggingService'

class DatabaseConnection {
  constructor() {
    this.pool = null
    this.isConnected = false
    this.connectionAttempts = 0
    this.maxRetries = 5
    this.retryDelay = 5000 // 5 seconds
  }

  /**
   * Initialize database connection
   */
  async initialize() {
    try {
      console.log('🗄️ Initializing database connection...')
      
      const config = {
        connectionString: environmentConfig.database.url,
        ssl: environmentConfig.database.ssl ? {
          rejectUnauthorized: false
        } : false,
        
        // Connection pool settings
        max: environmentConfig.database.maxConnections || 20,
        min: environmentConfig.database.minConnections || 2,
        idleTimeoutMillis: 30000,
        connectionTimeoutMillis: 10000,
        
        // Query settings
        statement_timeout: 30000,
        query_timeout: 30000,
        
        // Application name for monitoring
        application_name: 'pikar-ai'
      }
      
      this.pool = new Pool(config)
      
      // Test connection
      await this.testConnection()
      
      // Setup event handlers
      this.setupEventHandlers()
      
      this.isConnected = true
      console.log('✅ Database connection established successfully')
      
    } catch (error) {
      console.error('❌ Database connection failed:', error)
      await this.handleConnectionError(error)
      throw error
    }
  }

  /**
   * Test database connection
   */
  async testConnection() {
    const client = await this.pool.connect()
    try {
      const result = await client.query('SELECT NOW() as current_time, version() as version')
      console.log('Database connected:', result.rows[0].current_time)
      return result.rows[0]
    } finally {
      client.release()
    }
  }

  /**
   * Setup event handlers for connection monitoring
   */
  setupEventHandlers() {
    this.pool.on('connect', (client) => {
      console.log('New database client connected')
      loggingService.info('Database client connected', {
        totalCount: this.pool.totalCount,
        idleCount: this.pool.idleCount,
        waitingCount: this.pool.waitingCount
      })
    })

    this.pool.on('acquire', (client) => {
      loggingService.debug('Database client acquired from pool')
    })

    this.pool.on('remove', (client) => {
      console.log('Database client removed from pool')
      loggingService.info('Database client removed', {
        totalCount: this.pool.totalCount,
        idleCount: this.pool.idleCount
      })
    })

    this.pool.on('error', (error, client) => {
      console.error('Database pool error:', error)
      loggingService.error('Database pool error', error, {
        totalCount: this.pool.totalCount,
        idleCount: this.pool.idleCount,
        waitingCount: this.pool.waitingCount
      })
    })
  }

  /**
   * Handle connection errors with retry logic
   */
  async handleConnectionError(error) {
    this.connectionAttempts++
    
    if (this.connectionAttempts < this.maxRetries) {
      console.log(`Retrying database connection (${this.connectionAttempts}/${this.maxRetries})...`)
      
      await new Promise(resolve => setTimeout(resolve, this.retryDelay))
      
      try {
        await this.initialize()
      } catch (retryError) {
        await this.handleConnectionError(retryError)
      }
    } else {
      console.error('Max database connection retries exceeded')
      throw new Error('Database connection failed after maximum retries')
    }
  }

  /**
   * Execute a query with error handling
   */
  async query(text, params = []) {
    if (!this.isConnected) {
      throw new Error('Database not connected')
    }

    const start = Date.now()
    
    try {
      const result = await this.pool.query(text, params)
      const duration = Date.now() - start
      
      loggingService.debug('Database query executed', {
        query: text.substring(0, 100) + (text.length > 100 ? '...' : ''),
        duration,
        rowCount: result.rowCount
      })
      
      return result
    } catch (error) {
      const duration = Date.now() - start
      
      loggingService.error('Database query failed', error, {
        query: text.substring(0, 100) + (text.length > 100 ? '...' : ''),
        params: params.length > 0 ? '[PARAMS]' : 'none',
        duration
      })
      
      throw error
    }
  }

  /**
   * Execute a transaction
   */
  async transaction(callback) {
    if (!this.isConnected) {
      throw new Error('Database not connected')
    }

    const client = await this.pool.connect()
    
    try {
      await client.query('BEGIN')
      
      const result = await callback(client)
      
      await client.query('COMMIT')
      return result
      
    } catch (error) {
      await client.query('ROLLBACK')
      throw error
    } finally {
      client.release()
    }
  }

  /**
   * Get a client from the pool for manual transaction management
   */
  async getClient() {
    if (!this.isConnected) {
      throw new Error('Database not connected')
    }
    
    return await this.pool.connect()
  }

  /**
   * Get connection pool statistics
   */
  getPoolStats() {
    if (!this.pool) {
      return null
    }
    
    return {
      totalCount: this.pool.totalCount,
      idleCount: this.pool.idleCount,
      waitingCount: this.pool.waitingCount,
      maxConnections: this.pool.options.max,
      isConnected: this.isConnected
    }
  }

  /**
   * Health check for monitoring
   */
  async healthCheck() {
    try {
      const result = await this.query('SELECT 1 as health_check')
      const stats = this.getPoolStats()
      
      return {
        status: 'healthy',
        connected: this.isConnected,
        poolStats: stats,
        timestamp: new Date().toISOString()
      }
    } catch (error) {
      return {
        status: 'unhealthy',
        error: error.message,
        connected: this.isConnected,
        timestamp: new Date().toISOString()
      }
    }
  }

  /**
   * Close all connections
   */
  async close() {
    if (this.pool) {
      console.log('Closing database connections...')
      await this.pool.end()
      this.isConnected = false
      console.log('Database connections closed')
    }
  }

  /**
   * Graceful shutdown
   */
  async gracefulShutdown() {
    console.log('Initiating graceful database shutdown...')
    
    try {
      // Wait for active queries to complete (max 30 seconds)
      const shutdownTimeout = 30000
      const startTime = Date.now()
      
      while (this.pool && this.pool.totalCount > this.pool.idleCount) {
        if (Date.now() - startTime > shutdownTimeout) {
          console.warn('Forcing database shutdown due to timeout')
          break
        }
        
        console.log('Waiting for active queries to complete...')
        await new Promise(resolve => setTimeout(resolve, 1000))
      }
      
      await this.close()
      console.log('Database shutdown completed')
      
    } catch (error) {
      console.error('Error during database shutdown:', error)
      throw error
    }
  }
}

// Create singleton instance
export const db = new DatabaseConnection()

// Graceful shutdown handling
process.on('SIGTERM', async () => {
  console.log('SIGTERM received, shutting down database...')
  await db.gracefulShutdown()
  process.exit(0)
})

process.on('SIGINT', async () => {
  console.log('SIGINT received, shutting down database...')
  await db.gracefulShutdown()
  process.exit(0)
})

// Export query helper functions
export const query = (text, params) => db.query(text, params)
export const transaction = (callback) => db.transaction(callback)
export const getClient = () => db.getClient()

export default db
