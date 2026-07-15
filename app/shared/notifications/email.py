from __future__ import annotations

import logging
import smtplib
from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage
from enum import StrEnum
from html import escape
from pathlib import Path

from app.shared.config.settings import settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
REPO_ROOT = Path(__file__).resolve().parents[3]
LOGO_PATH = REPO_ROOT / "frontend" / "bwlogo.png"


class EmailDeliveryStatus(StrEnum):
    SENT = "sent"
    SMTP_NOT_CONFIGURED = "smtp_not_configured"
    ADMIN_EMAIL_NOT_CONFIGURED = "admin_email_not_configured"
    DELIVERY_FAILED = "delivery_failed"


@dataclass(frozen=True)
class EmailDeliveryResult:
    status: EmailDeliveryStatus

    @property
    def sent(self) -> bool:
        return self.status == EmailDeliveryStatus.SENT


def _masked_email(address: str) -> str:
    local, separator, domain = address.partition("@")
    return f"{local[:1]}***@{domain}" if separator else "***"


def _attach_logo(message: EmailMessage, *, logo_cid: str) -> None:
    if not LOGO_PATH.exists():
        logger.info("Logo de correo no disponible; se envia el mensaje sin imagen embebida")
        return
    with LOGO_PATH.open("rb") as logo_file:
        message.get_payload()[1].add_related(
            logo_file.read(),
            maintype="image",
            subtype="png",
            cid=logo_cid,
            filename="bwlogo.png",
        )


def _build_pending_registration_admin_message(
    *,
    to_email: str,
    nombre: str,
    username: str,
    registered_email: str,
    registered_at: datetime,
    user_id: int | None,
    approve_url: str | None = None,
    reject_url: str | None = None,
) -> EmailMessage:
    sender = settings.smtp_sender or settings.smtp_username or "noreply@buildwise.local"
    registered_at_text = registered_at.isoformat(timespec="seconds")
    user_id_text = str(user_id) if user_id is not None else "No disponible"
    logo_cid = "buildwise-logo"

    message = EmailMessage()
    message["Subject"] = "Nuevo usuario pendiente de aprobación en BuildWise"
    message["From"] = sender
    message["To"] = to_email
    message.set_content(
        f"""Se registró un nuevo usuario en BuildWise y espera aprobación administrativa.

Nombre: {nombre}
Usuario: {username}
Email: {registered_email}
Fecha de registro: {registered_at_text}
ID: {user_id_text}
Estado: Pendiente de aprobación

Ingresá al panel administrativo de BuildWise para revisar la solicitud.
La cuenta no fue aprobada automáticamente.
{f'Para habilitar: {approve_url}' if approve_url else ''}
{f'Para rechazar y eliminar: {reject_url}' if reject_url else ''}
"""
    )
    message.add_alternative(
        f"""
        <html>
          <body style="margin:0;padding:0;background:#f5f7fb;font-family:Arial,Helvetica,sans-serif;color:#0f172a;">
            <div style="max-width:640px;margin:0 auto;padding:32px 16px;">
              <div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:16px;overflow:hidden;">
                <div style="background:#0f172a;padding:24px;text-align:center;">
                  <img src="cid:{logo_cid}" alt="BuildWise" style="max-width:200px;width:100%;height:auto;" />
                </div>
                <div style="padding:28px;">
                  <h1 style="font-size:22px;margin:0 0 16px;">Nuevo usuario pendiente</h1>
                  <p>Se registró un nuevo usuario en BuildWise y espera aprobación administrativa.</p>
                  <table style="width:100%;border-collapse:collapse;">
                    <tr><th style="text-align:left;padding:6px;">Nombre</th><td style="padding:6px;">{escape(nombre)}</td></tr>
                    <tr><th style="text-align:left;padding:6px;">Usuario</th><td style="padding:6px;">{escape(username)}</td></tr>
                    <tr><th style="text-align:left;padding:6px;">Email</th><td style="padding:6px;">{escape(registered_email)}</td></tr>
                    <tr><th style="text-align:left;padding:6px;">Fecha</th><td style="padding:6px;">{escape(registered_at_text)}</td></tr>
                    <tr><th style="text-align:left;padding:6px;">ID</th><td style="padding:6px;">{escape(user_id_text)}</td></tr>
                    <tr><th style="text-align:left;padding:6px;">Estado</th><td style="padding:6px;">Pendiente de aprobación</td></tr>
                  </table>
                  <p>Ingresá al panel administrativo para revisar la solicitud. La cuenta no fue aprobada automáticamente.</p>
                  {f'<p><a href="{escape(approve_url, quote=True)}" style="display:inline-block;padding:12px 18px;background:#166534;color:#fff;text-decoration:none;">Habilitar</a> <a href="{escape(reject_url, quote=True)}" style="display:inline-block;padding:12px 18px;background:#991b1b;color:#fff;text-decoration:none;">Rechazar y eliminar</a></p>' if approve_url and reject_url else ''}
                </div>
              </div>
            </div>
          </body>
        </html>
        """,
        subtype="html",
    )
    _attach_logo(message, logo_cid=logo_cid)
    return message


