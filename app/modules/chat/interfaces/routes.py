import re
import unicodedata
from collections import Counter
from math import ceil
from time import perf_counter

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
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
from app.modules.chat.application.retrieval import build_backend_retrieval_context, classify_chat_intent
from app.modules.chat.application.service import (
    ADMIN_ONLY_RESPONSE,
    ChatCompletionClient,
    answer_question,
    is_admin_only_request,
    is_in_scope,
)
from app.modules.chat.infrastructure.llm_client import (
    AnthropicChatClient,
    FallbackChatClient,
    LLMConfigurationError,
    LLMProviderError,
    OpenAICompatibleChatClient,
)
from app.modules.chat.interfaces.schemas import (
    ChatAuditLogRead,
    ChatAuditMetricsRead,
    ChatDeterminismGroupRead,
    ChatDeterminismCanonicalItemRead,
    ChatDeterminismCanonicalReportRead,
    ChatDeterminismReportRead,
    ChatProviderConfigRead,
    ChatProviderConfigUpdate,
    ChatQueryCreate,
    ChatResponseRead,
    CommercialNeedCreate,
    CommercialNeedInterpretationRead,
    CommercialProposalCreate,
    CommercialProposalRead,
)
from app.shared.database.audit_models import AuditLog
from app.modules.pricing.domain.repositories import PricingRepository
from app.modules.pricing.infrastructure.models import CommercialMargin
from app.modules.pricing.interfaces.dependencies import get_pricing_repository
from app.shared.config.settings import settings
from app.shared.database.audit_service import register_audit_log
from app.shared.database.session import get_db

router = APIRouter(prefix="/chat", tags=["chat"])


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


def _resolve_provider_metadata(client) -> tuple[str | None, bool]:
    default_provider = "claude" if settings.chat_provider.strip().lower() == "anthropic" else "facultad"
    provider_name = getattr(client, "last_provider_name", getattr(client, "provider_name", default_provider))
    fallback_used = bool(getattr(client, "last_fallback_used", False))
    return provider_name, fallback_used


def get_chat_client() -> ChatCompletionClient:
    if settings.chat_provider.strip().lower() == "anthropic":
        primary = AnthropicChatClient()
        fallback = OpenAICompatibleChatClient()
        return FallbackChatClient(primary, fallback)
    primary = OpenAICompatibleChatClient()
    fallback = AnthropicChatClient()
    return FallbackChatClient(primary, fallback)


def _provider_key_from_settings() -> str:
    return "claude" if settings.chat_provider.strip().lower() == "anthropic" else "facultad"


def _provider_configured(provider_key: str) -> bool:
    if provider_key == "claude":
        return bool(settings.anthropic_base_url and settings.anthropic_api_key and settings.anthropic_model)
    return bool(settings.openai_base_url and settings.openai_api_key and settings.openai_model)


def _fallback_enabled_from_settings() -> bool:
    primary_key = _provider_key_from_settings()
    fallback_key = "facultad" if primary_key == "claude" else "claude"
    return _provider_configured(fallback_key)


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
        "horizonte_resuelto": 3,
        "fuentes_esperadas": ("operacion.price_history",),
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
        if isinstance(changes.get("duration_ms"), (int, float))
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
                "horizonte_resuelto": response.horizonte_resuelto,
                "proveedor_ia": response.proveedor_ia,
                "fallback_usado": response.fallback_usado,
                "duration_ms": duration_ms,
            },
            ip_address=ip_address,
        )
        db.commit()
    except SQLAlchemyError:
        db.rollback()


@router.get("/config", response_model=ChatProviderConfigRead)
def obtener_configuracion_chat(
    current_user: Usuario = Depends(get_current_user),
) -> ChatProviderConfigRead:
    if current_user.rol != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo un admin puede ver la configuracion de IA.")
    return ChatProviderConfigRead(
        proveedor_activo=_provider_key_from_settings(),
        modelo_facultad=settings.openai_model,
        modelo_claude=settings.anthropic_model,
        fallback_habilitado=_fallback_enabled_from_settings(),
    )


