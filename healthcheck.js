#!/usr/bin/env node

/**
 * Docker Health Check Script
 * Comprehensive health check for PIKAR AI application
 */

const http = require('http')
const fs = require('fs')
const path = require('path')

const HEALTH_CHECK_PORT = process.env.PORT || 3000
const HEALTH_CHECK_TIMEOUT = 5000
const MAX_MEMORY_USAGE = 1024 * 1024 * 1024 // 1GB
const MAX_CPU_USAGE = 80 // 80%

class HealthChecker {
  constructor() {
    this.checks = [
      { name: 'HTTP Server', check: this.checkHTTPServer.bind(this) },
      { name: 'Memory Usage', check: this.checkMemoryUsage.bind(this) },
      { name: 'Disk Space', check: this.checkDiskSpace.bind(this) },
      { name: 'Application Status', check: this.checkApplicationStatus.bind(this) },
      { name: 'Dependencies', check: this.checkDependencies.bind(this) }
    ]
  }

  async runHealthCheck() {
    console.log('🏥 Running health check...')
    
    const results = []
    let overallHealth = true

    for (const { name, check } of this.checks) {
      try {
        const startTime = Date.now()
        const result = await check()
        const duration = Date.now() - startTime
        
        results.push({
          name,
          status: result.healthy ? 'PASS' : 'FAIL',
          message: result.message,
          duration: `${duration}ms`,
          details: result.details || {}
        })
        
        if (!result.healthy) {
          overallHealth = false
        }
        
        console.log(`${result.healthy ? '✅' : '❌'} ${name}: ${result.message}`)
        
      } catch (error) {
        results.push({
          name,
          status: 'ERROR',
          message: error.message,
          error: error.stack
        })
        
        overallHealth = false
        console.log(`❌ ${name}: ERROR - ${error.message}`)
      }
    }

    const summary = {
      status: overallHealth ? 'HEALTHY' : 'UNHEALTHY',
      timestamp: new Date().toISOString(),
      uptime: process.uptime(),
      version: process.env.npm_package_version || '1.0.0',
      environment: process.env.NODE_ENV || 'unknown',
      checks: results
    }

    console.log(`\n🏥 Health check ${overallHealth ? 'PASSED' : 'FAILED'}`)
    console.log(`📊 Summary: ${JSON.stringify(summary, null, 2)}`)

    // Exit with appropriate code
    process.exit(overallHealth ? 0 : 1)
  }

  async checkHTTPServer() {
    return new Promise((resolve) => {
      const request = http.request({
        hostname: 'localhost',
        port: HEALTH_CHECK_PORT,
        path: '/health',
        method: 'GET',
        timeout: HEALTH_CHECK_TIMEOUT
      }, (response) => {
        let data = ''
        
        response.on('data', (chunk) => {
          data += chunk
        })
        
        response.on('end', () => {
          if (response.statusCode === 200) {
            resolve({
              healthy: true,
              message: 'HTTP server responding',
              details: {
                statusCode: response.statusCode,
                responseTime: Date.now()
              }
            })
          } else {
            resolve({
              healthy: false,
              message: `HTTP server returned status ${response.statusCode}`,
              details: { statusCode: response.statusCode, response: data }
            })
          }
        })
      })

      request.on('error', (error) => {
        resolve({
          healthy: false,
          message: `HTTP server not responding: ${error.message}`,
          details: { error: error.message }
        })
      })

      request.on('timeout', () => {
        request.destroy()
        resolve({
          healthy: false,
          message: 'HTTP server timeout',
          details: { timeout: HEALTH_CHECK_TIMEOUT }
        })
      })

      request.end()
    })
  }

  async checkMemoryUsage() {
    const memoryUsage = process.memoryUsage()
    const totalMemory = memoryUsage.rss
    const heapUsed = memoryUsage.heapUsed
    const heapTotal = memoryUsage.heapTotal
    
    const memoryHealthy = totalMemory < MAX_MEMORY_USAGE
    
    return {
      healthy: memoryHealthy,
      message: memoryHealthy 
        ? `Memory usage normal (${Math.round(totalMemory / 1024 / 1024)}MB)`
        : `Memory usage high (${Math.round(totalMemory / 1024 / 1024)}MB)`,
      details: {
        rss: Math.round(totalMemory / 1024 / 1024),
        heapUsed: Math.round(heapUsed / 1024 / 1024),
        heapTotal: Math.round(heapTotal / 1024 / 1024),
        external: Math.round(memoryUsage.external / 1024 / 1024),
        maxMemoryMB: Math.round(MAX_MEMORY_USAGE / 1024 / 1024)
      }
    }
  }