def _build_welcome_message(*, to_email: str, nombre: str, username: str) -> EmailMessage:
    sender = settings.smtp_sender or settings.smtp_username or "noreply@buildwise.local"
    safe_nombre = escape(nombre)
    safe_username = escape(username)
    safe_email = escape(to_email)

    logo_cid = "buildwise-logo"
    message = EmailMessage()
    message["Subject"] = "Bienvenido a BuildWise"
    message["From"] = sender
    message["To"] = to_email
    message.set_content(
        f"""Hola {nombre},

Tu cuenta en BuildWise ya quedó creada.

Usuario: {username}
Email: {to_email}

Ya podés ingresar al sistema y usar Forecast, Costos y Optimización.

Si hace falta cargar materiales o completar datos iniciales, eso lo hace el equipo de administración.

Saludos,
Equipo BuildWise
"""
    )
    message.add_alternative(
        f"""
        <html>
          <body style="margin:0; padding:0; background:#f5f7fb; font-family:Arial,Helvetica,sans-serif; color:#0f172a;">
            <div style="max-width:640px; margin:0 auto; padding:32px 16px;">
              <div style="background:#ffffff; border-radius:20px; overflow:hidden; box-shadow:0 10px 30px rgba(15,23,42,.08); border:1px solid #e2e8f0;">
                <div style="background:linear-gradient(135deg,#0f172a 0%,#1f3c88 100%); padding:28px 28px 20px; text-align:center;">
                  <img src="cid:{logo_cid}" alt="BuildWise" style="max-width:220px; width:100%; height:auto; display:block; margin:0 auto 14px;" />
                  <div style="font-size:14px; letter-spacing:.12em; text-transform:uppercase; color:rgba(255,255,255,.78); font-weight:700;">Cuenta creada</div>
                </div>
                <div style="padding:28px;">
                  <h1 style="margin:0 0 16px; font-size:24px; line-height:1.2; color:#0f172a;">Hola {safe_nombre}</h1>
                  <p style="margin:0 0 18px; font-size:16px; line-height:1.6; color:#334155;">
                    Tu cuenta en <strong>BuildWise</strong> ya está lista. Ya podés entrar al sistema y usar forecast, costos y optimización para tus materiales.
                  </p>
                  <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:16px; padding:16px 18px; margin:0 0 20px;">
                    <div style="font-size:13px; color:#64748b; text-transform:uppercase; letter-spacing:.08em; font-weight:700; margin-bottom:10px;">Datos de acceso</div>
                    <div style="font-size:15px; line-height:1.7; color:#0f172a;">
                      <div><strong>Usuario:</strong> {safe_username}</div>
                      <div><strong>Email:</strong> {safe_email}</div>
                    </div>
                  </div>
                  <p style="margin:0 0 24px; font-size:15px; line-height:1.6; color:#334155;">
                    Si hace falta cargar materiales o completar datos iniciales, eso lo hace el equipo de administración.
                  </p>
                  <div style="text-align:center;">
                    <span style="display:inline-block; background:#1f3c88; color:#ffffff; text-decoration:none; padding:12px 20px; border-radius:999px; font-weight:700; font-size:14px;">
                      BuildWise listo para usar
                    </span>
                  </div>
                </div>
              </div>
              <p style="margin:14px 0 0; text-align:center; font-size:12px; color:#94a3b8;">
                Este es un correo automático. Si no esperabas este mensaje, podés ignorarlo.
              </p>
            </div>
          </body>
        </html>
        """,
        subtype="html",
    )

    if LOGO_PATH.exists():
        with LOGO_PATH.open("rb") as logo_file:
            message.get_payload()[1].add_related(
                logo_file.read(),
                maintype="image",
                subtype="png",
                cid=logo_cid,
                filename="bwlogo.png",
            )
    else:
        logger.warning("No se encontro el logo para embebido en el mail: %s", LOGO_PATH)

    return message


