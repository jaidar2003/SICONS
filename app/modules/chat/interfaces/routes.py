import re
import unicodedata
from collections import Counter
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal
from math import ceil
from time import perf_counter

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.modules.auth.infrastructure.models import Usuario
from app.modules.auth.interfaces.dependencies import get_current_user
from app.modules.catalog.domain.repositories import MaterialRepository
from app.modules.catalog.infrastructure.models import Fuente, Presentacion
from app.modules.catalog.interfaces.dependencies import get_material_repository
from app.modules.chat.application.commercial_assistant import (
    generar_propuesta_comercial,
    interpretar_necesidad_comercial,
)
from app.modules.chat.application.context import build_material_context, resolve_horizon
from app.modules.chat.application.operations import (
    execute_operation,
    is_explicit_confirmation,
    needs_operation_plan,
    plan_operation,
)
from app.modules.chat.application.retrieval import (
    build_backend_retrieval_context,
    classify_chat_intent,
    suggest_visualization,
)
from app.modules.chat.application.service import (
    ADMIN_ONLY_RESPONSE,
    ChatCompletionClient,
    answer_question,
    is_admin_only_request,
    is_in_scope,
)
from app.modules.chat.domain.exceptions import CommercialInterpretationError, InvalidCommercialRequest
from app.modules.chat.infrastructure import provider_config
from app.modules.chat.infrastructure.llm_client import (
    AnthropicChatClient,
    FallbackChatClient,
    LLMConfigurationError,
    LLMProviderError,
    OpenAICompatibleChatClient,
)
from app.modules.chat.infrastructure.models import ChatMessage, ChatProviderSetting
from app.modules.chat.infrastructure.provider_config import (
    LAST_PROVIDER_STATUS as _LAST_PROVIDER_STATUS,
)
from app.modules.chat.infrastructure.provider_config import (
    apply_chat_config as _apply_chat_config,
)
from app.modules.chat.infrastructure.provider_config import chat_config_from_settings
from app.modules.chat.infrastructure.provider_config import fallback_enabled as _fallback_enabled_from_settings
from app.modules.chat.infrastructure.provider_config import provider_configured as _provider_configured
from app.modules.chat.infrastructure.provider_config import provider_model as _provider_model_from_settings
from app.modules.chat.infrastructure.provider_config import read_persisted_chat_config as _read_persisted_chat_config
from app.modules.chat.infrastructure.provider_config import remember_provider_error as _remember_provider_error
from app.modules.chat.infrastructure.provider_config import remember_provider_success as _remember_provider_success
from app.modules.chat.infrastructure.provider_config import resolve_provider_metadata as _resolve_provider_metadata
from app.modules.chat.infrastructure.provider_config import settings_provider_key as _settings_provider_key
from app.modules.chat.interfaces.audit_routes import build_audit_router
from app.modules.chat.interfaces.conversation_routes import (
    conversation_history as _conversation_history,
)
from app.modules.chat.interfaces.conversation_routes import (
    get_owned_conversation as _get_owned_conversation,
)
from app.modules.chat.interfaces.conversation_routes import (
    latest_assistant_message as _latest_assistant_message,
)
from app.modules.chat.interfaces.conversation_routes import (
    persist_conversation_turn as _persist_conversation_turn,
)
from app.modules.chat.interfaces.conversation_routes import (
    router as conversation_router,
)
from app.modules.chat.interfaces.schemas import (
    ChatAuditLogRead,
    ChatAuditMetricsRead,
    ChatDeterminismCanonicalItemRead,
    ChatDeterminismCanonicalReportRead,
    ChatDeterminismGroupRead,
    ChatDeterminismReportRead,
    ChatProviderConfigRead,
    ChatProviderConfigUpdate,
    ChatProviderStatusRead,
    ChatQueryCreate,
    ChatResponseRead,
    CommercialNeedCreate,
    CommercialNeedInterpretationRead,
    CommercialProposalCreate,
    CommercialProposalRead,
)
from app.modules.pricing.application.forecast_service import forecast_material, serie_mensual_material
from app.modules.pricing.application.purchase_recommendations import recomendar_momento_compra
from app.modules.pricing.domain.repositories import PricingRepository
from app.modules.pricing.infrastructure.models import CommercialMargin
from app.modules.pricing.interfaces.dependencies import get_pricing_repository
from app.shared.database.audit_models import AuditLog
from app.shared.database.audit_service import register_audit_log
from app.shared.database.session import get_db

router = APIRouter(prefix="/chat", tags=["chat"])
router.include_router(conversation_router)
settings = provider_config.settings


def _chat_config_from_settings() -> dict[str, str | None]:
    return chat_config_from_settings()

def _semantic_question_for_conversation(question: str, latest_assistant: ChatMessage | None) -> str:
    if latest_assistant is None:
        return question
    normalized = unicodedata.normalize("NFKD", question.lower()).encode("ascii", "ignore").decode("ascii")
    mentions_forecast = any(
        token in normalized
        for token in ("forecast", "proyeccion", "proyectado", "conviene", "recomendacion", "comprar", "esperar")
    )
    if mentions_forecast:
        return question
    previous_intent = latest_assistant.tipo_intencion
    horizon_follow_up = re.search(r"\b(ahora|mes|meses|horizonte|3|6|12)\b", normalized)
    if horizon_follow_up and previous_intent in {"FORECAST", "RECOMENDACION"}:
        inherited_intent = "forecast" if previous_intent == "FORECAST" else "recomendacion"
        return f"{question} {inherited_intent}"
    previous_visualization = latest_assistant.visualizacion_sugerida or {}
    previous_type = previous_visualization.get("tipo")
    if previous_type in {"FORECAST", "PRICE_HISTORY_FORECAST"} and re.search(r"\b(ahora|mostra|mostrame|ver|grafica|graficame|mes|meses|horizonte|12|6|3)\b", normalized):
        return f"{question} forecast"
    return question


def _requires_calculated_material_context(question: str) -> bool:
    normalized = question.lower()
    triggers = (
        "forecast",
        "proyeccion",
        "proyección",
        "proyectado",
        "conviene",
        "recomendacion",
        "recomendación",
        "comprar",
        "esperar",
        "mape",
        "mae",
        "confiabilidad",
        "decision",
        "decisión",
    )
    return any(trigger in normalized for trigger in triggers)


def _historical_display_horizon(intent: str | None, horizon: int | None) -> int | None:
    return None if intent == "HISTORICO" else horizon


