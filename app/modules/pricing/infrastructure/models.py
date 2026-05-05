from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.database.base import Base

if TYPE_CHECKING:
    from app.modules.catalog.infrastructure.models import Fuente, Material, Presentacion


class PrecioHistorico(Base):
    __tablename__ = "precios_historicos"
    __table_args__ = (
        ForeignKeyConstraint(
            ["presentacion_id", "material_id"],
            ["presentaciones.id", "presentaciones.material_id"],
            name="precios_historicos_presentacion_material_fk",
            ondelete="RESTRICT",
        ),
        CheckConstraint("precio_original >= 0", name="precios_historicos_precio_original_nonnegative"),
        CheckConstraint("precio_normalizado >= 0", name="precios_historicos_precio_normalizado_nonnegative"),
        CheckConstraint("btrim(moneda::text) <> ''::text", name="precios_historicos_moneda_not_blank"),
        CheckConstraint(
            "origen_dato IN ('REAL', 'ESTIMADO')",
            name="precios_historicos_origen_dato_allowed",
        ),
        Index("idx_precios_historicos_material_fecha", "material_id", text("fecha DESC")),
        Index("idx_precios_historicos_material_presentacion_fecha_fuente", "material_id", "presentacion_id", "fecha", "fuente_id"),
        Index("idx_precios_historicos_presentacion_id", "presentacion_id"),
        Index("idx_precios_historicos_fuente_id", "fuente_id"),
        Index("idx_precios_historicos_fecha", text("fecha DESC")),
        Index(
            "idx_precios_historicos_fuente_comprobante_unique",
            "fuente_id",
            "numero_comprobante",
            unique=True,
            postgresql_where=text("numero_comprobante IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materiales.id", name="precios_historicos_material_id_fkey", ondelete="RESTRICT"))
    presentacion_id: Mapped[int | None] = mapped_column(
        ForeignKey("presentaciones.id", name="precios_historicos_presentacion_id_fkey", ondelete="RESTRICT")
    )
    fuente_id: Mapped[int | None] = mapped_column(ForeignKey("fuentes.id", name="precios_historicos_fuente_id_fkey", ondelete="SET NULL"))
    fecha: Mapped[date] = mapped_column(Date)
    precio_original: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    precio_normalizado: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    moneda: Mapped[str] = mapped_column(String(10))
    numero_comprobante: Mapped[str | None] = mapped_column(String(50))
    origen_dato: Mapped[str] = mapped_column(String(20), server_default="REAL")
    metodo_estimacion: Mapped[str | None] = mapped_column(String(50))
    observaciones: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    material: Mapped["Material"] = relationship(back_populates="precios", foreign_keys=[material_id])
    presentacion: Mapped["Presentacion | None"] = relationship(back_populates="precios", foreign_keys=[presentacion_id])
    fuente: Mapped["Fuente | None"] = relationship(back_populates="precios", foreign_keys=[fuente_id])


class ExternalIndexValue(Base):
    __tablename__ = "external_index_values"
    __table_args__ = (
        UniqueConstraint("series_id", "date", name="external_index_values_series_date_unique"),
        CheckConstraint("value >= 0", name="external_index_values_value_nonnegative"),
        Index("idx_external_index_values_source_name", "source_name"),
        Index("idx_external_index_values_series_date", "series_id", "date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    source_name: Mapped[str] = mapped_column(String(50))
    series_id: Mapped[str] = mapped_column(String(100))
    date: Mapped[date] = mapped_column(Date)
    value: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
