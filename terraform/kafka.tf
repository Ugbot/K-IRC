resource "aiven_kafka" "kirc_kafka" {
  project      = var.aiven_project_name
  plan         = "business-4"
  service_name = "kirc-kafka"

  kafka_user_config {
    kafka_rest    = true
    kafka_connect = true
  }
}

resource "aiven_kafka_topic" "data_in" {
  project      = var.aiven_project_name
  service_name = aiven_kafka.kirc_kafka.service_name
  topic_name   = "data-in"
  partitions   = 3
  replication  = 2
}

resource "aiven_kafka_topic" "data_out" {
  project      = var.aiven_project_name
  service_name = aiven_kafka.kirc_kafka.service_name
  topic_name   = "data-out"
  partitions   = 3
  replication  = 2
}

resource "aiven_kafka_topic" "rpc_in" {
  project      = var.aiven_project_name
  service_name = aiven_kafka.kirc_kafka.service_name
  topic_name   = "rpc-in"
  partitions   = 3
  replication  = 2
}

resource "aiven_kafka_topic" "rpc_out" {
  project      = var.aiven_project_name
  service_name = aiven_kafka.kirc_kafka.service_name
  topic_name   = "rpc-out"
  partitions   = 3
  replication  = 2
}
