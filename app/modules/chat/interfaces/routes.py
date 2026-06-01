from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
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
    ChatQueryCreate,
    ChatResponseRead,
    CommercialNeedCreate,
    CommercialNeedInterpretationRead,
    CommercialProposalCreate,
    CommercialProposalRead,
)
from app.modules.pricing.domain.repositories import PricingRepository
from app.modules.pricing.infrastructure.models import CommercialMargin
from app.modules.pricing.interfaces.dependencies import get_pricing_repository
from app.shared.config.settings import settings
from app.shared.database.session import get_db

router = APIRouter(prefix="/chat", tags=["chat"])


def _resolve_provider_metadata(client) -> tuple[str | None, bool]:
    default_provider = "claude" if settings.chat_provider.strip().lower() == "anthropic" else "facultad"
    provider_name = getattr(client, "last_provider_name", getattr(client, "provider_name", default_provider))
    fallback_used = bool(getattr(client, "last_fallback_used", False))
    return provider_name, fallback_used


def get_chat_client() -> ChatCompletionClient:
    if settings.chat_provider.strip().lower() == "anthropic":
        return AnthropicChatClient()
    primary = OpenAICompatibleChatClient()
    fallback = AnthropicChatClient()
    return FallbackChatClient(primary, fallback)


@router.post("/consultas", response_model=ChatResponseRead)
def consultar_chat(
    payload: ChatQueryCreate,
    client: ChatCompletionClient = Depends(get_chat_client),
    material_repo: MaterialRepository = Depends(get_material_repository),
    pricing_repo: PricingRepository = Depends(get_pricing_repository),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> ChatResponseRead:
    if current_user.rol != "admin" and is_admin_only_request(payload.pregunta):
        return ChatResponseRead(aceptada=False, respuesta=ADMIN_ONLY_RESPONSE, proveedor_utilizado=False)
    try:
        context = None
        should_load_context = is_in_scope(payload.pregunta, has_context=payload.material_id is not None)
        if should_load_context and payload.material_id is not None:
            material = material_repo.get_by_id(payload.material_id)
            if material is not None:
                horizon = resolve_horizon(payload.pregunta, payload.horizonte_meses)
                if needs_operation_plan(payload.pregunta):
                    plan = plan_operation(
                        payload.pregunta,
                        client,
                        materials=material_repo.list_active(),
                        selected_material_id=material.id,
                        horizon=horizon,
                        history=[message.model_dump() for message in payload.historial],
                        administrative_catalog=_administrative_catalog(db) if current_user.rol == "admin" else None,
                        allow_admin=current_user.rol == "admin",
                    )
                    if plan["action"] != "NONE":
                        try:
                            context = execute_operation(
                                plan,
                                fallback_material=material,
                                fallback_horizon=horizon,
                                material_repo=material_repo,
                                pricing_repo=pricing_repo,
                                db=db,
                                current_user=current_user,
                                confirmed=is_explicit_confirmation(payload.pregunta),
                            ).context
                        except ValueError as exc:
                            context = (
                                "La operacion solicitada es parte de BuildWise, pero no se puede calcular aun: "
                                f"{exc} Pedi el dato faltante de manera concreta."
                            )
                if context is None:
                    context = build_material_context(
                        material,
                        horizon,
                        pricing_repo,
                        is_admin=current_user.rol == "admin",
                    )
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
    return ChatResponseRead(
        aceptada=result.aceptada,
        respuesta=result.respuesta,
        proveedor_utilizado=result.proveedor_utilizado,
        proveedor_ia=result.proveedor_ia,
        fallback_usado=result.fallback_usado,
    )


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