def _build_account_deleted_message(*, to_email: str, nombre: str, username: str) -> EmailMessage:
    sender = settings.smtp_sender or settings.smtp_username or "noreply@buildwise.local"
    safe_nombre = escape(nombre)
    safe_username = escape(username)
    safe_email = escape(to_email)
    logo_cid = "buildwise-logo"

    message = EmailMessage()
    message["Subject"] = "Tu cuenta de BuildWise fue deshabilitada"
    message["From"] = sender
    message["To"] = to_email
    message.set_content(
        f"""Hola {nombre},

Tu cuenta de BuildWise fue deshabilitada y ya no está disponible para acceder al sistema.

Usuario: {username}
Email: {to_email}

Si pensás que esto fue un error, contactá al equipo de BuildWise.

Saludos,
Equipo BuildWise
"""
    )
    message.add_alternative(
        f"""
        <html>
          <body style="margin:0; padding:0; background:#f5f7fb; font-family:Arial,Helvetica,sans-serif; color:#0f172a;">
            <div style="max-width:640px; margin:0 auto; padding:32px 16px;">
              <div style="background:#ffffff; border-radius:20px; overflow:hidden; box-shadow:0 10px 30px rgba(15,23,42,.08); border:1px solid #e2e8f0;">
                <div style="background:linear-gradient(135deg,#7f1d1d 0%,#991b1b 100%); padding:28px 28px 20px; text-align:center;">
                  <img src="cid:{logo_cid}" alt="BuildWise" style="max-width:220px; width:100%; height:auto; display:block; margin:0 auto 14px;" />
                  <div style="font-size:14px; letter-spacing:.12em; text-transform:uppercase; color:rgba(255,255,255,.82); font-weight:700;">Cuenta deshabilitada</div>
                </div>
                <div style="padding:28px;">
                  <h1 style="margin:0 0 16px; font-size:24px; line-height:1.2; color:#0f172a;">Hola {safe_nombre}</h1>
                  <p style="margin:0 0 18px; font-size:16px; line-height:1.6; color:#334155;">
                    Tu cuenta en <strong>BuildWise</strong> fue deshabilitada y ya no puede ingresar al sistema.
                  </p>
                  <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:16px; padding:16px 18px; margin:0 0 20px;">
                    <div style="font-size:13px; color:#64748b; text-transform:uppercase; letter-spacing:.08em; font-weight:700; margin-bottom:10px;">Datos asociados</div>
                    <div style="font-size:15px; line-height:1.7; color:#0f172a;">
                      <div><strong>Usuario:</strong> {safe_username}</div>
                      <div><strong>Email:</strong> {safe_email}</div>
                    </div>
                  </div>
                  <p style="margin:0 0 24px; font-size:15px; line-height:1.6; color:#334155;">
                    Si considerás que esto ocurrió por error, podés contactar al equipo de administración.
                  </p>
                </div>
              </div>
            </div>
          </body>
        </html>
        """,
        subtype="html",
    )

    if LOGO_PATH.exists():
        with LOGO_PATH.open("rb") as logo_file:
            message.get_payload()[1].add_related(
                logo_file.read(),
                maintype="image",
                subtype="png",
                cid=logo_cid,
                filename="bwlogo.png",
            )

    return message


