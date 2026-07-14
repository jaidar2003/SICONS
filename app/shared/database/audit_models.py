from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Identity, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base
from app.shared.database.types import BIGINT_ID


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("idx_audit_logs_usuario_id", "usuario_id"),
        Index("idx_audit_logs_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(BIGINT_ID, Identity(always=True), primary_key=True)
    usuario_id: Mapped[int | None] = mapped_column(BIGINT_ID, ForeignKey("usuarios.id"), nullable=True)
    accion: Mapped[str] = mapped_column(String(50), nullable=False)  # CREATED, UPDATED, DELETED, LOGIN, etc.
    recurso: Mapped[str] = mapped_column(String(50), nullable=False)  # Material, PrecioHistorico, Usuario, etc.
    recurso_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cambios: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)  # {"old": ..., "new": ...}
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
