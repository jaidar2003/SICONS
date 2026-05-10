from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from html import escape
from pathlib import Path

from app.shared.config.settings import settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
REPO_ROOT = Path(__file__).resolve().parents[3]
LOGO_PATH = REPO_ROOT / "frontend" / "bwlogo.png"


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


def send_welcome_email(*, to_email: str, nombre: str, username: str) -> bool:
    if not settings.smtp_host or not settings.smtp_sender:
        logger.info("SMTP no configurado, se omite el mail de bienvenida para %s", to_email)
        return False

    sender = settings.smtp_sender or settings.smtp_username or "noreply@buildwise.local"
    message = _build_welcome_message(to_email=to_email, nombre=nombre, username=username)
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
        logger.info("Mail de bienvenida enviado a %s desde %s", to_email, sender)
        return True
    except Exception:
        logger.exception("No se pudo enviar el mail de bienvenida a %s", to_email)
        return False


def send_account_deleted_email(*, to_email: str, nombre: str, username: str) -> bool:
    if not settings.smtp_host or not settings.smtp_sender:
        logger.info("SMTP no configurado, se omite el mail de baja para %s", to_email)
        return False

    sender = settings.smtp_sender or settings.smtp_username or "noreply@buildwise.local"
    message = _build_account_deleted_message(to_email=to_email, nombre=nombre, username=username)
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
        logger.info("Mail de baja enviado a %s desde %s", to_email, sender)
        return True
    except Exception:
        logger.exception("No se pudo enviar el mail de baja a %s", to_email)
        return False
