from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException
from pulp import LpMaximize, LpProblem, LpStatus, LpVariable, PULP_CBC_CMD, lpSum, value

from app.modules.catalog.application.utils import derive_material_key
from app.modules.catalog.domain.repositories import MaterialRepository
from app.modules.pricing.application.forecast_service import forecast_material
from app.modules.pricing.application.purchase_recommendations import (
    CONFIANZA_BAJA,
    CONFIANZA_NO_CALIBRADA,
    CONFIANZA_NO_DISPONIBLE,
    _resolver_confiabilidad,
)
from app.modules.pricing.domain.exceptions import MaterialNotFoundException
from app.modules.pricing.domain.repositories import PricingRepository


PESO_CRITICIDAD = {
    "alta": Decimal("3.00"),
    "media": Decimal("2.00"),
    "baja": Decimal("1.00"),
}

ESTADO_OPTIMAL = "OPTIMAL"


@dataclass(frozen=True)
class PurchaseOptimizationInputItem:
    material_id: int
    cantidad_objetivo: Decimal
    criticidad: str


@dataclass(frozen=True)
class OptimizationCandidate:
    material_id: int
    material_key: str
    cantidad_objetivo: Decimal
    precio_actual: Decimal
    precio_proyectado_horizonte: Decimal
    ahorro_unitario_estimado: Decimal
    criticidad: str
    peso_criticidad: Decimal
    confiabilidad: str
    no_calibrado: bool


@dataclass(frozen=True)
class PurchaseOptimizationItemResult:
    material_id: int
    material_key: str
    cantidad_objetivo: Decimal
    cantidad_recomendada_comprar_ahora: Decimal
    precio_actual: Decimal
    precio_proyectado_horizonte: Decimal
    costo_compra_ahora: Decimal
    ahorro_unitario_estimado: Decimal
    ahorro_total_estimado: Decimal
    criticidad: str
    peso_criticidad: Decimal
    confiabilidad: str


@dataclass(frozen=True)
class PurchaseOptimizationResult:
    presupuesto_total: Decimal
    presupuesto_utilizado: Decimal
    presupuesto_restante: Decimal
    horizonte_meses: int
    estado_optimizacion: str
    items: tuple[PurchaseOptimizationItemResult, ...]
    ahorro_total_estimado: Decimal
    justificacion: str
    advertencias: tuple[str, ...]


