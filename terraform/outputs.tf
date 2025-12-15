output "pg_service_uri" {
  description = "PostgreSQL service URI for connecting to the database"
  value       = aiven_pg.kirc_pg.service_uri
  sensitive   = true
}

output "pg_host" {
  description = "PostgreSQL host"
  value       = aiven_pg.kirc_pg.service_host
}

output "pg_port" {
  description = "PostgreSQL port"
  value       = aiven_pg.kirc_pg.service_port
}

output "pg_database" {
  description = "PostgreSQL database name"
  value       = aiven_pg_database.kirc_config.database_name
}

output "pg_username" {
  description = "PostgreSQL username"
  value       = aiven_pg.kirc_pg.service_username
}

output "pg_password" {
  description = "PostgreSQL password"
  value       = aiven_pg.kirc_pg.service_password
  sensitive   = true
}

output "pg_ca_cert" {
  description = "CA certificate for SSL connection"
  value       = aiven_pg.kirc_pg.service_ca_cert
  sensitive   = true
}

# Valkey outputs
output "valkey_service_uri" {
  description = "Valkey service URI for connecting"
  value       = aiven_valkey.kirc_valkey.service_uri
  sensitive   = true
}

output "valkey_host" {
  description = "Valkey host"
  value       = aiven_valkey.kirc_valkey.service_host
}

output "valkey_port" {
  description = "Valkey port"
  value       = aiven_valkey.kirc_valkey.service_port
}

output "valkey_password" {
  description = "Valkey password"
  value       = aiven_valkey.kirc_valkey.service_password
  sensitive   = true
}