def _latest_price_answer(
    *,
    question: str,
    material_name: str | None,
    source_evidence: list[dict],
) -> str | None:
    for source in source_evidence:
        if source.get("source") != "precios_historicos":
            continue
        records = source.get("records") or []
        if not records:
            return None
        latest = records[0]
        price = latest.get("precio_normalizado")
        unit = latest.get("unidad_base")
        observed_date = latest.get("fecha")
        source_name = latest.get("fuente") or "sin fuente"
        if not price or not unit or not observed_date:
            return None
        material_label = material_name or "el material"
        normalized_question = unicodedata.normalize("NFKD", question.lower()).encode("ascii", "ignore").decode("ascii")
        requested_kg = None
        if re.search(r"\b25\s*(kg|kilos?)\b", normalized_question) or "bolsa de 25" in normalized_question:
            requested_kg = Decimal("25")
        elif re.search(r"\b50\s*(kg|kilos?)\b", normalized_question) or "bolsa de 50" in normalized_question:
            requested_kg = Decimal("50")
        elif "bolsa" in normalized_question and "cemento" in normalized_question:
            requested_kg = Decimal("25")

        if requested_kg is not None and unit == "kg":
            bag_price = (Decimal(str(price)) * requested_kg).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            return (
                f"El ultimo precio observado de la bolsa de {requested_kg.normalize()} kg de {material_label}, "
                f"antes de las predicciones de Prophet, es ARS {bag_price}. "
                f"Surge de ARS {price} por kg, registrado el {observed_date}. "
                f"Fuente: {source_name}."
            )

        return (
            f"El ultimo precio observado de {material_label}, antes de las predicciones de Prophet, "
            f"es ARS {price} por {unit}, registrado el {observed_date}. "
            f"Fuente: {source_name}."
        )
    return None


def _catalog_direct_answer(
    *,
    question: str,
    material,
    material_repo: MaterialRepository,
    db: Session,
) -> str | None:
    normalized = unicodedata.normalize("NFKD", question.lower()).encode("ascii", "ignore").decode("ascii")
    if material is None and re.search(r"\b(materiales|catalogo|productos)\b", normalized):
        materials = material_repo.list_active()
        if not materials:
            return "No hay materiales activos cargados en BuildWise."
        items = ", ".join(f"{item.nombre} ({item.unidad_base})" for item in materials[:12])
        suffix = f" Hay {len(materials) - 12} materiales activos adicionales." if len(materials) > 12 else ""
        return f"Materiales activos disponibles en BuildWise: {items}.{suffix}"

    if material is None:
        return None

    presentations = list(
        db.scalars(
            select(Presentacion)
            .where(Presentacion.material_id == material.id, Presentacion.activa.is_(True))
            .order_by(Presentacion.id.asc())
        )
    )
    if re.search(r"\b(unidad|unidad base|kg|kilo|presentacion|presentaciones|bolsa|bolsas)\b", normalized):
        lines = [f"{material.nombre} usa como unidad base: {material.unidad_base}."]
        if presentations:
            formatted = "; ".join(
                f"{presentation.nombre_presentacion}: {presentation.cantidad_base.normalize()} {presentation.unidad_presentacion}"
                for presentation in presentations
            )
            lines.append(f"Presentaciones activas: {formatted}.")
        else:
            lines.append("No tiene presentaciones activas registradas.")
        return " ".join(lines)
    return None


def _calculated_direct_answer(
    *,
    question: str,
    intent: str | None,
    material,
    horizon: int | None,
    pricing_repo: PricingRepository,
) -> str | None:
    if material is None or horizon is None:
        return None
    normalized = unicodedata.normalize("NFKD", question.lower()).encode("ascii", "ignore").decode("ascii")
    if intent == "FORECAST" or re.search(r"\b(forecast|proyeccion|proyectado|mape|confiabilidad)\b", normalized):
        try:
            result = forecast_material(material, horizon, pricing_repo, usar_selector_modelo=True)
        except Exception:
            return None
        if not result.forecast or not result.dataset:
            return None
        latest = result.dataset[-1]
        target = result.forecast[-1]
        mape = getattr(result.metricas, "mape", None)
        confidence = getattr(getattr(result, "seleccion_modelo", None), "confiabilidad", None)
        details = [
            f"Forecast de {material.nombre} a {horizon} meses:",
            f"ultimo observado ARS {Decimal(f'{latest.y:.2f}')} por {material.unidad_base} el {latest.ds};",
            f"precio proyectado ARS {target.precio_proyectado} por {material.unidad_base} para {target.fecha}.",
        ]
        if confidence:
            details.append(f"Confiabilidad: {confidence}.")
        if mape is not None:
            details.append(f"MAPE: {mape}%.")
        return " ".join(details)

    if intent == "RECOMENDACION" or re.search(r"\b(conviene|recomendacion|comprar|esperar|decision)\b", normalized):
        try:
            recommendation = recomendar_momento_compra(
                material,
                horizon,
                "media",
                Decimal("1"),
                pricing_repo,
                usar_selector_modelo=True,
            )
        except Exception:
            return None
        parts = [
            f"Decision para {material.nombre} a {horizon} meses: {recommendation.decision}.",
            f"Confiabilidad: {recommendation.confiabilidad}.",
            recommendation.justificacion,
        ]
        if recommendation.precio_actual is not None and recommendation.precio_proyectado_horizonte is not None:
            fecha_base = getattr(recommendation, "fecha_base_observada", None)
            fecha_base_text = f" observado el {fecha_base}" if fecha_base is not None else ""
            parts.append(
                f"Ultimo precio real{fecha_base_text}: ARS {recommendation.precio_actual}; "
                f"proyectado al horizonte: ARS {recommendation.precio_proyectado_horizonte} por {material.unidad_base}."
            )
        if recommendation.variacion_esperada_pct is not None:
            parts.append(f"Variacion esperada: {recommendation.variacion_esperada_pct}%.")
        return " ".join(parts)
    return None


def _parse_demo_budget(question: str) -> Decimal | None:
    normalized = unicodedata.normalize("NFKD", question.lower()).encode("ascii", "ignore").decode("ascii")
    patterns = (
        r"\bpresupuesto(?:\s+de)?\s*(\d+(?:[.,]\d+)?)\s*(mil|k)?\b",
        r"\btengo\s+(\d+(?:[.,]\d+)?)\s*(mil|k)?\s*(?:pesos|ars)?\b",
        r"\b(\d+(?:[.,]\d+)?)\s*(mil|k)?\s*(?:pesos|ars)\b",
        r"\$\s*(\d+(?:[.,]\d+)?)\s*(mil|k)?\b",
    )
    match = next((re.search(pattern, normalized) for pattern in patterns if re.search(pattern, normalized)), None)
    if not match:
        return None
    raw_value = match.group(1)
    if "," in raw_value and "." in raw_value:
        raw_value = raw_value.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(?:\.\d{3})+", raw_value):
        raw_value = raw_value.replace(".", "")
    elif re.fullmatch(r"\d{1,3}(?:,\d{3})+", raw_value):
        raw_value = raw_value.replace(",", "")
    elif "," in raw_value:
        raw_value = raw_value.replace(",", ".")
    elif raw_value.count(".") > 1:
        raw_value = raw_value.replace(".", "")
    value = Decimal(raw_value)
    suffix = match.group(2)
    return value * Decimal("1000") if suffix in {"mil", "k"} else value