  async checkDiskSpace() {
    try {
      const stats = fs.statSync('/app')
      const logDir = '/app/logs'
      
      let logDirSize = 0
      if (fs.existsSync(logDir)) {
        const logFiles = fs.readdirSync(logDir)
        logDirSize = logFiles.reduce((total, file) => {
          const filePath = path.join(logDir, file)
          const fileStats = fs.statSync(filePath)
          return total + fileStats.size
        }, 0)
      }
      
      const logDirSizeMB = Math.round(logDirSize / 1024 / 1024)
      const diskHealthy = logDirSizeMB < 100 // Less than 100MB of logs
      
      return {
        healthy: diskHealthy,
        message: diskHealthy 
          ? `Disk space normal (logs: ${logDirSizeMB}MB)`
          : `Log directory size high (${logDirSizeMB}MB)`,
        details: {
          logDirectoryMB: logDirSizeMB,
          logDirectory: logDir
        }
      }
    } catch (error) {
      return {
        healthy: false,
        message: `Disk check failed: ${error.message}`,
        details: { error: error.message }
      }
    }
  }

  async checkApplicationStatus() {
    try {
      // Check if main application files exist
      const requiredFiles = [
        '/app/package.json',
        '/app/dist'
      ]
      
      const missingFiles = []
      for (const file of requiredFiles) {
        if (!fs.existsSync(file)) {
          missingFiles.push(file)
        }
      }
      
      if (missingFiles.length > 0) {
        return {
          healthy: false,
          message: `Missing required files: ${missingFiles.join(', ')}`,
          details: { missingFiles }
        }
      }
      
      // Check environment variables
      const requiredEnvVars = ['NODE_ENV']
      const missingEnvVars = requiredEnvVars.filter(envVar => !process.env[envVar])
      
      if (missingEnvVars.length > 0) {
        return {
          healthy: false,
          message: `Missing environment variables: ${missingEnvVars.join(', ')}`,
          details: { missingEnvVars }
        }
      }
      
      return {
        healthy: true,
        message: 'Application status normal',
        details: {
          nodeVersion: process.version,
          platform: process.platform,
          arch: process.arch,
          pid: process.pid,
          uptime: Math.round(process.uptime())
        }
      }
    } catch (error) {
      return {
        healthy: false,
        message: `Application status check failed: ${error.message}`,
        details: { error: error.message }
      }
    }
  }

  async checkDependencies() {
    try {
      // Check if critical dependencies are available
      const packageJson = JSON.parse(fs.readFileSync('/app/package.json', 'utf8'))
      const dependencies = Object.keys(packageJson.dependencies || {})
      
      // Check if node_modules exists and has expected structure
      const nodeModulesPath = '/app/node_modules'
      if (!fs.existsSync(nodeModulesPath)) {
        return {
          healthy: false,
          message: 'node_modules directory not found',
          details: { path: nodeModulesPath }
        }
      }
      
      // Sample a few critical dependencies
      const criticalDeps = ['react', 'express', 'axios'].filter(dep => dependencies.includes(dep))
      const missingDeps = []
      
      for (const dep of criticalDeps) {
        const depPath = path.join(nodeModulesPath, dep)
        if (!fs.existsSync(depPath)) {
          missingDeps.push(dep)
        }
      }
      
      if (missingDeps.length > 0) {
        return {
          healthy: false,
          message: `Missing critical dependencies: ${missingDeps.join(', ')}`,
          details: { missingDeps, totalDeps: dependencies.length }
        }
      }
      
      return {
        healthy: true,
        message: 'Dependencies available',
        details: {
          totalDependencies: dependencies.length,
          checkedDependencies: criticalDeps.length
        }
      }
    } catch (error) {
      return {
        healthy: false,
        message: `Dependency check failed: ${error.message}`,
        details: { error: error.message }
      }
    }
  }
}

// Run health check
const healthChecker = new HealthChecker()
healthChecker.runHealthCheck().catch((error) => {
  console.error('❌ Health check failed:', error)
  process.exit(1)
})
