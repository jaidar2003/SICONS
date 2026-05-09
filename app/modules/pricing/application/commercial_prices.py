from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.catalog.application.utils import derive_material_key
from app.modules.catalog.infrastructure.models import Material, Presentacion
from app.modules.pricing.application.forecast_service import forecast_material
from app.modules.pricing.domain.repositories import PricingRepository
from app.modules.pricing.infrastructure.models import CommercialMargin, PrecioHistorico


MARGEN_GLOBAL = "GLOBAL"
MARGEN_MATERIAL = "MATERIAL"
MARGEN_PRODUCT = "PRODUCT"
ORIGEN_SIN_MARGEN = "SIN_MARGEN"


@dataclass(frozen=True)
class CommercialMarginCandidate:
    id: int
    scope: str
    material_id: int | None
    presentation_id: int | None
    product_key: str | None
    margen_ganancia_pct: Decimal
    activo: bool
    updated_at: datetime


@dataclass(frozen=True)
class CommercialPriceResult:
    material_id: int
    material_key: str
    presentation_id: int | None
    product_key: str | None
    costo_base_actual: Decimal | None
    costo_base_proyectado: Decimal | None
    margen_ganancia_pct: Decimal | None
    origen_margen: str
    precio_final_actual: Decimal | None
    precio_final_proyectado: Decimal | None
    ganancia_unitaria_actual: Decimal | None
    ganancia_unitaria_proyectada: Decimal | None
    advertencias: tuple[str, ...]


def _quantize_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def derive_product_key(material_name: str, presentation_name: str | None = None) -> str:
    material_key = derive_material_key(material_name)
    if not presentation_name:
        return material_key
    presentation_key = derive_material_key(presentation_name)
    return f"{material_key}-{presentation_key}"


def calcular_precio_final(costo_base: Decimal, margen_ganancia_pct: Decimal) -> Decimal:
    return _quantize_money(costo_base * (Decimal("1") + (margen_ganancia_pct / Decimal("100"))))


def _cargar_historial_base(
    pricing_repo: PricingRepository,
    material_id: int,
    presentation_id: int | None = None,
) -> PrecioHistorico | None:
    precios = pricing_repo.get_historical_prices(material_id, date(2000, 1, 1))
    if presentation_id is not None:
        precios_presentacion = [precio for precio in precios if precio.presentacion_id == presentation_id]
        if precios_presentacion:
            precios = precios_presentacion
    if not precios:
        return None
    return max(precios, key=lambda precio: (precio.fecha, precio.id))


def _cargar_candidatos(db: Session) -> list[CommercialMarginCandidate]:
    stmt = select(CommercialMargin).where(CommercialMargin.activo.is_(True)).order_by(
        CommercialMargin.scope.asc(),
        CommercialMargin.updated_at.desc(),
        CommercialMargin.id.desc(),
    )
    rows = db.scalars(stmt)
    return [
        CommercialMarginCandidate(
            id=row.id,
            scope=row.scope,
            material_id=row.material_id,
            presentation_id=row.presentation_id,
            product_key=row.product_key,
            margen_ganancia_pct=row.margen_ganancia_pct,
            activo=row.activo,
            updated_at=row.updated_at,
        )
        for row in rows
    ]


def _priority(scope: str) -> int:
    if scope == MARGEN_PRODUCT:
        return 3
    if scope == MARGEN_MATERIAL:
        return 2
    if scope == MARGEN_GLOBAL:
        return 1
    return 0


def resolve_commercial_margin(
    candidates: Sequence[CommercialMarginCandidate],
    *,
    material_id: int,
    presentation_id: int | None,
    product_key: str | None,
) -> CommercialMarginCandidate | None:
    normalized_product_key = product_key.strip() if product_key else None

    matching = [
        candidate
        for candidate in candidates
        if candidate.activo
        and (
            (candidate.scope == MARGEN_GLOBAL)
            or (
                candidate.scope == MARGEN_MATERIAL
                and candidate.material_id == material_id
            )
            or (
                candidate.scope == MARGEN_PRODUCT
                and candidate.material_id == material_id
                and (
                    (presentation_id is not None and candidate.presentation_id == presentation_id)
                    or (
                        normalized_product_key is not None
                        and candidate.product_key is not None
                        and candidate.product_key == normalized_product_key
                    )
                )
            )
        )
    ]

    if not matching:
        return None

    return max(
        matching,
        key=lambda candidate: (
            _priority(candidate.scope),
            candidate.updated_at,
            candidate.id,
        ),
    )