def _build_password_recovery_message(*, to_email: str, nombre: str, username: str, reset_url: str) -> EmailMessage:
    sender = settings.smtp_sender or settings.smtp_username or "noreply@buildwise.local"
    safe_nombre = escape(nombre)
    safe_username = escape(username)
    safe_email = escape(to_email)
    safe_reset_url = escape(reset_url, quote=True)
    logo_cid = "buildwise-logo"

    message = EmailMessage()
    message["Subject"] = "Restablecer clave de BuildWise"
    message["From"] = sender
    message["To"] = to_email
    message.set_content(
        f"""Hola {nombre},

Recibimos una solicitud para recuperar la clave de tu cuenta de BuildWise.

Usuario: {username}
Email: {to_email}

Abrí este enlace para definir una nueva clave:
{reset_url}

El enlace vence por seguridad. Si no solicitaste este cambio, podés ignorar este mensaje.

Saludos,
Equipo BuildWise
"""
    )
    message.add_alternative(
        f"""
        <html>
          <body style="margin:0; padding:0; background:#f5f7fb; font-family:Arial,Helvetica,sans-serif; color:#0f172a;">
            <div style="max-width:640px; margin:0 auto; padding:32px 16px;">
              <div style="background:#ffffff; border-radius:20px; overflow:hidden; box-shadow:0 10px 30px rgba(15,23,42,.08); border:1px solid #e2e8f0;">
                <div style="background:linear-gradient(135deg,#0f172a 0%,#1f3c88 100%); padding:28px 28px 20px; text-align:center;">
                  <img src="cid:{logo_cid}" alt="BuildWise" style="max-width:220px; width:100%; height:auto; display:block; margin:0 auto 14px;" />
                  <div style="font-size:14px; letter-spacing:.12em; text-transform:uppercase; color:rgba(255,255,255,.78); font-weight:700;">Recuperacion de clave</div>
                </div>
                <div style="padding:28px;">
                  <h1 style="margin:0 0 16px; font-size:24px; line-height:1.2; color:#0f172a;">Hola {safe_nombre}</h1>
                  <p style="margin:0 0 18px; font-size:16px; line-height:1.6; color:#334155;">
                    Recibimos una solicitud para recuperar la clave de tu cuenta en <strong>BuildWise</strong>.
                  </p>
                  <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:16px; padding:16px 18px; margin:0 0 20px;">
                    <div style="font-size:13px; color:#64748b; text-transform:uppercase; letter-spacing:.08em; font-weight:700; margin-bottom:10px;">Datos de acceso</div>
                    <div style="font-size:15px; line-height:1.7; color:#0f172a;">
                      <div><strong>Usuario:</strong> {safe_username}</div>
                      <div><strong>Email:</strong> {safe_email}</div>
                    </div>
                  </div>
                  <div style="text-align:center; margin:0 0 20px;">
                    <a href="{safe_reset_url}" style="display:inline-block; background:#1f3c88; color:#ffffff; text-decoration:none; padding:12px 20px; border-radius:999px; font-weight:700; font-size:14px;">
                      Cambiar mi clave
                    </a>
                  </div>
                  <p style="margin:0; font-size:15px; line-height:1.6; color:#334155;">
                    El enlace vence por seguridad. Si no solicitaste este cambio, podés ignorar este mensaje.
                  </p>
                </div>
              </div>
              <p style="margin:14px 0 0; text-align:center; font-size:12px; color:#94a3b8;">
                Este es un correo automático. No respondas este mensaje.
              </p>
            </div>
          </body>
        </html>
        """,
        subtype="html",
    )

    if LOGO_PATH.exists():
        with LOGO_PATH.open("rb") as logo_file:
            message.get_payload()[1].add_related(
                logo_file.read(),
                maintype="image",
                subtype="png",
                cid=logo_cid,
                filename="bwlogo.png",
            )

    return message


