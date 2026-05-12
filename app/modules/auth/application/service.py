from dataclasses import dataclass
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.auth.infrastructure.models import Usuario
from app.shared.database.audit_service import register_audit_log
from app.shared.notifications.email import send_account_deleted_email, send_welcome_email
from app.shared.security.tokens import create_access_token, hash_password, verify_password


@dataclass(frozen=True)
class LoginResult:
    access_token: str
    expires_at: datetime
    usuario: Usuario


@dataclass(frozen=True)
class RegisterResult:
    message: str
    usuario: Usuario


def autenticar_usuario(db: Session, *, username: str, password: str) -> LoginResult:
    user = db.scalar(select(Usuario).where(Usuario.username == username))
    if user is None or not user.activo or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario o clave incorrectos")

    token, expires_at = create_access_token(user_id=user.id, username=user.username, rol=user.rol)

    register_audit_log(
        db,
        usuario_id=user.id,
        accion="LOGIN",
        recurso="Usuario",
        recurso_id=str(user.id),
    )
    db.commit()

    return LoginResult(access_token=token, expires_at=expires_at, usuario=user)


def registrar_cliente(db: Session, *, username: str, nombre: str, email: str, password: str) -> RegisterResult:
    username = username.strip()
    nombre = nombre.strip()
    email = email.strip().lower()

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
        password_hash=hash_password(password),
        rol="cliente",
        activo=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    register_audit_log(
        db,
        usuario_id=None,
        accion="REGISTER",
        recurso="Usuario",
        recurso_id=str(user.id),
        cambios={"username": user.username, "email": user.email},
    )
    db.commit()

    return RegisterResult(
        message="Cuenta creada. Queda pendiente de habilitacion por un administrador.",
        usuario=user,
    )


def listar_usuarios_registrados(db: Session) -> list[Usuario]:
    stmt = select(Usuario).order_by(Usuario.created_at.desc(), Usuario.id.desc())
    return list(db.scalars(stmt))


def habilitar_usuario(db: Session, *, user_id: int) -> Usuario:
    user = db.get(Usuario, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    if not user.email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El usuario no tiene email")

    was_active = user.activo
    user.activo = True

    register_audit_log(
        db,
        usuario_id=None,  # El que lo habilita es un admin, pero no lo pasamos a esta funcion todavia
        accion="ACTIVATE",
        recurso="Usuario",
        recurso_id=str(user.id),
    )

    db.commit()
    db.refresh(user)

    if not was_active:
        send_welcome_email(to_email=user.email, nombre=user.nombre, username=user.username)

    return user


def eliminar_usuario(db: Session, *, user_id: int, current_user: Usuario) -> None:
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

    register_audit_log(
        db,
        usuario_id=current_user.id,
        accion="DELETE",
        recurso="Usuario",
        recurso_id=str(user.id),
        cambios={"username": user_username, "email": user_email},
    )

    db.delete(user)
    db.commit()

    if user_email:
        send_account_deleted_email(to_email=user_email, nombre=user_nombre, username=user_username)
