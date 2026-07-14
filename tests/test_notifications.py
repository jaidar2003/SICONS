import smtplib
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from app.shared.config.settings import settings
from app.shared.notifications import email


@pytest.fixture
def mock_settings(monkeypatch):
    monkeypatch.setattr(settings, "smtp_host", "localhost")
    monkeypatch.setattr(settings, "smtp_port", 587)
    monkeypatch.setattr(settings, "smtp_sender", "test@buildwise.local")
    monkeypatch.setattr(settings, "smtp_username", "user")
    monkeypatch.setattr(settings, "smtp_password", "pass")
    monkeypatch.setattr(settings, "smtp_use_tls", True)
    monkeypatch.setattr(settings, "smtp_use_ssl", False)
    monkeypatch.setattr(settings, "admin_notification_email", "admin@example.com")
    return settings

def test_build_welcome_message():
    msg = email._build_welcome_message(to_email="user@example.com", nombre="User", username="user")
    assert msg["To"] == "user@example.com"
    assert msg["Subject"] == "Bienvenido a BuildWise"
    # For multipart messages, we check the payload
    payload = msg.get_payload()
    assert len(payload) >= 1
    # Check text part
    assert "User" in payload[0].get_content()

def test_build_welcome_message_no_logo(monkeypatch):
    monkeypatch.setattr(email, "LOGO_PATH", MagicMock(exists=lambda: False))
    msg = email._build_welcome_message(to_email="user@example.com", nombre="User", username="user")
    assert msg["To"] == "user@example.com"


def test_build_password_recovery_message():
    msg = email._build_password_recovery_message(
        to_email="user@example.com",
        nombre="User",
        username="user",
        reset_url="https://buildwise.com.ar/?reset_token=abc",
    )
    assert msg["To"] == "user@example.com"
    assert msg["Subject"] == "Restablecer clave de BuildWise"
    assert "https://buildwise.com.ar/?reset_token=abc" in msg.get_payload()[0].get_content()


def test_send_welcome_email_success(mock_settings):
    with patch("app.shared.notifications.email.smtplib.SMTP") as mock_smtp:
        mock_server = mock_smtp.return_value
        
        result = email.send_welcome_email(to_email="user@example.com", nombre="User", username="user")
        
        assert result is True
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("user", "pass")
        mock_server.send_message.assert_called_once()

def test_send_welcome_email_ssl(mock_settings, monkeypatch):
    monkeypatch.setattr(settings, "smtp_use_ssl", True)
    with patch("app.shared.notifications.email.smtplib.SMTP_SSL") as mock_smtp_ssl:
        mock_server = mock_smtp_ssl.return_value
        
        result = email.send_welcome_email(to_email="user@example.com", nombre="User", username="user")
        
        assert result is True
        mock_server.login.assert_called_once()

def test_send_welcome_email_no_config(monkeypatch):
    monkeypatch.setattr(settings, "smtp_host", None)
    result = email.send_welcome_email(to_email="user@example.com", nombre="User", username="user")
    assert result is False

def test_send_welcome_email_failure(mock_settings):
    with patch("app.shared.notifications.email.smtplib.SMTP") as mock_smtp:
        mock_smtp.side_effect = smtplib.SMTPException("SMTP error")
        result = email.send_welcome_email(to_email="user@example.com", nombre="User", username="user")
        assert result is False

def test_send_account_deleted_email_success(mock_settings):
    with patch("app.shared.notifications.email.smtplib.SMTP") as mock_smtp:
        mock_server = mock_smtp.return_value
        
        result = email.send_account_deleted_email(to_email="user@example.com", nombre="User", username="user")
        
        assert result is True
        mock_server.send_message.assert_called_once()

def test_send_account_deleted_email_no_config(monkeypatch):
    monkeypatch.setattr(settings, "smtp_host", None)
    result = email.send_account_deleted_email(to_email="user@example.com", nombre="User", username="user")
    assert result is False

def test_send_account_deleted_email_failure(mock_settings):
    with patch("app.shared.notifications.email.smtplib.SMTP") as mock_smtp:
        mock_smtp.side_effect = smtplib.SMTPException("SMTP error")
        result = email.send_account_deleted_email(to_email="user@example.com", nombre="User", username="user")
        assert result is False

