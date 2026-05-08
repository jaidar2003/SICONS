from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://buildwise:buildwise@localhost:5432/buildwise"
    auth_secret_key: str = "buildwise-dev-secret-change-me"
    auth_token_ttl_minutes: int = 480
    forecast_cache_ttl_seconds: int = 1800
    forecast_snapshot_path: str = "tmp/forecast_snapshots.json"
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    openai_model: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        return self.database_url


settings = Settings()
