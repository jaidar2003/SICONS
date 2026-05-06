from __future__ import annotations

import csv
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.catalog.application.utils import derive_material_key
from app.modules.catalog.infrastructure.models import Fuente, Material, Presentacion
from app.modules.pricing.infrastructure.models import ExternalIndexValue, PrecioHistorico
from app.modules.pricing.infrastructure.regressors import (
    BLUE_CSV,
    IPC_CSV,
    IPIM_NIVEL_GENERAL_SERIES_ID,
    MAYORISTA_CSV,
    OFICIAL_CSV,
)
from app.shared.database.session import SessionLocal


EXPECTED_MATERIAL_KEYS = {
    "Cemento Portland": "cemento-portland",
    "Pastina": "pastina",
    "Membrana Megaflex": "membrana-megaflex",
}

EXPECTED_PRESENTATIONS = {
    "Cemento Portland": {"Bolsa 25 kg", "Bolsa 50 kg"},
    "Pastina": {"Unidad 1 kg"},
    "Membrana Megaflex": {"Balde 20 kg"},
}

CANONICAL_CEMENT_SOURCE_NAME = "Dataset canónico Cemento Portland"
CANONICAL_CEMENT_SOURCE_TYPE = "dataset"
MIN_MONTHS_REQUIRED = 24

@dataclass(frozen=True)
class ValidationCheck:
    name: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class ValidationSummary:
    checks: tuple[ValidationCheck, ...]

    @property
    def ok(self) -> bool:
        return all(check.ok for check in self.checks)


def _month_start(value: date) -> date:
    return date(value.year, value.month, 1)


def _next_month(value: date) -> date:
    return date(value.year + (1 if value.month == 12 else 0), 1 if value.month == 12 else value.month + 1, 1)


def _monthly_range(months: set[date]) -> tuple[date, date, list[date]]:
    ordered = sorted(months)
    if not ordered:
        raise ValueError("No hay meses para validar.")

    first = ordered[0]
    last = ordered[-1]
    expected = first
    missing: list[date] = []
    while expected <= last:
        if expected not in months:
            missing.append(expected)
        expected = _next_month(expected)
    return first, last, missing


def _print_check(check: ValidationCheck) -> None:
    status = "OK" if check.ok else "FALLA"
    print(f"[{status}] {check.name}: {check.detail}")


def _required_regressors() -> dict[str, tuple[Path, str]]:
    return {
        "dolar_oficial": (OFICIAL_CSV, "venta"),
        "dolar_mayorista": (MAYORISTA_CSV, "venta"),
        "dolar_blue": (BLUE_CSV, "venta"),
        "ipc": (IPC_CSV, "ipc"),
    }


def _load_material(db: Session, name: str) -> Material | None:
    return db.scalar(select(Material).where(Material.nombre == name))


def _load_fuente(db: Session, name: str) -> Fuente | None:
    return db.scalar(select(Fuente).where(Fuente.nombre == name))


def _load_price_rows(
    db: Session,
    *,
    material_id: int,
    fuente_id: int | None = None,
) -> list[tuple[date, str, str | None, str, str, str]]:
    stmt = (
        select(
            PrecioHistorico.fecha,
            PrecioHistorico.numero_comprobante,
            PrecioHistorico.origen_dato,
            PrecioHistorico.metodo_estimacion,
            PrecioHistorico.moneda,
            PrecioHistorico.observaciones,
        )
        .where(PrecioHistorico.material_id == material_id)
        .order_by(PrecioHistorico.fecha.asc(), PrecioHistorico.numero_comprobante.asc())
    )
    if fuente_id is not None:
        stmt = stmt.where(PrecioHistorico.fuente_id == fuente_id)
    return list(db.execute(stmt).all())


def _validate_materials_and_keys(db: Session) -> list[ValidationCheck]:
    checks: list[ValidationCheck] = []
    for material_name, expected_key in EXPECTED_MATERIAL_KEYS.items():
        material = _load_material(db, material_name)
        if material is None:
            checks.append(
                ValidationCheck(
                    name=f"Material {material_name}",
                    ok=False,
                    detail="No existe en el catalogo.",
                )
            )
            continue

        material_key = derive_material_key(material.nombre)
        ok = material_key == expected_key
        detail = f"material_key derivado: {material_key} (esperado: {expected_key})"
        checks.append(ValidationCheck(name=f"Material {material_name}", ok=ok, detail=detail))
    return checks


