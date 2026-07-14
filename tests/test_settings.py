import pytest
from pydantic import ValidationError

from app.shared.config.settings import Settings


def test_development_accepts_documented_local_secret() -> None:
    settings = Settings(
        environment="development",
        auth_secret_key="buildwise-dev-secret-change-me",
        _env_file=None,
    )

    assert settings.is_production is False
    assert "buildwise" in settings.database_url


def test_production_rejects_documented_insecure_secret() -> None:
    with pytest.raises(ValidationError, match="secreto seguro"):
        Settings(
            environment="production",
            auth_secret_key="change-this-auth-secret-key",
            _env_file=None,
        )


def test_production_accepts_explicit_secure_secret() -> None:
    settings = Settings(
        environment="production",
        auth_secret_key="a-production-secret-managed-outside-the-repository",
        _env_file=None,
    )

    assert settings.is_production is True
    assert settings.forecast_allow_synchronous_compute is False


def test_production_allows_conscious_synchronous_forecast_override() -> None:
    settings = Settings(
        environment="production",
        auth_secret_key="a-production-secret-managed-outside-the-repository",
        forecast_allow_synchronous_compute=True,
        _env_file=None,
    )

    assert settings.forecast_allow_synchronous_compute is True


@pytest.mark.parametrize("environment", ["development", "test"])
def test_non_production_keeps_synchronous_forecast_fallback(environment: str) -> None:
    settings = Settings(
        environment=environment,
        auth_secret_key="buildwise-dev-secret-change-me",
        _env_file=None,
    )

    assert settings.forecast_allow_synchronous_compute is True
