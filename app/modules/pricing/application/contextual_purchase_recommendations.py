from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from fastapi import HTTPException

from app.modules.catalog.infrastructure.models import Material
from app.modules.pricing.application.purchase_recommendations import (
    CONFIANZA_BAJA,
    CONFIANZA_NO_CALIBRADA,
    CONFIANZA_NO_DISPONIBLE,
    PurchaseRecommendationResult,
    recomendar_momento_compra,
)

ACCION_COMPRAR_AHORA = "COMPRAR_AHORA"
ACCION_POSTERGAR = "POSTERGAR"
ACCION_ESCALONAR = "ESCALONAR"
ACCION_SIN_VENTAJA_CLARA = "SIN_VENTAJA_CLARA"

FASES_CRITICIDAD = {
    "estructura": "alta",
    "impermeabilizacion": "alta",
    "terminaciones": "media",
    "general": "media",
}

FACTORES_UMBRAL_RIESGO = {
    "baja": Decimal("1.00"),
    "media": Decimal("1.10"),
    "alta": Decimal("1.25"),
}


@dataclass(frozen=True)
class ContextualPurchaseRecommendationResult:
    material_id: int
    material_key: str
    fase_obra: str
    fecha_objetivo_uso: date | None
    horizonte_meses: int
    tolerancia_riesgo: str
    criticidad: str
    decision: str
    variacion_esperada_pct: Decimal | None
    precio_actual: Decimal | None
    precio_proyectado_horizonte: Decimal | None
    precio_proyectado_optimista: Decimal | None
    precio_proyectado_pesimista: Decimal | None
    cantidad_objetivo: Decimal | None
    impacto_economico_estimado: Decimal | None
    mape: Decimal | None
    umbral_decision_pct: Decimal | None
    supera_umbral_decision: bool
    confiabilidad: str
    justificacion: str
    advertencias: tuple[str, ...]


def resolver_horizonte_contextual(
    *,
    horizonte_meses: int | None,
    fecha_objetivo_uso: date | None,
    hoy: date | None = None,
) -> int:
    if fecha_objetivo_uso is None:
        if horizonte_meses is None:
            raise HTTPException(status_code=422, detail="Debe informar fecha_objetivo_uso u horizonte_meses.")
        return horizonte_meses

    fecha_base = hoy or date.today()
    if fecha_objetivo_uso <= fecha_base:
        raise HTTPException(status_code=422, detail="La fecha_objetivo_uso debe ser posterior a la fecha actual.")

    meses = (fecha_objetivo_uso.year - fecha_base.year) * 12 + fecha_objetivo_uso.month - fecha_base.month
    if fecha_objetivo_uso.day > fecha_base.day:
        meses += 1
    meses = max(1, meses)
    if meses > 12:
        raise HTTPException(status_code=422, detail="La fecha_objetivo_uso debe estar dentro de los proximos 12 meses.")
    return meses


def _resolver_umbral_contextual(umbral_base: Decimal | None, tolerancia_riesgo: str) -> Decimal:
    base = umbral_base or Decimal("5")
    return (base * FACTORES_UMBRAL_RIESGO[tolerancia_riesgo]).quantize(Decimal("0.0001"))


def _forecast_habilita_decision(recomendacion: PurchaseRecommendationResult) -> bool:
    if recomendacion.variacion_esperada_pct is None:
        return False
    if recomendacion.confiabilidad in {CONFIANZA_BAJA, CONFIANZA_NO_CALIBRADA, CONFIANZA_NO_DISPONIBLE}:
        return False
    return not any("no calibrado" in advertencia.lower() for advertencia in recomendacion.advertencias)


def _justificacion_forecast_no_habilitado(
    *,
    fase_obra: str,
    recomendacion: PurchaseRecommendationResult,
) -> str:
    if recomendacion.variacion_esperada_pct is None:
        return (
            f"No se recomienda una accion firme para la fase {fase_obra} porque no hay una variacion "
            "esperada disponible para el horizonte evaluado."
        )
    if recomendacion.confiabilidad in {CONFIANZA_BAJA, CONFIANZA_NO_CALIBRADA, CONFIANZA_NO_DISPONIBLE}:
        return (
            f"No se recomienda una accion firme para la fase {fase_obra} porque la confiabilidad del "
            f"forecast es {recomendacion.confiabilidad}. Debe revisarse antes de decidir."
        )
    if any("no calibrado" in advertencia.lower() for advertencia in recomendacion.advertencias):
        return (
            f"No se recomienda una accion firme para la fase {fase_obra} porque el forecast tiene "
            "advertencias de calibracion. Debe revisarse antes de decidir."
        )
    return (
        f"No se recomienda una accion firme para la fase {fase_obra} porque el forecast no habilita "
        "una decision automatica con los datos disponibles."
    )


