from dataclasses import dataclass
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modules.catalog.infrastructure.models import Material
from app.modules.pricing.application.forecast_service import forecast_material
from app.modules.pricing.domain.rules import (
    calcular_impacto_absoluto,
    calcular_puntaje_criticidad,
    calcular_variacion_esperada_porcentual,
    etiquetar_criticidad,
    explicar_priorizacion,
    normalizar_valores,
)
from app.modules.pricing.interfaces.schemas import (
    MaterialCriticidadCreate,
    MaterialCriticidadRead,
    MaterialCriticidadResponseRead,
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


def priorizar_materiales_desde_forecast(
    payload: MaterialCriticidadCreate,
    db: Session,
) -> MaterialCriticidadResponseRead:
    materiales_prioridad: list[MaterialPriorityInput] = []
    for item in payload.materiales:
        material = db.get(Material, item.material_id)
        if material is None:
            raise HTTPException(status_code=404, detail=f"Material no encontrado: {item.material_id}")

        forecast_result = forecast_material(material, payload.horizonte_meses, db)
        punto_objetivo = forecast_result.forecast[-1]
        materiales_prioridad.append(
            MaterialPriorityInput(
                material_id=material.id,
                material_nombre=material.nombre,
                unidad_base=material.unidad_base,
                cantidad_requerida=item.cantidad_requerida,
                precio_actual_normalizado=Decimal(f"{forecast_result.dataset[-1].y:.2f}"),
                precio_proyectado_normalizado=punto_objetivo.precio_proyectado,
            )
        )

    ranking = priorizar_materiales_criticos(materiales_prioridad, alpha=payload.alpha, beta=payload.beta)
    return MaterialCriticidadResponseRead(
        horizonte_meses=payload.horizonte_meses,
        alpha=payload.alpha,
        beta=payload.beta,
        materiales=[MaterialCriticidadRead(**resultado.__dict__) for resultado in ranking],
    )