def _validate_presentations(db: Session) -> list[ValidationCheck]:
    checks: list[ValidationCheck] = []
    for material_name, expected_presentations in EXPECTED_PRESENTATIONS.items():
        material = _load_material(db, material_name)
        if material is None:
            checks.append(
                ValidationCheck(
                    name=f"Presentaciones {material_name}",
                    ok=False,
                    detail="No existe el material asociado.",
                )
            )
            continue

        presentaciones = set(
            db.scalars(
                select(Presentacion.nombre_presentacion).where(Presentacion.material_id == material.id)
            ).all()
        )
        faltantes = sorted(expected_presentations - presentaciones)
        ok = not faltantes
        detail = (
            f"presentaciones encontradas: {sorted(presentaciones)}"
            if ok
            else f"faltan presentaciones: {faltantes}"
        )
        checks.append(ValidationCheck(name=f"Presentaciones {material_name}", ok=ok, detail=detail))
    return checks


def _validate_canonical_cement(db: Session) -> list[ValidationCheck]:
    checks: list[ValidationCheck] = []
    material = _load_material(db, "Cemento Portland")
    if material is None:
        return [
            ValidationCheck(
                name="Cemento canónico",
                ok=False,
                detail="No existe el material Cemento Portland.",
            )
        ]

    fuente = _load_fuente(db, CANONICAL_CEMENT_SOURCE_NAME)
    if fuente is None:
        return [
            ValidationCheck(
                name="Cemento canónico",
                ok=False,
                detail=f"No existe la fuente {CANONICAL_CEMENT_SOURCE_NAME!r}.",
            )
        ]

    rows = _load_price_rows(db, material_id=material.id, fuente_id=fuente.id)
    if not rows:
        return [
            ValidationCheck(
                name="Cemento canónico",
                ok=False,
                detail="La fuente canonica existe pero no tiene registros asociados.",
            )
        ]

    months = {_month_start(row[0]) for row in rows}
    first_month, last_month, missing = _monthly_range(months)
    real_rows = [row for row in rows if row[2] == "REAL"]
    estimated_rows = [row for row in rows if row[2] == "ESTIMADO"]
    invalid_rows = [
        row
        for row in rows
        if row[4] != "ARS" or row[2] != "REAL" or (row[3] not in (None, ""))
    ]
    source_names = set(
        db.scalars(
            select(Fuente.nombre)
            .join(PrecioHistorico, PrecioHistorico.fuente_id == Fuente.id)
            .where(PrecioHistorico.material_id == material.id)
        ).all()
    )
    canonical_presentations = set(
        db.scalars(
            select(Presentacion.nombre_presentacion)
            .join(PrecioHistorico, PrecioHistorico.presentacion_id == Presentacion.id)
            .where(
                PrecioHistorico.material_id == material.id,
                PrecioHistorico.fuente_id == fuente.id,
            )
        ).all()
    )

    checks.append(
        ValidationCheck(
            name="Cemento canónico - fuente",
            ok=fuente.nombre == CANONICAL_CEMENT_SOURCE_NAME and fuente.tipo_fuente == CANONICAL_CEMENT_SOURCE_TYPE,
            detail=f"fuente: {fuente.nombre} / tipo: {fuente.tipo_fuente}",
        )
    )
    checks.append(
        ValidationCheck(
            name="Cemento canónico - volumen",
            ok=len(rows) >= MIN_MONTHS_REQUIRED and len(months) >= MIN_MONTHS_REQUIRED,
            detail=f"registros: {len(rows)} / meses: {len(months)} / minimo: {MIN_MONTHS_REQUIRED}",
        )
    )
    checks.append(
        ValidationCheck(
            name="Cemento canónico - continuidad",
            ok=not missing,
            detail=(
                f"rango: {first_month.isoformat()} -> {last_month.isoformat()}"
                if not missing
                else f"huecos mensuales: {[month.isoformat() for month in missing]}"
            ),
        )
    )
    checks.append(
        ValidationCheck(
            name="Cemento canónico - calidad",
            ok=not invalid_rows,
            detail=(
                "todas las filas tienen origen REAL, metodo_estimacion vacio y moneda ARS"
                if not invalid_rows
                else f"filas invalidas detectadas: {len(invalid_rows)}"
            ),
        )
    )
    checks.append(
        ValidationCheck(
            name="Cemento canónico - origenes",
            ok=CANONICAL_CEMENT_SOURCE_NAME in source_names,
            detail=f"fuentes presentes: {sorted(source_names)}",
        )
    )
    checks.append(
        ValidationCheck(
            name="Cemento canónico - REAL",
            ok=bool(real_rows) and not estimated_rows,
            detail=f"REAL: {len(real_rows)} / ESTIMADO: {len(estimated_rows)}",
        )
    )
    checks.append(
        ValidationCheck(
            name="Cemento canónico - presentaciones",
            ok=canonical_presentations == EXPECTED_PRESENTATIONS["Cemento Portland"],
            detail=f"presentaciones canonicas: {sorted(canonical_presentations)}",
        )
    )
    return checks


