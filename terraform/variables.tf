variable "aiven_api_token" {
  description = "Aiven API token for authentication"
  type        = string
  sensitive   = true
}

variable "aiven_project_name" {
  description = "Name of your Aiven project"
  type        = string
}

variable "pg_service_name" {
  description = "Name for the PostgreSQL service"
  type        = string
  default     = "kirc-pg"
}

variable "valkey_service_name" {
  description = "Name for the Valkey service"
  type        = string
  default     = "kirc-valkey"
}
