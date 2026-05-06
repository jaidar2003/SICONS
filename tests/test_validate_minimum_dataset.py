from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.operations.bootstrap.validate_minimum_dataset as validation
from app.modules.catalog.infrastructure.models import Fuente, Material, Presentacion
from app.modules.pricing.infrastructure.models import ExternalIndexValue, PrecioHistorico


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
        conn.exec_driver_sql(
            """
            CREATE TABLE external_index_values (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_name VARCHAR(50) NOT NULL,
                series_id VARCHAR(100) NOT NULL,
                date DATE NOT NULL,
                value NUMERIC(18, 6) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (series_id, date)
            )
            """
        )
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return SessionLocal(), engine


def add_material(session, *, nombre: str, marca: str = "Demo") -> Material:
    material = Material(
        nombre=nombre,
        categoria="Materiales",
        marca=marca,
        unidad_base="kg",
        descripcion=f"{nombre} demo",
        activo=True,
    )
    session.add(material)
    session.flush()
    return material


def add_fuente(session, *, nombre: str, tipo_fuente: str) -> Fuente:
    fuente = Fuente(nombre=nombre, tipo_fuente=tipo_fuente, descripcion=f"Fuente {nombre}")
    session.add(fuente)
    session.flush()
    return fuente


def add_presentacion(session, *, material: Material, nombre: str, cantidad: str, unidad: str) -> Presentacion:
    presentacion = Presentacion(
        material_id=material.id,
        nombre_presentacion=nombre,
        cantidad_base=Decimal(cantidad),
        unidad_presentacion=unidad,
        activa=True,
    )
    session.add(presentacion)
    session.flush()
    return presentacion


def add_precio(
    session,
    *,
    material: Material,
    presentacion: Presentacion,
    fuente: Fuente,
    fecha: date,
    numero_comprobante: str,
    origen_dato: str,
    metodo_estimacion: str | None,
    precio_original: str,
    precio_normalizado: str,
    observaciones: str,
) -> PrecioHistorico:
    precio = PrecioHistorico(
        material_id=material.id,
        presentacion_id=presentacion.id,
        fuente_id=fuente.id,
        fecha=fecha,
        precio_original=Decimal(precio_original),
        precio_normalizado=Decimal(precio_normalizado),
        moneda="ARS",
        numero_comprobante=numero_comprobante,
        origen_dato=origen_dato,
        metodo_estimacion=metodo_estimacion,
        observaciones=observaciones,
    )
    session.add(precio)
    session.flush()
    return precio


def build_months(months: int = 24):
    year = 2022
    month = 1
    for _ in range(months):
        yield date(year, month, 1)
        month += 1
        if month == 13:
            month = 1
            year += 1


def write_regressor_csv(path, value_column: str, *, start_value: float = 100.0) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["fecha", value_column])
        writer.writeheader()
        for index, month in enumerate(build_months()):
            writer.writerow(
                {
                    "fecha": month.isoformat(),
                    value_column: f"{start_value + index:.2f}",
                }
            )