def _parse_bag_quantity(question: str) -> Decimal | None:
    normalized = unicodedata.normalize("NFKD", question.lower()).encode("ascii", "ignore").decode("ascii")
    match = re.search(r"\b(\d+(?:[.,]\d+)?)\s*bolsas?\b", normalized)
    if not match:
        return None
    raw_value = match.group(1)
    if "," in raw_value and "." in raw_value:
        raw_value = raw_value.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(?:\.\d{3})+", raw_value):
        raw_value = raw_value.replace(".", "")
    elif re.fullmatch(r"\d{1,3}(?:,\d{3})+", raw_value):
        raw_value = raw_value.replace(",", "")
    elif "," in raw_value:
        raw_value = raw_value.replace(",", ".")
    elif raw_value.count(".") > 1:
        raw_value = raw_value.replace(".", "")
    return Decimal(raw_value)


def _format_money(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}"


def _format_decimal_plain(value: Decimal) -> str:
    text = format(value.normalize(), "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def _demo_budget_purchase_answer(*, question: str, material, horizon: int, pricing_repo: PricingRepository) -> str | None:
    normalized = unicodedata.normalize("NFKD", question.lower()).encode("ascii", "ignore").decode("ascii")
    if "cemento" not in normalized or not re.search(r"\b(?:compr\w*|comr\w*)\b", normalized):
        return None
    if not ("bolsa" in normalized and ("presupuesto" in normalized or "pesos" in normalized or "$" in normalized)):
        return None
    bags = _parse_bag_quantity(question)
    budget = _parse_demo_budget(question)
    if material is None or bags is None or budget is None:
        return None

    result = forecast_material(material, horizon, pricing_repo, usar_selector_modelo=True)
    if not result.dataset or not result.forecast:
        return None
    latest = result.dataset[-1]
    target = result.forecast[-1]
    confidence = getattr(getattr(result, "seleccion_modelo", None), "confiabilidad", None) or "no_disponible"
    mape = getattr(result.metricas, "mape", None)

    bag_kg = Decimal("25")
    quantity_kg = bags * bag_kg if getattr(material, "unidad_base", None) == "kg" else bags
    current_unit = Decimal(f"{latest.y:.2f}")
    projected_unit = target.precio_proyectado
    current_bag = (current_unit * bag_kg).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    projected_bag = (projected_unit * bag_kg).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    total_now = (current_unit * quantity_kg).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    total_future = (projected_unit * quantity_kg).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    diff = (total_future - total_now).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    if total_now <= budget and diff > 0:
        decision = "Conviene comprarlas ahora."
        budget_line = f"El presupuesto de ARS {_format_money(budget)} alcanza para cubrir la compra completa al ultimo precio real."
    elif total_now > budget:
        affordable_bags = (budget / current_bag).quantize(Decimal("1"), rounding=ROUND_DOWN) if current_bag > 0 else Decimal("0")
        decision = "La senal de precio favorece comprar ahora, pero el presupuesto no alcanza para las 30 bolsas completas."
        budget_line = (
            f"Con ARS {_format_money(budget)} podrias comprar aproximadamente {affordable_bags} bolsas al ultimo precio real; "
            "para la compra completa conviene escalonar o aumentar presupuesto."
        )
    elif diff < 0:
        decision = "El forecast permite esperar, porque el costo proyectado baja frente al ultimo precio real."
        budget_line = f"El presupuesto de ARS {_format_money(budget)} alcanza para comprar ahora, pero el escenario proyectado es menor."
    else:
        decision = "No hay una ventaja economica clara; conviene monitorear antes de decidir."
        budget_line = f"El presupuesto de ARS {_format_money(budget)} se compara contra un total actual de ARS {_format_money(total_now)}."

    return (
        f"{decision} Base de calculo: ultimo precio real observado el {latest.ds}, no la fecha de hoy. "
        f"Asumo bolsa de 25 kg: {_format_decimal_plain(bags)} bolsas = {_format_decimal_plain(quantity_kg)} kg. "
        f"Precio actual por bolsa: ARS {_format_money(current_bag)}; proyectado a {horizon} meses ({target.fecha}): "
        f"ARS {_format_money(projected_bag)}. Total ahora: ARS {_format_money(total_now)}; total proyectado: "
        f"ARS {_format_money(total_future)}; diferencia estimada: ARS {_format_money(diff)}. "
        f"{budget_line} Confiabilidad del forecast: {confidence}"
        f"{f'; MAPE: {mape}%' if mape is not None else ''}."
    )


def _demo_cement_forecast_answer(*, question: str, material, horizon: int, pricing_repo: PricingRepository) -> str | None:
    normalized = unicodedata.normalize("NFKD", question.lower()).encode("ascii", "ignore").decode("ascii")
    if material is None or "cemento" not in normalized or "forecast" not in normalized:
        return None
    if not ("mape" in normalized and "confiabilidad" in normalized and ("recomendacion" in normalized or "decision" in normalized)):
        return None

    forecast = forecast_material(material, horizon, pricing_repo, usar_selector_modelo=True)
    recommendation = recomendar_momento_compra(
        material,
        horizon,
        "media",
        Decimal("1"),
        pricing_repo,
        usar_selector_modelo=True,
    )
    if not forecast.dataset or not forecast.forecast:
        return None
    latest = forecast.dataset[-1]
    target = forecast.forecast[-1]
    selection = getattr(forecast, "seleccion_modelo", None)
    confidence = getattr(selection, "confiabilidad", None) or recommendation.confiabilidad
    model = getattr(selection, "modelo_resuelto", None) or forecast.modelo
    mape = getattr(forecast.metricas, "mape", None)

    return (
        f"Analisis BuildWise de {material.nombre} a {horizon} meses. "
        f"Fecha base: ultimo precio real observado el {latest.ds}. "
        f"Precio base: ARS {Decimal(f'{latest.y:.2f}')} por {material.unidad_base}. "
        f"Forecast al {target.fecha}: ARS {target.precio_proyectado} por {material.unidad_base}. "
        f"MAPE: {mape}% sobre {forecast.metricas.folds} folds. "
        f"Confiabilidad: {confidence}. Modelo usado: {model}. "
        f"Recomendacion de decision: {recommendation.decision}. {recommendation.justificacion}"
    )


def _demo_cement_anomaly_answer(*, question: str, material, pricing_repo: PricingRepository) -> str | None:
    normalized = unicodedata.normalize("NFKD", question.lower()).encode("ascii", "ignore").decode("ascii")
    if material is None or "cemento" not in normalized or not re.search(r"\banomalia|anomalias\b", normalized):
        return None
    serie = serie_mensual_material(material, pricing_repo)
    anomalies = [point for point in serie if getattr(point, "es_anomalia", False)]
    dates = ", ".join(
        f"{point.fecha.isoformat()} ({getattr(point, 'severidad_anomalia', None) or 'sin severidad'})"
        for point in anomalies[:5]
    )
    detail = f" Fechas detectadas: {dates}." if dates else " No hay fechas marcadas como anomalas en la serie mensual evaluada."
    return (
        f"BuildWise detecta {len(anomalies)} anomalias en la serie mensual historica usada para el forecast de {material.nombre}."
        f"{detail} Una anomalia es un punto historico cuyo precio se aleja del rango esperado por el detector "
        "estadistico/Random Forest: puede ser un salto, caida o valor atipico frente a la tendencia y variables del material. "
        "No significa automaticamente que el dato sea falso; significa que debe revisarse porque puede afectar la confianza del forecast."
    )


def _demo_direct_answer(
    *,
    question: str,
    intent: str | None,
    material,
    horizon: int | None,
    pricing_repo: PricingRepository,
) -> str | None:
    if material is None:
        return None
    effective_horizon = horizon or 3
    for builder in (
        lambda: _demo_budget_purchase_answer(
            question=question,
            material=material,
            horizon=effective_horizon,
            pricing_repo=pricing_repo,
        ),
        lambda: _demo_cement_forecast_answer(
            question=question,
            material=material,
            horizon=effective_horizon,
            pricing_repo=pricing_repo,
        ),
        lambda: _demo_cement_anomaly_answer(
            question=question,
            material=material,
            pricing_repo=pricing_repo,
        ),
    ):
        answer = builder()
        if answer is not None:
            return answer
    return None


def get_chat_client() -> ChatCompletionClient:
    config = _read_persisted_chat_config()
    _apply_chat_config(config)
    if config["proveedor_activo"] == "claude":
        primary = AnthropicChatClient(model=config.get("modelo_claude"))
        fallback = OpenAICompatibleChatClient(model=config.get("modelo_facultad"))
        return FallbackChatClient(primary, fallback)
    primary = OpenAICompatibleChatClient(model=config.get("modelo_facultad"))
    fallback = AnthropicChatClient(model=config.get("modelo_claude"))
    return FallbackChatClient(primary, fallback)


def _provider_key_from_settings() -> str:
    return _settings_provider_key()


def _audit_changes(log: AuditLog) -> dict:
    return log.cambios if isinstance(log.cambios, dict) else {}


def _audit_log_read(log: AuditLog, username: str | None) -> ChatAuditLogRead:
    changes = _audit_changes(log)
    raw_sources = changes.get("fuentes_recuperadas") or []
    sources = raw_sources if isinstance(raw_sources, list) else []
    return ChatAuditLogRead(
        id=log.id,
        created_at=log.created_at,
        usuario_id=log.usuario_id,
        username=username,
        pregunta=changes.get("pregunta"),
        respuesta=changes.get("respuesta"),
        aceptada=changes.get("aceptada"),
        tipo_intencion=changes.get("tipo_intencion"),
        contexto_usado=changes.get("contexto_usado"),
        fuentes_recuperadas=sources,
        material_resuelto=changes.get("material_resuelto"),
        material_resolution_source=changes.get("material_resolution_source"),
        horizonte_resuelto=changes.get("horizonte_resuelto"),
        proveedor_ia=changes.get("proveedor_ia"),
        fallback_usado=changes.get("fallback_usado"),
        duration_ms=changes.get("duration_ms"),
        ip_address=log.ip_address,
    )


DETERMINISM_FIELDS = (
    "tipo_intencion",
    "material_resuelto",
    "horizonte_resuelto",
    "fuentes_recuperadas",
    "contexto_usado",
    "fallback_usado",
)

CANONICAL_DETERMINISM_BATTERY = (
    {
        "pregunta": "cual fue el ultimo precio de cemento?",
        "tipo_intencion": "HISTORICO",
        "material_resuelto": "Cemento Portland",
        "horizonte_resuelto": None,
        "fuentes_esperadas": ("catalogo.materiales", "precios_historicos"),
    },
    {
        "pregunta": "explicame el forecast de cemento",
        "tipo_intencion": "FORECAST",
        "material_resuelto": "Cemento Portland",
        "horizonte_resuelto": 3,
        "fuentes_esperadas": ("purchase_recommendations",),
    },
    {
        "pregunta": "me conviene comprar cemento?",
        "tipo_intencion": "RECOMENDACION",
        "material_resuelto": "Cemento Portland",
        "horizonte_resuelto": 3,
        "fuentes_esperadas": ("purchase_recommendations",),
    },
    {
        "pregunta": "necesito comprar 500 kg de cemento",
        "tipo_intencion": "PRESUPUESTO",
        "material_resuelto": "Cemento Portland",
        "horizonte_resuelto": 3,
        "fuentes_esperadas": ("presupuestacion.propuesta", "backend_deterministico"),
    },
    {
        "pregunta": "que materiales hay?",
        "tipo_intencion": "CATALOGO",
        "material_resuelto": None,
        "horizonte_resuelto": 3,
        "fuentes_esperadas": ("catalogo.materiales", "catalogo.presentaciones"),
    },
    {
        "pregunta": "lista usuarios",
        "tipo_intencion": "ADMIN",
        "material_resuelto": None,
        "horizonte_resuelto": 3,
        "fuentes_esperadas": ("operacion.list_users",),
    },
)


def _normalize_audit_question(question: str | None) -> str:
    normalized = unicodedata.normalize("NFKD", question or "").encode("ascii", "ignore").decode("ascii")
    normalized = re.sub(r"\s+", " ", normalized.lower()).strip()
    normalized = re.sub(r"[^\w\s]", "", normalized)
    return normalized


def _determinism_value(changes: dict, field: str):
    value = changes.get(field)
    if field == "fuentes_recuperadas":
        if not isinstance(value, list):
            return ()
        return tuple(sorted(str(item) for item in value))
    return value


def _iter_audit_changes(logs: list[AuditLog]) -> list[dict]:
    return [_audit_changes(log) for log in logs]


def _build_determinism_report(logs: list[AuditLog], limit_groups: int = 20) -> ChatDeterminismReportRead:
    grouped: dict[str, list[AuditLog]] = {}
    for log in logs:
        question_key = _normalize_audit_question(_audit_changes(log).get("pregunta"))
        if question_key:
            grouped.setdefault(question_key, []).append(log)

    repeated_groups = {question: items for question, items in grouped.items() if len(items) >= 2}
    groups: list[ChatDeterminismGroupRead] = []
    total_score = 0.0

    for question, items in repeated_groups.items():
        stable_fields: list[str] = []
        variable_fields: list[str] = []
        first_changes = _audit_changes(items[0])
        for field in DETERMINISM_FIELDS:
            values = {_determinism_value(_audit_changes(item), field) for item in items}
            if len(values) == 1:
                stable_fields.append(field)
            else:
                variable_fields.append(field)
        score = round(len(stable_fields) / len(DETERMINISM_FIELDS), 4)
        total_score += score
        groups.append(
            ChatDeterminismGroupRead(
                pregunta_normalizada=question,
                muestra=len(items),
                score=score,
                campos_estables=stable_fields,
                campos_variables=variable_fields,
                pregunta_ejemplo=first_changes.get("pregunta"),
                tipo_intencion=first_changes.get("tipo_intencion"),
                material_resuelto=first_changes.get("material_resuelto"),
                horizonte_resuelto=first_changes.get("horizonte_resuelto"),
                fuentes_recuperadas=list(_determinism_value(first_changes, "fuentes_recuperadas")),
            )
        )

    groups.sort(key=lambda item: (item.score, -item.muestra, item.pregunta_normalizada))
    score_promedio = round(total_score / len(groups), 4) if groups else None
    return ChatDeterminismReportRead(
        total_consultas=len(logs),
        grupos_repetidos=len(repeated_groups),
        consultas_evaluadas=sum(len(items) for items in repeated_groups.values()),
        score_promedio=score_promedio,
        campos_evaluados=list(DETERMINISM_FIELDS),
        grupos=groups[:limit_groups],
    )


def _build_chat_metrics(logs: list[AuditLog]) -> ChatAuditMetricsRead:
    changes_list = _iter_audit_changes(logs)
    durations = [
        int(changes.get("duration_ms"))
        for changes in changes_list
        if isinstance(changes.get("duration_ms"), int | float)
    ]
    intent_counter = Counter(
        str(changes.get("tipo_intencion") or "SIN_INTENCION")
        for changes in changes_list
    )
    total = len(logs)
    fallback_count = sum(1 for changes in changes_list if bool(changes.get("fallback_usado")))
    out_of_scope = sum(1 for changes in changes_list if changes.get("tipo_intencion") == "FUERA_ALCANCE")
    user_ids = {log.usuario_id for log in logs if log.usuario_id is not None}
    avg_duration = round(sum(durations) / len(durations), 2) if durations else None
    p95_duration = None
    if durations:
        ordered = sorted(durations)
        p95_index = max(0, ceil(0.95 * len(ordered)) - 1)
        p95_duration = float(ordered[p95_index])
    return ChatAuditMetricsRead(
        total_consultas=total,
        consultas_fuera_de_alcance=out_of_scope,
        tasa_fallback=round(fallback_count / total, 4) if total else 0.0,
        latencia_promedio_ms=avg_duration,
        latencia_p95_ms=p95_duration,
        consultas_por_intencion=dict(intent_counter),
        usuarios_unicos=len(user_ids),
    )


def _build_canonical_determinism_report(logs: list[AuditLog]) -> ChatDeterminismCanonicalReportRead:
    grouped: dict[str, list[AuditLog]] = {}
    for log in logs:
        question = _normalize_audit_question(_audit_changes(log).get("pregunta"))
        if question:
            grouped.setdefault(question, []).append(log)

    cases: list[ChatDeterminismCanonicalItemRead] = []
    score_total = 0.0
    evidence_count = 0
    for canonical in CANONICAL_DETERMINISM_BATTERY:
        question_key = _normalize_audit_question(canonical["pregunta"])
        items = grouped.get(question_key, [])
        evidence_count += 1 if items else 0
        changes_list = [_audit_changes(item) for item in items]
        if changes_list:
            first = changes_list[0]
            stable_fields: list[str] = []
            variable_fields: list[str] = []
            for field in DETERMINISM_FIELDS:
                values = {_determinism_value(changes, field) for changes in changes_list}
                if len(values) == 1:
                    stable_fields.append(field)
                else:
                    variable_fields.append(field)
            observed_intent = first.get("tipo_intencion")
            observed_material = first.get("material_resuelto")
            observed_horizon = first.get("horizonte_resuelto")
            observed_sources = list(_determinism_value(first, "fuentes_recuperadas"))
            score = 0.0
            comparisons = 0
            if canonical["tipo_intencion"]:
                comparisons += 1
                score += 1 if observed_intent == canonical["tipo_intencion"] else 0
            if canonical["material_resuelto"] is not None:
                comparisons += 1
                score += 1 if observed_material == canonical["material_resuelto"] else 0
            if canonical["horizonte_resuelto"] is not None:
                comparisons += 1
                score += 1 if observed_horizon == canonical["horizonte_resuelto"] else 0
            if canonical["fuentes_esperadas"]:
                comparisons += 1
                score += 1 if set(canonical["fuentes_esperadas"]).issubset(set(observed_sources)) else 0
            score = round(score / comparisons, 4) if comparisons else 0.0
            score_total += score
            cases.append(
                ChatDeterminismCanonicalItemRead(
                    pregunta=canonical["pregunta"],
                    muestra=len(items),
                    score=score,
                    cumple_expectativa=score >= 1,
                    tipo_intencion_esperada=canonical["tipo_intencion"],
                    tipo_intencion_observada=observed_intent,
                    material_esperado=canonical["material_resuelto"],
                    material_observado=observed_material,
                    horizonte_esperado=canonical["horizonte_resuelto"],
                    horizonte_observado=observed_horizon,
                    fuentes_esperadas=list(canonical["fuentes_esperadas"]),
                    fuentes_observadas=observed_sources,
                    campos_estables=stable_fields,
                    campos_variables=variable_fields,
                )
            )
        else:
            cases.append(
                ChatDeterminismCanonicalItemRead(
                    pregunta=canonical["pregunta"],
                    muestra=0,
                    score=0.0,
                    cumple_expectativa=False,
                    tipo_intencion_esperada=canonical["tipo_intencion"],
                    material_esperado=canonical["material_resuelto"],
                    horizonte_esperado=canonical["horizonte_resuelto"],
                    fuentes_esperadas=list(canonical["fuentes_esperadas"]),
                )
            )
    score_promedio = round(score_total / evidence_count, 4) if evidence_count else None
    return ChatDeterminismCanonicalReportRead(
        total_casos=len(cases),
        casos_con_evidencia=evidence_count,
        cobertura=round(evidence_count / len(cases), 4) if cases else 0.0,
        score_promedio=score_promedio,
        casos=cases,
    )


def _append_context_warning(context: str | None, warning: str) -> str:
    prefix = context or "CONTEXTO RECUPERADO DE BUILDWISE:"
    return f"{prefix}\n- Advertencia: {warning}"


def _register_chat_audit(
    db: Session,
    *,
    current_user: Usuario,
    pregunta: str,
    response: ChatResponseRead,
    duration_ms: int,
    ip_address: str | None,
    validation_status: str | None = None,
) -> None:
    try:
        register_audit_log(
            db,
            usuario_id=getattr(current_user, "id", None),
            accion="CHAT_QUERY",
            recurso="ChatConsulta",
            recurso_id=None,
            cambios={
                "pregunta": pregunta,
                "respuesta": response.respuesta,
                "aceptada": response.aceptada,
                "tipo_intencion": response.tipo_intencion,
                "contexto_usado": response.contexto_usado,
                "fuentes_recuperadas": response.fuentes_recuperadas,
                "material_resuelto": response.material_resuelto,
                "material_resolution_source": response.material_resolution_source,
                "horizonte_resuelto": response.horizonte_resuelto,
                "proveedor_utilizado": response.proveedor_utilizado,
                "proveedor_ia": response.proveedor_ia,
                "fallback_usado": response.fallback_usado,
                "validacion_respuesta": validation_status,
                "duration_ms": duration_ms,
            },
            ip_address=ip_address,
        )
        db.commit()
    except SQLAlchemyError:
        db.rollback()


router.include_router(
    build_audit_router(
        audit_log_read=_audit_log_read,
        build_metrics=_build_chat_metrics,
        build_determinism=lambda logs, limit: _build_determinism_report(logs, limit_groups=limit),
        build_canonical=_build_canonical_determinism_report,
    )
)


@router.get("/config", response_model=ChatProviderConfigRead)
def obtener_configuracion_chat(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> ChatProviderConfigRead:
    if current_user.rol != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo un admin puede ver la configuracion de IA.")
    config = _read_persisted_chat_config(db)
    _apply_chat_config(config)
    return ChatProviderConfigRead(
        proveedor_activo=str(config["proveedor_activo"]),
        modelo_facultad=config.get("modelo_facultad"),
        modelo_claude=config.get("modelo_claude"),
        fallback_habilitado=_fallback_enabled_from_settings(config),
    )


@router.get("/status", response_model=ChatProviderStatusRead)
def obtener_estado_chat(
    verificar: bool = False,
    client: ChatCompletionClient = Depends(get_chat_client),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> ChatProviderStatusRead:
    config = _read_persisted_chat_config(db)
    _apply_chat_config(config)
    if verificar:
        try:
            client.complete([{"role": "user", "content": "Responde solo OK."}])
            _remember_provider_success(client)
        except (LLMConfigurationError, LLMProviderError) as exc:
            _remember_provider_error(client, exc)
    primary_key = str(config["proveedor_activo"])
    fallback_key = "facultad" if primary_key == "claude" else "claude"
    fallback_enabled = _provider_configured(fallback_key, config)
    return ChatProviderStatusRead(
        proveedor_activo=primary_key,
        modelo_activo=_provider_model_from_settings(primary_key, config),
        fallback_habilitado=fallback_enabled,
        proveedor_fallback=fallback_key if fallback_enabled else None,
        modelo_fallback=_provider_model_from_settings(fallback_key, config) if fallback_enabled else None,
        estado_ultima_llamada=str(_LAST_PROVIDER_STATUS["estado_ultima_llamada"]),
        proveedor_ultima_llamada=_LAST_PROVIDER_STATUS["proveedor_ultima_llamada"],
        fallback_ultima_llamada=_LAST_PROVIDER_STATUS["fallback_ultima_llamada"],
        error_ultima_llamada=_LAST_PROVIDER_STATUS["error_ultima_llamada"],
    )


@router.patch("/config", response_model=ChatProviderConfigRead)
def actualizar_configuracion_chat(
    payload: ChatProviderConfigUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> ChatProviderConfigRead:
    if current_user.rol != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo un admin puede modificar la configuracion de IA.")
    config = {
        "proveedor_activo": payload.proveedor_activo,
        "modelo_facultad": payload.modelo_facultad,
        "modelo_claude": payload.modelo_claude,
    }
    try:
        row = db.get(ChatProviderSetting, "default")
        if row is None:
            row = ChatProviderSetting(key="default")
            db.add(row)
        row.proveedor_activo = payload.proveedor_activo
        row.modelo_facultad = payload.modelo_facultad
        row.modelo_claude = payload.modelo_claude
        db.commit()
        config = _read_persisted_chat_config(db)
    except SQLAlchemyError:
        db.rollback()
    _apply_chat_config(config)
    return ChatProviderConfigRead(
        proveedor_activo=str(config["proveedor_activo"]),
        modelo_facultad=config.get("modelo_facultad"),
        modelo_claude=config.get("modelo_claude"),
        fallback_habilitado=_fallback_enabled_from_settings(config),
    )


@router.post("/consultas", response_model=ChatResponseRead)
def consultar_chat(
    payload: ChatQueryCreate,
    request: Request,
    client: ChatCompletionClient = Depends(get_chat_client),
    material_repo: MaterialRepository = Depends(get_material_repository),
    pricing_repo: PricingRepository = Depends(get_pricing_repository),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> ChatResponseRead:
    started_at = perf_counter()
    conversation = None
    context = None
    fuentes_recuperadas: list[str] = []
    fuentes_evidencia: list[dict] = []
    material_resuelto = None
    material_resuelto_id = None
    material_resolution_source = None
    horizonte_resuelto = None
    material_for_calculated_context = None
    if payload.conversation_id is not None:
        conversation = _get_owned_conversation(db, payload.conversation_id, current_user.id)
    latest_assistant = _latest_assistant_message(db, conversation) if conversation is not None else None
    semantic_question = _semantic_question_for_conversation(payload.pregunta, latest_assistant)
    effective_material_id = payload.material_id or (conversation.material_actual_id if conversation is not None else None)
    effective_horizon = (
        payload.horizonte_meses
        if payload.horizonte_meses is not None
        else (conversation.horizonte_actual if conversation is not None else 3)
    )
    admin_only = is_admin_only_request(semantic_question)
    should_load_context = is_in_scope(semantic_question, has_context=effective_material_id is not None)
    tipo_intencion = classify_chat_intent(
        semantic_question,
        accepted_scope=should_load_context,
        admin_only=admin_only,
    )
    if current_user.rol != "admin" and admin_only:
        response = ChatResponseRead(
            aceptada=False,
            respuesta=ADMIN_ONLY_RESPONSE,
            proveedor_utilizado=False,
            tipo_intencion=tipo_intencion,
            conversation_id=conversation.id if conversation is not None else None,
        )
        if conversation is not None:
            _persist_conversation_turn(db, conversation=conversation, question=payload.pregunta, response=response)
        _register_chat_audit(
            db,
            current_user=current_user,
            pregunta=payload.pregunta,
            response=response,
            duration_ms=int((perf_counter() - started_at) * 1000),
            ip_address=request.client.host if request.client else None,
        )
        return response
    try:
        if should_load_context:
            material = material_repo.get_by_id(effective_material_id) if effective_material_id is not None else None
            if material is not None:
                material_resuelto_id = getattr(material, "id", None)
                material_resolution_source = "seleccionado" if payload.material_id is not None else "contexto"
            horizon = resolve_horizon(semantic_question, effective_horizon)
            horizonte_resuelto = horizon
            if needs_operation_plan(semantic_question):
                plan = plan_operation(
                    semantic_question,
                    client,
                    materials=material_repo.list_active(),
                    selected_material_id=material.id if material is not None else None,
                    horizon=horizon,
                    history=[message.model_dump() for message in payload.historial],
                    administrative_catalog=_administrative_catalog(db) if current_user.rol == "admin" else None,
                    allow_admin=current_user.rol == "admin",
                )
                if plan["action"] != "NONE":
                    try:
                        operation = execute_operation(
                            plan,
                            fallback_material=material,
                            fallback_horizon=horizon,
                            material_repo=material_repo,
                            pricing_repo=pricing_repo,
                            db=db,
                            current_user=current_user,
                            confirmed=is_explicit_confirmation(semantic_question),
                        )
                        context = operation.context
                        fuentes_recuperadas.append(f"operacion.{plan['action'].lower()}")
                        operation_material_id = plan.get("material_id") or getattr(material, "id", None)
                        if operation_material_id is not None:
                            operation_material = material_repo.get_by_id(int(operation_material_id))
                            if operation_material is not None:
                                material_resuelto = getattr(operation_material, "nombre", None)
                                material_resuelto_id = getattr(operation_material, "id", material_resuelto_id)
                                material_resolution_source = (
                                    "pregunta"
                                    if plan.get("material_id") is not None
                                    else ("seleccionado" if payload.material_id is not None else "contexto")
                                )
                        try:
                            operation_horizon = int(plan.get("horizonte_meses") or horizon)
                        except (TypeError, ValueError):
                            operation_horizon = horizon
                        horizonte_resuelto = operation_horizon if 1 <= operation_horizon <= 12 else horizon
                    except ValueError as exc:
                        context = (
                            "La operacion solicitada es parte de BuildWise, pero no se puede calcular aun: "
                            f"{exc} Pedi el dato faltante de manera concreta."
                        )
            if context is None:
                try:
                    retrieval = build_backend_retrieval_context(
                        semantic_question,
                        material_repo=material_repo,
                        pricing_repo=pricing_repo,
                        db=db,
                        selected_material_id=effective_material_id,
                        fallback_horizon=effective_horizon,
                        is_admin=current_user.rol == "admin",
                    )
                    context = retrieval.context
                    fuentes_recuperadas.extend(retrieval.sources)
                    fuentes_evidencia.extend(retrieval.source_evidence)
                    if retrieval.material is not None:
                        material_resuelto = getattr(retrieval.material, "nombre", None)
                        material_resuelto_id = getattr(retrieval.material, "id", material_resuelto_id)
                        material_resolution_source = (
                            "seleccionado"
                            if getattr(retrieval, "material_resolution_source", None) == "contexto" and payload.material_id is not None
                            else getattr(retrieval, "material_resolution_source", None)
                        )
                    horizonte_resuelto = retrieval.horizon
                except SQLAlchemyError:
                    retrieval = None
                    context = None
                retrieval_material = retrieval.material if retrieval is not None else None
                material_for_calculated_context = material or retrieval_material
                if context is None and material_for_calculated_context is not None:
                    try:
                        context = build_material_context(
                            material_for_calculated_context,
                            horizon,
                            pricing_repo,
                            is_admin=current_user.rol == "admin",
                        )
                        fuentes_recuperadas.append("purchase_recommendations")
                    except Exception:
                        context = _append_context_warning(
                            context,
                            "No fue posible calcular forecast/recomendacion en esta consulta; responder con el contexto disponible.",
                        )
                    material_resuelto = getattr(material_for_calculated_context, "nombre", None)
                    material_resuelto_id = getattr(material_for_calculated_context, "id", material_resuelto_id)
                    horizonte_resuelto = horizon
                elif (
                    context is not None
                    and material_for_calculated_context is not None
                    and retrieval is not None
                    and _requires_calculated_material_context(semantic_question)
                ):
                    try:
                        context = (
                            f"{context}\n\n"
                            + build_material_context(
                                material_for_calculated_context,
                                retrieval.horizon,
                                pricing_repo,
                                is_admin=current_user.rol == "admin",
                            )
                        )
                        fuentes_recuperadas.append("purchase_recommendations")
                    except Exception:
                        context = _append_context_warning(
                            context,
                            "No fue posible calcular forecast/recomendacion en esta consulta; responder con el contexto disponible.",
                        )
                    material_resuelto = getattr(material_for_calculated_context, "nombre", None)
                    material_resuelto_id = getattr(material_for_calculated_context, "id", material_resuelto_id)
                    horizonte_resuelto = retrieval.horizon

        direct_answer = _demo_direct_answer(
            question=semantic_question,
            intent=tipo_intencion,
            material=material_for_calculated_context,
            horizon=horizonte_resuelto or effective_horizon,
            pricing_repo=pricing_repo,
        )
        if direct_answer is not None:
            fuentes_recuperadas.append("demo.respuesta_deterministica")

        if direct_answer is None:
            direct_answer = (
            _latest_price_answer(question=semantic_question, material_name=material_resuelto, source_evidence=fuentes_evidencia)
            if tipo_intencion == "HISTORICO" and fuentes_evidencia
            else None
            )
        if direct_answer is None and tipo_intencion == "CATALOGO":
            direct_answer = _catalog_direct_answer(
                question=semantic_question,
                material=material_for_calculated_context,
                material_repo=material_repo,
                db=db,
            )
        if direct_answer is None and tipo_intencion in {"FORECAST", "RECOMENDACION"}:
            direct_answer = _calculated_direct_answer(
                question=semantic_question,
                intent=tipo_intencion,
                material=material_for_calculated_context,
                horizon=horizonte_resuelto or effective_horizon,
                pricing_repo=pricing_repo,
            )
        if direct_answer is not None:
            display_horizon = _historical_display_horizon(tipo_intencion, horizonte_resuelto)
            response = ChatResponseRead(
                aceptada=True,
                respuesta=direct_answer,
                proveedor_utilizado=False,
                proveedor_ia=None,
                fallback_usado=False,
                tipo_intencion=tipo_intencion,
                contexto_usado=bool(context),
                fuentes_recuperadas=list(dict.fromkeys(fuentes_recuperadas)),
                fuentes_evidencia=fuentes_evidencia,
                material_resuelto_id=material_resuelto_id,
                material_resuelto=material_resuelto,
                material_resolution_source=material_resolution_source,
                horizonte_resuelto=display_horizon,
                visualizacion_sugerida=suggest_visualization(
                    semantic_question,
                    intent=tipo_intencion,
                    material=material_for_calculated_context,
                    horizon=horizonte_resuelto or effective_horizon,
                )
                if context
                else None,
                conversation_id=conversation.id if conversation is not None else None,
            )
            if conversation is not None:
                _persist_conversation_turn(db, conversation=conversation, question=payload.pregunta, response=response)
            _register_chat_audit(
                db,
                current_user=current_user,
                pregunta=payload.pregunta,
                response=response,
                duration_ms=int((perf_counter() - started_at) * 1000),
                ip_address=request.client.host if request.client else None,
            )
            return response

        history = _conversation_history(db, conversation) if conversation is not None else [message.model_dump() for message in payload.historial]
        result = answer_question(
            semantic_question,
            client,
            context=context,
            history=history,
        )
        if result.proveedor_utilizado:
            _remember_provider_success(client)
    except LLMConfigurationError as exc:
        _remember_provider_error(client, exc)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except LLMProviderError as exc:
        _remember_provider_error(client, exc)
        if not context:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
        response = ChatResponseRead(
            aceptada=True,
            respuesta=(
                "No fue posible redactar la respuesta con IA, pero BuildWise recupero datos del backend. "
                "Revisa las fuentes y la evidencia calculada de esta consulta."
            ),
            proveedor_utilizado=True,
            proveedor_ia=_resolve_provider_metadata(client)[0],
            fallback_usado=_resolve_provider_metadata(client)[1],
            tipo_intencion=tipo_intencion,
            contexto_usado=True,
            fuentes_recuperadas=list(dict.fromkeys(fuentes_recuperadas)),
            fuentes_evidencia=fuentes_evidencia,
            material_resuelto_id=material_resuelto_id,
            material_resuelto=material_resuelto,
            material_resolution_source=material_resolution_source,
            horizonte_resuelto=_historical_display_horizon(tipo_intencion, horizonte_resuelto),
            visualizacion_sugerida=suggest_visualization(
                semantic_question,
                intent=tipo_intencion,
                material=material_for_calculated_context,
                horizon=horizonte_resuelto or effective_horizon,
            )
            if context
            else None,
            conversation_id=conversation.id if conversation is not None else None,
        )
        if conversation is not None:
            _persist_conversation_turn(db, conversation=conversation, question=payload.pregunta, response=response)
        _register_chat_audit(
            db,
            current_user=current_user,
            pregunta=payload.pregunta,
            response=response,
            duration_ms=int((perf_counter() - started_at) * 1000),
            ip_address=request.client.host if request.client else None,
        )
        return response
    response = ChatResponseRead(
        aceptada=result.aceptada,
        respuesta=result.respuesta,
        proveedor_utilizado=result.proveedor_utilizado,
        proveedor_ia=result.proveedor_ia,
        fallback_usado=result.fallback_usado,
        tipo_intencion=tipo_intencion if result.aceptada else "FUERA_ALCANCE",
        contexto_usado=bool(context),
        fuentes_recuperadas=list(dict.fromkeys(fuentes_recuperadas)),
        fuentes_evidencia=fuentes_evidencia,
        material_resuelto_id=material_resuelto_id,
        material_resuelto=material_resuelto,
        material_resolution_source=material_resolution_source,
        horizonte_resuelto=_historical_display_horizon(tipo_intencion if result.aceptada else "FUERA_ALCANCE", horizonte_resuelto),
        visualizacion_sugerida=suggest_visualization(
            semantic_question,
            intent=tipo_intencion if result.aceptada else "FUERA_ALCANCE",
            material=material_for_calculated_context,
            horizon=horizonte_resuelto or effective_horizon,
        )
        if result.aceptada and context
        else None,
        conversation_id=conversation.id if conversation is not None else None,
    )
    if conversation is not None:
        _persist_conversation_turn(db, conversation=conversation, question=payload.pregunta, response=response)
    _register_chat_audit(
        db,
        current_user=current_user,
        pregunta=payload.pregunta,
        response=response,
        duration_ms=int((perf_counter() - started_at) * 1000),
        ip_address=request.client.host if request.client else None,
        validation_status=result.validacion_respuesta,
    )
    return response


@router.post("/presupuestacion/interpretar", response_model=CommercialNeedInterpretationRead)
def interpretar_necesidad_para_presupuesto(
    payload: CommercialNeedCreate,
    client: ChatCompletionClient = Depends(get_chat_client),
    material_repo: MaterialRepository = Depends(get_material_repository),
    current_user: Usuario = Depends(get_current_user),
) -> CommercialNeedInterpretationRead:
    try:
        result = interpretar_necesidad_comercial(
            payload.necesidad,
            materials=material_repo.list_active(),
            client=client,
        )
    except LLMConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except LLMProviderError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except CommercialInterpretationError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return CommercialNeedInterpretationRead(
        **{
            "solicitud_original": result.solicitud_original,
            "material_id": result.material_id,
            "producto_nombre": result.producto_nombre,
            "cantidad": result.cantidad,
            "fase_obra": result.fase_obra,
            "fecha_objetivo_uso": result.fecha_objetivo_uso,
            "horizonte_meses": result.horizonte_meses,
            "presupuesto_maximo": result.presupuesto_maximo,
            "tolerancia_riesgo": result.tolerancia_riesgo,
            "datos_faltantes": list(result.datos_faltantes),
            "proveedor_utilizado": True,
            "proveedor_ia": _resolve_provider_metadata(client)[0],
            "fallback_usado": _resolve_provider_metadata(client)[1],
        }
    )


@router.post("/presupuestacion/propuesta", response_model=CommercialProposalRead)
def generar_propuesta_de_presupuesto(
    payload: CommercialProposalCreate,
    client: ChatCompletionClient = Depends(get_chat_client),
    material_repo: MaterialRepository = Depends(get_material_repository),
    pricing_repo: PricingRepository = Depends(get_pricing_repository),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> CommercialProposalRead:
    material = material_repo.get_by_id(payload.material_id)
    if material is None:
        raise HTTPException(status_code=404, detail="Material no encontrado")
    try:
        result = generar_propuesta_comercial(
            material=material,
            cantidad=payload.cantidad,
            fase_obra=payload.fase_obra,
            tolerancia_riesgo=payload.tolerancia_riesgo,
            fecha_objetivo_uso=payload.fecha_objetivo_uso,
            horizonte_meses=payload.horizonte_meses,
            presupuesto_maximo=payload.presupuesto_maximo,
            solicitud_original=payload.solicitud_original,
            pricing_repo=pricing_repo,
            db=db,
            client=client,
        )
    except LLMConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except LLMProviderError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except InvalidCommercialRequest as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    provider_name, fallback_used = _resolve_provider_metadata(client)
    return CommercialProposalRead(
        material_id=result.material_id,
        producto_nombre=result.producto_nombre,
        cantidad=result.cantidad,
        fase_obra=result.fase_obra,
        fecha_objetivo_uso=result.fecha_objetivo_uso,
        fecha_base_calculo=getattr(result, "fecha_base_calculo", None),
        horizonte_meses=result.horizonte_meses,
        tolerancia_riesgo=result.tolerancia_riesgo,
        presupuesto_maximo=result.presupuesto_maximo,
        precio_unitario_actual=result.precio_unitario_actual,
        total_actual=result.total_actual,
        precio_unitario_proyectado=result.precio_unitario_proyectado,
        total_proyectado=result.total_proyectado,
        diferencia_estimada=result.diferencia_estimada,
        decision=result.recomendacion.decision,
        confiabilidad=result.recomendacion.confiabilidad,
        mape=result.recomendacion.mape,
        justificacion=result.recomendacion.justificacion,
        propuesta=result.propuesta,
        advertencias=list(result.advertencias),
        fuente_decision=getattr(result, "fuente_decision", "backend_deterministico"),
        propuesta_generada_por=getattr(result, "propuesta_generada_por", "llm_validado"),
        proveedor_utilizado=True,
        proveedor_ia=provider_name,
        fallback_usado=fallback_used,
    )


def _administrative_catalog(db: Session) -> dict:
    return {
        "presentaciones": [
            {"id": item.id, "material_id": item.material_id, "nombre": item.nombre_presentacion}
            for item in db.scalars(select(Presentacion).where(Presentacion.activa.is_(True)))
        ],
        "fuentes": [{"id": item.id, "nombre": item.nombre} for item in db.scalars(select(Fuente))],
        "margenes": [
            {"id": item.id, "scope": item.scope, "margen_pct": str(item.margen_ganancia_pct)}
            for item in db.scalars(select(CommercialMargin))
        ],
        "usuarios": [
            {"id": item.id, "username": item.username, "activo": item.activo}
            for item in db.scalars(select(Usuario))
        ],
    }
