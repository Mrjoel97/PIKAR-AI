# Project name used for resource naming
project_name = "pikar-ai"

# Your Production Google Cloud project id
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
