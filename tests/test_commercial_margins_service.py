from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.modules.pricing.application.commercial_margins import (
    actualizar_margen_comercial,
    crear_margen_comercial,
    listar_margenes_comerciales,
)


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
            CREATE TABLE commercial_margins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scope VARCHAR(20) NOT NULL,
                material_id INTEGER,
                presentation_id INTEGER,
                product_key VARCHAR(200),
                margen_ganancia_pct NUMERIC(12, 2) NOT NULL,
                activo BOOLEAN NOT NULL DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT commercial_margins_scope_allowed CHECK (scope IN ('GLOBAL', 'MATERIAL', 'PRODUCT')),
                CONSTRAINT commercial_margins_margin_nonnegative CHECK (margen_ganancia_pct >= 0)
            )
            """
        )
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return SessionLocal(), engine


def test_crear_y_listar_margen_comercial() -> None:
    session, _engine = make_session()

    created = crear_margen_comercial(
        session,
        scope="GLOBAL",
        material_id=None,
        presentation_id=None,
        product_key=None,
        margen_ganancia_pct=Decimal("30.00"),
        activo=True,
    )
    margins = listar_margenes_comerciales(session)

    assert created.id == 1
    assert created.scope == "GLOBAL"
    assert created.margen_ganancia_pct == Decimal("30.00")
    assert [margin.id for margin in margins] == [created.id]


def test_actualizar_margen_comercial() -> None:
    session, _engine = make_session()
    created = crear_margen_comercial(
        session,
        scope="MATERIAL",
        material_id=1,
        presentation_id=None,
        product_key=None,
        margen_ganancia_pct=Decimal("20.00"),
        activo=True,
    )

    updated = actualizar_margen_comercial(
        session,
        margin_id=created.id,
        update_data={"margen_ganancia_pct": Decimal("25.50"), "activo": False},
    )

    assert updated.id == created.id
    assert updated.margen_ganancia_pct == Decimal("25.50")
    assert updated.activo is False


def test_actualizar_margen_inexistente_devuelve_404() -> None:
    session, _engine = make_session()

    with pytest.raises(HTTPException) as exc_info:
        actualizar_margen_comercial(session, margin_id=999, update_data={"activo": False})

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Margen comercial no encontrado"


def test_crear_margen_integrity_error() -> None:
    session = MagicMock()
    from sqlalchemy.exc import IntegrityError
    session.commit.side_effect = IntegrityError("mock", "mock", "mock")
    
    with pytest.raises(HTTPException) as exc_info:
        crear_margen_comercial(
            session,
            scope="GLOBAL",
            material_id=None,
            presentation_id=None,
            product_key=None,
            margen_ganancia_pct=Decimal("30.00"),
            activo=True,
        )
    assert exc_info.value.status_code == 409

def test_actualizar_margen_integrity_error() -> None:
    session = MagicMock()
    from sqlalchemy.exc import IntegrityError

    from app.modules.pricing.infrastructure.models import CommercialMargin
    
    margin = CommercialMargin(id=1, scope="GLOBAL", margen_ganancia_pct=Decimal("30.00"), activo=True)
    session.get.return_value = margin
    session.commit.side_effect = IntegrityError("mock", "mock", "mock")
    
    with pytest.raises(HTTPException) as exc_info:
        actualizar_margen_comercial(session, margin_id=1, update_data={"margen_ganancia_pct": Decimal("35.00")})
    assert exc_info.value.status_code == 409
