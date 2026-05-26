from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
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
    from app.modules.auth.infrastructure.models import Usuario
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
        Index("idx_external_index_values_source_name", "source_name"),
        Index("idx_external_index_values_series_date", "series_id", "date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    source_name: Mapped[str] = mapped_column(String(50))
    series_id: Mapped[str] = mapped_column(String(100))
    date: Mapped[date] = mapped_column(Date)
    value: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CommercialMargin(Base):
    __tablename__ = "commercial_margins"
    __table_args__ = (
        CheckConstraint("scope IN ('GLOBAL', 'MATERIAL', 'PRODUCT')", name="commercial_margins_scope_allowed"),
        CheckConstraint("margen_ganancia_pct >= 0", name="commercial_margins_margin_nonnegative"),
        CheckConstraint(
            """
            (
                scope = 'GLOBAL'
                AND material_id IS NULL
                AND presentation_id IS NULL
                AND product_key IS NULL
            )
            OR (
                scope = 'MATERIAL'
                AND material_id IS NOT NULL
            )
            OR (
                scope = 'PRODUCT'
                AND material_id IS NOT NULL
                AND (
                    presentation_id IS NOT NULL
                    OR product_key IS NOT NULL
                )
            )
            """.strip(),
            name="commercial_margins_scope_consistency",
        ),
        Index("idx_commercial_margins_scope_activo", "scope", "activo"),
        Index("idx_commercial_margins_material_id", "material_id"),
        Index("idx_commercial_margins_presentation_id", "presentation_id"),
        Index("idx_commercial_margins_product_key", "product_key"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    scope: Mapped[str] = mapped_column(String(20), nullable=False)
    material_id: Mapped[int | None] = mapped_column(ForeignKey("materiales.id", name="commercial_margins_material_id_fkey", ondelete="RESTRICT"))
    presentation_id: Mapped[int | None] = mapped_column(
        ForeignKey("presentaciones.id", name="commercial_margins_presentation_id_fkey", ondelete="RESTRICT")
    )
    product_key: Mapped[str | None] = mapped_column(String(200))
    margen_ganancia_pct: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("TRUE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    material: Mapped["Material | None"] = relationship(foreign_keys=[material_id])
    presentacion: Mapped["Presentacion | None"] = relationship(foreign_keys=[presentation_id])


class Alerta(Base):
    __tablename__ = "alertas"
    __table_args__ = (
        CheckConstraint(
            "tipo IN ('OPORTUNIDAD_COMPRA', 'DESVIO_PRECIO', 'DETERIORO_CONFIANZA')",
            name="alertas_tipo_allowed",
        ),
        CheckConstraint("prioridad IN ('ALTA', 'MEDIA', 'BAJA')", name="alertas_prioridad_allowed"),
        Index("idx_alertas_usuario_leida", "usuario_id", "leida"),
        Index("idx_alertas_material_id", "material_id"),
        Index("idx_alertas_created_at", text("created_at DESC")),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    usuario_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id", name="alertas_usuario_id_fkey", ondelete="CASCADE")
    )
    material_id: Mapped[int | None] = mapped_column(
        ForeignKey("materiales.id", name="alertas_material_id_fkey", ondelete="CASCADE")
    )
    tipo: Mapped[str] = mapped_column(String(50), nullable=False)
    prioridad: Mapped[str] = mapped_column(String(20), nullable=False)
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    mensaje: Mapped[str] = mapped_column(Text, nullable=False)
    data_context: Mapped[str | None] = mapped_column(Text)  # JSON con datos tecnicos del trigger
    leida: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("FALSE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    usuario: Mapped["Usuario | None"] = relationship(foreign_keys=[usuario_id])
    material: Mapped["Material | None"] = relationship(foreign_keys=[material_id])

