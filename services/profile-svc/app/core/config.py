from typing import List, Union

from pydantic import AnyHttpUrl, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment/.env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )

    # --- App ---
    APP_NAME: str = "profiles-svc"
    APP_ENV: str = "dev"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8080
    LOG_LEVEL: str = "INFO"

    # --- Auth/JWT ---
    JWT_AUDIENCE: str | None = None
    JWT_ISSUER: str | None = None
    JWT_PUBLIC_KEY_BASE64: str | None = None
    AUTH_INTROSPECTION_URL: str | None = None
    AUTH_INTROSPECTION_TOKEN: SecretStr | None = None

    # --- DB ---
    DB_HOST: str = "postgres"
    DB_PORT: int = 5432
    DB_USER: str = "app"
    DB_PASSWORD: SecretStr = SecretStr("app")
    DB_NAME: str = "appdb"
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 10
    DB_SCHEMA: str = "profiles"

    # --- CORS ---
    CORS_ORIGINS: Union[List[AnyHttpUrl], List[str]] = []

    @property
    def database_url(self) -> str:
        pwd = self.DB_PASSWORD.get_secret_value()
        return f"postgresql+asyncpg://{self.DB_USER}:{pwd}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _split_csv(cls, value):
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    # --- Kafka ---
    KAFKA_ENABLED: bool = True
    KAFKA_BOOTSTRAP: str = "kafka:9092"
    KAFKA_CLIENT_ID: str = "profiles-svc"
    KAFKA_TOPIC_PROFILE_REGISTERED: str = "profiles.client.registered.v1"
    # Topic to consume when a user verifies their email in auth-svc
    KAFKA_TOPIC_USER_VERIFIED: str = "user.verified.v1"

    # --- Media storage (MinIO/S3 compatible) ---
    MINIO_ENABLED: bool = False
    MINIO_ENDPOINT: str | None = None
    MINIO_ACCESS_KEY: SecretStr | None = None
    MINIO_SECRET_KEY: SecretStr | None = None
    MINIO_SECURE: bool = False
    MINIO_BUCKET: str = "profiles-media"
    MINIO_PUBLIC_URL: str | None = None


settings = Settings()
