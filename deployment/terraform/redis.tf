# Redis Cache Instance
# https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/redis_instance

resource "google_redis_instance" "cache" {
  for_each = local.deploy_project_ids

  name           = "${var.project_name}-cache"
  tier           = "BASIC"
  memory_size_gb = 1

  location_id = "${var.region}-a" # Use specific zone in region

  authorized_network = "default"  # Assuming default VPC, adjust if custom VPC used

  redis_version     = "REDIS_7_0"
  display_name      = "${var.project_name} Cache"

  project = each.value
  region  = var.region

  # Basic tier doesn't support HA or persistence features
  # For production (STANDARD_HA), uncomment below:
  # replica_count = 1
  # read_replicas_mode = "READ_REPLICAS_DISABLED"
  
  labels = {
    env = "production"
    app = var.project_name
  }
}

# Allow Cloud Run to connect to Redis
# Cloud Run communicates via Serverless VPC Access or Direct VPC Egress
# This firewall rule allows traffic on port 6379 from the VPC
resource "google_compute_firewall" "redis_access" {
  for_each = local.deploy_project_ids

  name    = "allow-redis-access-${var.project_name}"
  network = "default"
  project = each.value

  allow {
    protocol = "tcp"
    ports    = ["6379"]
  }

  # In a real environment with VPC connector, restrict source ranges
  # source_ranges = ["10.8.0.0/28"] 
  # For Direct VPC Egress or testing, careful with 0.0.0.0/0
  source_ranges = ["10.8.0.0/28"] 
  target_tags   = ["redis-cache"]
}

output "redis_host" {
  value = {
    for k, v in google_redis_instance.cache : k => v.host
  }
}

output "redis_port" {
  value = {
    for k, v in google_redis_instance.cache : k => v.port
  }
}
