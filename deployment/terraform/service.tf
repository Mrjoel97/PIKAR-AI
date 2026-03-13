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
  for_each = local.deploy_project_ids

  project_id = local.deploy_project_ids[each.key]
}

resource "google_cloud_run_v2_service" "app" {
  for_each = local.deploy_project_ids

  name                = var.project_name
  location            = var.region
  project             = each.value
  deletion_protection = false
  ingress             = "INGRESS_TRAFFIC_ALL"
  labels = {
    "created-by"                  = "adk"
  }

  template {
    annotations = {
      "autoscaling.knative.dev/metric" = "cpu"
      "autoscaling.knative.dev/target" = "70"
    }
    containers {
      # Placeholder, will be replaced by the CI/CD pipeline
      image = "us-docker.pkg.dev/cloudrun/container/hello"
      ports {
        container_port = 8080
      }
      env {
        name  = "APP_URL"
        value = "https://${var.project_name}-${data.google_project.project[each.key].number}.${var.region}.run.app"
      }
      env {
        name  = "BACKEND_API_URL"
        value = "https://${var.project_name}-${data.google_project.project[each.key].number}.${var.region}.run.app"
      }
      env {
        name  = "ENVIRONMENT"
        value = each.key == "prod" ? "production" : "staging"
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
        name  = "SUPABASE_SERVICE_ROLE_KEY"
        value = var.supabase_service_role_key
      }
      env {
        name  = "SUPABASE_JWT_SECRET"
        value = var.supabase_jwt_secret
      }
      env {
        name  = "ALLOWED_ORIGINS"
        value = var.allowed_origins
      }
      env {
        name  = "SCHEDULER_SECRET"
        value = var.scheduler_secret
      }
      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = each.value
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
        value = "1"
      }
      env {
        name  = "ALLOW_ANONYMOUS_CHAT"
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
      env {
        name = "WORKFLOW_SERVICE_SECRET"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.workflow_service_secret[each.key].secret_id
            version = "latest"
          }
        }
      }
      resources {
        limits = {
          cpu    = "4"
          memory = "8Gi"
        }
        cpu_idle = false
      }

      env {
        name  = "LOGS_BUCKET_NAME"
        value = google_storage_bucket.logs_data_bucket[each.value].name
      }

      env {
        name  = "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"
        value = "NO_CONTENT"
      }

      env {
        name  = "REDIS_HOST"
        value = google_redis_instance.cache[each.key].host
      }

      env {
        name  = "REDIS_PORT"
        value = google_redis_instance.cache[each.key].port
      }

      env {
        name  = "REDIS_DB"
        value = "0"
      }
    }

    vpc_access {
      connector = google_vpc_access_connector.run_connector[each.key].id
      egress    = "PRIVATE_RANGES_ONLY"
    }

    service_account                = google_service_account.app_sa[each.key].email
    max_instance_request_concurrency = 80

    scaling {
      min_instance_count = 2
      max_instance_count = 100
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
    google_project_service.deploy_project_services,
  ]
}


