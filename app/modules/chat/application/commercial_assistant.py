from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, replace
from datetime import date
from decimal import ROUND_DOWN, Decimal, InvalidOperation

from sqlalchemy.orm import Session

from app.modules.catalog.application.utils import derive_material_key
from app.modules.chat.application.service import ChatCompletionClient
from app.modules.chat.domain.exceptions import CommercialInterpretationError, InvalidCommercialRequest
from app.modules.pricing.application.commercial_prices import (
    calcular_precio_comercial,
    obtener_ultima_fecha_forecast_observada,
    obtener_ultima_fecha_precio_observado,
)
from app.modules.pricing.application.contextual_purchase_recommendations import (
    ACCION_COMPRAR_AHORA,
    ACCION_ESCALONAR,
    ContextualPurchaseRecommendationResult,
    recomendar_estrategia_contextual,
    resolver_horizonte_contextual,
)
from app.modules.pricing.domain.exceptions import InsufficientDataException
from app.modules.pricing.domain.repositories import PricingRepository

SUPPORTED_PRODUCT_KEYS = {"cemento-portland", "pastina", "membrana-megaflex"}
VALID_PHASES = {"estructura", "terminaciones", "impermeabilizacion", "general"}
VALID_RISK_LEVELS = {"baja", "media", "alta"}
# The business bought 50 kg bags historically, then switched exclusively to
# 25 kg bags when the former presentation disappeared. Historical records keep
# their actual presentation; current commercial requests use this conversion.
CURRENT_CEMENT_BAG_KG = Decimal("25")


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
    fuente_decision: str = "backend_deterministico"
    propuesta_generada_por: str = "llm_validado"
    fecha_base_calculo: date | None = None


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


def _normalize_decimal_text(value: str) -> str | None:
    cleaned = re.sub(r"[^\d,.-]", "", value.strip())
    if not cleaned:
        return None
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(?:\.\d{3})+", cleaned):
        cleaned = cleaned.replace(".", "")
    elif re.fullmatch(r"\d{1,3}(?:,\d{3})+", cleaned):
        cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    elif cleaned.count(".") > 1:
        cleaned = cleaned.replace(".", "")
    try:
        decimal = Decimal(cleaned)
    except InvalidOperation:
        return None
    normalized = format(decimal.normalize(), "f")
    return normalized.rstrip("0").rstrip(".") if "." in normalized else normalized


def _optional_decimal(value) -> Decimal | None:
    if value in (None, ""):
        return None
    if isinstance(value, Decimal):
        decimal = value
    else:
        normalized = _normalize_decimal_text(str(value))
        if normalized is None:
            raise ValueError("valor numerico invalido")
        try:
            decimal = Decimal(normalized)
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("valor numerico invalido") from exc
    return decimal if decimal > 0 else None


def _extract_decimal_from_text(text: str | None) -> Decimal | None:
    if not text:
        return None
    normalized = _normalize_decimal_text(text)
    if normalized is None:
        return None
    try:
        decimal = Decimal(normalized)
    except (InvalidOperation, ValueError):
        return None
    return decimal if decimal > 0 else None


def _extract_quantity_from_solicitud(solicitud: str | None) -> Decimal | None:
    if not solicitud:
        return None
    normalized = unicodedata.normalize("NFKD", solicitud.lower()).encode("ascii", "ignore").decode("ascii")
    match = re.search(r"\b(\d+(?:[.,]\d+)?)\s*bolsas?\b", normalized)
    if not match:
        match = re.search(r"\b(\d+(?:[.,]\d+)?)\b", normalized)
    return _extract_decimal_from_text(match.group(1) if match else None)


def _extract_bag_count_from_solicitud(solicitud: str | None) -> Decimal | None:
    if not solicitud:
        return None
    normalized = unicodedata.normalize("NFKD", solicitud.lower()).encode("ascii", "ignore").decode("ascii")
    match = re.search(r"\b(\d+(?:[.,]\d+)?)\s*bolsas?\b", normalized)
    return _extract_decimal_from_text(match.group(1) if match else None)


def _extract_budget_from_solicitud(solicitud: str | None) -> Decimal | None:
    if not solicitud:
        return None
    normalized = unicodedata.normalize("NFKD", solicitud.lower()).encode("ascii", "ignore").decode("ascii")
    patterns = (
        r"\bpresupuesto(?:\s+de)?\s*([\d.,]+)\s*(mil|k)?\b",
        r"\btengo\s+([\d.,]+)\s*(mil|k)?\s*(?:pesos|ars)?\b",
        r"\b([\d.,]+)\s*(mil|k)?\s*(?:pesos|ars)\b",
        r"\$\s*([\d.,]+)\s*(mil|k)?\b",
    )
    match = next((re.search(pattern, normalized) for pattern in patterns if re.search(pattern, normalized)), None)
    if match is None:
        return None
    value = _extract_decimal_from_text(match.group(1))
    if value is None:
        return None
    suffix = match.group(2)
    return value * Decimal("1000") if suffix in {"mil", "k"} else value


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


