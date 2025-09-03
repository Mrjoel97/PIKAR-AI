# PIKAR AI - Staging Environment Configuration
# Terraform variables for staging deployment

# Environment Configuration
environment = "staging"
location    = "East US"

# App Service Configuration
app_service_sku                    = "P1v3"
app_service_always_on             = true
app_service_http2_enabled         = true
app_service_minimum_tls_version   = "1.2"

# Database Configuration
database_sku                = "S2"
database_max_size_gb       = 250
database_backup_retention_days = 14
database_geo_backup_enabled = false

# Redis Configuration
redis_sku      = "Standard"
redis_family   = "C"
redis_capacity = 1
redis_patch_schedule_day  = "Sunday"
redis_patch_schedule_hour = 3

# Storage Configuration
storage_account_tier     = "Standard"
storage_replication_type = "LRS"

# CDN Configuration
cdn_sku                = "Standard_Microsoft"
enable_cdn_compression = true
cdn_optimization_type  = "GeneralWebDelivery"

# Container Registry Configuration
container_registry_sku         = "Standard"
enable_container_registry_admin = false

# Security Configuration
enable_ssl_certificate = true
custom_domain         = "staging.pikar-ai.com"
enable_waf           = false
enable_ddos_protection = false
enable_network_security = true
enable_private_endpoints = false
enable_managed_identity = true

# CORS Configuration
allowed_origins = [
  "https://staging.pikar-ai.com",
  "https://staging-app.pikar-ai.com",
  "http://localhost:3000",
  "http://localhost:5173"
]

# Security Alert Configuration
security_alert_emails = [
  "devops@pikar-ai.com",
  "staging-alerts@pikar-ai.com"
]

# Monitoring Configuration
enable_monitoring = true
application_insights_retention_days = 30
log_analytics_retention_days = 30
log_retention_days = 14
enable_diagnostic_logs = true
enable_application_insights_profiler = false
enable_application_insights_snapshot_debugger = false

# Auto-scaling Configuration
enable_auto_scaling = false
min_instances = 1
max_instances = 5
scale_out_cpu_threshold = 80
scale_in_cpu_threshold = 20

# Backup Configuration
enable_backup = true
backup_retention_days = 14

# Key Vault Configuration
enable_key_vault_soft_delete = true
key_vault_soft_delete_retention_days = 30

# SQL Security Configuration
enable_sql_threat_detection = true
sql_audit_log_retention_days = 30

# Base44 Integration Configuration
base44_base_url = "https://staging-api.base44.com"
base44_timeout = 30000

# Network Security Configuration
allowed_ip_ranges = [
  # Office IP ranges
  "203.0.113.0/24",
  "198.51.100.0/24",
  # Development IP ranges
  "192.168.1.0/24"
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
  Environment     = "staging"
  CostCenter     = "Engineering"
  Owner          = "DevOps Team"
  Project        = "PIKAR-AI"
  BusinessUnit   = "Technology"
  Purpose        = "Testing"
  AutoShutdown   = "true"
  BackupRequired = "false"
  MonitoringLevel = "standard"
}
