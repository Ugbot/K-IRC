"""Configuration management using pydantic-settings."""

from pydantic import Field, BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class KafkaSettings(BaseModel):
    """Kafka connection settings."""
    bootstrap_servers: str = "localhost:9092"
    security_protocol: str = "SASL_SSL"
    sasl_mechanism: str = "SCRAM-SHA-256"
    sasl_plain_username: str | None = None
    sasl_plain_password: str | None = None
    ssl_cafile: str = "./certs/ca.pem"
    ssl_certfile: str | None = None
    ssl_keyfile: str | None = None

    topic_data_in: str = "data-in"
    topic_data_out: str = "data-out"
    topic_rpc_in: str = "rpc-in"
    topic_rpc_out: str = "rpc-out"


class PostgresSettings(BaseModel):
    """PostgreSQL connection settings."""
    uri: str = "postgresql://user:pass@localhost:5432/kirc"


class ValkeySettings(BaseModel):
    """Valkey/Redis connection settings."""
    uri: str = "redis://localhost:6379"


class UserSettings(BaseModel):
    """User profile settings."""
    username: str = "guest"
    display_name: str = "Guest User"
    private_key_path: str = "id_rsa.pem"


class Settings(BaseSettings):
    """Main application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    kafka: KafkaSettings = Field(default_factory=KafkaSettings)
    postgres: PostgresSettings = Field(default_factory=PostgresSettings)
    valkey: ValkeySettings = Field(default_factory=ValkeySettings)
    user_config: UserSettings = Field(default_factory=UserSettings)


def load_settings() -> Settings:
    """Load settings from environment and .env file."""
    return Settings()