def _validate_hybrid_material(db: Session, material_name: str, expected_presentations: set[str]) -> list[ValidationCheck]:
    material = _load_material(db, material_name)
    if material is None:
        return [
            ValidationCheck(
                name=f"{material_name} - existencia",
                ok=False,
                detail="No existe el material asociado.",
            )
        ]

    rows = _load_price_rows(db, material_id=material.id)
    if not rows:
        return [
            ValidationCheck(
                name=f"{material_name} - serie",
                ok=False,
                detail="No tiene precios historicos cargados.",
            )
        ]

    months = {_month_start(row[0]) for row in rows}
    first_month, last_month, missing = _monthly_range(months)
    presentaciones = set(
        db.scalars(
            select(Presentacion.nombre_presentacion).where(Presentacion.material_id == material.id)
        ).all()
    )

    real_rows = [row for row in rows if row[2] == "REAL"]
    estimated_rows = [row for row in rows if row[2] == "ESTIMADO"]
    invalid_real_rows = [row for row in real_rows if row[3] not in (None, "")]
    invalid_estimated_rows = [row for row in estimated_rows if row[3] in (None, "")]
    moneda_invalid_rows = [row for row in rows if row[4] != "ARS"]

    return [
        ValidationCheck(
            name=f"{material_name} - material_key",
            ok=derive_material_key(material.nombre) == EXPECTED_MATERIAL_KEYS[material_name],
            detail=f"material_key derivado: {derive_material_key(material.nombre)}",
        ),
        ValidationCheck(
            name=f"{material_name} - presentaciones",
            ok=presentaciones == expected_presentations,
            detail=f"presentaciones encontradas: {sorted(presentaciones)}",
        ),
        ValidationCheck(
            name=f"{material_name} - continuidad",
            ok=not missing and len(months) >= MIN_MONTHS_REQUIRED,
            detail=(
                f"rango: {first_month.isoformat()} -> {last_month.isoformat()}"
                if not missing
                else f"huecos mensuales: {[month.isoformat() for month in missing]}"
            ),
        ),
        ValidationCheck(
            name=f"{material_name} - mezcla REAL/ESTIMADO",
            ok=bool(real_rows) and bool(estimated_rows),
            detail=f"REAL: {len(real_rows)} / ESTIMADO: {len(estimated_rows)}",
        ),
        ValidationCheck(
            name=f"{material_name} - metodo_estimacion",
            ok=not invalid_real_rows and not invalid_estimated_rows,
            detail=(
                "REAL sin metodo_estimacion y ESTIMADO con metodo_estimacion"
                if not invalid_real_rows and not invalid_estimated_rows
                else f"filas invalidas -> REAL: {len(invalid_real_rows)}, ESTIMADO: {len(invalid_estimated_rows)}"
            ),
        ),
        ValidationCheck(
            name=f"{material_name} - moneda",
            ok=not moneda_invalid_rows,
            detail=f"filas invalidas: {len(moneda_invalid_rows)}",
        ),
    ]


