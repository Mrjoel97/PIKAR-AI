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

locals {
  cicd_services = [
    "cloudbuild.googleapis.com",
    "discoveryengine.googleapis.com",
    "speech.googleapis.com",
    "aiplatform.googleapis.com",
    "serviceusage.googleapis.com",
    "bigquery.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "cloudtrace.googleapis.com",
    "telemetry.googleapis.com",
    "artifactregistry.googleapis.com",
  ]

  deploy_project_services = [
    "aiplatform.googleapis.com",
    "run.googleapis.com",
    "redis.googleapis.com",
    "vpcaccess.googleapis.com",
    "discoveryengine.googleapis.com",
    "speech.googleapis.com",
    "texttospeech.googleapis.com",
    "secretmanager.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "bigquery.googleapis.com",
    "serviceusage.googleapis.com",
    "logging.googleapis.com",
    "cloudtrace.googleapis.com",
    "telemetry.googleapis.com",
    "artifactregistry.googleapis.com",
  ]

  deploy_project_ids = {
    prod    = var.prod_project_id
    staging = var.staging_project_id
  }

  all_project_ids = [
    var.cicd_runner_project_id,
    var.prod_project_id,
    var.staging_project_id
  ]

  runtime_secret_values = merge(
    {
      WORKFLOW_SERVICE_SECRET   = var.workflow_service_secret
      SCHEDULER_SECRET          = var.scheduler_secret
      SUPABASE_SERVICE_ROLE_KEY = var.supabase_service_role_key
      SUPABASE_JWT_SECRET       = var.supabase_jwt_secret
    },
    var.runtime_secret_values,
  )

  runtime_secret_secret_ids = {
    for name, _ in local.runtime_secret_values :
    name => "${var.project_name}-${lower(replace(name, "_", "-"))}"
  }

}



