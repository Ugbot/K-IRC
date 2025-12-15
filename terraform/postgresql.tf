resource "aiven_pg" "kirc_pg" {
  project      = var.aiven_project_name
  plan         = "free"
  service_name = var.pg_service_name

  pg_user_config {
    pg_version = "16"
  }
}

resource "aiven_pg_database" "kirc_config" {
  project       = var.aiven_project_name
  service_name  = aiven_pg.kirc_pg.service_name
  database_name = "kirc_config"
}
