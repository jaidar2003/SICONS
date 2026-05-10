from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fastapi import HTTPException

from app.modules.catalog.application.utils import derive_material_key
from app.modules.catalog.infrastructure.models import Material
from app.modules.pricing.application.forecast_service import forecast_material
from app.modules.pricing.domain.rules import calcular_variacion_esperada_porcentual

UMBRAL_ALZA = Decimal("5")
UMBRAL_BAJA = Decimal("-5")

CONFIANZA_ALTA = "alta"
CONFIANZA_MEDIA = "media"
CONFIANZA_MEDIA_BAJA = "media-baja"
CONFIANZA_BAJA = "baja"
CONFIANZA_NO_CALIBRADA = "no_calibrada"
CONFIANZA_NO_DISPONIBLE = "no_disponible"

DECISION_COMPRAR_AHORA = "COMPRAR_AHORA"
DECISION_ESPERAR = "ESPERAR"
DECISION_MONITOREAR = "MONITOREAR"

CRITICIDADES_VALIDAS = {"alta", "media", "media-baja", "baja"}


@dataclass(frozen=True)
class PurchaseRecommendationInput:
    material_id: int
    material_key: str
    horizonte_meses: int
    criticidad: str
    cantidad_objetivo: Decimal
    variacion_esperada_pct: Decimal | None
    confiabilidad: str
    no_calibrado: bool
    advertencias: tuple[str, ...]


@dataclass(frozen=True)
class PurchaseRecommendationResult:
    material_id: int
    material_key: str
    horizonte_meses: int
    decision: str
    variacion_esperada_pct: Decimal | None
    confiabilidad: str
    criticidad: str
    justificacion: str
    advertencias: tuple[str, ...]


def _resolver_confiabilidad(forecast_result) -> str:
    selection = getattr(forecast_result, "seleccion_modelo", None)
    if selection is not None and getattr(selection, "confiabilidad", None):
        return selection.confiabilidad

    mape = getattr(forecast_result.metricas, "mape", None)
    if mape is None:
        return CONFIANZA_NO_DISPONIBLE
    if mape <= Decimal("5"):
        return CONFIANZA_ALTA
    if mape <= Decimal("8"):
        return CONFIANZA_MEDIA
    if mape <= Decimal("12"):
        return CONFIANZA_MEDIA_BAJA
    return CONFIANZA_BAJA


def _es_suficiente_confiabilidad(confiabilidad: str, no_calibrado: bool) -> bool:
    return not no_calibrado and confiabilidad not in {CONFIANZA_BAJA, CONFIANZA_NO_CALIBRADA, CONFIANZA_NO_DISPONIBLE}


def evaluar_recomendacion_compra(
    *,
    material_id: int,
    material_key: str,
    horizonte_meses: int,
    cantidad_objetivo: Decimal | None,
    variacion_esperada_pct: Decimal | None,
    confiabilidad: str,
    criticidad: str,
    no_calibrado: bool,
    advertencias: list[str] | tuple[str, ...] | None = None,
) -> PurchaseRecommendationResult:
    advertencias_tuple = tuple(advertencias or ())

    if variacion_esperada_pct is None:
        return PurchaseRecommendationResult(
            material_id=material_id,
            material_key=material_key,
            horizonte_meses=horizonte_meses,
            decision=DECISION_MONITOREAR,
            variacion_esperada_pct=None,
            confiabilidad=CONFIANZA_NO_DISPONIBLE,
            criticidad=criticidad,
            justificacion=(
                "No fue posible obtener una variacion esperada confiable para el horizonte "
                "analizado, por lo que se recomienda monitorear."
            ),
            advertencias=advertencias_tuple
            + ("No hay datos suficientes para construir una recomendacion cuantitativa.",),
        )

    if not _es_suficiente_confiabilidad(confiabilidad, no_calibrado):
        return PurchaseRecommendationResult(
            material_id=material_id,
            material_key=material_key,
            horizonte_meses=horizonte_meses,
            decision=DECISION_MONITOREAR,
            variacion_esperada_pct=variacion_esperada_pct,
            confiabilidad=confiabilidad,
            criticidad=criticidad,
            justificacion=(
                f"Se recomienda monitorear porque la confiabilidad es {confiabilidad} "
                "o el modelo no esta calibrado de forma suficiente."
            ),
            advertencias=advertencias_tuple
            + ("La recomendacion se marca como conservadora por baja confiabilidad o no calibrado.",),
        )

    decision = DECISION_MONITOREAR
    if variacion_esperada_pct >= UMBRAL_ALZA and criticidad in {"alta", "media"}:
        decision = DECISION_COMPRAR_AHORA
    elif variacion_esperada_pct <= UMBRAL_BAJA and criticidad in {"baja", "media"}:
        decision = DECISION_ESPERAR
    elif variacion_esperada_pct <= UMBRAL_BAJA and criticidad == "alta":
        decision = DECISION_ESPERAR

    if criticidad == "alta" and decision == DECISION_ESPERAR and variacion_esperada_pct > UMBRAL_BAJA:
        decision = DECISION_MONITOREAR

    if decision == DECISION_MONITOREAR and criticidad == "alta" and variacion_esperada_pct >= UMBRAL_ALZA:
        decision = DECISION_COMPRAR_AHORA

    if decision == DECISION_MONITOREAR and criticidad == "baja" and variacion_esperada_pct <= UMBRAL_BAJA:
        decision = DECISION_ESPERAR

    if decision == DECISION_COMPRAR_AHORA:
        justificacion = (
            f"Se recomienda comprar ahora porque la variacion esperada es {variacion_esperada_pct}% "
            f"en el horizonte evaluado, la criticidad es {criticidad}, la confiabilidad es {confiabilidad} "
            f"y la cantidad objetivo es {cantidad_objetivo if cantidad_objetivo is not None else 'no informada'}."
        )
    elif decision == DECISION_ESPERAR:
        justificacion = (
            f"Se recomienda esperar porque la variacion esperada es {variacion_esperada_pct}% "
            f"en el horizonte evaluado, la criticidad es {criticidad}, la confiabilidad es {confiabilidad} "
            f"y la cantidad objetivo es {cantidad_objetivo if cantidad_objetivo is not None else 'no informada'}."
        )
    else:
        justificacion = (
            f"Se recomienda monitorear porque la variacion esperada es {variacion_esperada_pct}% "
            f"en el horizonte evaluado, la criticidad es {criticidad}, la confiabilidad es {confiabilidad} "
            f"y la cantidad objetivo es {cantidad_objetivo if cantidad_objetivo is not None else 'no informada'}."
        )

    return PurchaseRecommendationResult(
        material_id=material_id,
        material_key=material_key,
        horizonte_meses=horizonte_meses,
        decision=decision,
        variacion_esperada_pct=variacion_esperada_pct,
        confiabilidad=confiabilidad,
        criticidad=criticidad,
        justificacion=justificacion,
        advertencias=advertencias_tuple,
    )


