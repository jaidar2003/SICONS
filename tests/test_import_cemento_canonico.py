from collections import Counter
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.modules.catalog.infrastructure.models import Fuente, Material, Presentacion
from app.modules.pricing.infrastructure.models import PrecioHistorico
from app.operations.bootstrap.export_cemento_canonico import EXPORT_COLUMNS
from app.operations.bootstrap.import_cemento_canonico import (
    CANONICAL_SOURCE_NAME,
    import_cemento_canonico,
    read_canonical_csv,
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
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (nombre, unidad_base, marca)
            )
            """
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE fuentes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre VARCHAR(150) NOT NULL UNIQUE,
                tipo_fuente VARCHAR(50),
                descripcion TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE presentaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                material_id INTEGER NOT NULL,
                nombre_presentacion VARCHAR(100) NOT NULL,
                cantidad_base NUMERIC(12, 4) NOT NULL,
                unidad_presentacion VARCHAR(20) NOT NULL,
                activa BOOLEAN NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (material_id, nombre_presentacion)
            )
            """
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE precios_historicos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                material_id INTEGER NOT NULL,
                presentacion_id INTEGER,
                fuente_id INTEGER,
                fecha DATE NOT NULL,
                precio_original NUMERIC(14, 2) NOT NULL,
                precio_normalizado NUMERIC(14, 4) NOT NULL,
                moneda VARCHAR(10) NOT NULL,
                numero_comprobante VARCHAR(50),
                origen_dato VARCHAR(20) NOT NULL DEFAULT 'REAL',
                metodo_estimacion VARCHAR(50),
                observaciones TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (fuente_id, numero_comprobante)
            )
            """
        )
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return SessionLocal(), engine


def build_canonical_rows(months: int = 24):
    rows = []
    year = 2022
    month = 1
    for index in range(months):
        fecha_base = date(year, month, 3)
        precio_50 = Decimal("603.61") + Decimal(index)
        precio_25 = Decimal("301.81") + Decimal(index)
        rows.append(
            {
                "fecha": fecha_base.isoformat(),
                "empresa": "HOLCIM",
                "numero_comprobante": f"0280-{133721 + index:08d}",
                "articulo": "CEMENTO CPC40 BOL 50 KG",
                "precio_original": f"{precio_50:.2f}",
                "precio_normalizado": f"{(precio_50 / Decimal('50')).quantize(Decimal('0.0001'))}",
                "moneda": "ARS",
                "origen_dato": "REAL",
                "metodo_estimacion": "",
                "observaciones_origen": "Importado desde Factura compra - HOLCIM - CEMENTO CPC40 BOL 50 KG",
            }
        )
        rows.append(
            {
                "fecha": fecha_base.isoformat(),
                "empresa": "HOLCIM",
                "numero_comprobante": f"0280-{233721 + index:08d}",
                "articulo": "CEMENTO CPC40 X 25 KG",
                "precio_original": f"{precio_25:.2f}",
                "precio_normalizado": f"{(precio_25 / Decimal('25')).quantize(Decimal('0.0001'))}",
                "moneda": "ARS",
                "origen_dato": "REAL",
                "metodo_estimacion": "",
                "observaciones_origen": "Importado desde Factura compra - HOLCIM - CEMENTO CPC40 X 25 KG",
            }
        )
        month += 1
        if month == 13:
            month = 1
            year += 1
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    import csv

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=EXPORT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def test_importa_correctamente_un_csv_valido(tmp_path) -> None:
    session, _ = make_session()
    csv_path = tmp_path / "cemento.csv"
    write_csv(csv_path, build_canonical_rows())

    summary = import_cemento_canonico(session, input_path=csv_path)
    session.commit()

    assert summary.inserted == 48
    assert summary.updated == 0
    assert summary.unchanged == 0

    material = session.query(Material).filter_by(nombre="Cemento Portland").one()
    fuente = session.query(Fuente).filter_by(nombre=CANONICAL_SOURCE_NAME).one()
    presentaciones = session.query(Presentacion).filter(Presentacion.material_id == material.id).all()
    precios = session.query(PrecioHistorico).filter(PrecioHistorico.material_id == material.id).all()

    assert material.unidad_base == "kg"
    assert fuente.tipo_fuente == "dataset"
    assert {p.nombre_presentacion for p in presentaciones} == {"Bolsa 25 kg", "Bolsa 50 kg"}
    assert len(precios) == 48
    assert {p.origen_dato for p in precios} == {"REAL"}
    assert {p.metodo_estimacion for p in precios} == {None}
    assert {p.moneda for p in precios} == {"ARS"}
    assert min(p.fecha for p in precios) == date(2022, 1, 3)
    assert max(p.fecha for p in precios) == date(2023, 12, 3)


def test_import_es_idempotente(tmp_path) -> None:
    session, _ = make_session()
    csv_path = tmp_path / "cemento.csv"
    write_csv(csv_path, build_canonical_rows())

    first = import_cemento_canonico(session, input_path=csv_path)
    session.commit()
    second = import_cemento_canonico(session, input_path=csv_path)
    session.commit()

    assert first.inserted == 48
    assert second.inserted == 0
    assert second.updated == 0
    assert session.query(PrecioHistorico).count() == 48


def test_falla_si_falta_una_columna_requerida(tmp_path) -> None:
    import csv

    session, _ = make_session()
    csv_path = tmp_path / "cemento.csv"
    rows = build_canonical_rows()
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [col for col in EXPORT_COLUMNS if col != "moneda"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    with pytest.raises(ValueError, match="columnas esperadas"):
        import_cemento_canonico(session, input_path=csv_path)


def test_falla_si_moneda_distinta_de_ars(tmp_path) -> None:
    session, _ = make_session()
    csv_path = tmp_path / "cemento.csv"
    rows = build_canonical_rows()
    rows[0]["moneda"] = "USD"
    write_csv(csv_path, rows)

    with pytest.raises(ValueError, match="Moneda invalida"):
        import_cemento_canonico(session, input_path=csv_path)


def test_falla_si_origen_dato_distinto_de_real(tmp_path) -> None:
    session, _ = make_session()
    csv_path = tmp_path / "cemento.csv"
    rows = build_canonical_rows()
    rows[0]["origen_dato"] = "ESTIMADO"
    write_csv(csv_path, rows)

    with pytest.raises(ValueError, match="origen_dato invalido"):
        import_cemento_canonico(session, input_path=csv_path)


def test_falla_si_precios_no_son_positivos(tmp_path) -> None:
    session, _ = make_session()
    csv_path = tmp_path / "cemento.csv"
    rows = build_canonical_rows()
    rows[0]["precio_original"] = "0.00"
    write_csv(csv_path, rows)

    with pytest.raises(ValueError, match="precio_original invalido"):
        import_cemento_canonico(session, input_path=csv_path)


def test_falla_si_no_hay_datos_suficientes(tmp_path) -> None:
    session, _ = make_session()
    csv_path = tmp_path / "cemento.csv"
    write_csv(csv_path, build_canonical_rows(months=12))

    with pytest.raises(ValueError, match="No hay datos suficientes"):
        import_cemento_canonico(session, input_path=csv_path)


def test_falla_si_hay_huecos_mensuales(tmp_path) -> None:
    session, _ = make_session()
    csv_path = tmp_path / "cemento.csv"
    rows = build_canonical_rows(months=25)
    # remove all rows from one month to force a gap while keeping enough months overall
    rows = [row for row in rows if not row["fecha"].startswith("2022-06")]
    write_csv(csv_path, rows)

    with pytest.raises(ValueError, match="huecos mensuales"):
        import_cemento_canonico(session, input_path=csv_path)


def test_reutiliza_material_fuente_y_presentaciones(tmp_path) -> None:
    session, _ = make_session()
    csv_path = tmp_path / "cemento.csv"
    write_csv(csv_path, build_canonical_rows())

    import_cemento_canonico(session, input_path=csv_path)
    session.commit()
    import_cemento_canonico(session, input_path=csv_path)
    session.commit()

    assert session.query(Material).filter_by(nombre="Cemento Portland").count() == 1
    assert session.query(Fuente).filter_by(nombre=CANONICAL_SOURCE_NAME).count() == 1
    assert session.query(Presentacion).count() == 2
    assert Counter(p.nombre_presentacion for p in session.query(Presentacion).all()) == Counter(
        {"Bolsa 25 kg": 1, "Bolsa 50 kg": 1}
    )
