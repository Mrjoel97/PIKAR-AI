#!/bin/sh
set -e

# PIKAR AI - Docker Entrypoint Script
# Handles application startup, configuration, and health checks

echo "🚀 Starting PIKAR AI application..."

# Environment validation
if [ -z "$NODE_ENV" ]; then
    echo "⚠️  NODE_ENV not set, defaulting to production"
    export NODE_ENV=production
fi

# Database migration check (if applicable)
if [ "$NODE_ENV" = "production" ] && [ "$RUN_MIGRATIONS" = "true" ]; then
    echo "🔄 Running database migrations..."
    npm run migrate || {
        echo "❌ Database migration failed"
        exit 1
    }
fi

# Cache warming (if applicable)
if [ "$WARM_CACHE" = "true" ]; then
    echo "🔥 Warming application cache..."
    npm run cache:warm || {
        echo "⚠️  Cache warming failed, continuing..."
    }
fi

# Security checks
echo "🔒 Running security checks..."
if [ -f "/app/security-check.js" ]; then
    node security-check.js || {
        echo "❌ Security check failed"
        exit 1
    }
fi

# Performance optimization
echo "⚡ Applying performance optimizations..."
export UV_THREADPOOL_SIZE=128
export NODE_OPTIONS="--max-old-space-size=2048 --optimize-for-size"

# Logging configuration
export LOG_LEVEL=${LOG_LEVEL:-info}
export LOG_FORMAT=${LOG_FORMAT:-json}

# Create log directory if it doesn't exist
mkdir -p /app/logs

# Start application with proper signal handling
echo "✅ Starting PIKAR AI server on port ${PORT:-3000}..."
exec npm start
