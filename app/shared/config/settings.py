from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://sicons:sicons@localhost:5432/sicons"
    auth_secret_key: str = "sicons-dev-secret-change-me"
    auth_token_ttl_minutes: int = 480
    forecast_cache_ttl_seconds: int = 1800

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        return self.database_url


settings = Settings()
