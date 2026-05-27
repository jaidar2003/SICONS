from unittest.mock import MagicMock, patch
from decimal import Decimal
import pytest
import smtplib

from app.shared.notifications import email
from app.shared.config.settings import settings

@pytest.fixture
def mock_settings(monkeypatch):
    monkeypatch.setattr(settings, "smtp_host", "localhost")
    monkeypatch.setattr(settings, "smtp_port", 587)
    monkeypatch.setattr(settings, "smtp_sender", "test@buildwise.local")
    monkeypatch.setattr(settings, "smtp_username", "user")
    monkeypatch.setattr(settings, "smtp_password", "pass")
    monkeypatch.setattr(settings, "smtp_use_tls", True)
    monkeypatch.setattr(settings, "smtp_use_ssl", False)
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
        mock_smtp.side_effect = Exception("SMTP error")
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
        mock_smtp.side_effect = Exception("SMTP error")
        result = email.send_account_deleted_email(to_email="user@example.com", nombre="User", username="user")
        assert result is False

def test_send_account_deleted_email_ssl(mock_settings, monkeypatch):
    monkeypatch.setattr(settings, "smtp_use_ssl", True)
    with patch("app.shared.notifications.email.smtplib.SMTP_SSL") as mock_smtp_ssl:
        mock_server = mock_smtp_ssl.return_value
        
        result = email.send_account_deleted_email(to_email="user@example.com", nombre="User", username="user")
        
        assert result is True
