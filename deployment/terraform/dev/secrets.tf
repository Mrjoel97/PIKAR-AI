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

resource "google_secret_manager_secret" "runtime_secret" {
  for_each = local.runtime_secret_values

  project   = var.dev_project_id
  secret_id = local.runtime_secret_secret_ids[each.key]

  replication {
    auto {}
  }

  depends_on = [resource.google_project_service.services]
}

resource "google_secret_manager_secret_version" "runtime_secret_version" {
  for_each = google_secret_manager_secret.runtime_secret

  secret      = each.value.id
  secret_data = local.runtime_secret_values[each.key]
}

resource "google_secret_manager_secret_iam_member" "runtime_secret_accessor" {
  for_each = google_secret_manager_secret.runtime_secret

  project   = var.dev_project_id
  secret_id = each.value.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.app_sa.email}"
}
