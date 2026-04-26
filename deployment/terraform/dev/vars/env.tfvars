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
  STITCH_API_KEY          = "replace-with-stitch-api-key"
  RESEND_API_KEY          = "replace-with-resend-api-key"
  RESEND_WEBHOOK_SECRET   = "replace-with-resend-webhook-secret"
  FACEBOOK_APP_SECRET     = "replace-with-facebook-app-secret"
  TIKTOK_CLIENT_SECRET    = "replace-with-tiktok-client-secret"
  LINKEDIN_CLIENT_SECRET  = "replace-with-linkedin-client-secret"
  LINKEDIN_WEBHOOK_SECRET = "replace-with-linkedin-webhook-secret"
  HUBSPOT_CLIENT_SECRET   = "replace-with-hubspot-client-secret"
  SHOPIFY_CLIENT_SECRET   = "replace-with-shopify-client-secret"
}
runtime_plain_env_values = {
  EMBEDDING_QUOTA_COOLDOWN_SECONDS = "900"
  FACEBOOK_APP_ID                  = "replace-with-facebook-app-id"
  GEMINI_AGENT_MODEL_FALLBACK      = "gemini-2.5-flash"
  GEMINI_AGENT_MODEL_PRIMARY       = "gemini-2.5-pro"
  HUBSPOT_CLIENT_ID                = "replace-with-hubspot-client-id"
  LINKEDIN_CLIENT_ID               = "replace-with-linkedin-client-id"
  REDIS_ENABLED                    = "1"
  RESEND_FORWARD_TO                = "replace-with-forwarding-email"
  RESEND_FROM_EMAIL                = "noreply@example.com"
  SHOPIFY_CLIENT_ID                = "replace-with-shopify-client-id"
  SKILL_EMBEDDING_WARMUP_ENABLED   = "0"
  TIKTOK_CLIENT_KEY                = "replace-with-tiktok-client-key"
}
