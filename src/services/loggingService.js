/**
 * Logging Service
 * Comprehensive logging system with structured logging, log levels, and centralized management
 */

import { environmentConfig } from '@/config/environment'

class LoggingService {
  constructor() {
fix/stripe-client-safe-payments
    // Log levels hierarchy (define before computing level)

    // Define levels before computing the level
main
    this.logLevels = {
      error: 0,
      warn: 1,
      info: 2,
      debug: 3,
      trace: 4
    }

    this.logLevel = this.getLogLevel()
    this.logBuffer = []
    this.maxBufferSize = 1000
    this.flushInterval = 30000 // 30 seconds
    this.isInitialized = false

    // Log formatters
    this.formatters = {
      json: this.formatJSON.bind(this),
      text: this.formatText.bind(this),
      structured: this.formatStructured.bind(this)
    }

    // Log transports
    this.transports = new Map()

    this.setupTransports()
    this.startFlushInterval()
  }

  /**
   * Initialize logging service
   */
  async initialize() {
    try {
      console.log('📝 Initializing Logging Service...')
      
      // Setup console transport
      this.addTransport('console', {
        level: this.logLevel,
        format: 'structured',
        enabled: true
      })
      
      // Setup remote transport if configured (optional)
      const remoteEndpoint = (typeof environmentConfig.get === 'function')
        ? environmentConfig.get('VITE_LOG_REMOTE_ENDPOINT', null)
        : null
      if (remoteEndpoint) {
        this.addTransport('remote', {
          level: 'info',
          format: 'json',
          endpoint: remoteEndpoint,
          enabled: true,
          batchSize: 50
        })
      }

      // Setup file transport for Node.js environments (optional)
      const fileEnabled = (typeof environmentConfig.get === 'function')
        ? environmentConfig.get('VITE_LOG_FILE_ENABLED', false)
        : false
      const filename = (typeof environmentConfig.get === 'function')
        ? environmentConfig.get('VITE_LOG_FILE_NAME', 'app.log')
        : 'app.log'
      if (typeof window === 'undefined' && fileEnabled) {
        this.addTransport('file', {
          level: 'info',
          format: 'json',
          filename,
          enabled: true
        })
      }
      
      this.isInitialized = true
      
      this.info('Logging Service initialized', {
        logLevel: this.logLevel,
        transports: Array.from(this.transports.keys()),
        bufferSize: this.maxBufferSize
      })
      
    } catch (error) {
      console.error('❌ Logging Service initialization failed:', error)
      throw error
    }
  }

  /**
   * Get current log level from environment
   */
  getLogLevel() {
fix/stripe-client-safe-payments
    // Read from environment with safe default
    
    // Safe env read with default

  main
    const envLevel = (typeof environmentConfig.get === 'function')
      ? environmentConfig.get('VITE_LOG_LEVEL', 'info')
      : 'info'
    const levels = { error: 0, warn: 1, info: 2, debug: 3, trace: 4 }
    return Object.prototype.hasOwnProperty.call(levels, envLevel) ? envLevel : 'info'
  }

  /**
   * Setup default transports
   */
  setupTransports() {
    // Console transport is always available
    this.transports.set('console', {
      level: this.logLevel,
      format: 'structured',
      enabled: true,
      write: this.writeToConsole.bind(this)
    })
  }

  /**
   * Add a transport
   */
  addTransport(name, config) {
    const transport = {
      ...config,
      write: this.getTransportWriter(name, config)
    }
    
    this.transports.set(name, transport)
  }

  /**
   * Get transport writer function
   */
  getTransportWriter(name, config) {
    switch (name) {
      case 'console':
        return this.writeToConsole.bind(this)
      case 'remote':
        return this.writeToRemote.bind(this, config)
      case 'file':
        return this.writeToFile.bind(this, config)
      default:
        return this.writeToConsole.bind(this)
    }
  }

  /**
   * Log error message
   */
  error(message, meta = {}, error = null) {
    this.log('error', message, {
      ...meta,
      error: error ? {
        name: error.name,
        message: error.message,
        stack: error.stack
      } : undefined
    })
  }

  /**
   * Log warning message
   */
  warn(message, meta = {}) {
    this.log('warn', message, meta)
  }

  /**
   * Log info message
   */
  info(message, meta = {}) {
    this.log('info', message, meta)
  }

  /**
   * Log debug message
   */
  debug(message, meta = {}) {
    this.log('debug', message, meta)
  }

  /**
   * Log trace message
   */
  trace(message, meta = {}) {
    this.log('trace', message, meta)
  }

  /**
   * Main logging method
   */
  log(level, message, meta = {}) {
    // Check if log level is enabled
    if (this.logLevels[level] > this.logLevels[this.logLevel]) {
      return
    }

    const logEntry = this.createLogEntry(level, message, meta)
    
    // Add to buffer
    this.logBuffer.push(logEntry)
    
    // Maintain buffer size
    if (this.logBuffer.length > this.maxBufferSize) {
      this.logBuffer.shift()
    }
    
    // Write to transports
    this.writeToTransports(logEntry)
  }

