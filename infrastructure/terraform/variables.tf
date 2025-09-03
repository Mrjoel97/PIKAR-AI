# PIKAR AI - Terraform Variables
# Variable definitions for infrastructure deployment

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "production"], var.environment)
    error_message = "Environment must be one of: dev, staging, production."
  }
}

variable "location" {
  description = "Azure region for resources"
  type        = string
  default     = "East US"
}

variable "app_service_sku" {
  description = "SKU for App Service Plan"
  type        = string
  default     = "P1v3"
  validation {
    condition = contains([
      "B1", "B2", "B3",
      "S1", "S2", "S3",
      "P1v2", "P2v2", "P3v2",
      "P1v3", "P2v3", "P3v3"
    ], var.app_service_sku)
    error_message = "App Service SKU must be a valid Azure App Service plan SKU."
  }
}

variable "database_sku" {
  description = "SKU for SQL Database"
  type        = string
  default     = "S2"
}

variable "database_max_size_gb" {
  description = "Maximum size of SQL Database in GB"
  type        = number
  default     = 250
}

variable "redis_sku" {
  description = "SKU for Redis Cache"
  type        = string
  default     = "Standard"
  validation {
    condition     = contains(["Basic", "Standard", "Premium"], var.redis_sku)
    error_message = "Redis SKU must be one of: Basic, Standard, Premium."
  }
}

variable "redis_family" {
  description = "Redis family"
  type        = string
  default     = "C"
  validation {
    condition     = contains(["C", "P"], var.redis_family)
    error_message = "Redis family must be C or P."
  }
}

variable "redis_capacity" {
  description = "Redis cache capacity"
  type        = number
  default     = 1
  validation {
    condition     = var.redis_capacity >= 0 && var.redis_capacity <= 6
    error_message = "Redis capacity must be between 0 and 6."
  }
}

variable "sql_admin_username" {
  description = "SQL Server administrator username"
  type        = string
  default     = "pikaradmin"
  sensitive   = true
}

variable "sql_admin_password" {
  description = "SQL Server administrator password"
  type        = string
  sensitive   = true
  validation {
    condition     = length(var.sql_admin_password) >= 8
    error_message = "SQL admin password must be at least 8 characters long."
  }
}

variable "sql_azuread_admin_login" {
  description = "Azure AD admin login for SQL Server"
  type        = string
}

variable "sql_azuread_admin_object_id" {
  description = "Azure AD admin object ID for SQL Server"
  type        = string
}

variable "allowed_origins" {
  description = "List of allowed CORS origins"
  type        = list(string)
  default = [
    "https://pikar-ai.com",
    "https://www.pikar-ai.com",
    "https://app.pikar-ai.com"
  ]
}

variable "security_alert_emails" {
  description = "List of email addresses for security alerts"
  type        = list(string)
  default     = ["security@pikar-ai.com"]
}

# Environment-specific variable files
variable "enable_backup" {
  description = "Enable automated backups"
  type        = bool
  default     = true
}

variable "backup_retention_days" {
  description = "Number of days to retain backups"
  type        = number
  default     = 30
}

variable "enable_monitoring" {
  description = "Enable advanced monitoring and alerting"
  type        = bool
  default     = true
}

variable "enable_auto_scaling" {
  description = "Enable auto-scaling for App Service"
  type        = bool
  default     = false
}

variable "min_instances" {
  description = "Minimum number of instances for auto-scaling"
  type        = number
  default     = 1
}

variable "max_instances" {
  description = "Maximum number of instances for auto-scaling"
  type        = number
  default     = 10
}

variable "scale_out_cpu_threshold" {
  description = "CPU threshold for scaling out"
  type        = number
  default     = 70
}

variable "scale_in_cpu_threshold" {
  description = "CPU threshold for scaling in"
  type        = number
  default     = 30
}

variable "enable_ssl_certificate" {
  description = "Enable SSL certificate management"
  type        = bool
  default     = true
}

variable "custom_domain" {
  description = "Custom domain name"
  type        = string
  default     = ""
}

variable "enable_waf" {
  description = "Enable Web Application Firewall"
  type        = bool
  default     = false
}

variable "enable_ddos_protection" {
  description = "Enable DDoS protection"
  type        = bool
  default     = false
}

variable "log_retention_days" {
  description = "Number of days to retain logs"
  type        = number
  default     = 30
}

variable "enable_diagnostic_logs" {
  description = "Enable diagnostic logging"
  type        = bool
  default     = true
}

variable "enable_network_security" {
  description = "Enable network security features"
  type        = bool
  default     = true
}

variable "allowed_ip_ranges" {
  description = "List of allowed IP ranges for network access"
  type        = list(string)
  default     = []
}

variable "enable_private_endpoints" {
  description = "Enable private endpoints for services"
  type        = bool
  default     = false
}

variable "enable_managed_identity" {
  description = "Enable managed identity for services"
  type        = bool
  default     = true
}

