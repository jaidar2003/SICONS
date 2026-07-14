from datetime import UTC, datetime

from app.shared.config.settings import settings
from app.shared.notifications.email import _masked_email, send_pending_registration_admin_email


def main() -> int:
    recipient = settings.admin_notification_email
    if not recipient:
        print("No se envio: ADMIN_NOTIFICATION_EMAIL no esta configurado.")
        return 1
    print(f"Enviando prueba administrativa a {_masked_email(recipient)}")
    result = send_pending_registration_admin_email(
        nombre="Usuario ficticio de prueba",
        username="buildwise-email-test",
        registered_email="ficticio@example.invalid",
        registered_at=datetime.now(UTC),
        user_id=None,
    )
    print("Resultado: enviado" if result.sent else f"Resultado seguro: {result.status.value}")
    return 0 if result.sent else 1


if __name__ == "__main__":
    raise SystemExit(main())
