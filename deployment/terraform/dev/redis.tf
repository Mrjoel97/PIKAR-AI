# Redis Cache Instance
# https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/redis_instance

resource "google_redis_instance" "cache" {
  name           = "${var.project_name}-cache"
  tier           = "BASIC"
  memory_size_gb = 1

  location_id = "${var.region}-a"

  authorized_network = "default"

  redis_version = "REDIS_7_0"
  display_name  = "${var.project_name} Cache"

  project = var.dev_project_id
  region  = var.region

  labels = {
    env = "development"
    app = var.project_name
  }
}

resource "google_vpc_access_connector" "run_connector" {
  name          = "${var.project_name}-connector"
  project       = var.dev_project_id
  region        = var.region
  network       = "default"
  ip_cidr_range = "10.8.0.0/28"
  min_instances = 2
  max_instances = 3
}

resource "google_compute_firewall" "redis_access" {
  name    = "allow-redis-access-${var.project_name}"
  network = "default"
  project = var.dev_project_id

  allow {
    protocol = "tcp"
    ports    = ["6379"]
  }

  source_ranges = ["10.8.0.0/28"]
  target_tags   = ["redis-cache"]
}