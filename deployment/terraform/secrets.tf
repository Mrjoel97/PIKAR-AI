# Copyright 2025 Google LLC.
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

resource "google_secret_manager_secret" "workflow_service_secret" {
  for_each = local.deploy_project_ids

  project   = each.value
  secret_id = "${var.project_name}-workflow-service-secret"

  replication {
    auto {}
  }

  depends_on = [google_project_service.deploy_project_services]
}

resource "google_secret_manager_secret_version" "workflow_service_secret_version" {
  for_each = local.deploy_project_ids

  secret      = google_secret_manager_secret.workflow_service_secret[each.key].id
  secret_data = var.workflow_service_secret
}

resource "google_secret_manager_secret_iam_member" "workflow_service_secret_accessor" {
  for_each = local.deploy_project_ids

  project   = each.value
  secret_id = google_secret_manager_secret.workflow_service_secret[each.key].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.app_sa[each.key].email}"
}
