from __future__ import annotations

import argparse
import csv
import hashlib
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.modules.catalog.infrastructure.models import Material
from app.modules.pricing.application.series import PrecioSerieInput, construir_serie_mensual
from app.modules.pricing.infrastructure.models import PrecioHistorico
from app.shared.database.session import SessionLocal


EXPORT_COLUMNS = (
    "fecha",
    "empresa",
    "numero_comprobante",
    "articulo",
    "precio_original",
    "precio_normalizado",
    "moneda",
    "origen_dato",
    "metodo_estimacion",
    "observaciones_origen",
)
DEFAULT_OUTPUT = Path("db/bootstrap/cemento_portland_historico.csv")
DEFAULT_MATERIAL_NOMBRE = "Cemento Portland"
EXPORT_HASH_SALT = "cemento-canonico-v1"
MIN_MONTHLY_POINTS = 24


@dataclass(frozen=True)
class CanonicalExportRow:
    fecha: date
    empresa: str
    numero_comprobante: str
    articulo: str
    precio_original: Decimal
    precio_normalizado: Decimal
    moneda: str
    origen_dato: str
    metodo_estimacion: str
    observaciones_origen: str

    def to_csv_row(self) -> dict[str, str]:
        return {
            "fecha": self.fecha.isoformat(),
            "empresa": self.empresa,
            "numero_comprobante": self.numero_comprobante,
            "articulo": self.articulo,
            "precio_original": f"{self.precio_original.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}",
            "precio_normalizado": f"{self.precio_normalizado.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)}",
            "moneda": self.moneda,
            "origen_dato": self.origen_dato,
            "metodo_estimacion": self.metodo_estimacion,
            "observaciones_origen": self.observaciones_origen,
        }


@dataclass(frozen=True)
class ExportSummary:
    material_nombre: str
    fuente_nombre: str
    cantidad_registros: int
    fecha_min: date
    fecha_max: date
    cantidad_meses: int
    anonimizado: bool
    continuidad_ok: bool
    comparacion_serie_ok: bool | None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Exporta el historico canonico de Cemento Portland a CSV.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Ruta de salida del CSV canonico.")
    parser.add_argument(
        "--anonimizar-comprobante",
        action="store_true",
        help="Anonimiza numero_comprobante con hash deterministico truncado.",
    )
    parser.add_argument(
        "--material-nombre",
        default=DEFAULT_MATERIAL_NOMBRE,
        help="Nombre del material a exportar.",
    )
    parser.add_argument(
        "--fuente-nombre",
        default=None,
        help="Nombre de la fuente historica a exportar. Si se omite y hay multiples fuentes, el script falla.",
    )
    parser.add_argument(
        "--comparar-serie-mensual",
        action="store_true",
        help="Compara la serie mensual reconstruida desde el CSV contra la serie mensual de la base.",
    )
    return parser


def extract_empresa_articulo(observaciones: str | None) -> tuple[str, str, str]:
    if observaciones is None or not observaciones.strip():
        raise ValueError("No se pudo extraer empresa y articulo: observaciones vacias.")

    parts = [part.strip() for part in observaciones.split(" - ")]
    if len(parts) < 3:
        raise ValueError(f"No se pudo extraer empresa y articulo desde observaciones: {observaciones!r}")
    empresa = parts[-2]
    articulo = parts[-1]
    if not empresa or not articulo:
        raise ValueError(f"No se pudo extraer empresa y articulo desde observaciones: {observaciones!r}")
    return empresa, articulo, observaciones


def anonymize_comprobante(numero_comprobante: str) -> str:
    digest = hashlib.sha256(f"{EXPORT_HASH_SALT}:{numero_comprobante}".encode("utf-8")).hexdigest()[:16]
    return f"CMT-{digest}"


def resolve_source_name(records: list[PrecioHistorico], fuente_nombre: str | None) -> str:
    source_names = {record.fuente.nombre for record in records if record.fuente and record.fuente.nombre}
    if fuente_nombre is not None:
        if fuente_nombre not in source_names:
            raise ValueError(f"No existe la fuente {fuente_nombre!r} entre los registros seleccionados.")
        return fuente_nombre

    if len(source_names) != 1:
        raise ValueError(
            "No se puede distinguir con confianza la fuente historica canonica. "
            "Indica --fuente-nombre explicitamente."
        )
    return next(iter(source_names))