def calcular_precio_comercial(
    *,
    material: Material,
    pricing_repo: PricingRepository,
    db: Session,
    horizonte_meses: int = 3,
    presentation_id: int | None = None,
    product_key: str | None = None,
    usar_selector_modelo: bool = True,
) -> CommercialPriceResult:
    presentation: Presentacion | None = None
    advertencias: list[str] = []

    if presentation_id is not None:
        presentation = db.get(Presentacion, presentation_id)
        if presentation is None:
            raise HTTPException(status_code=404, detail="Presentacion no encontrada")
        if presentation.material_id != material.id:
            raise HTTPException(status_code=422, detail="La presentacion no pertenece al material")

    material_key = derive_material_key(material.nombre)
    derived_product_key = product_key or derive_product_key(material.nombre, presentation.nombre_presentacion if presentation else None)
    historial_base = _cargar_historial_base(pricing_repo, material.id, presentation_id)
    costo_base_actual = _quantize_money(historial_base.precio_normalizado) if historial_base is not None else None

    forecast_base = None
    try:
        forecast_result = forecast_material(
            material,
            horizonte_meses,
            pricing_repo,
            usar_selector_modelo=usar_selector_modelo,
        )
        if forecast_result.forecast:
            forecast_base = _quantize_money(forecast_result.forecast[-1].precio_proyectado)
    except HTTPException as exc:
        advertencias.append(f"No fue posible calcular el costo proyectado: {exc.detail}")

    candidates = _cargar_candidatos(db)
    margin = resolve_commercial_margin(
        candidates,
        material_id=material.id,
        presentation_id=presentation_id,
        product_key=derived_product_key,
    )

    if margin is None:
        advertencias.append("No hay margen comercial activo configurado; se devuelve el costo base.")
        margen_ganancia_pct = None
        origen_margen = ORIGEN_SIN_MARGEN
    else:
        margen_ganancia_pct = _quantize_money(margin.margen_ganancia_pct)
        origen_margen = margin.scope

    precio_final_actual = (
        calcular_precio_final(costo_base_actual, margen_ganancia_pct) if costo_base_actual is not None and margen_ganancia_pct is not None else costo_base_actual
    )
    ganancia_unitaria_actual = (
        _quantize_money(precio_final_actual - costo_base_actual)
        if precio_final_actual is not None and costo_base_actual is not None
        else None
    )

    precio_final_proyectado = (
        calcular_precio_final(forecast_base, margen_ganancia_pct) if forecast_base is not None and margen_ganancia_pct is not None else forecast_base
    )
    ganancia_unitaria_proyectada = (
        _quantize_money(precio_final_proyectado - forecast_base)
        if precio_final_proyectado is not None and forecast_base is not None
        else None
    )

    if costo_base_actual is None:
        advertencias.append("No hay precio historico base disponible para el material.")
    if forecast_base is None:
        advertencias.append("No hay precio proyectado disponible para el horizonte solicitado.")

    return CommercialPriceResult(
        material_id=material.id,
        material_key=material_key,
        presentation_id=presentation_id,
        product_key=derived_product_key if presentation_id is not None or product_key else None,
        costo_base_actual=costo_base_actual,
        costo_base_proyectado=forecast_base,
        margen_ganancia_pct=margen_ganancia_pct,
        origen_margen=origen_margen,
        precio_final_actual=precio_final_actual,
        precio_final_proyectado=precio_final_proyectado,
        ganancia_unitaria_actual=ganancia_unitaria_actual,
        ganancia_unitaria_proyectada=ganancia_unitaria_proyectada,
        advertencias=tuple(advertencias),
    )


def build_margin_candidate(margin: CommercialMargin) -> CommercialMarginCandidate:
    return CommercialMarginCandidate(
        id=margin.id,
        scope=margin.scope,
        material_id=margin.material_id,
        presentation_id=margin.presentation_id,
        product_key=margin.product_key,
        margen_ganancia_pct=margin.margen_ganancia_pct,
        activo=margin.activo,
        updated_at=margin.updated_at,
    )
