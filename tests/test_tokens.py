import pytest
from datetime import UTC, datetime, timedelta
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