def _solicitud_menciona_anio_explicito(solicitud: str | None) -> bool:
    return bool(solicitud and re.search(r"\b20\d{2}\b", solicitud))


def _normalizar_fecha_objetivo_ambigua(
    *,
    fecha_objetivo_uso: date | None,
    fecha_base_calculo: date | None,
    solicitud_original: str | None,
) -> date | None:
    if fecha_objetivo_uso is None or fecha_base_calculo is None:
        return fecha_objetivo_uso
    if fecha_objetivo_uso > fecha_base_calculo or _solicitud_menciona_anio_explicito(solicitud_original):
        return fecha_objetivo_uso

    year = fecha_base_calculo.year
    while True:
        try:
            candidate = date(year, fecha_objetivo_uso.month, fecha_objetivo_uso.day)
        except ValueError:
            candidate = date(year, fecha_objetivo_uso.month, 28)
        if candidate > fecha_base_calculo:
            return candidate
        year += 1


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
        "Extrae una necesidad de compra para BuildWise. Responde solamente JSON valido con las claves: "
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
        raise CommercialInterpretationError("La IA no devolvio una interpretacion estructurada valida.") from exc

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
        raise CommercialInterpretationError("La IA devolvio importes invalidos.") from exc

    if matched is not None and derive_material_key(matched.nombre) == "cemento-portland":
        cantidad = _extract_bag_count_from_solicitud(solicitud) or cantidad

    if cantidad is None:
        cantidad = _extract_quantity_from_solicitud(solicitud)
    if presupuesto is None:
        presupuesto = _extract_budget_from_solicitud(solicitud)
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


def _mentions_bags(text: str | None) -> bool:
    if not text:
        return False
    return bool(re.search(r"\bbolsas?\b", text.lower()))


def _commercial_quantity_context(*, material, cantidad: Decimal, solicitud_original: str | None) -> tuple[Decimal, str, Decimal | None]:
    material_key = derive_material_key(material.nombre)
    unidad_base = getattr(material, "unidad_base", None)
    if material_key == "cemento-portland" and unidad_base == "kg" and _mentions_bags(solicitud_original):
        cantidad_calculo = cantidad * CURRENT_CEMENT_BAG_KG
        return cantidad_calculo, f"{cantidad} bolsas de 25 kg ({cantidad_calculo} kg)", CURRENT_CEMENT_BAG_KG
    return cantidad, f"{cantidad} {unidad_base or 'unidades'}", None


DECISION_TERMS = {
    "COMPRAR_AHORA": ("comprar ahora", "comprar inmediatamente", "conviene comprar"),
    "POSTERGAR": ("postergar", "esperar", "comprar mas adelante", "comprar más adelante"),
    "ESCALONAR": ("escalonar", "comprar por etapas", "compra escalonada"),
    "SIN_VENTAJA_CLARA": ("sin ventaja clara", "no hay una ventaja clara", "monitorear"),
}


def _normalize_numeric_token(value: str) -> str | None:
    cleaned = re.sub(r"[^\d,.-]", "", value)
    if not cleaned:
        return None
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    try:
        decimal = Decimal(cleaned)
    except InvalidOperation:
        return None
    normalized = format(decimal.normalize(), "f")
    return normalized.rstrip("0").rstrip(".") if "." in normalized else normalized


def _allowed_numeric_values(context: dict) -> set[str]:
    allowed = set()
    for value in context.values():
        if value is None:
            continue
        if isinstance(value, str | int | Decimal):
            normalized = _normalize_numeric_token(str(value))
            if normalized is not None:
                allowed.add(normalized)
    date_values = (context.get("fecha_objetivo_uso"), context.get("fecha_base_calculo"))
    for target_date in date_values:
        if not isinstance(target_date, str):
            continue
        for token in target_date.split("-"):
            normalized = _normalize_numeric_token(token)
            if normalized is not None:
                allowed.add(normalized)
    return allowed


def _llm_proposal_is_safe(text: str, context: dict) -> bool:
    normalized_text = text.lower()
    expected_decision = str(context["accion_recomendada"])
    for decision, terms in DECISION_TERMS.items():
        if decision == expected_decision:
            continue
        if any(term in normalized_text for term in terms):
            return False

    allowed_numbers = _allowed_numeric_values(context)
    for token in re.findall(r"\d+(?:[.,]\d+)?", text):
        normalized = _normalize_numeric_token(token)
        if normalized is not None and normalized not in allowed_numbers:
            return False
    return True


