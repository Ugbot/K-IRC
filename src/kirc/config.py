"""Configuration management using pydantic-settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class KafkaSettings(BaseSettings):
    """Kafka connection settings."""

    model_config = SettingsConfigDict(env_prefix="KAFKA_")

    bootstrap_servers: str = Field(description="Kafka bootstrap servers")
    security_protocol: str = Field(default="SSL", description="Security protocol")
    ssl_cafile: str = Field(default="./certs/kafka_ca.pem", description="CA certificate path")
    ssl_certfile: str = Field(
        default="./certs/kafka_service.cert", description="Client certificate path"
    )
    ssl_keyfile: str = Field(default="./certs/kafka_service.key", description="Client key path")

    topic_data_in: str = Field(default="data-in", description="Incoming data topic")
    topic_data_out: str = Field(default="data-out", description="Outgoing data topic")
    topic_rpc_in: str = Field(default="rpc-in", description="Incoming RPC topic")
    topic_rpc_out: str = Field(default="rpc-out", description="Outgoing RPC topic")


class PostgresSettings(BaseSettings):
    """PostgreSQL connection settings."""

    model_config = SettingsConfigDict(env_prefix="POSTGRES_")

    uri: str = Field(description="PostgreSQL connection URI")


class ValkeySettings(BaseSettings):
    """Valkey/Redis connection settings."""

    model_config = SettingsConfigDict(env_prefix="VALKEY_")

    uri: str = Field(description="Valkey connection URI")


class UserSettings(BaseSettings):
    """User profile settings."""

    model_config = SettingsConfigDict(env_prefix="KIRC_")

    username: str = Field(description="Unique username")
    display_name: str = Field(default="", description="Display name")


class Settings(BaseSettings):
    """Main application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    kafka: KafkaSettings = Field(default_factory=KafkaSettings)
    postgres: PostgresSettings = Field(default_factory=PostgresSettings)
    valkey: ValkeySettings = Field(default_factory=ValkeySettings)
    user: UserSettings = Field(default_factory=UserSettings)


def load_settings() -> Settings:
    """Load settings from environment and .env file."""
    return Settings()
