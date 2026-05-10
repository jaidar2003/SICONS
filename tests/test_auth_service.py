import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.modules.auth.application.service import autenticar_usuario, habilitar_usuario, registrar_cliente


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