def recomendar_momento_compra(
    material: Material,
    horizonte_meses: int,
    criticidad: str,
    cantidad_objetivo: Decimal,
    pricing_repo,
    *,
    usar_selector_modelo: bool = False,
) -> PurchaseRecommendationResult:
    material_key = derive_material_key(material.nombre)
    advertencias: list[str] = []

    try:
        forecast_result = forecast_material(
            material,
            horizonte_meses,
            pricing_repo,
            usar_selector_modelo=usar_selector_modelo,
        )
    except HTTPException as exc:
        advertencias.append(str(exc.detail))
        return evaluar_recomendacion_compra(
            material_id=material.id,
            material_key=material_key,
            horizonte_meses=horizonte_meses,
            cantidad_objetivo=cantidad_objetivo,
            variacion_esperada_pct=None,
            confiabilidad=CONFIANZA_NO_DISPONIBLE,
            criticidad=criticidad,
            no_calibrado=True,
            advertencias=advertencias,
        )

    if not forecast_result.forecast:
        advertencias.append("El forecast no devolvio puntos proyectados.")
        return evaluar_recomendacion_compra(
            material_id=material.id,
            material_key=material_key,
            horizonte_meses=horizonte_meses,
            cantidad_objetivo=cantidad_objetivo,
            variacion_esperada_pct=None,
            confiabilidad=CONFIANZA_NO_DISPONIBLE,
            criticidad=criticidad,
            no_calibrado=True,
            advertencias=advertencias,
        )

    if not getattr(forecast_result, "dataset", None):
        advertencias.append("El forecast no devolvio historial suficiente para comparar variacion.")
        return evaluar_recomendacion_compra(
            material_id=material.id,
            material_key=material_key,
            horizonte_meses=horizonte_meses,
            variacion_esperada_pct=None,
            confiabilidad=CONFIANZA_NO_DISPONIBLE,
            criticidad=criticidad,
            no_calibrado=True,
            advertencias=advertencias,
        )

    ultimo_precio = Decimal(f"{forecast_result.dataset[-1].y:.2f}")
    punto_objetivo = forecast_result.forecast[-1]
    variacion_esperada_pct = calcular_variacion_esperada_porcentual(
        ultimo_precio,
        punto_objetivo.precio_proyectado,
    )

    selection = getattr(forecast_result, "seleccion_modelo", None)
    no_calibrado = bool(getattr(selection, "no_calibrado", False))
    confiabilidad = _resolver_confiabilidad(forecast_result)
    if no_calibrado:
        advertencias.append("La recomendacion se apoya en un forecast marcado como no calibrado.")

    return evaluar_recomendacion_compra(
        material_id=material.id,
        material_key=selection.material_key if selection is not None and getattr(selection, "material_key", None) else material_key,
        horizonte_meses=horizonte_meses,
        cantidad_objetivo=cantidad_objetivo,
        variacion_esperada_pct=variacion_esperada_pct,
        confiabilidad=confiabilidad,
        criticidad=criticidad,
        no_calibrado=no_calibrado,
        advertencias=advertencias,
    )
