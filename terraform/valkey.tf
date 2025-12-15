resource "aiven_valkey" "kirc_valkey" {
  project      = var.aiven_project_name
  plan         = "free"
  service_name = var.valkey_service_name

  valkey_user_config {
    valkey_maxmemory_policy = "allkeys-lru"
  }
}
