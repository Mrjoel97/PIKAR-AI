-- Performance index for api_health_checks table.
-- Supports efficient queries filtering by endpoint with time-ordered results,
-- as used by the health checker service for rolling stats and anomaly detection.

CREATE INDEX IF NOT EXISTS api_health_checks_endpoint_checked_at
    ON api_health_checks (endpoint, checked_at DESC);