  /**
   * Create structured log entry
   */
  createLogEntry(level, message, meta = {}) {
    return {
      timestamp: new Date().toISOString(),
      level: level.toUpperCase(),
      message,
      meta: {
        ...meta,
        environment: environmentConfig.environment || 'unknown',
        service: 'pikar-ai',
        version: environmentConfig.version || '1.0.0',
        sessionId: this.getSessionId(),
        userId: this.getUserId(),
        requestId: this.getRequestId()
      }
    }
  }

  /**
   * Write log entry to all enabled transports
   */
  writeToTransports(logEntry) {
    for (const [name, transport] of this.transports.entries()) {
      if (!transport.enabled) continue
      
      // Check transport log level
      if (this.logLevels[logEntry.level.toLowerCase()] > this.logLevels[transport.level]) {
        continue
      }
      
      try {
        transport.write(logEntry, transport)
      } catch (error) {
        console.error(`Failed to write to transport ${name}:`, error)
      }
    }
  }

  /**
   * Write to console transport
   */
  writeToConsole(logEntry, transport) {
    const formatted = this.formatters[transport.format](logEntry)
    
    switch (logEntry.level) {
      case 'ERROR':
        console.error(formatted)
        break
      case 'WARN':
        console.warn(formatted)
        break
      case 'INFO':
        console.info(formatted)
        break
      case 'DEBUG':
        console.debug(formatted)
        break
      case 'TRACE':
        console.trace(formatted)
        break
      default:
        console.log(formatted)
    }
  }

  /**
   * Write to remote transport
   */
  async writeToRemote(config, logEntry) {
    // Add to remote buffer
    if (!this.remoteBuffer) {
      this.remoteBuffer = []
    }
    
    this.remoteBuffer.push(logEntry)
    
    // Flush if batch size reached
    if (this.remoteBuffer.length >= (config.batchSize || 50)) {
      await this.flushRemoteBuffer(config)
    }
  }

  /**
   * Write to file transport (Node.js only)
   */
  async writeToFile(config, logEntry) {
    if (typeof window !== 'undefined') return
    
    try {
      const fs = require('fs').promises
      const formatted = this.formatters[config.format](logEntry) + '\n'
      
      await fs.appendFile(config.filename, formatted, 'utf8')
    } catch (error) {
      console.error('Failed to write to log file:', error)
    }
  }

