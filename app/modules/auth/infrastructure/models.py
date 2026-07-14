from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Identity, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.database.base import Base
from app.shared.database.types import BIGINT_ID


class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = (
        CheckConstraint("rol IN ('admin', 'cliente')", name="usuarios_rol_allowed"),
        CheckConstraint("trim(username) <> ''", name="usuarios_username_not_blank"),
    )

    id: Mapped[int] = mapped_column(BIGINT_ID, Identity(always=True), primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(160), unique=True, nullable=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(220), nullable=False)
    rol: Mapped[str] = mapped_column(String(20), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="TRUE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