def _deliver_email(message: EmailMessage, *, to_email: str, log_label: str) -> EmailDeliveryResult:
    if not settings.smtp_host or not settings.smtp_sender:
        logger.info("SMTP no configurado; se omite el correo de %s", log_label)
        return EmailDeliveryResult(EmailDeliveryStatus.SMTP_NOT_CONFIGURED)

    try:
        if settings.smtp_use_ssl:
            server: smtplib.SMTP | smtplib.SMTP_SSL = smtplib.SMTP_SSL(
                settings.smtp_host,
                settings.smtp_port,
                timeout=settings.smtp_timeout_seconds,
            )
        else:
            server = smtplib.SMTP(
                settings.smtp_host,
                settings.smtp_port,
                timeout=settings.smtp_timeout_seconds,
            )

        with server:
            if settings.smtp_use_tls and not settings.smtp_use_ssl:
                server.starttls()
            if settings.smtp_username and settings.smtp_password:
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(message)
        logger.info("Correo de %s enviado a %s", log_label, _masked_email(to_email))
        return EmailDeliveryResult(EmailDeliveryStatus.SENT)
    except (smtplib.SMTPException, OSError, TimeoutError) as exc:
        logger.warning("Fallo seguro al enviar correo de %s: %s", log_label, type(exc).__name__)
        return EmailDeliveryResult(EmailDeliveryStatus.DELIVERY_FAILED)


def _send_email(message: EmailMessage, *, to_email: str, log_label: str) -> bool:
    return _deliver_email(message, to_email=to_email, log_label=log_label).sent


def send_pending_registration_admin_email(
    *,
    nombre: str,
    username: str,
    registered_email: str,
    registered_at: datetime,
    user_id: int | None,
    approve_url: str | None = None,
    reject_url: str | None = None,
) -> EmailDeliveryResult:
    to_email = settings.admin_notification_email
    if not to_email:
        logger.info("Destinatario administrativo no configurado; se omite la notificacion de registro")
        return EmailDeliveryResult(EmailDeliveryStatus.ADMIN_EMAIL_NOT_CONFIGURED)
    try:
        message = _build_pending_registration_admin_message(
            to_email=to_email,
            nombre=nombre,
            username=username,
            registered_email=registered_email,
            registered_at=registered_at,
            user_id=user_id,
            approve_url=approve_url,
            reject_url=reject_url,
        )
    except (ValueError, TypeError, OSError) as exc:
        logger.warning("No se pudo construir la notificacion de registro: %s", type(exc).__name__)
        return EmailDeliveryResult(EmailDeliveryStatus.DELIVERY_FAILED)
    return _deliver_email(message, to_email=to_email, log_label="registro pendiente")


def send_welcome_email(*, to_email: str, nombre: str, username: str) -> bool:
    message = _build_welcome_message(to_email=to_email, nombre=nombre, username=username)
    return _send_email(message, to_email=to_email, log_label="bienvenida")


def send_account_deleted_email(*, to_email: str, nombre: str, username: str) -> bool:
    message = _build_account_deleted_message(to_email=to_email, nombre=nombre, username=username)
    return _send_email(message, to_email=to_email, log_label="baja")


def send_password_recovery_email(*, to_email: str, nombre: str, username: str, reset_url: str) -> bool:
    message = _build_password_recovery_message(
        to_email=to_email,
        nombre=nombre,
        username=username,
        reset_url=reset_url,
    )
    return _send_email(message, to_email=to_email, log_label="recuperacion de clave")
