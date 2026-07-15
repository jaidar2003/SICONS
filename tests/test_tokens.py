
import pytest

from app.shared.security import tokens


def test_verify_password_invalid_format():
    assert tokens.verify_password("p", "invalid-format") is False

def test_verify_password_invalid_algorithm():
    assert tokens.verify_password("p", "sha1$1000$salt$hash") is False

def test_decode_access_token_invalid_format():
    with pytest.raises(ValueError, match="Token invalido"):
        tokens.decode_access_token("invalidtoken")

def test_decode_access_token_invalid_signature():
    token, _ = tokens.create_access_token(user_id=1, username="u", rol="admin")
    parts = token.split(".")
    invalid_token = parts[0] + "." + "invalidsignature"
    with pytest.raises(ValueError, match="Token invalido"):
        tokens.decode_access_token(invalid_token)

def test_decode_access_token_expired():
    from app.shared.config.settings import settings
    # Create an already expired token by setting TTL to negative
    with pytest.MonkeyPatch().context() as m:
        m.setattr(settings, "auth_token_ttl_minutes", -10)
        token, _ = tokens.create_access_token(user_id=1, username="u", rol="admin")
    
    with pytest.raises(ValueError, match="Token expirado"):
        tokens.decode_access_token(token)


def test_password_reset_token_roundtrip():
    token, expires_at = tokens.create_password_reset_token(user_id=1, password_hash="hash")
    payload = tokens.decode_password_reset_token(token)

    assert expires_at
    assert payload["sub"] == 1
    assert payload["purpose"] == "password_reset"
    assert payload["pwd"] == tokens.password_reset_fingerprint("hash")


def test_decode_password_reset_token_rejects_access_token():
    token, _ = tokens.create_access_token(user_id=1, username="u", rol="admin")

    with pytest.raises(ValueError, match="Token invalido"):
        tokens.decode_password_reset_token(token)


def test_registration_action_tokens_are_signed_and_action_scoped():
    token, expires_at = tokens.create_registration_action_token(user_id=7, email="user@example.com", action="approve")
    payload = tokens.decode_registration_action_token(token)
    assert expires_at
    assert payload["sub"] == 7
    assert payload["action"] == "approve"
    assert payload["email"] == tokens.registration_action_fingerprint("USER@example.com")


def test_registration_action_token_rejects_invalid_action():
    with pytest.raises(ValueError, match="Accion"):
        tokens.create_registration_action_token(user_id=7, email="user@example.com", action="delete")