  /**
   * Flush remote buffer
   */
  async flushRemoteBuffer(config) {
    if (!this.remoteBuffer || this.remoteBuffer.length === 0) return
    
    const logs = [...this.remoteBuffer]
    this.remoteBuffer = []
    
    try {
      const response = await fetch(config.endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${environmentConfig.logging.apiKey || ''}`
        },
        body: JSON.stringify({
          logs,
          source: 'pikar-ai',
          environment: environmentConfig.environment
        })
      })
      
      if (!response.ok) {
        throw new Error(`Remote logging failed: ${response.status} ${response.statusText}`)
      }
    } catch (error) {
      console.error('Failed to send logs to remote endpoint:', error)
      // Re-add logs to buffer for retry
      this.remoteBuffer.unshift(...logs)
    }
  }

  /**
   * Start flush interval for remote logging
   */
  startFlushInterval() {
    setInterval(async () => {
      const remoteTransport = this.transports.get('remote')
      if (remoteTransport && remoteTransport.enabled) {
        await this.flushRemoteBuffer(remoteTransport)
      }
    }, this.flushInterval)
  }

  /**
   * Format log entry as JSON
   */
  formatJSON(logEntry) {
    return JSON.stringify(logEntry)
  }

  /**
   * Format log entry as text
   */
  formatText(logEntry) {
    const { timestamp, level, message, meta } = logEntry
    const metaStr = Object.keys(meta).length > 0 ? ` ${JSON.stringify(meta)}` : ''
    return `${timestamp} [${level}] ${message}${metaStr}`
  }

  /**
   * Format log entry as structured text
   */
  formatStructured(logEntry) {
    const { timestamp, level, message, meta } = logEntry
    const time = new Date(timestamp).toLocaleTimeString()
    
    let formatted = `${time} ${this.getLevelIcon(level)} [${level}] ${message}`
    
    // Add important meta fields
    if (meta.userId) formatted += ` | User: ${meta.userId}`
    if (meta.requestId) formatted += ` | Request: ${meta.requestId}`
    if (meta.error) formatted += ` | Error: ${meta.error.message}`
    
    // Add remaining meta as JSON if present
    const remainingMeta = { ...meta }
    delete remainingMeta.userId
    delete remainingMeta.requestId
    delete remainingMeta.error
    delete remainingMeta.environment
    delete remainingMeta.service
    delete remainingMeta.version
    delete remainingMeta.sessionId
    
    if (Object.keys(remainingMeta).length > 0) {
      formatted += ` | Meta: ${JSON.stringify(remainingMeta)}`
    }
    
    return formatted
  }

  /**
   * Get icon for log level
   */
  getLevelIcon(level) {
    const icons = {
      ERROR: '❌',
      WARN: '⚠️',
      INFO: 'ℹ️',
      DEBUG: '🐛',
      TRACE: '🔍'
    }
    return icons[level] || 'ℹ️'
  }

  /**
   * Get session ID from context
   */
  getSessionId() {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('sessionId') || 'unknown'
    }
    return 'server'
  }

  /**
   * Get user ID from context
   */
  getUserId() {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('userId') || 'anonymous'
    }
    return 'system'
  }

  /**
   * Get request ID from context
   */
  getRequestId() {
    // This would typically come from request context
    return 'req_' + Math.random().toString(36).substr(2, 9)
  }

  /**
   * Create child logger with additional context
   */
  child(context = {}) {
    return {
      error: (message, meta = {}, error = null) => 
        this.error(message, { ...context, ...meta }, error),
      warn: (message, meta = {}) => 
        this.warn(message, { ...context, ...meta }),
      info: (message, meta = {}) => 
        this.info(message, { ...context, ...meta }),
      debug: (message, meta = {}) => 
        this.debug(message, { ...context, ...meta }),
      trace: (message, meta = {}) => 
        this.trace(message, { ...context, ...meta })
    }
  }

  /**
   * Log performance metrics
   */
  logPerformance(operation, duration, meta = {}) {
    this.info(`Performance: ${operation}`, {
      ...meta,
      operation,
      duration,
      performanceLog: true
    })
  }

  /**
   * Log security events
   */
  logSecurity(event, meta = {}) {
    this.warn(`Security: ${event}`, {
      ...meta,
      securityEvent: event,
      securityLog: true
    })
  }

  /**
   * Log business events
   */
  logBusiness(event, meta = {}) {
    this.info(`Business: ${event}`, {
      ...meta,
      businessEvent: event,
      businessLog: true
    })
  }

  /**
   * Log API requests
   */
  logAPIRequest(method, url, status, duration, meta = {}) {
    const level = status >= 400 ? 'warn' : 'info'
    this[level](`API ${method} ${url}`, {
      ...meta,
      method,
      url,
      status,
      duration,
      apiLog: true
    })
  }

  /**
   * Log agent executions
   */
  logAgentExecution(agentType, task, status, duration, meta = {}) {
    const level = status === 'success' ? 'info' : 'warn'
    this[level](`Agent ${agentType}: ${task}`, {
      ...meta,
      agentType,
      task,
      status,
      duration,
      agentLog: true
    })
  }

  /**
   * Get recent logs
   */
  getRecentLogs(count = 100, level = null) {
    let logs = [...this.logBuffer]
    
    if (level) {
      logs = logs.filter(log => log.level.toLowerCase() === level.toLowerCase())
    }
    
    return logs.slice(-count)
  }

  /**
   * Search logs
   */
  searchLogs(query, options = {}) {
    const {
      level = null,
      startTime = null,
      endTime = null,
      limit = 100
    } = options
    
    let logs = [...this.logBuffer]
    
    // Filter by level
    if (level) {
      logs = logs.filter(log => log.level.toLowerCase() === level.toLowerCase())
    }
    
    // Filter by time range
    if (startTime) {
      logs = logs.filter(log => new Date(log.timestamp) >= new Date(startTime))
    }
    
    if (endTime) {
      logs = logs.filter(log => new Date(log.timestamp) <= new Date(endTime))
    }
    
    // Search in message and meta
    if (query) {
      const queryLower = query.toLowerCase()
      logs = logs.filter(log => {
        const messageMatch = log.message.toLowerCase().includes(queryLower)
        const metaMatch = JSON.stringify(log.meta).toLowerCase().includes(queryLower)
        return messageMatch || metaMatch
      })
    }
    
    return logs.slice(-limit)
  }

  /**
   * Get log statistics
   */
  getLogStatistics(timeWindow = 3600000) { // Default 1 hour
    const cutoff = Date.now() - timeWindow
    const recentLogs = this.logBuffer.filter(log => 
      new Date(log.timestamp).getTime() > cutoff
    )
    
    const stats = {
      total: recentLogs.length,
      byLevel: {},
      byHour: {},
      errors: 0,
      warnings: 0
    }
    
    recentLogs.forEach(log => {
      // Count by level
      stats.byLevel[log.level] = (stats.byLevel[log.level] || 0) + 1
      
      // Count by hour
      const hour = new Date(log.timestamp).getHours()
      stats.byHour[hour] = (stats.byHour[hour] || 0) + 1
      
      // Count errors and warnings
      if (log.level === 'ERROR') stats.errors++
      if (log.level === 'WARN') stats.warnings++
    })
    
    return stats
  }

  /**
   * Clear log buffer
   */
  clearLogs() {
    this.logBuffer = []
  }

  /**
   * Set log level
   */
  setLogLevel(level) {
    if (Object.prototype.hasOwnProperty.call(this.logLevels, level)) {
      this.logLevel = level
      this.info(`Log level changed to ${level}`)
    }
  }

  /**
   * Enable/disable transport
   */
  setTransportEnabled(name, enabled) {
    const transport = this.transports.get(name)
    if (transport) {
      transport.enabled = enabled
      this.info(`Transport ${name} ${enabled ? 'enabled' : 'disabled'}`)
    }
  }
}

export const loggingService = new LoggingService()
