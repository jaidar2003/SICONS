from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.catalog.infrastructure.models import Fuente, Material, Presentacion
from app.modules.pricing.infrastructure.models import PrecioHistorico
from app.operations.bootstrap.common import get_or_create_fuente, get_or_create_material, get_or_create_presentacion
from app.operations.bootstrap.export_cemento_canonico import DEFAULT_MATERIAL_NOMBRE, EXPORT_COLUMNS
from app.shared.database.session import SessionLocal

DEFAULT_INPUT = Path("db/bootstrap/cemento_portland_historico.csv")
CANONICAL_SOURCE_NAME = "Dataset canónico Cemento Portland"
CANONICAL_SOURCE_TYPE = "dataset"
CANONICAL_SOURCE_DESCRIPTION = "Serie historica canónica y versionada de Cemento Portland"
MIN_MONTHLY_POINTS = 24


@dataclass(frozen=True)
class CanonicalCementoRow:
    fecha: date
    empresa: str
    numero_comprobante: str
    articulo: str
    precio_original: Decimal
    precio_normalizado: Decimal
    moneda: str
    origen_dato: str
    metodo_estimacion: str | None
    observaciones_origen: str


@dataclass(frozen=True)
class ImportSummary:
    inserted: int
    updated: int
    unchanged: int
    cantidad_registros: int
    cantidad_meses: int
    rango_desde: date
    rango_hasta: date


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Importa el historico canonico de Cemento Portland desde CSV.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Ruta del CSV canonico de entrada.")
    parser.add_argument(
        "--material-nombre",
        default=DEFAULT_MATERIAL_NOMBRE,
        help="Nombre del material a importar.",
    )
    return parser


def normalize_header(value: str) -> str:
    return " ".join(value.strip().lower().split())


def parse_date(value: str) -> date:
    return date.fromisoformat(value.strip())


def parse_decimal(value: str) -> Decimal:
    return Decimal(value.strip())


def article_to_presentacion(articulo: str) -> tuple[str, Decimal, str]:
    normalized = normalize_header(articulo)
    if normalized == "cemento cpc40 x 25 kg":
        return "Bolsa 25 kg", Decimal("25"), "kg"
    if normalized == "cemento cpc40 bol 50 kg":
        return "Bolsa 50 kg", Decimal("50"), "kg"
    raise ValueError(f"Articulo no reconocido para Cemento Portland: {articulo!r}")


def read_canonical_csv(path: Path) -> list[CanonicalCementoRow]:
    if not path.exists():
        raise FileNotFoundError(f"No existe el CSV canonico de Cemento Portland: {path}")

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("El CSV canonico no tiene encabezado.")
        if list(reader.fieldnames) != list(EXPORT_COLUMNS):
            raise ValueError(
                "El CSV canonico no tiene las columnas esperadas. "
                f"Esperadas: {list(EXPORT_COLUMNS)}. Encontradas: {reader.fieldnames}."
            )

        rows: list[CanonicalCementoRow] = []
        for index, raw_row in enumerate(reader, start=2):
            if raw_row is None or not any((value or "").strip() for value in raw_row.values()):
                raise ValueError(f"Fila vacia detectada en la linea {index} del CSV canonico.")

            fecha = parse_date(raw_row["fecha"])
            empresa = raw_row["empresa"].strip()
            numero_comprobante = raw_row["numero_comprobante"].strip()
            articulo = raw_row["articulo"].strip()
            precio_original = parse_decimal(raw_row["precio_original"])
            precio_normalizado = parse_decimal(raw_row["precio_normalizado"])
            moneda = raw_row["moneda"].strip()
            origen_dato = raw_row["origen_dato"].strip()
            metodo_estimacion = raw_row["metodo_estimacion"].strip() or None
            observaciones_origen = raw_row["observaciones_origen"].strip()

            if not empresa:
                raise ValueError(f"Empresa vacia en la linea {index}.")
            if not numero_comprobante:
                raise ValueError(f"numero_comprobante vacio en la linea {index}.")
            if not articulo:
                raise ValueError(f"Articulo vacio en la linea {index}.")
            if precio_original <= 0:
                raise ValueError(f"precio_original invalido en la linea {index}: {precio_original}")
            if precio_normalizado <= 0:
                raise ValueError(f"precio_normalizado invalido en la linea {index}: {precio_normalizado}")
            if moneda != "ARS":
                raise ValueError(f"Moneda invalida en la linea {index}: {moneda!r}")
            if origen_dato != "REAL":
                raise ValueError(f"origen_dato invalido en la linea {index}: {origen_dato!r}")
            if metodo_estimacion not in (None, ""):
                raise ValueError(f"metodo_estimacion debe estar vacio en la linea {index}.")
            if not observaciones_origen:
                raise ValueError(f"observaciones_origen vacio en la linea {index}.")

            rows.append(
                CanonicalCementoRow(
                    fecha=fecha,
                    empresa=empresa,
                    numero_comprobante=numero_comprobante,
                    articulo=articulo,
                    precio_original=precio_original,
                    precio_normalizado=precio_normalizado,
                    moneda=moneda,
                    origen_dato=origen_dato,
                    metodo_estimacion=metodo_estimacion,
                    observaciones_origen=observaciones_origen,
                )
            )

    if not rows:
        raise ValueError("El CSV canonico no contiene filas.")
    return rows


