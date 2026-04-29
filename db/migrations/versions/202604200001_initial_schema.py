"""initial schema

Revision ID: 202604200001
Revises:
Create Date: 2026-04-20 00:00:01
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "202604200001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "materiales",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("nombre", sa.String(length=150), nullable=False),
        sa.Column("categoria", sa.String(length=100), nullable=True),
        sa.Column("marca", sa.String(length=100), nullable=True),
        sa.Column("unidad_base", sa.String(length=20), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("nombre", "unidad_base", "marca", name="materiales_nombre_unidad_marca_unique"),
    )

    op.create_table(
        "presentaciones",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("material_id", sa.BigInteger(), nullable=False),
        sa.Column("nombre_presentacion", sa.String(length=100), nullable=False),
        sa.Column("cantidad_base", sa.Numeric(12, 4), nullable=False),
        sa.Column("unidad_presentacion", sa.String(length=20), nullable=False),
        sa.Column("activa", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("cantidad_base > 0", name="presentaciones_cantidad_base_positive"),
        sa.ForeignKeyConstraint(["material_id"], ["materiales.id"], name="presentaciones_material_id_fkey", ondelete="RESTRICT"),
        sa.UniqueConstraint("id", "material_id", name="presentaciones_id_material_unique"),
        sa.UniqueConstraint("material_id", "nombre_presentacion", name="presentaciones_material_nombre_unique"),
    )

    op.create_table(
        "fuentes",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("nombre", sa.String(length=150), nullable=False),
        sa.Column("tipo_fuente", sa.String(length=50), nullable=True),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("nombre", name="fuentes_nombre_key"),
    )

    op.create_table(
        "precios_historicos",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("material_id", sa.BigInteger(), nullable=False),
        sa.Column("presentacion_id", sa.BigInteger(), nullable=True),
        sa.Column("fuente_id", sa.BigInteger(), nullable=True),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("precio_original", sa.Numeric(14, 2), nullable=False),
        sa.Column("precio_normalizado", sa.Numeric(14, 4), nullable=False),
        sa.Column("moneda", sa.String(length=10), nullable=False, server_default="ARS"),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("btrim(moneda::text) <> ''::text", name="precios_historicos_moneda_not_blank"),
        sa.CheckConstraint("precio_normalizado >= 0", name="precios_historicos_precio_normalizado_nonnegative"),
        sa.CheckConstraint("precio_original >= 0", name="precios_historicos_precio_original_nonnegative"),
        sa.ForeignKeyConstraint(["fuente_id"], ["fuentes.id"], name="precios_historicos_fuente_id_fkey", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["material_id"], ["materiales.id"], name="precios_historicos_material_id_fkey", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["presentacion_id", "material_id"],
            ["presentaciones.id", "presentaciones.material_id"],
            name="precios_historicos_presentacion_material_fk",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["presentacion_id"], ["presentaciones.id"], name="precios_historicos_presentacion_id_fkey", ondelete="RESTRICT"),
        sa.UniqueConstraint(
            "material_id",
            "presentacion_id",
            "fecha",
            "fuente_id",
            name="precios_historicos_material_presentacion_fecha_fuente_unique",
        ),
    )

    op.create_index("idx_presentaciones_material_id", "presentaciones", ["material_id"])
    op.execute("CREATE INDEX idx_precios_historicos_fecha ON precios_historicos(fecha DESC)")
    op.create_index("idx_precios_historicos_fuente_id", "precios_historicos", ["fuente_id"])
    op.execute("CREATE INDEX idx_precios_historicos_material_fecha ON precios_historicos(material_id, fecha DESC)")
    op.create_index("idx_precios_historicos_presentacion_id", "precios_historicos", ["presentacion_id"])


def downgrade() -> None:
    op.drop_index("idx_precios_historicos_presentacion_id", table_name="precios_historicos")
    op.drop_index("idx_precios_historicos_material_fecha", table_name="precios_historicos")
    op.drop_index("idx_precios_historicos_fuente_id", table_name="precios_historicos")
    op.drop_index("idx_precios_historicos_fecha", table_name="precios_historicos")
    op.drop_index("idx_presentaciones_material_id", table_name="presentaciones")
    op.drop_table("precios_historicos")
    op.drop_table("fuentes")
    op.drop_table("presentaciones")
    op.drop_table("materiales")
