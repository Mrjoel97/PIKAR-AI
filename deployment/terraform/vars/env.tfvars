# Project name used for resource naming
project_name = "pikar-ai"

# Production Google Cloud project id.
# Current live production uses: pikar-ai-project
prod_project_id = "your-production-project-id"

# Your Staging / Test Google Cloud project id
staging_project_id = "your-staging-project-id"

# Your Google Cloud project ID that will be used to host the Cloud Build pipelines.
cicd_runner_project_id = "your-cicd-project-id"
# Name of the host connection you created in Cloud Build
host_connection_name = "git-pikar-ai"
github_pat_secret_id = "your-github_pat_secret_id"

repository_owner = "Your GitHub organization or username."

# Name of the repository you added to Cloud Build
repository_name = "pikar-ai"

# The Google Cloud region you will use to deploy the infrastructure
# Current live production uses: us-central1
region = "us-central1"

# Shared secret for backend <-> edge service authentication
# Generate with: openssl rand -hex 32
workflow_service_secret = "replace-with-64-char-hex-secret"


# Supabase backend runtime configuration
supabase_url = "https://your-project.supabase.co"
supabase_anon_key = "replace-with-your-supabase-anon-key"
supabase_service_role_key = "replace-with-your-supabase-service-role-key"
supabase_jwt_secret = "replace-with-your-supabase-jwt-secret"
allowed_origins = "https://your-frontend.example.com"
scheduler_secret = "replace-with-your-scheduler-secret"
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

# Notes:
# - Redis instance name is derived from project_name: ${project_name}-cache
# - VPC connector name is derived from project_name: ${project_name}-connector
# - Cloud Run picks up REDIS_HOST and REDIS_PORT from terraform/service.tf
# - Do not commit real secrets or private IPs into this file