def recomendar_estrategia_contextual(
    material: Material,
    *,
    fase_obra: str,
    tolerancia_riesgo: str,
    cantidad_objetivo: Decimal,
    pricing_repo,
    horizonte_meses: int | None = None,
    fecha_objetivo_uso: date | None = None,
    hoy: date | None = None,
    usar_selector_modelo: bool = False,
) -> ContextualPurchaseRecommendationResult:
    horizonte_resuelto = resolver_horizonte_contextual(
        horizonte_meses=horizonte_meses,
        fecha_objetivo_uso=fecha_objetivo_uso,
        hoy=hoy,
    )
    criticidad = FASES_CRITICIDAD[fase_obra]
    recomendacion = recomendar_momento_compra(
        material,
        horizonte_resuelto,
        criticidad,
        cantidad_objetivo,
        pricing_repo,
        usar_selector_modelo=usar_selector_modelo,
    )
    umbral_decision = _resolver_umbral_contextual(recomendacion.umbral_decision_pct, tolerancia_riesgo)
    variacion = recomendacion.variacion_esperada_pct
    supera_umbral = variacion is not None and abs(variacion) >= umbral_decision
    corto_plazo_critico = horizonte_resuelto <= 3 and criticidad == "alta" and tolerancia_riesgo == "baja"

    if not _forecast_habilita_decision(recomendacion):
        decision = ACCION_SIN_VENTAJA_CLARA
        justificacion = _justificacion_forecast_no_habilitado(
            fase_obra=fase_obra,
            recomendacion=recomendacion,
        )
    elif variacion is not None and variacion >= umbral_decision:
        decision = ACCION_COMPRAR_AHORA
        justificacion = (
            f"Se recomienda comprar ahora para la fase {fase_obra}: el uso se evalua a "
            f"{horizonte_resuelto} meses, la tolerancia al riesgo es {tolerancia_riesgo} y la suba "
            f"esperada de {variacion}% supera el umbral contextual de {umbral_decision}%."
        )
    elif variacion is not None and variacion <= -umbral_decision:
        if corto_plazo_critico:
            decision = ACCION_ESCALONAR
            justificacion = (
                f"Se recomienda escalonar la compra para la fase {fase_obra}: se proyecta una baja de precio, "
                "pero la necesidad es critica y cercana con tolerancia baja al riesgo."
            )
        else:
            decision = ACCION_POSTERGAR
            justificacion = (
                f"Se recomienda postergar para la fase {fase_obra}: la baja esperada de {variacion}% "
                f"supera el umbral contextual de {umbral_decision}% y el horizonte es de {horizonte_resuelto} meses."
            )
    elif corto_plazo_critico:
        decision = ACCION_ESCALONAR
        justificacion = (
            f"Se recomienda escalonar la compra para la fase {fase_obra}: no hay una ventaja economica clara "
            "por encima del error del modelo, pero la necesidad critica es cercana."
        )
    else:
        decision = ACCION_SIN_VENTAJA_CLARA
        justificacion = (
            f"No hay ventaja clara para la fase {fase_obra}: la variacion esperada de {variacion}% "
            f"no supera el umbral contextual de {umbral_decision}% para tolerancia {tolerancia_riesgo}."
        )

    return ContextualPurchaseRecommendationResult(
        material_id=recomendacion.material_id,
        material_key=recomendacion.material_key,
        fase_obra=fase_obra,
        fecha_objetivo_uso=fecha_objetivo_uso,
        horizonte_meses=horizonte_resuelto,
        tolerancia_riesgo=tolerancia_riesgo,
        criticidad=criticidad,
        decision=decision,
        variacion_esperada_pct=variacion,
        precio_actual=recomendacion.precio_actual,
        precio_proyectado_horizonte=recomendacion.precio_proyectado_horizonte,
        precio_proyectado_optimista=recomendacion.precio_proyectado_optimista,
        precio_proyectado_pesimista=recomendacion.precio_proyectado_pesimista,
        cantidad_objetivo=recomendacion.cantidad_objetivo,
        impacto_economico_estimado=recomendacion.impacto_economico_estimado,
        mape=recomendacion.mape,
        umbral_decision_pct=umbral_decision,
        supera_umbral_decision=supera_umbral,
        confiabilidad=recomendacion.confiabilidad,
        justificacion=justificacion,
        advertencias=recomendacion.advertencias,
    )
