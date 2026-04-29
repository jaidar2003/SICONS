from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.auth.infrastructure.models import Usuario
from app.modules.auth.interfaces.dependencies import get_current_user
from app.modules.auth.interfaces.schemas import LoginRequest, LoginResponse, UsuarioRead
from app.shared.database.session import get_db
from app.shared.security.tokens import create_access_token, verify_password


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = db.scalar(select(Usuario).where(Usuario.username == payload.username))
    if user is None or not user.activo or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario o clave incorrectos")

    token, expires_at = create_access_token(user_id=user.id, username=user.username, rol=user.rol)
    return LoginResponse(access_token=token, expires_at=expires_at, usuario=user)


@router.get("/me", response_model=UsuarioRead)
def me(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    return current_user