@router.get("/auditoria", response_model=list[ChatAuditLogRead])
def listar_auditoria_chat(
    limit: int = Query(default=50, ge=1, le=200),
    tipo_intencion: str | None = Query(default=None),
    fallback_usado: bool | None = Query(default=None),
    usuario_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> list[ChatAuditLogRead]:
    if current_user.rol != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo un admin puede ver la auditoria del asistente.")

    stmt = (
        select(AuditLog, Usuario.username)
        .outerjoin(Usuario, Usuario.id == AuditLog.usuario_id)
        .where(AuditLog.accion == "CHAT_QUERY")
        .where(AuditLog.recurso == "ChatConsulta")
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(limit)
    )
    if usuario_id is not None:
        stmt = stmt.where(AuditLog.usuario_id == usuario_id)
    if tipo_intencion:
        stmt = stmt.where(AuditLog.cambios["tipo_intencion"].as_string() == tipo_intencion)
    if fallback_usado is not None:
        stmt = stmt.where(AuditLog.cambios["fallback_usado"].as_boolean() == fallback_usado)

    rows = db.execute(stmt).all()
    return [_audit_log_read(log, username) for log, username in rows]


@router.get("/auditoria/metricas", response_model=ChatAuditMetricsRead)
def obtener_metricas_auditoria_chat(
    limit: int = Query(default=500, ge=10, le=1000),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> ChatAuditMetricsRead:
    if current_user.rol != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo un admin puede ver las metricas de auditoria.")

    stmt = (
        select(AuditLog)
        .where(AuditLog.accion == "CHAT_QUERY")
        .where(AuditLog.recurso == "ChatConsulta")
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(limit)
    )
    logs = list(db.scalars(stmt))
    return _build_chat_metrics(logs)


@router.get("/auditoria/determinismo", response_model=ChatDeterminismReportRead)
def medir_determinismo_rag(
    limit: int = Query(default=200, ge=2, le=1000),
    limit_groups: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> ChatDeterminismReportRead:
    if current_user.rol != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo un admin puede medir determinismo del RAG.")

    stmt = (
        select(AuditLog)
        .where(AuditLog.accion == "CHAT_QUERY")
        .where(AuditLog.recurso == "ChatConsulta")
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(limit)
    )
    logs = list(db.scalars(stmt))
    return _build_determinism_report(logs, limit_groups=limit_groups)


@router.get("/auditoria/determinismo/canonicas", response_model=ChatDeterminismCanonicalReportRead)
def medir_determinismo_canonicas(
    limit: int = Query(default=500, ge=10, le=1000),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> ChatDeterminismCanonicalReportRead:
    if current_user.rol != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo un admin puede medir la bateria canonica del RAG.")

    stmt = (
        select(AuditLog)
        .where(AuditLog.accion == "CHAT_QUERY")
        .where(AuditLog.recurso == "ChatConsulta")
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(limit)
    )
    logs = list(db.scalars(stmt))
    return _build_canonical_determinism_report(logs)


@router.patch("/config", response_model=ChatProviderConfigRead)
def actualizar_configuracion_chat(
    payload: ChatProviderConfigUpdate,
    current_user: Usuario = Depends(get_current_user),
) -> ChatProviderConfigRead:
    if current_user.rol != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo un admin puede modificar la configuracion de IA.")
    settings.chat_provider = "anthropic" if payload.proveedor_activo == "claude" else "openai"
    settings.openai_model = payload.modelo_facultad
    settings.anthropic_model = payload.modelo_claude
    return ChatProviderConfigRead(
        proveedor_activo=_provider_key_from_settings(),
        modelo_facultad=settings.openai_model,
        modelo_claude=settings.anthropic_model,
        fallback_habilitado=_fallback_enabled_from_settings(),
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
    admin_only = is_admin_only_request(payload.pregunta)
    should_load_context = is_in_scope(payload.pregunta, has_context=payload.material_id is not None)
    tipo_intencion = classify_chat_intent(
        payload.pregunta,
        accepted_scope=should_load_context,
        admin_only=admin_only,
    )
    if current_user.rol != "admin" and admin_only:
        response = ChatResponseRead(
            aceptada=False,
            respuesta=ADMIN_ONLY_RESPONSE,
            proveedor_utilizado=False,
            tipo_intencion=tipo_intencion,
        )
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
        context = None
        fuentes_recuperadas: list[str] = []
        material_resuelto = None
        horizonte_resuelto = None
        if should_load_context:
            material = material_repo.get_by_id(payload.material_id) if payload.material_id is not None else None
            horizon = resolve_horizon(payload.pregunta, payload.horizonte_meses)
            horizonte_resuelto = horizon
            if needs_operation_plan(payload.pregunta):
                plan = plan_operation(
                    payload.pregunta,
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
                            confirmed=is_explicit_confirmation(payload.pregunta),
                        )
                        context = operation.context
                        fuentes_recuperadas.append(f"operacion.{plan['action'].lower()}")
                        operation_material_id = plan.get("material_id") or getattr(material, "id", None)
                        if operation_material_id is not None:
                            operation_material = material_repo.get_by_id(int(operation_material_id))
                            if operation_material is not None:
                                material_resuelto = getattr(operation_material, "nombre", None)
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
                        payload.pregunta,
                        material_repo=material_repo,
                        pricing_repo=pricing_repo,
                        db=db,
                        selected_material_id=payload.material_id,
                        fallback_horizon=payload.horizonte_meses,
                        is_admin=current_user.rol == "admin",
                    )
                    context = retrieval.context
                    fuentes_recuperadas.extend(retrieval.sources)
                    if retrieval.material is not None:
                        material_resuelto = getattr(retrieval.material, "nombre", None)
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
                    horizonte_resuelto = horizon
                elif (
                    context is not None
                    and material_for_calculated_context is not None
                    and retrieval is not None
                    and _requires_calculated_material_context(payload.pregunta)
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
                    horizonte_resuelto = retrieval.horizon
        result = answer_question(
            payload.pregunta,
            client,
            context=context,
            history=[message.model_dump() for message in payload.historial],
        )
    except LLMConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except LLMProviderError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    response = ChatResponseRead(
        aceptada=result.aceptada,
        respuesta=result.respuesta,
        proveedor_utilizado=result.proveedor_utilizado,
        proveedor_ia=result.proveedor_ia,
        fallback_usado=result.fallback_usado,
        tipo_intencion=tipo_intencion if result.aceptada else "FUERA_ALCANCE",
        contexto_usado=bool(context),
        fuentes_recuperadas=list(dict.fromkeys(fuentes_recuperadas)),
        material_resuelto=material_resuelto,
        horizonte_resuelto=horizonte_resuelto,
    )
    _register_chat_audit(
        db,
        current_user=current_user,
        pregunta=payload.pregunta,
        response=response,
        duration_ms=int((perf_counter() - started_at) * 1000),
        ip_address=request.client.host if request.client else None,
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
    provider_name, fallback_used = _resolve_provider_metadata(client)
    return CommercialProposalRead(
        material_id=result.material_id,
        producto_nombre=result.producto_nombre,
        cantidad=result.cantidad,
        fase_obra=result.fase_obra,
        fecha_objetivo_uso=result.fecha_objetivo_uso,
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
