from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.auth.infrastructure.models import Usuario
from app.modules.auth.interfaces.dependencies import get_current_user, require_admin
from app.modules.auth.interfaces.schemas import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    UsuarioAdminRead,
    UsuarioRead,
)
from app.shared.database.session import get_db
from app.shared.notifications.email import send_account_deleted_email, send_welcome_email
from app.shared.security.tokens import create_access_token, hash_password, verify_password


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = db.scalar(select(Usuario).where(Usuario.username == payload.username))
    if user is None or not user.activo or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario o clave incorrectos")

    token, expires_at = create_access_token(user_id=user.id, username=user.username, rol=user.rol)
    return LoginResponse(access_token=token, expires_at=expires_at, usuario=user)


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> RegisterResponse:
    username = payload.username.strip()
    nombre = payload.nombre.strip()
    email = payload.email.strip().lower()

    if not username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El usuario no puede estar vacio")
    if not nombre:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El nombre no puede estar vacio")
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El email no es valido")

    existing_username = db.scalar(select(Usuario).where(Usuario.username == username))
    if existing_username is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El usuario ya existe")

    existing_email = db.scalar(select(Usuario).where(Usuario.email == email))
    if existing_email is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El email ya esta registrado")

    user = Usuario(
        username=username,
        email=email,
        nombre=nombre,
        password_hash=hash_password(payload.password),
        rol="cliente",
        activo=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return RegisterResponse(
        message="Cuenta creada. Queda pendiente de habilitacion por un administrador.",
        usuario=user,
    )


@router.get("/me", response_model=UsuarioRead)
def me(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    return current_user


@router.get("/usuarios", response_model=list[UsuarioAdminRead])
def listar_usuarios(db: Session = Depends(get_db), current_user: Usuario = Depends(require_admin)) -> list[Usuario]:
    stmt = select(Usuario).order_by(Usuario.created_at.desc(), Usuario.id.desc())
    return list(db.scalars(stmt))


@router.post("/usuarios/{user_id}/habilitar", response_model=UsuarioAdminRead)
def habilitar_usuario(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
) -> Usuario:
    user = db.get(Usuario, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    if not user.email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El usuario no tiene email")

    was_active = user.activo
    user.activo = True
    db.commit()
    db.refresh(user)

    if not was_active:
        send_welcome_email(to_email=user.email, nombre=user.nombre, username=user.username)

    return user


@router.delete("/usuarios/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_usuario(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
) -> None:
    if current_user.id == user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No te puedes eliminar a vos mismo")

    user = db.get(Usuario, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    if user.rol == "admin":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se puede eliminar un usuario admin")

    user_email = user.email
    user_nombre = user.nombre
    user_username = user.username
    db.delete(user)
    db.commit()

    if user_email:
        send_account_deleted_email(to_email=user_email, nombre=user_nombre, username=user_username)
