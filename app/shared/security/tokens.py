import base64
import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta

from app.shared.config.settings import settings

PASSWORD_ITERATIONS = 260_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt, expected = password_hash.split("$", 3)
        iterations = int(iterations_text)
    except ValueError:
        return False

    if algorithm != "pbkdf2_sha256":
        return False

    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations).hex()
    return hmac.compare_digest(digest, expected)


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def create_access_token(*, user_id: int, username: str, rol: str) -> tuple[str, datetime]:
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.auth_token_ttl_minutes)
    payload = {
        "sub": user_id,
        "username": username,
        "rol": rol,
        "exp": int(expires_at.timestamp()),
    }
    payload_part = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(settings.auth_secret_key.encode("utf-8"), payload_part.encode("ascii"), hashlib.sha256).digest()
    return f"{payload_part}.{_b64url_encode(signature)}", expires_at


def password_reset_fingerprint(password_hash: str) -> str:
    digest = hmac.new(settings.auth_secret_key.encode("utf-8"), password_hash.encode("utf-8"), hashlib.sha256).hexdigest()
    return digest[:32]


def create_password_reset_token(*, user_id: int, password_hash: str) -> tuple[str, datetime]:
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.password_reset_token_ttl_minutes)
    payload = {
        "sub": user_id,
        "purpose": "password_reset",
        "pwd": password_reset_fingerprint(password_hash),
        "exp": int(expires_at.timestamp()),
    }
    payload_part = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(settings.auth_secret_key.encode("utf-8"), payload_part.encode("ascii"), hashlib.sha256).digest()
    return f"{payload_part}.{_b64url_encode(signature)}", expires_at


def decode_access_token(token: str) -> dict:
    try:
        payload_part, signature_part = token.split(".", 1)
    except ValueError as exc:
        raise ValueError("Token invalido") from exc

    expected = hmac.new(settings.auth_secret_key.encode("utf-8"), payload_part.encode("ascii"), hashlib.sha256).digest()
    received = _b64url_decode(signature_part)
    if not hmac.compare_digest(received, expected):
        raise ValueError("Token invalido")

    payload = json.loads(_b64url_decode(payload_part))
    if int(payload.get("exp", 0)) < int(datetime.now(UTC).timestamp()):
        raise ValueError("Token expirado")
    return payload


def decode_password_reset_token(token: str) -> dict:
    payload = decode_access_token(token)
    if payload.get("purpose") != "password_reset":
        raise ValueError("Token invalido")
    return payload
