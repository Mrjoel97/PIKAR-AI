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

resource "google_secret_manager_secret" "runtime_secret" {
  for_each = {
    for pair in setproduct(keys(local.deploy_project_ids), keys(local.runtime_secret_values)) :
    "${pair[0]}:${pair[1]}" => {
      project_key = pair[0]
      project_id  = local.deploy_project_ids[pair[0]]
      env_name    = pair[1]
    }
  }

  project   = each.value.project_id
  secret_id = local.runtime_secret_secret_ids[each.value.env_name]

  replication {
    auto {}
  }

  depends_on = [google_project_service.deploy_project_services]
}

resource "google_secret_manager_secret_version" "runtime_secret_version" {
  for_each = google_secret_manager_secret.runtime_secret

  secret      = each.value.id
  secret_data = local.runtime_secret_values[split(":", each.key)[1]]
}

resource "google_secret_manager_secret_iam_member" "runtime_secret_accessor" {
  for_each = {
    for pair in setproduct(keys(local.deploy_project_ids), keys(local.runtime_secret_values)) :
    "${pair[0]}:${pair[1]}" => {
      project_key = pair[0]
      project_id  = local.deploy_project_ids[pair[0]]
      env_name    = pair[1]
    }
  }

  project   = each.value.project_id
  secret_id = google_secret_manager_secret.runtime_secret[each.key].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.app_sa[each.value.project_key].email}"
}
