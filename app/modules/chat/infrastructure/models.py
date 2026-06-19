from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.database.base import Base


class ChatConversation(Base):
    __tablename__ = "chat_conversations"
    __table_args__ = (
        CheckConstraint("trim(titulo) <> ''", name="chat_conversations_titulo_not_blank"),
        Index("idx_chat_conversations_usuario_updated", "usuario_id", "updated_at"),
        Index("idx_chat_conversations_usuario_archived", "usuario_id", "archived_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    usuario_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False)
    titulo: Mapped[str] = mapped_column(String(160), nullable=False)
    material_actual_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("materiales.id", ondelete="SET NULL"), nullable=True)
    horizonte_actual: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')", name="chat_messages_role_allowed"),
        CheckConstraint("trim(content) <> ''", name="chat_messages_content_not_blank"),
        Index("idx_chat_messages_conversation_created", "conversation_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("chat_conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tipo_intencion: Mapped[str | None] = mapped_column(String(30), nullable=True)
    contexto_usado: Mapped[bool | None] = mapped_column(nullable=True)
    fuentes_recuperadas: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    fuentes_evidencia: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    material_resuelto_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("materiales.id", ondelete="SET NULL"), nullable=True)
    material_resuelto: Mapped[str | None] = mapped_column(String(160), nullable=True)
    material_resolution_source: Mapped[str | None] = mapped_column(String(30), nullable=True)
    horizonte_resuelto: Mapped[int | None] = mapped_column(Integer, nullable=True)
    visualizacion_sugerida: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    proveedor_ia: Mapped[str | None] = mapped_column(String(40), nullable=True)
    fallback_usado: Mapped[bool | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    conversation: Mapped[ChatConversation] = relationship(back_populates="messages")


class ChatProviderSetting(Base):
    __tablename__ = "chat_provider_settings"

    key: Mapped[str] = mapped_column(String(40), primary_key=True)
    proveedor_activo: Mapped[str] = mapped_column(String(20), nullable=False)
    modelo_facultad: Mapped[str | None] = mapped_column(String(200), nullable=True)
    modelo_claude: Mapped[str | None] = mapped_column(String(200), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
