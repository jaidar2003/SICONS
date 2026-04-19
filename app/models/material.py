from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.precio_historico import PrecioHistorico
    from app.models.presentacion import Presentacion


class Material(Base):
    __tablename__ = "materiales"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(150))
    categoria: Mapped[str | None] = mapped_column(String(100))
    marca: Mapped[str | None] = mapped_column(String(100))
    unidad_base: Mapped[str] = mapped_column(String(20))
    descripcion: Mapped[str | None] = mapped_column(Text)
    activo: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    presentaciones: Mapped[list["Presentacion"]] = relationship(back_populates="material")
    precios: Mapped[list["PrecioHistorico"]] = relationship(back_populates="material")