def test_send_account_deleted_email_ssl(mock_settings, monkeypatch):
    monkeypatch.setattr(settings, "smtp_use_ssl", True)
    with patch("app.shared.notifications.email.smtplib.SMTP_SSL"):
        result = email.send_account_deleted_email(to_email="user@example.com", nombre="User", username="user")
        
        assert result is True


def test_send_password_recovery_email_success(mock_settings):
    with patch("app.shared.notifications.email.smtplib.SMTP") as mock_smtp:
        mock_server = mock_smtp.return_value

        result = email.send_password_recovery_email(
            to_email="user@example.com",
            nombre="User",
            username="user",
            reset_url="https://buildwise.com.ar/?reset_token=abc",
        )

        assert result is True
        mock_server.send_message.assert_called_once()


def test_build_pending_registration_admin_message_escapes_html_and_has_no_secrets(mock_settings, monkeypatch):
    monkeypatch.setattr(email, "LOGO_PATH", MagicMock(exists=lambda: False))
    message = email._build_pending_registration_admin_message(
        to_email="admin@example.com",
        nombre='<script>alert("x")</script>',
        username="user\nBcc: attacker@example.com",
        registered_email="new@example.com",
        registered_at=datetime(2026, 7, 14, 20, 0, tzinfo=UTC),
        user_id=42,
    )
    text = message.get_body(preferencelist=("plain",)).get_content()
    html = message.get_body(preferencelist=("html",)).get_content()

    assert message["Subject"] == "Nuevo usuario pendiente de aprobación en BuildWise"
    assert message["To"] == "admin@example.com"
    assert message["From"] == "test@buildwise.local"
    assert "Pendiente de aprobación" in text
    assert "2026-07-14T20:00:00+00:00" in text
    assert "ID: 42" in text
    assert "&lt;script&gt;" in html
    assert "<script>" not in html
    assert "password" not in text.lower()
    assert "smtp" not in text.lower()
    assert message["Bcc"] is None
    assert message["Cc"] is None


def test_pending_registration_admin_email_requires_recipient(mock_settings, monkeypatch):
    monkeypatch.setattr(settings, "admin_notification_email", None)
    result = email.send_pending_registration_admin_email(
        nombre="Nuevo",
        username="nuevo",
        registered_email="new@example.com",
        registered_at=datetime.now(UTC),
        user_id=1,
    )
    assert result.status == email.EmailDeliveryStatus.ADMIN_EMAIL_NOT_CONFIGURED


def test_pending_registration_admin_email_success(mock_settings):
    with patch("app.shared.notifications.email.smtplib.SMTP") as mock_smtp:
        result = email.send_pending_registration_admin_email(
            nombre="Nuevo",
            username="nuevo",
            registered_email="new@example.com",
            registered_at=datetime.now(UTC),
            user_id=1,
        )
    assert result.sent is True
    message = mock_smtp.return_value.send_message.call_args.args[0]
    assert message["To"] == "admin@example.com"


def test_pending_registration_admin_email_builder_failure_is_safe(mock_settings, monkeypatch):
    monkeypatch.setattr(
        email,
        "_build_pending_registration_admin_message",
        lambda **_kwargs: (_ for _ in ()).throw(ValueError("invalid header")),
    )
    result = email.send_pending_registration_admin_email(
        nombre="Nuevo",
        username="nuevo",
        registered_email="new@example.com",
        registered_at=datetime.now(UTC),
        user_id=1,
    )
    assert result.status == email.EmailDeliveryStatus.DELIVERY_FAILED


@pytest.mark.parametrize("failure", [TimeoutError(), smtplib.SMTPAuthenticationError(535, b"denied"), smtplib.SMTPException()])
def test_pending_registration_admin_email_failure_is_safe(mock_settings, failure, caplog):
    with patch("app.shared.notifications.email.smtplib.SMTP", side_effect=failure):
        result = email.send_pending_registration_admin_email(
            nombre="Nuevo",
            username="nuevo",
            registered_email="new@example.com",
            registered_at=datetime.now(UTC),
            user_id=1,
        )
    assert result.status == email.EmailDeliveryStatus.DELIVERY_FAILED
    assert "admin@example.com" not in caplog.text
    assert "denied" not in caplog.text
