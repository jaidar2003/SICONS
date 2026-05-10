from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException

from app.modules.catalog.application.utils import derive_material_key
from app.modules.catalog.infrastructure.models import Material
from app.modules.pricing.application.forecast_service import forecast_material
from app.modules.pricing.application.purchase_recommendations import (
    CONFIANZA_BAJA,
    CONFIANZA_NO_CALIBRADA,
    CONFIANZA_NO_DISPONIBLE,
    _resolver_confiabilidad,
)
from app.modules.pricing.domain.rules import calcular_variacion_esperada_porcentual

ESTRATEGIA_COMPRAR_AHORA = "COMPRAR_AHORA"
ESTRATEGIA_ESPERAR_AL_HORIZONTE = "ESPERAR_AL_HORIZONTE"
ESTRATEGIA_COMPRA_PARCIAL = "COMPRA_PARCIAL"
PORCENTAJE_COMPRA_INMEDIATA_DEFAULT = Decimal("0.50")


@dataclass(frozen=True)
class PurchaseStrategy:
    nombre: str
    costo_estimado: Decimal
    riesgo: str
    descripcion: str


@dataclass(frozen=True)
class PurchaseStrategiesResult:
    material_id: int
    material_key: str
    horizonte_meses: int
    cantidad_objetivo: Decimal
    porcentaje_compra_inmediata: Decimal
    precio_actual: Decimal
    precio_proyectado_horizonte: Decimal
    variacion_esperada_pct: Decimal
    confiabilidad: str
    estrategias: tuple[PurchaseStrategy, ...]
    mejor_estrategia: str
    ahorro_estimado: Decimal
    justificacion: str
    advertencias: tuple[str, ...]