def _quantize_amount(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _quantize_quantity(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def _es_confiabilidad_baja(confiabilidad: str, no_calibrado: bool) -> bool:
    return no_calibrado or confiabilidad in {
        CONFIANZA_BAJA,
        CONFIANZA_NO_CALIBRADA,
        CONFIANZA_NO_DISPONIBLE,
    }


def _normalizar_estado_optimizacion(status_code: int) -> str:
    return LpStatus[status_code].replace(" ", "_").upper()


def _build_candidate(item: PurchaseOptimizationInputItem, material, forecast_result) -> OptimizationCandidate:
    selection = getattr(forecast_result, "seleccion_modelo", None)
    material_key = selection.material_key if selection is not None and getattr(selection, "material_key", None) else derive_material_key(material.nombre)
    precio_actual = Decimal(f"{forecast_result.dataset[-1].y:.2f}")
    precio_proyectado_horizonte = forecast_result.forecast[-1].precio_proyectado
    ahorro_unitario = max(precio_proyectado_horizonte - precio_actual, Decimal("0"))
    confiabilidad = _resolver_confiabilidad(forecast_result)
    no_calibrado = bool(getattr(selection, "no_calibrado", False))

    return OptimizationCandidate(
        material_id=material.id,
        material_key=material_key,
        cantidad_objetivo=item.cantidad_objetivo,
        precio_actual=precio_actual,
        precio_proyectado_horizonte=precio_proyectado_horizonte,
        ahorro_unitario_estimado=_quantize_amount(ahorro_unitario),
        criticidad=item.criticidad,
        peso_criticidad=PESO_CRITICIDAD[item.criticidad],
        confiabilidad=confiabilidad,
        no_calibrado=no_calibrado,
    )


def optimizar_compra_items(
    *,
    presupuesto_total: Decimal,
    horizonte_meses: int,
    candidates: list[OptimizationCandidate],
    advertencias: list[str] | tuple[str, ...] | None = None,
) -> PurchaseOptimizationResult:
    if not candidates:
        raise HTTPException(status_code=422, detail="No hay materiales validos para optimizar la compra.")

    problem = LpProblem("purchase_budget_optimization", LpMaximize)
    variables: dict[int, LpVariable] = {}

    for candidate in candidates:
        upper_bound = float(candidate.cantidad_objetivo if candidate.ahorro_unitario_estimado > 0 else Decimal("0"))
        variables[candidate.material_id] = LpVariable(
            f"x_{candidate.material_id}",
            lowBound=0,
            upBound=upper_bound,
        )

    problem += lpSum(
        float(candidate.ahorro_unitario_estimado * candidate.peso_criticidad) * variables[candidate.material_id]
        for candidate in candidates
    )
    problem += lpSum(float(candidate.precio_actual) * variables[candidate.material_id] for candidate in candidates) <= float(
        presupuesto_total
    )

    status_code = problem.solve(PULP_CBC_CMD(msg=False))
    estado_optimizacion = _normalizar_estado_optimizacion(status_code)
    if estado_optimizacion not in {ESTADO_OPTIMAL, "NOT_SOLVED"} and not candidates:
        raise HTTPException(status_code=422, detail="No fue posible resolver la optimizacion de compra.")

    resultados: list[PurchaseOptimizationItemResult] = []
    presupuesto_utilizado = Decimal("0")
    ahorro_total_estimado = Decimal("0")
    for candidate in candidates:
        valor_variable = value(variables[candidate.material_id])
        cantidad_recomendada = _quantize_quantity(Decimal(f"{(valor_variable or 0):.4f}"))
        costo_compra_ahora = _quantize_amount(candidate.precio_actual * cantidad_recomendada)
        ahorro_total = _quantize_amount(candidate.ahorro_unitario_estimado * cantidad_recomendada)
        presupuesto_utilizado += costo_compra_ahora
        ahorro_total_estimado += ahorro_total
        resultados.append(
            PurchaseOptimizationItemResult(
                material_id=candidate.material_id,
                material_key=candidate.material_key,
                cantidad_objetivo=candidate.cantidad_objetivo,
                cantidad_recomendada_comprar_ahora=cantidad_recomendada,
                precio_actual=candidate.precio_actual,
                precio_proyectado_horizonte=candidate.precio_proyectado_horizonte,
                costo_compra_ahora=costo_compra_ahora,
                ahorro_unitario_estimado=candidate.ahorro_unitario_estimado,
                ahorro_total_estimado=ahorro_total,
                criticidad=candidate.criticidad,
                peso_criticidad=candidate.peso_criticidad,
                confiabilidad=candidate.confiabilidad,
            )
        )

    advertencias_resultado = list(advertencias or [])
    presupuesto_utilizado = _quantize_amount(presupuesto_utilizado)
    ahorro_total_estimado = _quantize_amount(ahorro_total_estimado)
    presupuesto_restante = _quantize_amount(presupuesto_total - presupuesto_utilizado)

    return PurchaseOptimizationResult(
        presupuesto_total=_quantize_amount(presupuesto_total),
        presupuesto_utilizado=presupuesto_utilizado,
        presupuesto_restante=presupuesto_restante,
        horizonte_meses=horizonte_meses,
        estado_optimizacion=estado_optimizacion,
        items=tuple(resultados),
        ahorro_total_estimado=ahorro_total_estimado,
        justificacion=(
            "La optimizacion prioriza materiales con mayor ahorro esperado ajustado por criticidad, "
            "respetando el presupuesto disponible."
        ),
        advertencias=tuple(advertencias_resultado),
    )


def optimizar_compra_con_presupuesto(
    *,
    presupuesto_total: Decimal,
    horizonte_meses: int,
    materiales: list[PurchaseOptimizationInputItem],
    material_repo: MaterialRepository,
    pricing_repo: PricingRepository,
    usar_selector_modelo: bool = False,
) -> PurchaseOptimizationResult:
    candidates: list[OptimizationCandidate] = []
    advertencias: list[str] = []

    for item in materiales:
        material = material_repo.get_by_id(item.material_id)
        if material is None:
            raise MaterialNotFoundException(item.material_id)

        try:
            forecast_result = forecast_material(
                material,
                horizonte_meses,
                pricing_repo,
                usar_selector_modelo=usar_selector_modelo,
            )
        except Exception as exc:
            advertencias.append(f"Se excluye material_id={item.material_id} de la optimizacion: {exc}.")
            continue

        if not forecast_result.forecast or not getattr(forecast_result, "dataset", None):
            advertencias.append(
                f"Se excluye material_id={item.material_id} de la optimizacion por falta de forecast util."
            )
            continue

        candidate = _build_candidate(item, material, forecast_result)
        selection = getattr(forecast_result, "seleccion_modelo", None)
        if selection is not None and getattr(selection, "advertencia", None):
            advertencias.append(f"{candidate.material_key}: {selection.advertencia}")
        if _es_confiabilidad_baja(candidate.confiabilidad, candidate.no_calibrado):
            advertencias.append(
                f"{candidate.material_key}: el material se optimiza con cautela por confiabilidad {candidate.confiabilidad}"
                f"{' y modelo no calibrado' if candidate.no_calibrado else ''}."
            )

        candidates.append(candidate)

    return optimizar_compra_items(
        presupuesto_total=presupuesto_total,
        horizonte_meses=horizonte_meses,
        candidates=candidates,
        advertencias=advertencias,
    )