def _read_monthly_csv_regressor(path: Path, value_column: str, regressor_name: str) -> ValidationCheck:
    if not path.exists():
        return ValidationCheck(
            name=f"Regresor {regressor_name}",
            ok=False,
            detail=f"No existe el CSV local: {path}",
        )

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            return ValidationCheck(
                name=f"Regresor {regressor_name}",
                ok=False,
                detail="El CSV no tiene encabezado.",
            )

        if "fecha" not in reader.fieldnames or value_column not in reader.fieldnames:
            return ValidationCheck(
                name=f"Regresor {regressor_name}",
                ok=False,
                detail=f"Columnas requeridas no encontradas: {reader.fieldnames}",
            )

        months: set[date] = set()
        rows = 0
        invalid_rows = 0
        for raw_row in reader:
            rows += 1
            try:
                fecha = datetime.fromisoformat(raw_row["fecha"]).date()
                float((raw_row[value_column] or "").replace(",", "."))
            except Exception:
                invalid_rows += 1
                continue
            months.add(_month_start(fecha))

        if rows == 0:
            return ValidationCheck(
                name=f"Regresor {regressor_name}",
                ok=False,
                detail="El CSV no contiene filas.",
            )
        if invalid_rows:
            return ValidationCheck(
                name=f"Regresor {regressor_name}",
                ok=False,
                detail=f"Filas invalidas: {invalid_rows} de {rows}.",
            )

        first_month, last_month, missing = _monthly_range(months)
        if len(months) < MIN_MONTHS_REQUIRED:
            return ValidationCheck(
                name=f"Regresor {regressor_name}",
                ok=False,
                detail=f"Meses detectados: {len(months)} / minimo requerido: {MIN_MONTHS_REQUIRED}",
            )
        if missing:
            return ValidationCheck(
                name=f"Regresor {regressor_name}",
                ok=False,
                detail=f"Huecos mensuales: {[month.isoformat() for month in missing]}",
            )

        return ValidationCheck(
            name=f"Regresor {regressor_name}",
            ok=True,
            detail=f"CSV local disponible: {path} ({rows} filas, {first_month.isoformat()} -> {last_month.isoformat()})",
        )


def _validate_ipim_local(db: Session) -> ValidationCheck:
    count = db.scalar(
        select(func.count(ExternalIndexValue.id)).where(ExternalIndexValue.series_id == IPIM_NIVEL_GENERAL_SERIES_ID)
    )
    if not count:
        return ValidationCheck(
            name="Regresor ipim_nivel_general",
            ok=False,
            detail="No hay valores locales cargados para la serie IPIM.",
        )

    first_date, last_date = db.execute(
        select(
            func.min(ExternalIndexValue.date),
            func.max(ExternalIndexValue.date),
        ).where(ExternalIndexValue.series_id == IPIM_NIVEL_GENERAL_SERIES_ID)
    ).one()
    return ValidationCheck(
        name="Regresor ipim_nivel_general",
        ok=True,
        detail=f"Valores locales disponibles: {count} ({first_date} -> {last_date})",
    )


def validate_minimum_dataset(db: Session) -> ValidationSummary:
    checks: list[ValidationCheck] = []
    checks.extend(_validate_materials_and_keys(db))
    checks.extend(_validate_presentations(db))
    checks.extend(_validate_canonical_cement(db))
    checks.extend(_validate_hybrid_material(db, "Pastina", {"Unidad 1 kg"}))
    checks.extend(_validate_hybrid_material(db, "Membrana Megaflex", {"Balde 20 kg"}))
    checks.append(_validate_ipim_local(db))
    for regressor_name, (path, value_column) in _required_regressors().items():
        checks.append(_read_monthly_csv_regressor(path, value_column, regressor_name))
    return ValidationSummary(checks=tuple(checks))


def main() -> None:
    print("=== BuildWise Minimum Dataset Validation ===\n")
    with SessionLocal() as db:
        summary = validate_minimum_dataset(db)

    for check in summary.checks:
        _print_check(check)

    print("\n" + "=" * 48)
    if summary.ok:
        print("VALIDATION SUCCESSFUL: dataset minimo reproducible listo para tesis.")
        sys.exit(0)

    print("VALIDATION FAILED: revisar los checks indicados arriba.")
    sys.exit(1)


if __name__ == "__main__":
    main()