def _deterministic_proposal(context: dict) -> str:
    parts = [
        f"Para {context.get('cantidad_label') or context['cantidad']} de {context['producto']}, BuildWise calculo la decision {context['accion_recomendada']}.",
    ]
    if context.get("total_actual") is not None:
        parts.append(f"El total actual estimado es ARS {context['total_actual']}.")
    if context.get("total_proyectado") is not None:
        parts.append(f"El total proyectado para el horizonte evaluado es ARS {context['total_proyectado']}.")
    if context.get("diferencia_estimada") is not None:
        parts.append(f"La diferencia estimada es ARS {context['diferencia_estimada']}.")
    if context.get("mape") is not None:
        parts.append(f"La confianza se informa como {context['confianza']} con MAPE {context['mape']}%.")
    parts.append(str(context["justificacion"]))
    return " ".join(parts)


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
        raise InvalidCommercialRequest("El producto no pertenece al alcance de compra del MVP.")

    try:
        fecha_base_calculo = obtener_ultima_fecha_forecast_observada(
            material=material,
            pricing_repo=pricing_repo,
            horizonte_meses=1,
            usar_selector_modelo=usar_selector_modelo,
        )
    except (AttributeError, InsufficientDataException):
        try:
            fecha_base_calculo = obtener_ultima_fecha_precio_observado(pricing_repo, material.id)
        except AttributeError:
            fecha_base_calculo = None
    fecha_objetivo_resuelta = _normalizar_fecha_objetivo_ambigua(
        fecha_objetivo_uso=fecha_objetivo_uso,
        fecha_base_calculo=fecha_base_calculo,
        solicitud_original=solicitud_original,
    )
    horizonte = resolver_horizonte_contextual(
        horizonte_meses=horizonte_meses,
        fecha_objetivo_uso=fecha_objetivo_resuelta,
        hoy=fecha_base_calculo,
    )
    cantidad_calculo, cantidad_label, factor_bolsa_kg = _commercial_quantity_context(
        material=material,
        cantidad=cantidad,
        solicitud_original=solicitud_original,
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
        cantidad_objetivo=cantidad_calculo,
        horizonte_meses=horizonte if fecha_objetivo_resuelta is None else None,
        fecha_objetivo_uso=fecha_objetivo_resuelta,
        hoy=fecha_base_calculo,
        pricing_repo=pricing_repo,
        usar_selector_modelo=usar_selector_modelo,
    )
    fecha_base_calculo = (
        getattr(commercial_price, "ultima_fecha_observada", None)
        or getattr(recommendation, "fecha_base_observada", None)
        or fecha_base_calculo
    )
    total_actual = _total(commercial_price.precio_final_actual, cantidad_calculo)
    total_proyectado = _total(commercial_price.precio_final_proyectado, cantidad_calculo)
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
        precio_unidad_compra = (
            commercial_price.precio_final_actual * factor_bolsa_kg
            if factor_bolsa_kg is not None
            else commercial_price.precio_final_actual
        )
        cantidad_cubierta = (presupuesto_maximo / precio_unidad_compra).quantize(
            Decimal("0.0001"),
            rounding=ROUND_DOWN,
        )
        unidad_cubierta = "bolsas" if factor_bolsa_kg is not None else "unidades"
        recommendation = replace(
            recommendation,
            decision=ACCION_ESCALONAR,
            justificacion=(
                f"La senal de precio favorece comprar ahora, pero el presupuesto maximo de ARS {presupuesto_maximo} "
                f"no cubre las {cantidad_label}. Se recomienda escalonar: permite adquirir hasta "
                f"{cantidad_cubierta} {unidad_cubierta} al precio vigente."
            ),
        )
        advertencias.append("La compra inmediata completa supera el presupuesto maximo informado.")
    calculated_context = {
        "producto": material.nombre,
        "cantidad": str(cantidad),
        "cantidad_label": cantidad_label,
        "cantidad_calculo": str(cantidad_calculo),
        "unidad_calculo": getattr(material, "unidad_base", None),
        "fase_obra": fase_obra,
        "horizonte_meses": horizonte,
        "fecha_base_calculo": fecha_base_calculo.isoformat() if fecha_base_calculo else None,
        "fecha_objetivo_uso": fecha_objetivo_resuelta.isoformat() if fecha_objetivo_resuelta else None,
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
        "Redacta una propuesta de compra breve en espanol para un comprador de BuildWise. "
        "Usa exclusivamente los valores del contexto calculado; no cambies importes, decision ni confianza. "
        "Cuando menciones comprar ahora, aclaralo como compra al ultimo precio real observado en fecha_base_calculo, no como fecha calendario de hoy. "
        "No agregues numeros que no esten en el contexto. Si falta un valor, indica que no esta disponible. "
        "Menciona que la proyeccion es estimada y depende del forecast. "
        f"CONTEXTO CALCULADO: {json.dumps(calculated_context, ensure_ascii=True)}."
    )
    user_request = solicitud_original or "Generar propuesta de compra confirmada."
    proposal_text = client.complete([{"role": "system", "content": prompt}, {"role": "user", "content": user_request}])
    propuesta_generada_por = "llm_validado"
    if not _llm_proposal_is_safe(proposal_text, calculated_context):
        proposal_text = _deterministic_proposal(calculated_context)
        propuesta_generada_por = "backend_deterministico"
        advertencias.append("La redaccion generativa fue reemplazada por una explicacion deterministica del backend.")

    return CommercialProposalResult(
        material_id=material.id,
        producto_nombre=material.nombre,
        cantidad=cantidad,
        fase_obra=fase_obra,
        fecha_objetivo_uso=fecha_objetivo_resuelta,
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
        propuesta_generada_por=propuesta_generada_por,
        fecha_base_calculo=fecha_base_calculo,
    )
