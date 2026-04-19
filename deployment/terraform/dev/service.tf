# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Get project information to access the project number
data "google_project" "project" {
  project_id = var.dev_project_id
}


resource "google_cloud_run_v2_service" "app" {
  name                = var.project_name
  location            = var.region
  project             = var.dev_project_id
  deletion_protection = false
  ingress             = "INGRESS_TRAFFIC_ALL"
  labels = {
    "created-by"                  = "adk"
  }

  template {
    containers {
      image = "us-docker.pkg.dev/cloudrun/container/hello"
      ports {
        container_port = 8080
      }
      env {
        name  = "APP_URL"
        value = "https://${var.project_name}-${data.google_project.project.number}.${var.region}.run.app"
      }
      env {
        name  = "BACKEND_API_URL"
        value = "https://${var.project_name}-${data.google_project.project.number}.${var.region}.run.app"
      }
      env {
        name  = "ENVIRONMENT"
        value = "development"
      }
      env {
        name  = "SUPABASE_URL"
        value = var.supabase_url
      }
      env {
        name  = "SUPABASE_ANON_KEY"
        value = var.supabase_anon_key
      }
      env {
        name  = "ALLOWED_ORIGINS"
        value = var.allowed_origins
      }
      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.dev_project_id
      }
      env {
        name  = "GOOGLE_CLOUD_LOCATION"
        value = var.region
      }
      env {
        name  = "GOOGLE_GENAI_USE_VERTEXAI"
        value = "1"
      }
      env {
        name  = "REMOTION_RENDER_ENABLED"
        value = "1"
      }
      env {
        name  = "REMOTION_RENDER_DIR"
        value = "/code/remotion-render"
      }
      env {
        name  = "REQUIRE_STRICT_AUTH"
        value = "0"
      }
      env {
        name  = "WORKFLOW_STRICT_TOOL_RESOLUTION"
        value = "true"
      }
      env {
        name  = "WORKFLOW_STRICT_CRITICAL_TOOL_GUARD"
        value = "true"
      }
      env {
        name  = "WORKFLOW_ALLOW_FALLBACK_SIMULATION"
        value = "false"
      }
      env {
        name  = "WORKFLOW_ENFORCE_READINESS_GATE"
        value = "true"
      }
      dynamic "env" {
        for_each = local.runtime_secret_values
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.runtime_secret[env.key].secret_id
              version = "latest"
            }
          }
        }
      }
      resources {
        limits = {
          cpu    = "4"
          memory = "8Gi"
        }
      }

      env {
        name  = "LOGS_BUCKET_NAME"
        value = google_storage_bucket.logs_data_bucket.name
      }

      env {
        name  = "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"
        value = "NO_CONTENT"
      }

      env {
        name  = "REDIS_HOST"
        value = google_redis_instance.cache.host
      }

      env {
        name  = "REDIS_PORT"
        value = google_redis_instance.cache.port
      }

      env {
        name  = "REDIS_DB"
        value = "0"
      }
    }

    vpc_access {
      connector = google_vpc_access_connector.run_connector.id
      egress    = "PRIVATE_RANGES_ONLY"
    }

    service_account = google_service_account.app_sa.email
    max_instance_request_concurrency = 40

    scaling {
      min_instance_count = 1
      max_instance_count = 10
    }

    session_affinity = true
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  # This lifecycle block prevents Terraform from overwriting the container image when it's
  # updated by Cloud Run deployments outside of Terraform (e.g., via CI/CD pipelines)
  lifecycle {
    ignore_changes = [
      template[0].containers[0].image,
    ]
  }

  # Make dependencies conditional to avoid errors.
  depends_on = [
    resource.google_project_service.services,
  ]
}


