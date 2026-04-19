# Project name used for resource naming
project_name = "pikar-ai"

# Your Dev Google Cloud project id
dev_project_id = "your-dev-project-id"

# The Google Cloud region you will use to deploy the infrastructure
region = "us-central1"


# Supabase backend runtime configuration
supabase_url = "https://your-project.supabase.co"
supabase_anon_key = "replace-with-your-supabase-anon-key"
supabase_service_role_key = "replace-with-your-supabase-service-role-key"
supabase_jwt_secret = "replace-with-your-supabase-jwt-secret"
scheduler_secret = "replace-with-your-scheduler-secret"
workflow_service_secret = "replace-with-64-char-hex-secret"
runtime_secret_values = {
  ADMIN_ENCRYPTION_KEY    = "replace-with-admin-encryption-key"
  TAVILY_API_KEY          = "replace-with-tavily-api-key"
  FIRECRAWL_API_KEY       = "replace-with-firecrawl-api-key"
  RESEND_API_KEY          = "replace-with-resend-api-key"
  RESEND_WEBHOOK_SECRET   = "replace-with-resend-webhook-secret"
  FACEBOOK_APP_SECRET     = "replace-with-facebook-app-secret"
  TIKTOK_CLIENT_SECRET    = "replace-with-tiktok-client-secret"
  LINKEDIN_CLIENT_SECRET  = "replace-with-linkedin-client-secret"
  LINKEDIN_WEBHOOK_SECRET = "replace-with-linkedin-webhook-secret"
  HUBSPOT_CLIENT_SECRET   = "replace-with-hubspot-client-secret"
  SHOPIFY_CLIENT_SECRET   = "replace-with-shopify-client-secret"
}
