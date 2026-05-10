from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.catalog.infrastructure.models import Fuente, Material
from app.modules.pricing.domain.exceptions import PriceImputationError
from app.modules.pricing.infrastructure.models import ExternalIndexValue, PrecioHistorico

ESTIMATED_ORIGIN = "ESTIMADO"
REAL_ORIGIN = "REAL"


@dataclass(frozen=True)
class ImputationResult:
    material_id: int
    source_name: str
    series_id: str
    metodo_estimacion: str
    inserted: int
    updated: int
    skipped_real_months: int
    generated_months: list[date]


def _month_start(value: date) -> date:
    return date(value.year, value.month, 1)


def _next_month(value: date) -> date:
    if value.month == 12:
        return date(value.year + 1, 1, 1)
    return date(value.year, value.month + 1, 1)


def _generate_months(start_date: date, end_date: date) -> list[date]:
    months: list[date] = []
    current = _month_start(start_date)
    end_month = _month_start(end_date)
    while current <= end_month:
        months.append(current)
        current = _next_month(current)
    return months


def _quantize_money(value: Decimal, places: str) -> Decimal:
    return value.quantize(Decimal(places), rounding=ROUND_HALF_UP)


def _calculate_estimated_price(*, base_price: Decimal, base_index: Decimal, target_index: Decimal) -> Decimal:
    if base_index <= 0:
        raise PriceImputationError("El indice base debe ser mayor a 0 para imputar precios.")
    if target_index <= 0:
        raise PriceImputationError("El indice objetivo debe ser mayor a 0 para imputar precios.")
    return base_price * (target_index / base_index)


def _get_or_create_estimation_fuente(db: Session) -> Fuente:
    fuente = db.scalar(select(Fuente).where(Fuente.nombre == "Estimado"))
    if fuente is not None:
        return fuente

    fuente = Fuente(
        nombre="Estimado",
        tipo_fuente="estimacion",
        descripcion="Valor imputado usando un indice externo oficial",
    )
    db.add(fuente)
    db.flush()
    return fuente


def _load_material(db: Session, material_id: int) -> Material:
    material = db.get(Material, material_id)
    if material is None:
        raise PriceImputationError(f"No existe el material con ID {material_id}.")
    return material


def _load_price_rows(db: Session, material_id: int, end_date: date) -> list[PrecioHistorico]:
    stmt = (
        select(PrecioHistorico)
        .where(
            PrecioHistorico.material_id == material_id,
            PrecioHistorico.fecha <= end_date,
        )
        .order_by(PrecioHistorico.fecha.asc(), PrecioHistorico.id.asc())
    )
    return list(db.scalars(stmt))


def _load_index_map(db: Session, series_id: str, end_date: date) -> dict[date, Decimal]:
    stmt = (
        select(ExternalIndexValue)
        .where(
            ExternalIndexValue.series_id == series_id,
            ExternalIndexValue.date <= _month_start(end_date),
        )
        .order_by(ExternalIndexValue.date.asc())
    )
    return {
        _month_start(value.date): Decimal(value.value)
        for value in db.scalars(stmt)
    }


def impute_monthly_prices(
    db: Session,
    *,
    material_id: int,
    start_date: date,
    end_date: date,
    index_series_id: str,
    source_name: str,
    metodo_estimacion: str,
) -> ImputationResult:
    if start_date > end_date:
        raise PriceImputationError("start_date no puede ser mayor que end_date.")

    material = _load_material(db, material_id)
    prices = _load_price_rows(db, material_id, end_date)
    if not prices:
        raise PriceImputationError("No hay precios historicos para usar como base de imputacion.")

    months = _generate_months(start_date, end_date)
    indices = _load_index_map(db, index_series_id, end_date)
    missing_index_months = [month.isoformat() for month in months if month not in indices]
    if missing_index_months:
        raise PriceImputationError(
            f"Faltan indices externos para los meses: {', '.join(missing_index_months)}."
        )

    fuente_estimada = _get_or_create_estimation_fuente(db)
    by_month: dict[date, list[PrecioHistorico]] = {}
    for price in prices:
        by_month.setdefault(_month_start(price.fecha), []).append(price)

    real_prices = [
        price
        for price in prices
        if (price.origen_dato or REAL_ORIGIN) != ESTIMATED_ORIGIN
    ]
    if not real_prices:
        raise PriceImputationError("No existe un precio real previo para usar como base de imputacion.")

    inserted = 0
    updated = 0
    skipped_real_months = 0
    generated_months: list[date] = []

    for month in months:
        month_rows = by_month.get(month, [])
        if any((row.origen_dato or REAL_ORIGIN) != ESTIMATED_ORIGIN for row in month_rows):
            skipped_real_months += 1
            continue

        base_price = next((row for row in reversed(real_prices) if row.fecha < month), None)
        if base_price is None:
            raise PriceImputationError(
                f"No existe un precio real anterior a {month.isoformat()} para imputar."
            )

        base_month = _month_start(base_price.fecha)
        base_index = indices.get(base_month)
        if base_index is None:
            raise PriceImputationError(
                f"Falta el indice base para el mes {base_month.isoformat()}."
            )
        target_index = indices.get(month)
        if target_index is None:
            raise PriceImputationError(
                f"Falta el indice objetivo para el mes {month.isoformat()}."
            )

        estimated_normalized = _quantize_money(
            _calculate_estimated_price(
                base_price=Decimal(base_price.precio_normalizado),
                base_index=base_index,
                target_index=target_index,
            ),
            "0.0001",
        )
        estimated_original = _quantize_money(
            _calculate_estimated_price(
                base_price=Decimal(base_price.precio_original),
                base_index=base_index,
                target_index=target_index,
            ),
            "0.01",
        )

        existing_estimated = next(
            (row for row in month_rows if (row.origen_dato or REAL_ORIGIN) == ESTIMATED_ORIGIN),
            None,
        )
        observaciones = (
            f"Estimado usando {metodo_estimacion} sobre base real {base_price.fecha.isoformat()} "
            f"con serie externa {index_series_id}."
        )
        if existing_estimated is None:
            db.add(
                PrecioHistorico(
                    material_id=material.id,
                    presentacion_id=base_price.presentacion_id,
                    fuente_id=fuente_estimada.id,
                    fecha=month,
                    precio_original=estimated_original,
                    precio_normalizado=estimated_normalized,
                    moneda=base_price.moneda,
                    numero_comprobante=f"ESTIMADO-{month.isoformat()}",
                    origen_dato=ESTIMATED_ORIGIN,
                    metodo_estimacion=metodo_estimacion,
                    observaciones=observaciones,
                )
            )
            inserted += 1
        else:
            existing_estimated.presentacion_id = base_price.presentacion_id
            existing_estimated.fuente_id = fuente_estimada.id
            existing_estimated.precio_original = estimated_original
            existing_estimated.precio_normalizado = estimated_normalized
            existing_estimated.moneda = base_price.moneda
            existing_estimated.numero_comprobante = f"ESTIMADO-{month.isoformat()}"
            existing_estimated.origen_dato = ESTIMATED_ORIGIN
            existing_estimated.metodo_estimacion = metodo_estimacion
            existing_estimated.observaciones = observaciones
            updated += 1

        generated_months.append(month)

    db.commit()
    return ImputationResult(
        material_id=material.id,
        source_name=source_name,
        series_id=index_series_id,
        metodo_estimacion=metodo_estimacion,
        inserted=inserted,
        updated=updated,
        skipped_real_months=skipped_real_months,
        generated_months=generated_months,
    )
