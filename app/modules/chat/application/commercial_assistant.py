from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import date
from decimal import ROUND_DOWN, Decimal, InvalidOperation

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modules.catalog.application.utils import derive_material_key
from app.modules.chat.application.service import ChatCompletionClient
from app.modules.pricing.application.commercial_prices import calcular_precio_comercial
from app.modules.pricing.application.contextual_purchase_recommendations import (
    ACCION_COMPRAR_AHORA,
    ACCION_ESCALONAR,
    ContextualPurchaseRecommendationResult,
    recomendar_estrategia_contextual,
    resolver_horizonte_contextual,
)
from app.modules.pricing.domain.repositories import PricingRepository

SUPPORTED_PRODUCT_KEYS = {"cemento-portland", "pastina", "membrana-megaflex"}
VALID_PHASES = {"estructura", "terminaciones", "impermeabilizacion", "general"}
VALID_RISK_LEVELS = {"baja", "media", "alta"}


@dataclass(frozen=True)
class CommercialNeedInterpretation:
    solicitud_original: str
    material_id: int | None
    producto_nombre: str | None
    cantidad: Decimal | None
    fase_obra: str | None
    fecha_objetivo_uso: date | None
    horizonte_meses: int | None
    presupuesto_maximo: Decimal | None
    tolerancia_riesgo: str
    datos_faltantes: tuple[str, ...]


@dataclass(frozen=True)
class CommercialProposalResult:
    material_id: int
    producto_nombre: str
    cantidad: Decimal
    fase_obra: str
    fecha_objetivo_uso: date | None
    horizonte_meses: int
    tolerancia_riesgo: str
    presupuesto_maximo: Decimal | None
    precio_unitario_actual: Decimal | None
    total_actual: Decimal | None
    precio_unitario_proyectado: Decimal | None
    total_proyectado: Decimal | None
    diferencia_estimada: Decimal | None
    recomendacion: ContextualPurchaseRecommendationResult
    propuesta: str
    advertencias: tuple[str, ...]


def _strip_json_fence(content: str) -> str:
    stripped = content.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return stripped


def _optional_decimal(value) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        decimal = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("valor numerico invalido") from exc
    return decimal if decimal > 0 else None


def _optional_date(value) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def _optional_horizon(value) -> int | None:
    if value in (None, ""):
        return None
    try:
        horizon = int(value)
    except (TypeError, ValueError):
        return None
    return horizon if 1 <= horizon <= 12 else None


def _supported_materials(materials) -> list:
    return [material for material in materials if derive_material_key(material.nombre) in SUPPORTED_PRODUCT_KEYS]


def interpretar_necesidad_comercial(
    solicitud: str,
    *,
    materials,
    client: ChatCompletionClient,
) -> CommercialNeedInterpretation:
    supported = _supported_materials(materials)
    catalog = [{"material_id": material.id, "producto": material.nombre} for material in supported]
    prompt = (
        "Extrae una necesidad comercial para BuildWise. Responde solamente JSON valido con las claves: "
        "material_id, producto_nombre, cantidad, fase_obra, fecha_objetivo_uso, horizonte_meses, "
        "presupuesto_maximo, tolerancia_riesgo, datos_faltantes. "
        "fase_obra solo puede ser estructura, terminaciones, impermeabilizacion o general; "
        "tolerancia_riesgo solo baja, media o alta. No inventes datos. "
        f"Catalogo permitido: {json.dumps(catalog, ensure_ascii=True)}."
    )
    content = client.complete([{"role": "system", "content": prompt}, {"role": "user", "content": solicitud.strip()}])
    try:
        parsed = json.loads(_strip_json_fence(content))
    except (json.JSONDecodeError, TypeError) as exc:
        raise HTTPException(status_code=502, detail="La IA no devolvio una interpretacion estructurada valida.") from exc

    try:
        requested_id = int(parsed.get("material_id")) if parsed.get("material_id") is not None else None
    except (TypeError, ValueError):
        requested_id = None
    product_name = str(parsed.get("producto_nombre") or "").strip()
    matched = next((material for material in supported if material.id == requested_id), None)
    if matched is None and product_name:
        product_key = derive_material_key(product_name)
        matched = next((material for material in supported if derive_material_key(material.nombre) == product_key), None)

    try:
        cantidad = _optional_decimal(parsed.get("cantidad"))
        presupuesto = _optional_decimal(parsed.get("presupuesto_maximo"))
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="La IA devolvio importes invalidos.") from exc

    fase = parsed.get("fase_obra") if parsed.get("fase_obra") in VALID_PHASES else None
    fecha_objetivo = _optional_date(parsed.get("fecha_objetivo_uso"))
    horizonte = _optional_horizon(parsed.get("horizonte_meses")) if fecha_objetivo is None else None
    tolerancia = parsed.get("tolerancia_riesgo")
    if tolerancia not in VALID_RISK_LEVELS:
        tolerancia = "media"

    missing = set()
    if matched is None:
        missing.add("producto")
    if cantidad is None:
        missing.add("cantidad")
    if fase is None:
        missing.add("fase_obra")
    if fecha_objetivo is None and horizonte is None:
        missing.add("fecha_objetivo_uso_o_horizonte_meses")
    for item in parsed.get("datos_faltantes") or []:
        if item in {"producto", "cantidad", "fase_obra", "fecha_objetivo_uso_o_horizonte_meses", "presupuesto_maximo"}:
            missing.add(item)

    return CommercialNeedInterpretation(
        solicitud_original=solicitud,
        material_id=matched.id if matched is not None else None,
        producto_nombre=matched.nombre if matched is not None else None,
        cantidad=cantidad,
        fase_obra=fase,
        fecha_objetivo_uso=fecha_objetivo,
        horizonte_meses=horizonte,
        presupuesto_maximo=presupuesto,
        tolerancia_riesgo=tolerancia,
        datos_faltantes=tuple(sorted(missing)),
    )


