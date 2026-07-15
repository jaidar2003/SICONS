from html import escape

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.modules.auth.application.service import (
    autenticar_usuario,
    listar_usuarios_registrados,
    preview_registration_action,
    process_registration_action,
    registrar_cliente,
    restablecer_password,
    solicitar_recuperacion_password,
    validar_token_recuperacion_password,
)
from app.modules.auth.application.service import (
    eliminar_usuario as eliminar_usuario_service,
)
from app.modules.auth.application.service import (
    habilitar_usuario as habilitar_usuario_service,
)
from app.modules.auth.infrastructure.models import Usuario
from app.modules.auth.interfaces.dependencies import get_current_user, require_admin
from app.modules.auth.interfaces.schemas import (
    LoginRequest,
    LoginResponse,
    MessageResponse,
    PasswordRecoveryRequest,
    PasswordResetRequest,
    PasswordResetTokenValidationRequest,
    RegisterRequest,
    RegisterResponse,
    UsuarioAdminRead,
    UsuarioRead,
)
from app.shared.database.session import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


def _registration_action_page(*, token: str, action: str, username: str) -> str:
    verb = "habilitar" if action == "approve" else "rechazar y eliminar"
    color = "#166534" if action == "approve" else "#991b1b"
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><title>BuildWise</title></head>
<body style="font-family:Arial,sans-serif;background:#f5f7fb;padding:40px;color:#0f172a">
<main style="max-width:560px;margin:auto;background:white;padding:28px;border:1px solid #e2e8f0">
<h1>Confirmar solicitud</h1><p>Vas a {verb} la cuenta <strong>{escape(username)}</strong>.</p>
<form method="post" action="/auth/registration-action?token={escape(token, quote=True)}">
<button type="submit" style="background:{color};color:white;border:0;padding:12px 18px;cursor:pointer">Confirmar</button>
</form><p>Si no querés realizar la acción, cerrá esta ventana.</p></main></body></html>"""


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    result = autenticar_usuario(db, username=payload.username, password=payload.password)
    return LoginResponse(access_token=result.access_token, expires_at=result.expires_at, usuario=result.usuario)


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> RegisterResponse:
    result = registrar_cliente(
        db,
        username=payload.username,
        nombre=payload.nombre,
        email=payload.email,
        password=payload.password,
    )
    return RegisterResponse(message=result.message, usuario=result.usuario)


@router.get("/registration-action/confirm", response_class=HTMLResponse, include_in_schema=False)
def confirm_registration_action(token: str = Query(min_length=1, max_length=2000), db: Session = Depends(get_db)) -> str:
    preview = preview_registration_action(db, token=token)
    return _registration_action_page(token=token, action=preview.action, username=preview.username)


@router.post("/registration-action", response_class=HTMLResponse, include_in_schema=False)
def execute_registration_action(token: str = Query(min_length=1, max_length=2000), db: Session = Depends(get_db)) -> str:
    result = process_registration_action(db, token=token)
    outcome = "habilitada" if result.action == "approve" else "rechazada y eliminada"
    return f"<!doctype html><html lang='es'><meta charset='utf-8'><body><h1>Solicitud procesada</h1><p>La cuenta {escape(result.username)} fue {outcome}.</p></body></html>"


@router.post("/password-recovery", response_model=MessageResponse)
def password_recovery(payload: PasswordRecoveryRequest, db: Session = Depends(get_db)) -> MessageResponse:
    result = solicitar_recuperacion_password(db, identifier=payload.identifier)
    return MessageResponse(message=result.message)


@router.post("/password-reset", response_model=MessageResponse)
def password_reset(payload: PasswordResetRequest, db: Session = Depends(get_db)) -> MessageResponse:
    result = restablecer_password(db, token=payload.token, password=payload.password)
    return MessageResponse(message=result.message)


@router.post("/password-reset/validate", response_model=MessageResponse)
def validate_password_reset_token(
    payload: PasswordResetTokenValidationRequest,
    db: Session = Depends(get_db),
) -> MessageResponse:
    result = validar_token_recuperacion_password(db, token=payload.token)
    return MessageResponse(message=result.message)


@router.get("/me", response_model=UsuarioRead)
def me(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    return current_user


@router.get("/usuarios", response_model=list[UsuarioAdminRead])
def listar_usuarios(db: Session = Depends(get_db), current_user: Usuario = Depends(require_admin)) -> list[Usuario]:
    return listar_usuarios_registrados(db)


@router.post("/usuarios/{user_id}/habilitar", response_model=UsuarioAdminRead)
def habilitar_usuario(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
) -> Usuario:
    return habilitar_usuario_service(db, user_id=user_id)


@router.delete("/usuarios/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_usuario(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
) -> None:
    eliminar_usuario_service(db, user_id=user_id, current_user=current_user)
