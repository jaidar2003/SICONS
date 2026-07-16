from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.auth.infrastructure.models import Usuario
from app.modules.auth.interfaces.dependencies import get_current_user
from app.modules.chat.infrastructure.models import ChatConversation, ChatMessage
from app.modules.chat.interfaces.schemas import (
    ChatConversationCreate,
    ChatConversationRead,
    ChatConversationUpdate,
    ChatMessageRead,
    ChatResponseRead,
)
from app.shared.database.session import get_db

router = APIRouter()


def conversation_title(question: str | None = None) -> str:
    text = (question or "Nueva conversación").strip()
    if not text:
        return "Nueva conversación"
    return text[:157] + "..." if len(text) > 160 else text


def get_owned_conversation(db: Session, conversation_id: int, user_id: int) -> ChatConversation:
    conversation = db.get(ChatConversation, conversation_id)
    if conversation is None or conversation.usuario_id != user_id or conversation.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversación no encontrada")
    return conversation


def conversation_history(db: Session, conversation: ChatConversation, limit: int = 8) -> list[dict[str, str]]:
    rows = list(
        db.scalars(
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conversation.id)
            .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
            .limit(limit)
        )
    )
    return [{"role": message.role, "content": message.content} for message in reversed(rows)]


def latest_assistant_message(db: Session, conversation: ChatConversation) -> ChatMessage | None:
    return db.scalar(
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conversation.id, ChatMessage.role == "assistant")
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .limit(1)
    )


def recent_user_messages(db: Session, conversation: ChatConversation, limit: int = 12) -> list[str]:
    rows = list(
        db.scalars(
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conversation.id, ChatMessage.role == "user")
            .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
            .limit(limit)
        )
    )
    return [message.content for message in reversed(rows)]


def message_read(message: ChatMessage) -> ChatMessageRead:
    return ChatMessageRead(
        id=message.id,
        conversation_id=message.conversation_id,
        role=message.role,
        content=message.content,
        tipo_intencion=message.tipo_intencion,
        contexto_usado=message.contexto_usado,
        fuentes_recuperadas=message.fuentes_recuperadas or [],
        fuentes_evidencia=message.fuentes_evidencia or [],
        material_resuelto_id=message.material_resuelto_id,
        material_resuelto=message.material_resuelto,
        material_resolution_source=message.material_resolution_source,
        horizonte_resuelto=message.horizonte_resuelto,
        visualizacion_sugerida=message.visualizacion_sugerida,
        proveedor_ia=message.proveedor_ia,
        fallback_usado=message.fallback_usado,
        created_at=message.created_at,
    )


def conversation_read(db: Session, conversation: ChatConversation) -> ChatConversationRead:
    latest = db.scalar(
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conversation.id)
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .limit(1)
    )
    return ChatConversationRead(
        id=conversation.id,
        titulo=conversation.titulo,
        material_actual_id=conversation.material_actual_id,
        horizonte_actual=conversation.horizonte_actual,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        archived_at=conversation.archived_at,
        ultimo_mensaje=latest.content if latest is not None else None,
    )


def persist_conversation_turn(
    db: Session,
    *,
    conversation: ChatConversation,
    question: str,
    response: ChatResponseRead,
) -> None:
    db.add(ChatMessage(conversation_id=conversation.id, role="user", content=question.strip()))
    db.add(
        ChatMessage(
            conversation_id=conversation.id,
            role="assistant",
            content=response.respuesta,
            tipo_intencion=response.tipo_intencion,
            contexto_usado=response.contexto_usado,
            fuentes_recuperadas=response.fuentes_recuperadas,
            fuentes_evidencia=[item.model_dump(mode="json") for item in response.fuentes_evidencia],
            material_resuelto_id=response.material_resuelto_id,
            material_resuelto=response.material_resuelto,
            material_resolution_source=response.material_resolution_source,
            horizonte_resuelto=response.horizonte_resuelto,
            visualizacion_sugerida=response.visualizacion_sugerida.model_dump(mode="json") if response.visualizacion_sugerida else None,
            proveedor_ia=response.proveedor_ia,
            fallback_usado=response.fallback_usado,
        )
    )
    if response.material_resuelto_id is not None:
        conversation.material_actual_id = response.material_resuelto_id
    if response.horizonte_resuelto is not None:
        conversation.horizonte_actual = response.horizonte_resuelto
    conversation.updated_at = datetime.now(UTC)
    db.flush()


@router.get("/conversaciones", response_model=list[ChatConversationRead])
def listar_conversaciones(
    include_archived: bool = False,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> list[ChatConversationRead]:
    stmt = select(ChatConversation).where(ChatConversation.usuario_id == current_user.id)
    if not include_archived:
        stmt = stmt.where(ChatConversation.archived_at.is_(None))
    stmt = stmt.order_by(ChatConversation.updated_at.desc(), ChatConversation.id.desc())
    return [conversation_read(db, conversation) for conversation in db.scalars(stmt)]


@router.post("/conversaciones", response_model=ChatConversationRead, status_code=status.HTTP_201_CREATED)
def crear_conversacion(
    payload: ChatConversationCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> ChatConversationRead:
    conversation = ChatConversation(usuario_id=current_user.id, titulo=conversation_title(payload.titulo))
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation_read(db, conversation)


@router.get("/conversaciones/{conversation_id}/mensajes", response_model=list[ChatMessageRead])
def listar_mensajes_conversacion(
    conversation_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    order: str = Query("asc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> list[ChatMessageRead]:
    conversation = get_owned_conversation(db, conversation_id, current_user.id)
    order_by = (
        (ChatMessage.created_at.desc(), ChatMessage.id.desc())
        if order == "desc"
        else (ChatMessage.created_at.asc(), ChatMessage.id.asc())
    )
    messages = db.scalars(
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conversation.id)
        .order_by(*order_by)
        .offset(offset)
        .limit(limit)
    )
    return [message_read(message) for message in messages]


@router.patch("/conversaciones/{conversation_id}", response_model=ChatConversationRead)
def actualizar_conversacion(
    conversation_id: int,
    payload: ChatConversationUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
) -> ChatConversationRead:
    conversation = get_owned_conversation(db, conversation_id, current_user.id)
    if payload.titulo is not None:
        conversation.titulo = conversation_title(payload.titulo)
    if payload.archived is True:
        conversation.archived_at = datetime.now(UTC)
    elif payload.archived is False:
        conversation.archived_at = None
    conversation.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(conversation)
    return conversation_read(db, conversation)