def _quantize_amount(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _es_confiabilidad_baja(confiabilidad: str, no_calibrado: bool) -> bool:
    return no_calibrado or confiabilidad in {
        CONFIANZA_BAJA,
        CONFIANZA_NO_CALIBRADA,
        CONFIANZA_NO_DISPONIBLE,
    }


def _calcular_costo(precio: Decimal, cantidad: Decimal) -> Decimal:
    return _quantize_amount(precio * cantidad)


def _riesgo_estrategia(nombre: str, variacion_esperada_pct: Decimal) -> str:
    if nombre == ESTRATEGIA_COMPRAR_AHORA:
        return "bajo" if variacion_esperada_pct >= 0 else "medio"
    if nombre == ESTRATEGIA_ESPERAR_AL_HORIZONTE:
        return "medio" if variacion_esperada_pct >= 0 else "bajo"
    return "medio"


def _construir_justificacion(
    *,
    mejor_estrategia: str,
    variacion_esperada_pct: Decimal,
    confiabilidad: str,
    no_calibrado: bool,
) -> str:
    variacion_texto = variacion_esperada_pct.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    if _es_confiabilidad_baja(confiabilidad, no_calibrado):
        return (
            f"La comparacion favorece {mejor_estrategia} por costo esperado, pero debe tomarse "
            f"como orientativa porque la confiabilidad es {confiabilidad} y el modelo "
            f"{'esta no calibrado' if no_calibrado else 'requiere cautela metodologica'}."
        )

    if mejor_estrategia == ESTRATEGIA_COMPRAR_AHORA:
        return (
            "Comprar ahora reduce el costo esperado frente a esperar, dado que el modelo "
            f"proyecta una suba del {variacion_texto}%."
        )
    if mejor_estrategia == ESTRATEGIA_ESPERAR_AL_HORIZONTE:
        return (
            "Esperar al horizonte reduce el costo esperado frente a comprar ahora, dado que "
            f"el modelo proyecta una baja del {abs(variacion_texto)}%."
        )
    return (
        "La compra parcial amortigua el costo esperado entre comprar ahora y esperar, con una "
        f"variacion proyectada de {variacion_texto}%."
    )


def evaluar_estrategias_compra(
    *,
    material_id: int,
    material_key: str,
    horizonte_meses: int,
    cantidad_objetivo: Decimal,
    precio_actual: Decimal,
    precio_proyectado_horizonte: Decimal,
    confiabilidad: str,
    no_calibrado: bool,
    porcentaje_compra_inmediata: Decimal = PORCENTAJE_COMPRA_INMEDIATA_DEFAULT,
    advertencias: list[str] | tuple[str, ...] | None = None,
) -> PurchaseStrategiesResult:
    porcentaje = Decimal(porcentaje_compra_inmediata)
    advertencias_resultado = list(advertencias or [])
    variacion_esperada_pct = calcular_variacion_esperada_porcentual(precio_actual, precio_proyectado_horizonte)

    costo_ahora = _calcular_costo(precio_actual, cantidad_objetivo)
    costo_esperar = _calcular_costo(precio_proyectado_horizonte, cantidad_objetivo)
    cantidad_inmediata = cantidad_objetivo * porcentaje
    cantidad_diferida = cantidad_objetivo - cantidad_inmediata
    costo_parcial = _calcular_costo(precio_actual, cantidad_inmediata) + _calcular_costo(
        precio_proyectado_horizonte, cantidad_diferida
    )

    estrategias = (
        PurchaseStrategy(
            nombre=ESTRATEGIA_COMPRAR_AHORA,
            costo_estimado=costo_ahora,
            riesgo=_riesgo_estrategia(ESTRATEGIA_COMPRAR_AHORA, variacion_esperada_pct),
            descripcion="Compra completa al precio actual.",
        ),
        PurchaseStrategy(
            nombre=ESTRATEGIA_ESPERAR_AL_HORIZONTE,
            costo_estimado=costo_esperar,
            riesgo=_riesgo_estrategia(ESTRATEGIA_ESPERAR_AL_HORIZONTE, variacion_esperada_pct),
            descripcion="Compra completa al precio proyectado.",
        ),
        PurchaseStrategy(
            nombre=ESTRATEGIA_COMPRA_PARCIAL,
            costo_estimado=_quantize_amount(costo_parcial),
            riesgo=_riesgo_estrategia(ESTRATEGIA_COMPRA_PARCIAL, variacion_esperada_pct),
            descripcion="Compra parcial actual y parcial al precio proyectado.",
        ),
    )

    mejor = min(estrategias, key=lambda estrategia: estrategia.costo_estimado)
    ahorro_estimado = _quantize_amount(max(estrategia.costo_estimado for estrategia in estrategias) - mejor.costo_estimado)

    if _es_confiabilidad_baja(confiabilidad, no_calibrado):
        advertencias_resultado.append(
            "La comparacion es metodologicamente debil por baja confiabilidad o forecast no calibrado."
        )

    return PurchaseStrategiesResult(
        material_id=material_id,
        material_key=material_key,
        horizonte_meses=horizonte_meses,
        cantidad_objetivo=cantidad_objetivo,
        porcentaje_compra_inmediata=porcentaje,
        precio_actual=precio_actual,
        precio_proyectado_horizonte=precio_proyectado_horizonte,
        variacion_esperada_pct=variacion_esperada_pct,
        confiabilidad=confiabilidad,
        estrategias=estrategias,
        mejor_estrategia=mejor.nombre,
        ahorro_estimado=ahorro_estimado,
        justificacion=_construir_justificacion(
            mejor_estrategia=mejor.nombre,
            variacion_esperada_pct=variacion_esperada_pct,
            confiabilidad=confiabilidad,
            no_calibrado=no_calibrado,
        ),
        advertencias=tuple(advertencias_resultado),
    )


def comparar_estrategias_compra(
    material: Material,
    horizonte_meses: int,
    cantidad_objetivo: Decimal,
    pricing_repo,
    *,
    porcentaje_compra_inmediata: Decimal = PORCENTAJE_COMPRA_INMEDIATA_DEFAULT,
    usar_selector_modelo: bool = False,
) -> PurchaseStrategiesResult:
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
        raise HTTPException(
            status_code=422,
            detail=f"No fue posible comparar estrategias de compra: {exc.detail}",
        ) from exc

    if not forecast_result.forecast:
        raise HTTPException(status_code=422, detail="El forecast no devolvio puntos proyectados.")

    if not getattr(forecast_result, "dataset", None):
        raise HTTPException(status_code=422, detail="El forecast no devolvio historial suficiente para comparar estrategias.")

    precio_actual = Decimal(f"{forecast_result.dataset[-1].y:.2f}")
    precio_proyectado_horizonte = forecast_result.forecast[-1].precio_proyectado
    selection = getattr(forecast_result, "seleccion_modelo", None)
    confiabilidad = _resolver_confiabilidad(forecast_result)
    no_calibrado = bool(getattr(selection, "no_calibrado", False))

    if selection is not None and getattr(selection, "advertencia", None):
        advertencias.append(selection.advertencia)
    if no_calibrado:
        advertencias.append("La comparacion se apoya en un forecast marcado como no calibrado.")

    return evaluar_estrategias_compra(
        material_id=material.id,
        material_key=selection.material_key if selection is not None and getattr(selection, "material_key", None) else material_key,
        horizonte_meses=horizonte_meses,
        cantidad_objetivo=cantidad_objetivo,
        precio_actual=precio_actual,
        precio_proyectado_horizonte=precio_proyectado_horizonte,
        confiabilidad=confiabilidad,
        no_calibrado=no_calibrado,
        porcentaje_compra_inmediata=porcentaje_compra_inmediata,
        advertencias=advertencias,
    )
