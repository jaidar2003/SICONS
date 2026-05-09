from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.modules.catalog.infrastructure.models import Material
from app.modules.pricing.application.commercial_prices import build_margin_candidate, resolve_commercial_margin
from app.modules.pricing.infrastructure.models import CommercialMargin
from app.operations.bootstrap.seed_commercial_margins import (
    DEFAULT_GLOBAL_MARGIN,
    DEFAULT_MATERIAL_MARGINS,
    seed_commercial_margins,
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
            CREATE TABLE materiales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre VARCHAR(150) NOT NULL,
                categoria VARCHAR(100),
                marca VARCHAR(100),
                unidad_base VARCHAR(20) NOT NULL,
                descripcion TEXT,
                activo BOOLEAN NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE presentaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                material_id INTEGER,
                nombre_presentacion VARCHAR(100),
                cantidad_base NUMERIC(12, 4),
                unidad_presentacion VARCHAR(20),
                activa BOOLEAN,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
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
                CONSTRAINT commercial_margins_margin_nonnegative CHECK (margen_ganancia_pct >= 0),
                CONSTRAINT commercial_margins_scope_consistency CHECK (
                    (
                        scope = 'GLOBAL'
                        AND material_id IS NULL
                        AND presentation_id IS NULL
                        AND product_key IS NULL
                    )
                    OR (
                        scope = 'MATERIAL'
                        AND material_id IS NOT NULL
                    )
                    OR (
                        scope = 'PRODUCT'
                        AND material_id IS NOT NULL
                        AND (
                            presentation_id IS NOT NULL
                            OR product_key IS NOT NULL
                        )
                    )
                )
            )
            """
        )
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return SessionLocal(), engine


def _add_material(session, *, nombre: str) -> Material:
    material = Material(
        nombre=nombre,
        categoria="Materiales de obra",
        marca="Demo",
        unidad_base="kg",
        descripcion=f"{nombre} demo",
        activo=True,
    )
    session.add(material)
    session.flush()
    return material


def test_seed_crea_margen_global_y_margenes_de_material() -> None:
    session, _engine = make_session()
    _add_material(session, nombre="Cemento Portland")
    _add_material(session, nombre="Pastina")
    _add_material(session, nombre="Membrana Megaflex")
    session.commit()

    result = seed_commercial_margins(session)
    session.commit()

    margins = session.scalars(select(CommercialMargin).order_by(CommercialMargin.id.asc())).all()
    assert len(margins) == 4
    assert result.warnings == []

    global_margin = next(margin for margin in margins if margin.scope == "GLOBAL")
    assert global_margin.margen_ganancia_pct == DEFAULT_GLOBAL_MARGIN

    material_margins = {
        margin.material.nombre: margin.margen_ganancia_pct
        for margin in margins
        if margin.scope == "MATERIAL"
    }
    assert material_margins == {
        material_name: margin
        for material_name, margin in DEFAULT_MATERIAL_MARGINS
    }


def test_seed_es_idempotente_y_no_duplica_registros() -> None:
    session, _engine = make_session()
    _add_material(session, nombre="Cemento Portland")
    _add_material(session, nombre="Pastina")
    _add_material(session, nombre="Membrana Megaflex")
    session.commit()

    first = seed_commercial_margins(session)
    session.commit()
    second = seed_commercial_margins(session)
    session.commit()

    margins = session.scalars(select(CommercialMargin)).all()
    assert len(margins) == 4
    assert first.created == 4
    assert second.created == 0
    assert second.updated == 4


def test_resolucion_prefiere_material_sobre_global() -> None:
    session, _engine = make_session()
    _add_material(session, nombre="Cemento Portland")
    _add_material(session, nombre="Pastina")
    _add_material(session, nombre="Membrana Megaflex")
    session.commit()

    seed_commercial_margins(session)
    session.commit()

    cemento = session.scalar(select(Material).where(Material.nombre == "Cemento Portland"))
    assert cemento is not None

    candidates = [build_margin_candidate(margin) for margin in session.scalars(select(CommercialMargin)).all()]

    resolved = resolve_commercial_margin(
        candidates,
        material_id=cemento.id,
        presentation_id=None,
        product_key=None,
    )

    assert resolved is not None
    assert resolved.scope == "MATERIAL"
    assert resolved.margen_ganancia_pct == Decimal("25.00")