def validate_rows(rows: list[CanonicalCementoRow]) -> int:
    seen_comprobantes: set[str] = set()
    monthly_points: set[date] = set()
    for row in rows:
        if row.numero_comprobante in seen_comprobantes:
            raise ValueError(f"Duplicado detectado para numero_comprobante: {row.numero_comprobante}")
        seen_comprobantes.add(row.numero_comprobante)
        monthly_points.add(date(row.fecha.year, row.fecha.month, 1))

    monthly_sorted = sorted(monthly_points)
    if len(monthly_sorted) < MIN_MONTHLY_POINTS:
        raise ValueError(
            f"No hay datos suficientes para el import canónico. "
            f"Meses detectados: {len(monthly_sorted)}. Minimo requerido: {MIN_MONTHLY_POINTS}."
        )

    expected = monthly_sorted[0]
    for current in monthly_sorted[1:]:
        next_expected = date(expected.year + (1 if expected.month == 12 else 0), 1 if expected.month == 12 else expected.month + 1, 1)
        if current != next_expected:
            raise ValueError(
                f"La serie canónica tiene huecos mensuales entre {expected.isoformat()} y {current.isoformat()}."
            )
        expected = current

    return len(monthly_sorted)


def resolve_presentacion(material: Material, articulo: str, db: Session) -> Presentacion:
    nombre_presentacion, cantidad_base, unidad_presentacion = article_to_presentacion(articulo)
    return get_or_create_presentacion(
        db,
        material=material,
        nombre_presentacion=nombre_presentacion,
        cantidad_base=cantidad_base,
        unidad_presentacion=unidad_presentacion,
    )


def upsert_precio(
    db: Session,
    *,
    row: CanonicalCementoRow,
    material: Material,
    presentacion: Presentacion,
    fuente: Fuente,
) -> str:
    existing = db.scalar(
        select(PrecioHistorico).where(
            PrecioHistorico.fuente_id == fuente.id,
            PrecioHistorico.numero_comprobante == row.numero_comprobante,
        )
    )
    if existing is None:
        db.add(
            PrecioHistorico(
                material_id=material.id,
                presentacion_id=presentacion.id,
                fuente_id=fuente.id,
                fecha=row.fecha,
                precio_original=row.precio_original,
                precio_normalizado=row.precio_normalizado,
                moneda=row.moneda,
                numero_comprobante=row.numero_comprobante,
                origen_dato="REAL",
                metodo_estimacion=None,
                observaciones=row.observaciones_origen,
            )
        )
        return "inserted"

    changed = (
        existing.material_id != material.id
        or existing.presentacion_id != presentacion.id
        or existing.fecha != row.fecha
        or Decimal(existing.precio_original) != row.precio_original
        or Decimal(existing.precio_normalizado) != row.precio_normalizado
        or existing.moneda != row.moneda
        or existing.origen_dato != "REAL"
        or existing.metodo_estimacion not in (None, "")
        or existing.observaciones != row.observaciones_origen
    )
    if not changed:
        return "unchanged"

    existing.material_id = material.id
    existing.presentacion_id = presentacion.id
    existing.fecha = row.fecha
    existing.precio_original = row.precio_original
    existing.precio_normalizado = row.precio_normalizado
    existing.moneda = row.moneda
    existing.origen_dato = "REAL"
    existing.metodo_estimacion = None
    existing.observaciones = row.observaciones_origen
    return "updated"


def import_cemento_canonico(
    db: Session,
    *,
    input_path: Path = DEFAULT_INPUT,
    material_nombre: str = DEFAULT_MATERIAL_NOMBRE,
) -> ImportSummary:
    rows = read_canonical_csv(input_path)
    cantidad_meses = validate_rows(rows)

    material = get_or_create_material(
        db,
        nombre=material_nombre,
        categoria="Materiales de obra",
        marca="Holcim",
        unidad_base="kg",
        descripcion="Cemento Portland canonico para bootstrap reproducible",
    )
    fuente = get_or_create_fuente(
        db,
        nombre=CANONICAL_SOURCE_NAME,
        tipo_fuente=CANONICAL_SOURCE_TYPE,
        descripcion=CANONICAL_SOURCE_DESCRIPTION,
    )

    inserted = 0
    updated = 0
    unchanged = 0
    for row in rows:
        presentacion = resolve_presentacion(material, row.articulo, db)
        result = upsert_precio(db, row=row, material=material, presentacion=presentacion, fuente=fuente)
        if result == "inserted":
            inserted += 1
        elif result == "updated":
            updated += 1
        else:
            unchanged += 1

    return ImportSummary(
        inserted=inserted,
        updated=updated,
        unchanged=unchanged,
        cantidad_registros=len(rows),
        cantidad_meses=cantidad_meses,
        rango_desde=rows[0].fecha,
        rango_hasta=rows[-1].fecha,
    )


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    with SessionLocal() as db:
        summary = import_cemento_canonico(
            db,
            input_path=Path(args.input),
            material_nombre=args.material_nombre,
        )
        db.commit()
        print(f"Material: {args.material_nombre}")
        print(f"Fuente: {CANONICAL_SOURCE_NAME}")
        print(f"Cantidad de registros: {summary.cantidad_registros}")
        print(f"Rango temporal: {summary.rango_desde.isoformat()} -> {summary.rango_hasta.isoformat()}")
        print(f"Cantidad de meses: {summary.cantidad_meses}")
        print("Anonimizacion: no")
        print("Continuidad mensual: ok")


if __name__ == "__main__":
    main()
