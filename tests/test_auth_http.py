from collections.abc import Generator
from contextlib import contextmanager

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.modules.auth.infrastructure.models import Usuario
from app.shared.database.session import get_db
from app.shared.security.tokens import hash_password


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


def add_user(
    db: Session,
    *,
    username: str,
    email: str,
    password: str,
    rol: str = "cliente",
    activo: bool = True,
) -> Usuario:
    user = Usuario(
        username=username,
        email=email,
        nombre=username.title(),
        password_hash=hash_password(password),
        rol=rol,
        activo=activo,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@contextmanager
def with_test_client(session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def auth_header(client: TestClient, *, username: str, password: str) -> dict[str, str]:
    response = client.post("/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_register_crea_usuario_pendiente_y_bloquea_login() -> None:
    session, _engine = make_session()
    with with_test_client(session) as client:
        response = client.post(
            "/auth/register",
            json={
                "username": "cliente",
                "nombre": "Cliente Demo",
                "email": "cliente@example.com",
                "password": "password123",
            },
        )
        login_response = client.post("/auth/login", json={"username": "cliente", "password": "password123"})

    assert response.status_code == 201
    assert response.json()["usuario"]["email"] == "cliente@example.com"
    assert login_response.status_code == 401


def test_admin_habilita_usuario_pendiente() -> None:
    session, _engine = make_session()
    admin = add_user(session, username="admin", email="admin@example.com", password="admin123", rol="admin")
    pending = add_user(session, username="cliente", email="cliente@example.com", password="password123", activo=False)

    with with_test_client(session) as client:
        response = client.post(f"/auth/usuarios/{pending.id}/habilitar", headers=auth_header(client, username=admin.username, password="admin123"))

    assert response.status_code == 200
    assert response.json()["activo"] is True
    assert session.get(Usuario, pending.id).activo is True


def test_cliente_no_puede_listar_usuarios() -> None:
    session, _engine = make_session()
    add_user(session, username="cliente", email="cliente@example.com", password="password123")

    with with_test_client(session) as client:
        response = client.get("/auth/usuarios", headers=auth_header(client, username="cliente", password="password123"))

    assert response.status_code == 403


def test_admin_elimina_usuario_cliente() -> None:
    session, _engine = make_session()
    admin = add_user(session, username="admin", email="admin@example.com", password="admin123", rol="admin")
    client_user = add_user(session, username="cliente", email="cliente@example.com", password="password123")

    with with_test_client(session) as client:
        response = client.delete(f"/auth/usuarios/{client_user.id}", headers=auth_header(client, username=admin.username, password="admin123"))
    remaining = session.scalar(select(Usuario).where(Usuario.id == client_user.id))

    assert response.status_code == 204
    assert remaining is None