def select_records(
    db: Session,
    *,
    material_nombre: str,
    fuente_nombre: str | None = None,
) -> tuple[Material, str, list[PrecioHistorico]]:
    material = db.scalar(select(Material).where(Material.nombre == material_nombre))
    if material is None:
        raise ValueError(f"No existe el material {material_nombre!r}.")

    stmt = (
        select(PrecioHistorico)
        .where(PrecioHistorico.material_id == material.id)
        .options(
            joinedload(PrecioHistorico.fuente),
            joinedload(PrecioHistorico.presentacion),
            joinedload(PrecioHistorico.material),
        )
        .order_by(PrecioHistorico.fecha.asc(), PrecioHistorico.numero_comprobante.asc(), PrecioHistorico.id.asc())
    )
    records = list(db.scalars(stmt))
    if not records:
        raise ValueError(f"No hay precios historicos para {material_nombre!r}.")

    resolved_source = resolve_source_name(records, fuente_nombre)
    filtered_records = [
        record for record in records if record.fuente and record.fuente.nombre == resolved_source
    ]
    if not filtered_records:
        raise ValueError(f"No hay registros para la fuente {resolved_source!r}.")

    return material, resolved_source, filtered_records


def build_export_rows(
    records: list[PrecioHistorico],
    *,
    anonimizar_comprobante: bool = False,
) -> list[CanonicalExportRow]:
    rows: list[CanonicalExportRow] = []
    for record in records:
        empresa, articulo, observaciones_origen = extract_empresa_articulo(record.observaciones)
        numero_comprobante = record.numero_comprobante or ""
        if not numero_comprobante:
            raise ValueError(f"El registro {record.id} no tiene numero_comprobante.")
        exportado = anonymize_comprobante(numero_comprobante) if anonimizar_comprobante else numero_comprobante
        rows.append(
            CanonicalExportRow(
                fecha=record.fecha,
                empresa=empresa,
                numero_comprobante=exportado,
                articulo=articulo,
                precio_original=Decimal(record.precio_original),
                precio_normalizado=Decimal(record.precio_normalizado),
                moneda=record.moneda,
                origen_dato="REAL",
                metodo_estimacion="",
                observaciones_origen=observaciones_origen,
            )
        )
    rows.sort(key=lambda item: (item.fecha, item.numero_comprobante))
    return rows


def ensure_monthly_continuity(rows: list[CanonicalExportRow]) -> int:
    if not rows:
        raise ValueError("No hay filas para validar continuidad mensual.")

    monthly_dates = sorted({date(row.fecha.year, row.fecha.month, 1) for row in rows})
    expected = monthly_dates[0]
    for current in monthly_dates[1:]:
        next_expected = date(expected.year + (1 if expected.month == 12 else 0), 1 if expected.month == 12 else expected.month + 1, 1)
        if current != next_expected:
            raise ValueError(
                f"La serie exportada tiene huecos mensuales entre {expected.isoformat()} y {current.isoformat()}."
            )
        expected = current

    if len(monthly_dates) < MIN_MONTHLY_POINTS:
        raise ValueError(
            f"No hay datos suficientes para exportar la serie canonica. "
            f"Meses detectados: {len(monthly_dates)}. Minimo requerido: {MIN_MONTHLY_POINTS}."
        )
    return len(monthly_dates)


def validate_export_rows(rows: list[CanonicalExportRow]) -> int:
    if not rows:
        raise ValueError("No hay filas para exportar.")

    seen_comprobantes: set[str] = set()
    for row in rows:
        if row.precio_original <= 0:
            raise ValueError(f"precio_original invalido en {row.fecha.isoformat()}: {row.precio_original}")
        if row.precio_normalizado <= 0:
            raise ValueError(f"precio_normalizado invalido en {row.fecha.isoformat()}: {row.precio_normalizado}")
        if row.moneda != "ARS":
            raise ValueError(f"Moneda invalida en {row.fecha.isoformat()}: {row.moneda!r}")
        if row.origen_dato != "REAL":
            raise ValueError(f"origen_dato invalido en {row.fecha.isoformat()}: {row.origen_dato!r}")
        if row.metodo_estimacion != "":
            raise ValueError(
                f"metodo_estimacion debe estar vacio en la exportacion canonica: {row.metodo_estimacion!r}"
            )
        if not row.numero_comprobante:
            raise ValueError(f"numero_comprobante vacio en {row.fecha.isoformat()}.")
        if row.numero_comprobante in seen_comprobantes:
            raise ValueError(f"Duplicado detectado para numero_comprobante exportado: {row.numero_comprobante}")
        seen_comprobantes.add(row.numero_comprobante)

    return ensure_monthly_continuity(rows)


