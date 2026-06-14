
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.modules.auth.application.service import (
    autenticar_usuario,
    eliminar_usuario,
    habilitar_usuario,
    registrar_cliente,
    restablecer_password,
    solicitar_recuperacion_password,
    validar_token_recuperacion_password,
)
from app.modules.auth.infrastructure.models import Usuario
from app.shared.security.tokens import hash_password, verify_password


def make_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as conn:
        conn.exec_driver_sql(
            """
            CREATE TABLE usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(80) NOT NULL UNIQUE,
                email VARCHAR(160) UNIQUE,
                nombre VARCHAR(120) NOT NULL,
                password_hash VARCHAR(220) NOT NULL,
                rol VARCHAR(20) NOT NULL,
                activo BOOLEAN NOT NULL DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT usuarios_rol_allowed CHECK (rol IN ('admin', 'cliente')),
                CONSTRAINT usuarios_username_not_blank CHECK (trim(username) <> '')
            )
            """
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER,
                accion VARCHAR(50) NOT NULL,
                recurso VARCHAR(50) NOT NULL,
                recurso_id VARCHAR(100),
                cambios JSON,
                ip_address VARCHAR(45),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
            )
            """
        )
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return SessionLocal(), engine


def test_registrar_cliente_crea_usuario_inactivo() -> None:
    session, _engine = make_session()

    result = registrar_cliente(
        session,
        username="cliente_nuevo",
        nombre="Cliente Nuevo",
        email="cliente@example.com",
        password="password123",
    )

    assert result.message == "Cuenta creada. Queda pendiente de habilitacion por un administrador."
    assert result.usuario.username == "cliente_nuevo"
    assert result.usuario.email == "cliente@example.com"
    assert result.usuario.rol == "cliente"
    assert result.usuario.activo is False


def test_registrar_cliente_rechaza_email_duplicado() -> None:
    session, _engine = make_session()
    registrar_cliente(
        session,
        username="cliente_a",
        nombre="Cliente A",
        email="cliente@example.com",
        password="password123",
    )

    with pytest.raises(HTTPException) as exc_info:
        registrar_cliente(
            session,
            username="cliente_b",
            nombre="Cliente B",
            email="cliente@example.com",
            password="password123",
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "El email ya esta registrado"


def test_usuario_inactivo_no_puede_autenticarse_hasta_habilitarse() -> None:
    session, _engine = make_session()
    result = registrar_cliente(
        session,
        username="cliente_nuevo",
        nombre="Cliente Nuevo",
        email="cliente@example.com",
        password="password123",
    )

    with pytest.raises(HTTPException) as exc_info:
        autenticar_usuario(session, username="cliente_nuevo", password="password123")

    assert exc_info.value.status_code == 401

    habilitado = habilitar_usuario(session, user_id=result.usuario.id)
    login = autenticar_usuario(session, username="cliente_nuevo", password="password123")

    assert habilitado.activo is True
    assert login.usuario.id == result.usuario.id
    assert login.access_token

def test_registrar_cliente_invalid_data() -> None:
    session, _engine = make_session()
    with pytest.raises(HTTPException) as exc:
        registrar_cliente(session, username="", nombre="n", email="e@e.com", password="p")
    assert exc.value.status_code == 400
    
    with pytest.raises(HTTPException) as exc:
        registrar_cliente(session, username="u", nombre="", email="e@e.com", password="p")
    assert exc.value.status_code == 400
    
    with pytest.raises(HTTPException) as exc:
        registrar_cliente(session, username="u", nombre="n", email="invalid-email", password="p")
    assert exc.value.status_code == 400

def test_registrar_cliente_duplicate() -> None:
    session, _engine = make_session()
    registrar_cliente(session, username="dup", nombre="n", email="dup@e.com", password="p")
    
    with pytest.raises(HTTPException) as exc:
        registrar_cliente(session, username="dup", nombre="n2", email="other@e.com", password="p")
    assert exc.value.status_code == 409
    
    with pytest.raises(HTTPException) as exc:
        registrar_cliente(session, username="other", nombre="n2", email="dup@e.com", password="p")
    assert exc.value.status_code == 409

def test_habilitar_usuario_not_found() -> None:
    session, _engine = make_session()
    with pytest.raises(HTTPException) as exc:
        habilitar_usuario(session, user_id=999)
    assert exc.value.status_code == 404

def test_eliminar_usuario_restrictions() -> None:
    session, _engine = make_session()
    admin = Usuario(id=1, username="a", email="a@a.com", nombre="a", password_hash="h", rol="admin")
    other_admin = Usuario(id=2, username="a2", email="a2@a.com", nombre="a2", password_hash="h", rol="admin")
    session.add_all([admin, other_admin])
    session.commit()
    
    # Delete self
    with pytest.raises(HTTPException) as exc:
        eliminar_usuario(session, user_id=1, current_user=admin)
    assert exc.value.status_code == 400
    
    # Delete non-existent
    with pytest.raises(HTTPException) as exc:
        eliminar_usuario(session, user_id=999, current_user=admin)
    assert exc.value.status_code == 404
        
    # Test case: target is admin
    admin2 = Usuario(username="admin2", email="admin2@example.com", nombre="Admin 2", password_hash="p", rol="admin", activo=True)
    session.add(admin2)
    session.commit()
    with pytest.raises(HTTPException) as exc:
        eliminar_usuario(session, user_id=admin2.id, current_user=admin)
    assert exc.value.status_code == 400
    assert "No se puede eliminar un usuario admin" in exc.value.detail


def test_habilitar_usuario_sin_email() -> None:
    session, _engine = make_session()
    # Manual insertion to avoid validation if any
    from app.modules.auth.infrastructure.models import Usuario
    user = Usuario(username="noemail", email="", nombre="No Email", password_hash="h", rol="cliente", activo=False)
    session.add(user)
    session.commit()
    
    with pytest.raises(HTTPException) as exc:
        habilitar_usuario(session, user_id=user.id)
    assert exc.value.status_code == 400
    assert "no tiene email" in exc.value.detail


def test_solicitar_recuperacion_password_actualiza_clave_y_envia_email(monkeypatch) -> None:
    session, _engine = make_session()
    sent_payload = {}

    user = Usuario(
        username="cliente",
        email="cliente@example.com",
        nombre="Cliente",
        password_hash=hash_password("password123"),
        rol="cliente",
        activo=True,
    )
    session.add(user)
    session.commit()

    def fake_send_password_recovery_email(**kwargs):
        sent_payload.update(kwargs)
        return True

    monkeypatch.setattr(
        "app.modules.auth.application.service.send_password_recovery_email",
        fake_send_password_recovery_email,
    )

    result = solicitar_recuperacion_password(session, identifier="cliente@example.com")
    session.refresh(user)

    assert result.email_sent is True
    assert result.message == "Te enviamos un enlace para restablecer la clave."
    assert sent_payload["to_email"] == "cliente@example.com"
    assert sent_payload["username"] == "cliente"
    assert "reset_token=" in sent_payload["reset_url"]
    assert verify_password("password123", user.password_hash) is True


def test_solicitar_recuperacion_password_informa_mail_no_registrado(monkeypatch) -> None:
    session, _engine = make_session()
    called = False

    def fake_send_password_recovery_email(**_kwargs):
        nonlocal called
        called = True
        return True

    monkeypatch.setattr(
        "app.modules.auth.application.service.send_password_recovery_email",
        fake_send_password_recovery_email,
    )

    with pytest.raises(HTTPException) as exc:
        solicitar_recuperacion_password(session, identifier="nadie@example.com")

    assert exc.value.status_code == 404
    assert exc.value.detail == "Este mail no esta registrado"
    assert called is False


def test_solicitar_recuperacion_password_no_registra_auditoria_si_falla_email(monkeypatch) -> None:
    session, _engine = make_session()
    user = Usuario(
        username="cliente",
        email="cliente@example.com",
        nombre="Cliente",
        password_hash=hash_password("password123"),
        rol="cliente",
        activo=True,
    )
    session.add(user)
    session.commit()

    monkeypatch.setattr(
        "app.modules.auth.application.service.send_password_recovery_email",
        lambda **_kwargs: False,
    )

    result = solicitar_recuperacion_password(session, identifier="cliente")
    session.refresh(user)

    assert result.email_sent is False
    assert verify_password("password123", user.password_hash) is True


def test_restablecer_password_actualiza_clave_y_autentica(monkeypatch) -> None:
    session, _engine = make_session()
    sent_payload = {}
    user = Usuario(
        username="cliente",
        email="cliente@example.com",
        nombre="Cliente",
        password_hash=hash_password("password123"),
        rol="cliente",
        activo=True,
    )
    session.add(user)
    session.commit()

    def fake_send_password_recovery_email(**kwargs):
        sent_payload.update(kwargs)
        return True

    monkeypatch.setattr(
        "app.modules.auth.application.service.send_password_recovery_email",
        fake_send_password_recovery_email,
    )

    solicitar_recuperacion_password(session, identifier="cliente")
    token = sent_payload["reset_url"].split("reset_token=", 1)[1]
    result = restablecer_password(session, token=token, password="newpassword123")

    assert result.message == "La clave fue actualizada. Ya podés ingresar con la nueva contraseña."
    assert autenticar_usuario(session, username="cliente", password="newpassword123").usuario.id == user.id


def test_validar_token_recuperacion_password_acepta_token_vigente(monkeypatch) -> None:
    session, _engine = make_session()
    sent_payload = {}
    user = Usuario(
        username="cliente",
        email="cliente@example.com",
        nombre="Cliente",
        password_hash=hash_password("password123"),
        rol="cliente",
        activo=True,
    )
    session.add(user)
    session.commit()

    monkeypatch.setattr(
        "app.modules.auth.application.service.send_password_recovery_email",
        lambda **kwargs: sent_payload.update(kwargs) or True,
    )

    solicitar_recuperacion_password(session, identifier="cliente")
    token = sent_payload["reset_url"].split("reset_token=", 1)[1]
    result = validar_token_recuperacion_password(session, token=token)

    assert result.message == "Token de recuperacion valido"


def test_restablecer_password_rechaza_token_reutilizado(monkeypatch) -> None:
    session, _engine = make_session()
    sent_payload = {}
    user = Usuario(
        username="cliente",
        email="cliente@example.com",
        nombre="Cliente",
        password_hash=hash_password("password123"),
        rol="cliente",
        activo=True,
    )
    session.add(user)
    session.commit()

    monkeypatch.setattr(
        "app.modules.auth.application.service.send_password_recovery_email",
        lambda **kwargs: sent_payload.update(kwargs) or True,
    )

    solicitar_recuperacion_password(session, identifier="cliente")
    token = sent_payload["reset_url"].split("reset_token=", 1)[1]
    restablecer_password(session, token=token, password="newpassword123")

    with pytest.raises(HTTPException) as exc:
        restablecer_password(session, token=token, password="otherpassword123")

    assert exc.value.status_code == 400
