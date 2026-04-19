from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Identity, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.material import Material
    from app.models.precio_historico import PrecioHistorico


class Presentacion(Base):
    __tablename__ = "presentaciones"
    __table_args__ = (
        UniqueConstraint("id", "material_id", name="presentaciones_id_material_unique"),
        UniqueConstraint("material_id", "nombre_presentacion", name="presentaciones_material_nombre_unique"),
        CheckConstraint("cantidad_base > 0", name="presentaciones_cantidad_base_positive"),
        Index("idx_presentaciones_material_id", "material_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materiales.id", name="presentaciones_material_id_fkey", ondelete="RESTRICT"))
    nombre_presentacion: Mapped[str] = mapped_column(String(100))
    cantidad_base: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    unidad_presentacion: Mapped[str] = mapped_column(String(20))
    activa: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    material: Mapped["Material"] = relationship(back_populates="presentaciones", foreign_keys=[material_id])
    precios: Mapped[list["PrecioHistorico"]] = relationship(
        back_populates="presentacion",
        foreign_keys="PrecioHistorico.presentacion_id",
    )
