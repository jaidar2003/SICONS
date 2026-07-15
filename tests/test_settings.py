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


def test_admin_notification_email_is_optional_and_normalized() -> None:
    without_recipient = Settings(environment="test", auth_secret_key="safe-test-secret", _env_file=None)
    configured = Settings(
        environment="test",
        auth_secret_key="safe-test-secret",
        admin_notification_email=" Admin@Example.COM ",
        _env_file=None,
    )
    assert without_recipient.admin_notification_email is None
    assert configured.admin_notification_email == "admin@example.com"


@pytest.mark.parametrize("value", ["invalid", "a@", "a@example.com\nBcc:x@example.com"])
def test_admin_notification_email_rejects_invalid_values(value: str) -> None:
    with pytest.raises(ValueError, match="ADMIN_NOTIFICATION_EMAIL"):
        Settings(environment="test", auth_secret_key="safe-test-secret", admin_notification_email=value, _env_file=None)


def test_production_admin_actions_require_https_backend_url() -> None:
    with pytest.raises(ValueError, match="BACKEND_PUBLIC_URL"):
        Settings(
            environment="production",
            auth_secret_key="safe-production-secret",
            admin_notification_email="admin@example.com",
            backend_public_url="http://api.example.com",
            _env_file=None,
        )
