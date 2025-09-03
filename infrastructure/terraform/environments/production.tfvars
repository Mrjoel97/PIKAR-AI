# PIKAR AI - Production Environment Configuration
# Terraform variables for production deployment

# Environment Configuration
environment = "production"
location    = "East US"

# App Service Configuration
app_service_sku                    = "P2v3"
app_service_always_on             = true
app_service_http2_enabled         = true
app_service_minimum_tls_version   = "1.2"

# Database Configuration
database_sku                = "S3"
database_max_size_gb       = 500
database_backup_retention_days = 35
database_geo_backup_enabled = true

# Redis Configuration
redis_sku      = "Premium"
redis_family   = "P"
redis_capacity = 2
redis_patch_schedule_day  = "Sunday"
redis_patch_schedule_hour = 2

# Storage Configuration
storage_account_tier     = "Standard"
storage_replication_type = "GRS"

# CDN Configuration
cdn_sku                = "Standard_Microsoft"
enable_cdn_compression = true
cdn_optimization_type  = "GeneralWebDelivery"

# Container Registry Configuration
container_registry_sku         = "Premium"
enable_container_registry_admin = false

# Security Configuration
enable_ssl_certificate = true
custom_domain         = "pikar-ai.com"
enable_waf           = true
enable_ddos_protection = true
enable_network_security = true
enable_private_endpoints = true
enable_managed_identity = true

# CORS Configuration
allowed_origins = [
  "https://pikar-ai.com",
  "https://www.pikar-ai.com",
  "https://app.pikar-ai.com",
  "https://admin.pikar-ai.com"
]

# Security Alert Configuration
security_alert_emails = [
  "security@pikar-ai.com",
  "devops@pikar-ai.com",
  "alerts@pikar-ai.com"
]

# Monitoring Configuration
enable_monitoring = true
application_insights_retention_days = 90
log_analytics_retention_days = 90
log_retention_days = 90
enable_diagnostic_logs = true
enable_application_insights_profiler = true
enable_application_insights_snapshot_debugger = false

# Auto-scaling Configuration
enable_auto_scaling = true
min_instances = 2
max_instances = 20
scale_out_cpu_threshold = 70
scale_in_cpu_threshold = 30

# Backup Configuration
enable_backup = true
backup_retention_days = 90

# Key Vault Configuration
enable_key_vault_soft_delete = true
key_vault_soft_delete_retention_days = 90

# SQL Security Configuration
enable_sql_threat_detection = true
sql_audit_log_retention_days = 90

# Base44 Integration Configuration
base44_base_url = "https://api.base44.com"
base44_timeout = 30000

# Network Security Configuration
allowed_ip_ranges = [
  # Office IP ranges
  "203.0.113.0/24",
  "198.51.100.0/24"
]

# Additional Key Vault Access Policies
key_vault_access_policies = [
  {
    tenant_id = "your-tenant-id"
    object_id = "devops-group-object-id"
    key_permissions = ["Get", "List", "Update", "Create", "Import", "Delete", "Recover", "Backup", "Restore"]
    secret_permissions = ["Get", "List", "Set", "Delete", "Recover", "Backup", "Restore"]
    certificate_permissions = ["Get", "List", "Update", "Create", "Import", "Delete", "Recover", "Backup", "Restore"]
  }
]

# Additional Tags
tags = {
  Environment     = "production"
  CostCenter     = "Engineering"
  Owner          = "DevOps Team"
  Project        = "PIKAR-AI"
  BusinessUnit   = "Technology"
  Compliance     = "SOC2"
  DataClass      = "Confidential"
  BackupRequired = "true"
  MonitoringLevel = "enhanced"
}
