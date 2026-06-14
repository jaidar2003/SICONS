from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.modules.auth.application.service import (
    autenticar_usuario,
    listar_usuarios_registrados,
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