def seed_valid_dataset(session, tmp_path):
    cemento = add_material(session, nombre="Cemento Portland", marca="Holcim")
    pastina = add_material(session, nombre="Pastina", marca="SIKA")
    membrana = add_material(session, nombre="Membrana Megaflex", marca="MEGAFLEX")

    cemento_25 = add_presentacion(session, material=cemento, nombre="Bolsa 25 kg", cantidad="25", unidad="kg")
    cemento_50 = add_presentacion(session, material=cemento, nombre="Bolsa 50 kg", cantidad="50", unidad="kg")
    pastina_1 = add_presentacion(session, material=pastina, nombre="Unidad 1 kg", cantidad="1", unidad="kg")
    membrana_20 = add_presentacion(session, material=membrana, nombre="Balde 20 kg", cantidad="20", unidad="kg")

    fuente_canonica = add_fuente(
        session,
        nombre="Dataset canónico Cemento Portland",
        tipo_fuente="dataset",
    )
    fuente_factura = add_fuente(session, nombre="Factura compra", tipo_fuente="factura")
    fuente_pastina_real = add_fuente(session, nombre="Factura compra SIKA Pastina", tipo_fuente="factura")
    fuente_pastina_estimado = add_fuente(session, nombre="Estimacion IPC SIKA Pastina", tipo_fuente="estimacion")
    fuente_membrana_real = add_fuente(session, nombre="Factura compra Megaflex Membrana", tipo_fuente="factura")
    fuente_membrana_estimado = add_fuente(session, nombre="Estimacion IPC Megaflex Membrana", tipo_fuente="estimacion")

    for index, month in enumerate(build_months()):
        add_precio(
            session,
            material=cemento,
            presentacion=cemento_25,
            fuente=fuente_canonica,
            fecha=month,
            numero_comprobante=f"CAN-25-{index:03d}",
            origen_dato="REAL",
            metodo_estimacion=None,
            precio_original=f"{300 + index:.2f}",
            precio_normalizado=f"{(Decimal(300 + index) / Decimal('25')).quantize(Decimal('0.0001'))}",
            observaciones="Cemento canonico 25 kg",
        )
        add_precio(
            session,
            material=cemento,
            presentacion=cemento_50,
            fuente=fuente_canonica,
            fecha=month,
            numero_comprobante=f"CAN-50-{index:03d}",
            origen_dato="REAL",
            metodo_estimacion=None,
            precio_original=f"{600 + index:.2f}",
            precio_normalizado=f"{(Decimal(600 + index) / Decimal('50')).quantize(Decimal('0.0001'))}",
            observaciones="Cemento canonico 50 kg",
        )

        if index == 0:
            add_precio(
                session,
                material=cemento,
                presentacion=cemento_50,
                fuente=fuente_factura,
                fecha=month,
                numero_comprobante="FCA-0001",
                origen_dato="REAL",
                metodo_estimacion=None,
                precio_original="610.00",
                precio_normalizado="12.2000",
                observaciones="Factura compra operativa",
            )

        if index % 2 == 0:
            add_precio(
                session,
                material=pastina,
                presentacion=pastina_1,
                fuente=fuente_pastina_real,
                fecha=month,
                numero_comprobante=f"PAS-R-{index:03d}",
                origen_dato="REAL",
                metodo_estimacion=None,
                precio_original=f"{1000 + index:.2f}",
                precio_normalizado=f"{(Decimal(1000 + index) / Decimal('1')).quantize(Decimal('0.0001'))}",
                observaciones="Pastina real",
            )
            add_precio(
                session,
                material=membrana,
                presentacion=membrana_20,
                fuente=fuente_membrana_real,
                fecha=month,
                numero_comprobante=f"MEM-R-{index:03d}",
                origen_dato="REAL",
                metodo_estimacion=None,
                precio_original=f"{2000 + index:.2f}",
                precio_normalizado=f"{(Decimal(2000 + index) / Decimal('20')).quantize(Decimal('0.0001'))}",
                observaciones="Membrana real",
            )
        else:
            add_precio(
                session,
                material=pastina,
                presentacion=pastina_1,
                fuente=fuente_pastina_estimado,
                fecha=month,
                numero_comprobante=f"PAS-E-{index:03d}",
                origen_dato="ESTIMADO",
                metodo_estimacion="IPC",
                precio_original=f"{1000 + index:.2f}",
                precio_normalizado=f"{(Decimal(1000 + index) / Decimal('1')).quantize(Decimal('0.0001'))}",
                observaciones="Pastina estimada",
            )
            add_precio(
                session,
                material=membrana,
                presentacion=membrana_20,
                fuente=fuente_membrana_estimado,
                fecha=month,
                numero_comprobante=f"MEM-E-{index:03d}",
                origen_dato="ESTIMADO",
                metodo_estimacion="IPC",
                precio_original=f"{2000 + index:.2f}",
                precio_normalizado=f"{(Decimal(2000 + index) / Decimal('20')).quantize(Decimal('0.0001'))}",
                observaciones="Membrana estimada",
            )

    session.commit()
    regressor_paths = {
        "dolar_oficial": tmp_path / "dolar_oficial_historico.csv",
        "dolar_mayorista": tmp_path / "dolar_mayorista_historico.csv",
        "dolar_blue": tmp_path / "dolar_blue_historico.csv",
        "ipc": tmp_path / "ipc_nacional.csv",
    }
    write_regressor_csv(regressor_paths["dolar_oficial"], "venta", start_value=100.0)
    write_regressor_csv(regressor_paths["dolar_mayorista"], "venta", start_value=90.0)
    write_regressor_csv(regressor_paths["dolar_blue"], "venta", start_value=110.0)
    write_regressor_csv(regressor_paths["ipc"], "ipc", start_value=1.0)

    validation.OFICIAL_CSV = regressor_paths["dolar_oficial"]
    validation.MAYORISTA_CSV = regressor_paths["dolar_mayorista"]
    validation.BLUE_CSV = regressor_paths["dolar_blue"]
    validation.IPC_CSV = regressor_paths["ipc"]

    return {
        "cemento": cemento,
        "pastina": pastina,
        "membrana": membrana,
        "fuente_canonica": fuente_canonica,
        "fuente_factura": fuente_factura,
        "fuente_pastina_real": fuente_pastina_real,
        "fuente_pastina_estimado": fuente_pastina_estimado,
        "fuente_membrana_real": fuente_membrana_real,
        "fuente_membrana_estimado": fuente_membrana_estimado,
        "regressor_paths": regressor_paths,
    }


