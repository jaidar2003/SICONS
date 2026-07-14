import re

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_AUTH_SECRETS = {
    "buildwise-dev-secret-change-me",
    "change-this-auth-secret-key",
}


class Settings(BaseSettings):
    environment: str = "development"
    database_url: str = "postgresql+psycopg://buildwise:buildwise@localhost:5432/buildwise"
    auth_secret_key: str
    auth_token_ttl_minutes: int = 480
    password_reset_token_ttl_minutes: int = 60
    frontend_base_url: str = "http://localhost:3000"
    cors_origins: str = (
        "http://localhost:3000,http://127.0.0.1:3000,"
        "http://localhost:3001,http://127.0.0.1:3001,"
        "https://buildwise-tif.vercel.app,https://buildwise.com.ar"
    )
    forecast_cache_ttl_seconds: int = 1800
    forecast_snapshot_path: str = "tmp/forecast_snapshots.json"
    forecast_allow_synchronous_compute: bool = True
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_sender: str | None = None
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False
    smtp_timeout_seconds: int = 10
    admin_notification_email: str | None = None
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    openai_model: str | None = None
    openai_timeout_seconds: int = 30
    chat_provider: str = "openai"
    anthropic_api_key: str | None = None
    anthropic_base_url: str = "https://api.anthropic.com/v1"
    anthropic_model: str | None = None
    anthropic_version: str = "2023-06-01"
    anthropic_max_tokens: int = 1024

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        environment = self.environment.strip().lower()
        if environment not in {"development", "test", "production"}:
            raise ValueError("ENVIRONMENT debe ser development, test o production")
        if environment == "production" and self.auth_secret_key in INSECURE_AUTH_SECRETS:
            raise ValueError("AUTH_SECRET_KEY debe configurarse con un secreto seguro en produccion")
        if environment == "production" and "forecast_allow_synchronous_compute" not in self.model_fields_set:
            self.forecast_allow_synchronous_compute = False
        if self.admin_notification_email:
            email = self.admin_notification_email.strip().lower()
            if "\n" in email or "\r" in email or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
                raise ValueError("ADMIN_NOTIFICATION_EMAIL no es valido")
            self.admin_notification_email = email
        return self

    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() == "production"

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        return self.database_url

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