variable "key_vault_access_policies" {
  description = "Additional Key Vault access policies"
  type = list(object({
    tenant_id = string
    object_id = string
    key_permissions = list(string)
    secret_permissions = list(string)
    certificate_permissions = list(string)
  }))
  default = []
}

variable "tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default     = {}
}

# Base44 Integration Variables
variable "base44_api_key" {
  description = "Base44 API key for AI agent integration"
  type        = string
  sensitive   = true
  default     = ""
}

variable "base44_base_url" {
  description = "Base44 API base URL"
  type        = string
  default     = "https://api.base44.com"
}

variable "base44_timeout" {
  description = "Base44 API timeout in milliseconds"
  type        = number
  default     = 30000
}

# Performance and Scaling Variables
variable "app_service_always_on" {
  description = "Keep App Service always on"
  type        = bool
  default     = true
}

variable "app_service_http2_enabled" {
  description = "Enable HTTP/2 for App Service"
  type        = bool
  default     = true
}

variable "app_service_minimum_tls_version" {
  description = "Minimum TLS version for App Service"
  type        = string
  default     = "1.2"
  validation {
    condition     = contains(["1.0", "1.1", "1.2"], var.app_service_minimum_tls_version)
    error_message = "Minimum TLS version must be 1.0, 1.1, or 1.2."
  }
}

variable "database_backup_retention_days" {
  description = "Database backup retention in days"
  type        = number
  default     = 35
}

variable "database_geo_backup_enabled" {
  description = "Enable geo-redundant backups for database"
  type        = bool
  default     = true
}

variable "redis_patch_schedule_day" {
  description = "Day of week for Redis patching"
  type        = string
  default     = "Sunday"
  validation {
    condition = contains([
      "Monday", "Tuesday", "Wednesday", "Thursday", 
      "Friday", "Saturday", "Sunday"
    ], var.redis_patch_schedule_day)
    error_message = "Redis patch schedule day must be a valid day of the week."
  }
}

variable "redis_patch_schedule_hour" {
  description = "Hour for Redis patching (UTC)"
  type        = number
  default     = 2
  validation {
    condition     = var.redis_patch_schedule_hour >= 0 && var.redis_patch_schedule_hour <= 23
    error_message = "Redis patch schedule hour must be between 0 and 23."
  }
}

variable "storage_account_tier" {
  description = "Storage account tier"
  type        = string
  default     = "Standard"
  validation {
    condition     = contains(["Standard", "Premium"], var.storage_account_tier)
    error_message = "Storage account tier must be Standard or Premium."
  }
}

variable "storage_replication_type" {
  description = "Storage account replication type"
  type        = string
  default     = "GRS"
  validation {
    condition     = contains(["LRS", "GRS", "RAGRS", "ZRS", "GZRS", "RAGZRS"], var.storage_replication_type)
    error_message = "Storage replication type must be a valid Azure storage replication type."
  }
}

variable "cdn_sku" {
  description = "CDN profile SKU"
  type        = string
  default     = "Standard_Microsoft"
  validation {
    condition = contains([
      "Standard_Akamai", "Standard_ChinaCdn", "Standard_Microsoft", 
      "Standard_Verizon", "Premium_Verizon"
    ], var.cdn_sku)
    error_message = "CDN SKU must be a valid Azure CDN SKU."
  }
}

variable "enable_cdn_compression" {
  description = "Enable CDN compression"
  type        = bool
  default     = true
}

variable "cdn_optimization_type" {
  description = "CDN optimization type"
  type        = string
  default     = "GeneralWebDelivery"
}

# Monitoring and Alerting Variables
variable "application_insights_retention_days" {
  description = "Application Insights data retention in days"
  type        = number
  default     = 90
}

variable "log_analytics_retention_days" {
  description = "Log Analytics workspace retention in days"
  type        = number
  default     = 90
}

variable "enable_application_insights_profiler" {
  description = "Enable Application Insights Profiler"
  type        = bool
  default     = false
}

variable "enable_application_insights_snapshot_debugger" {
  description = "Enable Application Insights Snapshot Debugger"
  type        = bool
  default     = false
}

# Security Variables
variable "enable_key_vault_soft_delete" {
  description = "Enable Key Vault soft delete"
  type        = bool
  default     = true
}

variable "key_vault_soft_delete_retention_days" {
  description = "Key Vault soft delete retention in days"
  type        = number
  default     = 90
}

variable "enable_sql_threat_detection" {
  description = "Enable SQL threat detection"
  type        = bool
  default     = true
}

variable "sql_audit_log_retention_days" {
  description = "SQL audit log retention in days"
  type        = number
  default     = 90
}

variable "enable_container_registry_admin" {
  description = "Enable Container Registry admin user"
  type        = bool
  default     = false
}

variable "container_registry_sku" {
  description = "Container Registry SKU"
  type        = string
  default     = "Standard"
  validation {
    condition     = contains(["Basic", "Standard", "Premium"], var.container_registry_sku)
    error_message = "Container Registry SKU must be Basic, Standard, or Premium."
  }
}
