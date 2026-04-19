from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.fuente import Fuente
    from app.models.material import Material
    from app.models.presentacion import Presentacion


class PrecioHistorico(Base):
    __tablename__ = "precios_historicos"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materiales.id"))
    presentacion_id: Mapped[int | None] = mapped_column(ForeignKey("presentaciones.id"))
    fuente_id: Mapped[int | None] = mapped_column(ForeignKey("fuentes.id"))
    fecha: Mapped[date] = mapped_column(Date)
    precio_original: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    precio_normalizado: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    moneda: Mapped[str] = mapped_column(String(10))
    observaciones: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    material: Mapped["Material"] = relationship(back_populates="precios")
    presentacion: Mapped["Presentacion | None"] = relationship(back_populates="precios")
    fuente: Mapped["Fuente | None"] = relationship(back_populates="precios")