def compare_monthly_series(rows: list[CanonicalExportRow], records: list[PrecioHistorico]) -> bool:
    csv_inputs = [
        PrecioSerieInput(
            fecha=row.fecha,
            precio_normalizado=row.precio_normalizado,
            unidad_base="kg",
            fuente="Historico canonico Cemento Portland",
            numero_comprobante=row.numero_comprobante,
        )
        for row in rows
    ]
    db_inputs = [
        PrecioSerieInput(
            fecha=record.fecha,
            precio_normalizado=Decimal(record.precio_normalizado),
            unidad_base=record.material.unidad_base,
            fuente=record.fuente.nombre if record.fuente else None,
            numero_comprobante=record.numero_comprobante,
        )
        for record in records
    ]

    csv_series = construir_serie_mensual(csv_inputs)
    db_series = construir_serie_mensual(db_inputs)
    if len(csv_series) != len(db_series):
        raise ValueError("La serie mensual exportada no coincide en cantidad de puntos con la serie mensual de base.")

    for csv_point, db_point in zip(csv_series, db_series, strict=True):
        if csv_point.fecha != db_point.fecha:
            raise ValueError(
                f"La serie mensual exportada difiere en fecha: {csv_point.fecha.isoformat()} != {db_point.fecha.isoformat()}."
            )
        if csv_point.precio_promedio_normalizado != db_point.precio_promedio_normalizado:
            raise ValueError(
                "La serie mensual exportada difiere en precio_promedio_normalizado "
                f"para {csv_point.fecha.isoformat()}."
            )
    return True


def write_csv(rows: list[CanonicalExportRow], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=EXPORT_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_csv_row())


def export_cemento_canonico(
    db: Session,
    *,
    output: Path = DEFAULT_OUTPUT,
    anonimizar_comprobante: bool = False,
    material_nombre: str = DEFAULT_MATERIAL_NOMBRE,
    fuente_nombre: str | None = None,
    comparar_serie_mensual: bool = False,
) -> ExportSummary:
    material, resolved_source, records = select_records(
        db,
        material_nombre=material_nombre,
        fuente_nombre=fuente_nombre,
    )
    rows = build_export_rows(records, anonimizar_comprobante=anonimizar_comprobante)
    cantidad_meses = validate_export_rows(rows)
    write_csv(rows, output)
    comparacion_ok = compare_monthly_series(rows, records) if comparar_serie_mensual else None

    return ExportSummary(
        material_nombre=material.nombre,
        fuente_nombre=resolved_source,
        cantidad_registros=len(rows),
        fecha_min=rows[0].fecha,
        fecha_max=rows[-1].fecha,
        cantidad_meses=cantidad_meses,
        anonimizado=anonimizar_comprobante,
        continuidad_ok=True,
        comparacion_serie_ok=comparacion_ok,
    )


def print_summary(summary: ExportSummary) -> None:
    print(f"material: {summary.material_nombre}")
    print(f"fuente: {summary.fuente_nombre}")
    print(f"cantidad_registros: {summary.cantidad_registros}")
    print(f"rango_temporal: {summary.fecha_min.isoformat()} a {summary.fecha_max.isoformat()}")
    print(f"cantidad_meses: {summary.cantidad_meses}")
    print(f"anonimizacion: {'si' if summary.anonimizado else 'no'}")
    print(f"continuidad_mensual: {'ok' if summary.continuidad_ok else 'fail'}")
    if summary.comparacion_serie_ok is not None:
        print(f"comparacion_serie_mensual: {'ok' if summary.comparacion_serie_ok else 'fail'}")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    with SessionLocal() as db:
        summary = export_cemento_canonico(
            db,
            output=Path(args.output),
            anonimizar_comprobante=args.anonimizar_comprobante,
            material_nombre=args.material_nombre,
            fuente_nombre=args.fuente_nombre,
            comparar_serie_mensual=args.comparar_serie_mensual,
        )
    print_summary(summary)


if __name__ == "__main__":
    main()