def seed_ipim(session, *, months: int = 24) -> None:
    for index, month in enumerate(build_months(months)):
        session.add(
            ExternalIndexValue(
                source_name="Snapshot local INDEC",
                series_id=validation.IPIM_NIVEL_GENERAL_SERIES_ID,
                date=month,
                value=Decimal(f"{100 + index:.6f}"),
            )
        )
    session.commit()


def test_pasa_con_dataset_minimo_valido(tmp_path) -> None:
    session, _ = make_session()
    seed_valid_dataset(session, tmp_path)
    seed_ipim(session)

    summary = validation.validate_minimum_dataset(session)

    assert summary.ok
    assert any(check.name == "Cemento canónico - fuente" and check.ok for check in summary.checks)
    assert any(check.name == "Pastina - mezcla REAL/ESTIMADO" and check.ok for check in summary.checks)
    assert any(check.name == "Membrana Megaflex - mezcla REAL/ESTIMADO" and check.ok for check in summary.checks)
    assert any(check.name == "Regresor ipim_nivel_general" and check.ok for check in summary.checks)


def test_falla_si_falta_cemento_canonico(tmp_path) -> None:
    session, _ = make_session()
    data = seed_valid_dataset(session, tmp_path)
    session.query(PrecioHistorico).filter(PrecioHistorico.fuente_id == data["fuente_canonica"].id).delete(synchronize_session=False)
    session.commit()
    seed_ipim(session)

    summary = validation.validate_minimum_dataset(session)

    assert not summary.ok
    assert any(check.name == "Cemento canónico" and not check.ok for check in summary.checks)


def test_falla_si_cemento_depende_solo_de_factura_compra(tmp_path) -> None:
    session, _ = make_session()
    data = seed_valid_dataset(session, tmp_path)
    session.query(PrecioHistorico).filter(PrecioHistorico.fuente_id == data["fuente_canonica"].id).delete(synchronize_session=False)
    session.commit()
    seed_ipim(session)

    summary = validation.validate_minimum_dataset(session)

    assert not summary.ok
    assert any(check.name.startswith("Cemento canónico") and not check.ok for check in summary.checks)


def test_falla_si_pastina_no_tiene_estimado(tmp_path) -> None:
    session, _ = make_session()
    data = seed_valid_dataset(session, tmp_path)
    session.query(PrecioHistorico).filter(
        PrecioHistorico.material_id == data["pastina"].id,
        PrecioHistorico.origen_dato == "ESTIMADO",
    ).delete(synchronize_session=False)
    session.commit()
    seed_ipim(session)

    summary = validation.validate_minimum_dataset(session)

    assert not summary.ok
    assert any(check.name == "Pastina - mezcla REAL/ESTIMADO" and not check.ok for check in summary.checks)


def test_falla_si_membrana_no_tiene_real(tmp_path) -> None:
    session, _ = make_session()
    data = seed_valid_dataset(session, tmp_path)
    session.query(PrecioHistorico).filter(
        PrecioHistorico.material_id == data["membrana"].id,
        PrecioHistorico.origen_dato == "REAL",
    ).delete(synchronize_session=False)
    session.commit()
    seed_ipim(session)

    summary = validation.validate_minimum_dataset(session)

    assert not summary.ok
    assert any(check.name == "Membrana Megaflex - mezcla REAL/ESTIMADO" and not check.ok for check in summary.checks)


def test_falla_si_falta_ipim(tmp_path) -> None:
    session, _ = make_session()
    seed_valid_dataset(session, tmp_path)

    summary = validation.validate_minimum_dataset(session)

    assert not summary.ok
    assert any(check.name == "Regresor ipim_nivel_general" and not check.ok for check in summary.checks)


def test_falla_si_material_no_deriva_material_key_esperado(tmp_path, monkeypatch) -> None:
    session, _ = make_session()
    seed_valid_dataset(session, tmp_path)
    seed_ipim(session)
    monkeypatch.setitem(validation.EXPECTED_MATERIAL_KEYS, "Pastina", "pastina-incorrecta")

    summary = validation.validate_minimum_dataset(session)

    assert not summary.ok
    assert any(check.name == "Material Pastina" and not check.ok for check in summary.checks)


def test_falla_si_hay_huecos_mensuales_en_una_serie_requerida(tmp_path) -> None:
    session, _ = make_session()
    data = seed_valid_dataset(session, tmp_path)
    session.query(PrecioHistorico).filter(
        PrecioHistorico.material_id == data["cemento"].id,
        PrecioHistorico.fuente_id == data["fuente_canonica"].id,
        PrecioHistorico.fecha == date(2022, 6, 1),
    ).delete(synchronize_session=False)
    session.commit()
    seed_ipim(session)

    summary = validation.validate_minimum_dataset(session)

    assert not summary.ok
    assert any(check.name == "Cemento canónico - continuidad" and not check.ok for check in summary.checks)