def _total(unit_price: Decimal | None, quantity: Decimal) -> Decimal | None:
    if unit_price is None:
        return None
    return (unit_price * quantity).quantize(Decimal("0.01"))


def generar_propuesta_comercial(
    *,
    material,
    cantidad: Decimal,
    fase_obra: str,
    tolerancia_riesgo: str,
    pricing_repo: PricingRepository,
    db: Session,
    client: ChatCompletionClient,
    fecha_objetivo_uso: date | None = None,
    horizonte_meses: int | None = None,
    presupuesto_maximo: Decimal | None = None,
    solicitud_original: str | None = None,
    usar_selector_modelo: bool = True,
) -> CommercialProposalResult:
    if derive_material_key(material.nombre) not in SUPPORTED_PRODUCT_KEYS:
        raise HTTPException(status_code=422, detail="El producto no pertenece al alcance comercial del MVP.")

    horizonte = resolver_horizonte_contextual(
        horizonte_meses=horizonte_meses,
        fecha_objetivo_uso=fecha_objetivo_uso,
    )
    commercial_price = calcular_precio_comercial(
        material=material,
        pricing_repo=pricing_repo,
        db=db,
        horizonte_meses=horizonte,
        usar_selector_modelo=usar_selector_modelo,
    )
    recommendation = recomendar_estrategia_contextual(
        material,
        fase_obra=fase_obra,
        tolerancia_riesgo=tolerancia_riesgo,
        cantidad_objetivo=cantidad,
        horizonte_meses=horizonte if fecha_objetivo_uso is None else None,
        fecha_objetivo_uso=fecha_objetivo_uso,
        pricing_repo=pricing_repo,
        usar_selector_modelo=usar_selector_modelo,
    )
    total_actual = _total(commercial_price.precio_final_actual, cantidad)
    total_proyectado = _total(commercial_price.precio_final_proyectado, cantidad)
    diferencia = (
        (total_proyectado - total_actual).quantize(Decimal("0.01"))
        if total_actual is not None and total_proyectado is not None
        else None
    )
    advertencias = list(commercial_price.advertencias) + list(recommendation.advertencias)
    if (
        presupuesto_maximo is not None
        and total_actual is not None
        and total_actual > presupuesto_maximo
        and recommendation.decision == ACCION_COMPRAR_AHORA
        and commercial_price.precio_final_actual is not None
    ):
        cantidad_cubierta = (presupuesto_maximo / commercial_price.precio_final_actual).quantize(
            Decimal("0.0001"),
            rounding=ROUND_DOWN,
        )
        recommendation = replace(
            recommendation,
            decision=ACCION_ESCALONAR,
            justificacion=(
                f"La senal de precio favorece comprar ahora, pero el presupuesto maximo de ARS {presupuesto_maximo} "
                f"no cubre las {cantidad} unidades. Se recomienda escalonar: permite adquirir hasta "
                f"{cantidad_cubierta} unidades al precio vigente."
            ),
        )
        advertencias.append("La compra inmediata completa supera el presupuesto maximo informado.")
    calculated_context = {
        "producto": material.nombre,
        "cantidad": str(cantidad),
        "fase_obra": fase_obra,
        "horizonte_meses": horizonte,
        "fecha_objetivo_uso": fecha_objetivo_uso.isoformat() if fecha_objetivo_uso else None,
        "presupuesto_maximo": str(presupuesto_maximo) if presupuesto_maximo is not None else None,
        "precio_unitario_actual": (
            str(commercial_price.precio_final_actual) if commercial_price.precio_final_actual is not None else None
        ),
        "total_actual": str(total_actual) if total_actual is not None else None,
        "precio_unitario_proyectado": (
            str(commercial_price.precio_final_proyectado)
            if commercial_price.precio_final_proyectado is not None
            else None
        ),
        "total_proyectado": str(total_proyectado) if total_proyectado is not None else None,
        "diferencia_estimada": str(diferencia) if diferencia is not None else None,
        "accion_recomendada": recommendation.decision,
        "confianza": recommendation.confiabilidad,
        "mape": str(recommendation.mape) if recommendation.mape is not None else None,
        "justificacion": recommendation.justificacion,
    }
    prompt = (
        "Redacta una propuesta comercial breve en espanol para un cliente de BuildWise. "
        "Usa exclusivamente los valores del contexto calculado; no cambies importes, decision ni confianza. "
        "Menciona que la proyeccion es estimada y depende del forecast. "
        f"CONTEXTO CALCULADO: {json.dumps(calculated_context, ensure_ascii=True)}."
    )
    user_request = solicitud_original or "Generar propuesta comercial confirmada."
    proposal_text = client.complete([{"role": "system", "content": prompt}, {"role": "user", "content": user_request}])

    return CommercialProposalResult(
        material_id=material.id,
        producto_nombre=material.nombre,
        cantidad=cantidad,
        fase_obra=fase_obra,
        fecha_objetivo_uso=fecha_objetivo_uso,
        horizonte_meses=horizonte,
        tolerancia_riesgo=tolerancia_riesgo,
        presupuesto_maximo=presupuesto_maximo,
        precio_unitario_actual=commercial_price.precio_final_actual,
        total_actual=total_actual,
        precio_unitario_proyectado=commercial_price.precio_final_proyectado,
        total_proyectado=total_proyectado,
        diferencia_estimada=diferencia,
        recomendacion=recommendation,
        propuesta=proposal_text,
        advertencias=tuple(advertencias),
    )
