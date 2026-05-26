from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.auth.infrastructure.models import Usuario
from app.modules.auth.interfaces.dependencies import get_current_user
from app.modules.catalog.domain.repositories import MaterialRepository
from app.modules.catalog.infrastructure.models import Fuente, Presentacion
from app.modules.catalog.interfaces.dependencies import get_material_repository
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
    LLMConfigurationError,
    LLMProviderError,
    OpenAICompatibleChatClient,
)
from app.modules.chat.interfaces.schemas import ChatQueryCreate, ChatResponseRead
from app.modules.pricing.domain.repositories import PricingRepository
from app.modules.pricing.infrastructure.models import CommercialMargin
from app.modules.pricing.interfaces.dependencies import get_pricing_repository
from app.shared.config.settings import settings
from app.shared.database.session import get_db

router = APIRouter(prefix="/chat", tags=["chat"])


def get_chat_client() -> ChatCompletionClient:
    if settings.chat_provider.strip().lower() == "anthropic":
        return AnthropicChatClient()
    return OpenAICompatibleChatClient()


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
