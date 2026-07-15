# Notificación administrativa de registros

Cuando el registro público crea una cuenta, el usuario queda inactivo y la auditoría `REGISTER` se confirma antes de intentar enviar correo. Si `ADMIN_NOTIFICATION_EMAIL` y SMTP están configurados, BuildWise avisa al administrador que existe una solicitud pendiente.

La notificación no activa la cuenta, no contiene contraseñas ni tokens y no permite aprobar desde el correo. El administrador debe ingresar al panel existente. El usuario recibe el correo de bienvenida únicamente después de ser habilitado.

## Configuración

```env
SMTP_HOST=
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_SENDER=
SMTP_USE_TLS=true
SMTP_USE_SSL=false
SMTP_TIMEOUT_SECONDS=10
ADMIN_NOTIFICATION_EMAIL=
BACKEND_PUBLIC_URL=https://api.example.com
REGISTRATION_ACTION_TOKEN_TTL_MINUTES=60
```

`ADMIN_NOTIFICATION_EMAIL` es opcional. Dejarla vacía desactiva únicamente la notificación administrativa. Cuando está configurada en producción, `BACKEND_PUBLIC_URL` debe usar HTTPS. Los botones Habilitar y Rechazar abren una confirmación; abrir el correo no ejecuta la acción. En OpenStack estas variables se colocan en `.env.openstack`, que se entrega al contenedor mediante `env_file` y no debe versionarse. Para puerto 587 se usa STARTTLS; para SMTP SSL directo se configura el puerto correspondiente, `SMTP_USE_SSL=true` y `SMTP_USE_TLS=false`.

## Fallos y trazabilidad

El envío es best-effort. Una falta de configuración, timeout, error de autenticación o error SMTP no revierte el usuario ni cambia la respuesta HTTP 201. Auditoría registra uno de estos eventos sin destinatarios ni contenido del mensaje:

- `ADMIN_REGISTRATION_NOTIFICATION_SENT`
- `ADMIN_REGISTRATION_NOTIFICATION_FAILED`
- `ADMIN_REGISTRATION_NOTIFICATION_SKIPPED`

Los motivos categóricos son `sent`, `delivery_failed`, `smtp_not_configured` y `admin_email_not_configured`. No existe reintento persistente ni outbox; una interrupción después del commit puede impedir la notificación aunque la cuenta quede creada.

## Prueba manual opt-in

La prueba utiliza datos ficticios, no crea usuarios y nunca se ejecuta en CI:

```bash
python -m app.operations.test_admin_notification_email
```

El comando muestra solamente el destinatario enmascarado y un resultado seguro. La recepción y renderización deben confirmarse manualmente en la casilla administrativa.

## Abuso y operación

Registros inválidos o duplicados no envían nuevas notificaciones. El request no controla el destinatario y sus campos se escapan en HTML. Sigue existiendo riesgo de spam mediante registros válidos con emails distintos; rate limiting, CAPTCHA, outbox y reintentos persistentes quedan como mejoras futuras.

Los demás correos mantienen responsabilidades separadas: recuperación restablece contraseña mediante token, bienvenida se envía tras habilitación y baja informa la deshabilitación de la cuenta.
