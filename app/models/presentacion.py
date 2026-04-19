from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.material import Material
    from app.models.precio_historico import PrecioHistorico


class Presentacion(Base):
    __tablename__ = "presentaciones"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materiales.id"))
    nombre_presentacion: Mapped[str] = mapped_column(String(100))
    cantidad_base: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    unidad_presentacion: Mapped[str] = mapped_column(String(20))
    activa: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    material: Mapped["Material"] = relationship(back_populates="presentaciones")
    precios: Mapped[list["PrecioHistorico"]] = relationship(back_populates="presentacion")
