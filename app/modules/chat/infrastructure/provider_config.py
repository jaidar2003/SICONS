from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.modules.chat.infrastructure.models import ChatProviderSetting
from app.shared.config.settings import settings
from app.shared.database.session import SessionLocal

LAST_PROVIDER_STATUS: dict[str, object] = {
    "estado_ultima_llamada": "sin_datos",
    "proveedor_ultima_llamada": None,
    "fallback_ultima_llamada": None,
    "error_ultima_llamada": None,
}


def settings_provider_key() -> str:
    return "claude" if settings.chat_provider.strip().lower() == "anthropic" else "facultad"


def chat_config_from_settings() -> dict[str, str | None]:
    return {
        "proveedor_activo": settings_provider_key(),
        "modelo_facultad": settings.openai_model,
        "modelo_claude": settings.anthropic_model,
    }


def read_persisted_chat_config(db: Session | None = None) -> dict[str, str | None]:
    close_db = db is None
    db = db or SessionLocal()
    try:
        row = db.get(ChatProviderSetting, "default")
        if row is None:
            return chat_config_from_settings()
        return {
            "proveedor_activo": row.proveedor_activo,
            "modelo_facultad": row.modelo_facultad,
            "modelo_claude": row.modelo_claude,
        }
    except SQLAlchemyError:
        return chat_config_from_settings()
    finally:
        if close_db:
            db.close()


def apply_chat_config(config: dict[str, str | None]) -> None:
    settings.chat_provider = "anthropic" if config["proveedor_activo"] == "claude" else "openai"
    settings.openai_model = config.get("modelo_facultad")
    settings.anthropic_model = config.get("modelo_claude")


def provider_configured(provider_key: str, config: dict[str, str | None] | None = None) -> bool:
    config = config or chat_config_from_settings()
    if provider_key == "claude":
        return bool(settings.anthropic_base_url and settings.anthropic_api_key and config.get("modelo_claude"))
    return bool(settings.openai_base_url and settings.openai_api_key and config.get("modelo_facultad"))


def fallback_enabled(config: dict[str, str | None] | None = None) -> bool:
    config = config or chat_config_from_settings()
    primary_key = str(config["proveedor_activo"])
    fallback_key = "facultad" if primary_key == "claude" else "claude"
    return provider_configured(fallback_key, config)


def provider_model(provider_key: str, config: dict[str, str | None] | None = None) -> str | None:
    config = config or chat_config_from_settings()
    return config.get("modelo_claude") if provider_key == "claude" else config.get("modelo_facultad")


def resolve_provider_metadata(client) -> tuple[str | None, bool]:
    default_provider = settings_provider_key()
    provider_name = getattr(client, "last_provider_name", getattr(client, "provider_name", default_provider))
    return provider_name, bool(getattr(client, "last_fallback_used", False))


def remember_provider_success(client) -> None:
    provider_name, fallback_used = resolve_provider_metadata(client)
    LAST_PROVIDER_STATUS.update(
        estado_ultima_llamada="ok",
        proveedor_ultima_llamada=provider_name,
        fallback_ultima_llamada=fallback_used,
        error_ultima_llamada=None,
    )


def remember_provider_error(client, error: Exception) -> None:
    provider_name, fallback_used = resolve_provider_metadata(client)
    LAST_PROVIDER_STATUS.update(
        estado_ultima_llamada="error",
        proveedor_ultima_llamada=provider_name,
        fallback_ultima_llamada=fallback_used,
        error_ultima_llamada=str(error),
    )
