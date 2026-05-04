from dataclasses import dataclass
from decimal import Decimal

from app.modules.pricing.domain.rules import (
    calcular_impacto_absoluto,
    calcular_puntaje_criticidad,
    calcular_variacion_esperada_porcentual,
    etiquetar_criticidad,
    explicar_priorizacion,
    normalizar_valores,
)


DEFAULT_ALPHA = Decimal("0.50")
DEFAULT_BETA = Decimal("0.50")


@dataclass(frozen=True)
class MaterialPriorityInput:
    material_id: int
    material_nombre: str
    unidad_base: str
    cantidad_requerida: Decimal
    precio_actual_normalizado: Decimal
    precio_proyectado_normalizado: Decimal


@dataclass(frozen=True)
class MaterialPriorityResult:
    material_id: int
    material_nombre: str
    unidad_base: str
    cantidad_requerida: Decimal
    precio_actual_normalizado: Decimal
    precio_proyectado_normalizado: Decimal
    impacto_absoluto: Decimal
    variacion_esperada_porcentual: Decimal
    impacto_normalizado: Decimal
    variacion_normalizada: Decimal
    criticidad: Decimal
    nivel_criticidad: str
    explicacion: str


def priorizar_materiales_criticos(
    materiales: list[MaterialPriorityInput],
    alpha: Decimal = DEFAULT_ALPHA,
    beta: Decimal = DEFAULT_BETA,
) -> list[MaterialPriorityResult]:
    if not materiales:
        return []

    impactos = [
        calcular_impacto_absoluto(
            material.precio_actual_normalizado,
            material.precio_proyectado_normalizado,
            material.cantidad_requerida,
        )
        for material in materiales
    ]
    variaciones = [
        calcular_variacion_esperada_porcentual(
            material.precio_actual_normalizado,
            material.precio_proyectado_normalizado,
        )
        for material in materiales
    ]

    impactos_normalizados = normalizar_valores(impactos)
    variaciones_normalizadas = normalizar_valores(variaciones)

    resultados = [
        MaterialPriorityResult(
            material_id=material.material_id,
            material_nombre=material.material_nombre,
            unidad_base=material.unidad_base,
            cantidad_requerida=material.cantidad_requerida,
            precio_actual_normalizado=material.precio_actual_normalizado,
            precio_proyectado_normalizado=material.precio_proyectado_normalizado,
            impacto_absoluto=impacto,
            variacion_esperada_porcentual=variacion,
            impacto_normalizado=impacto_normalizado,
            variacion_normalizada=variacion_normalizada,
            criticidad=calcular_puntaje_criticidad(variacion_normalizada, impacto_normalizado, alpha, beta),
            nivel_criticidad=etiquetar_criticidad(
                calcular_puntaje_criticidad(variacion_normalizada, impacto_normalizado, alpha, beta)
            ),
            explicacion=explicar_priorizacion(
                variacion_normalizada,
                impacto_normalizado,
                variacion,
                impacto,
            ),
        )
        for material, impacto, variacion, impacto_normalizado, variacion_normalizada in zip(
            materiales,
            impactos,
            variaciones,
            impactos_normalizados,
            variaciones_normalizadas,
            strict=True,
        )
    ]

    return sorted(
        resultados,
        key=lambda item: (item.criticidad, item.impacto_absoluto, item.variacion_esperada_porcentual),
        reverse=True,
    )
