"""add commercial margins

Revision ID: 202605090001
Revises: 202605080001
Create Date: 2026-05-09 00:01:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "202605090001"
down_revision: str | None = "202605080001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "commercial_margins",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("scope", sa.String(length=20), nullable=False),
        sa.Column("material_id", sa.BigInteger(), nullable=True),
        sa.Column("presentation_id", sa.BigInteger(), nullable=True),
        sa.Column("product_key", sa.String(length=200), nullable=True),
        sa.Column("margen_ganancia_pct", sa.Numeric(12, 2), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("scope IN ('GLOBAL', 'MATERIAL', 'PRODUCT')", name="commercial_margins_scope_allowed"),
        sa.CheckConstraint("margen_ganancia_pct >= 0", name="commercial_margins_margin_nonnegative"),
        sa.CheckConstraint(
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
        sa.ForeignKeyConstraint(["material_id"], ["materiales.id"], name="commercial_margins_material_id_fkey", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["presentation_id"],
            ["presentaciones.id"],
            name="commercial_margins_presentation_id_fkey",
            ondelete="RESTRICT",
        ),
    )
    op.create_index("idx_commercial_margins_scope_activo", "commercial_margins", ["scope", "activo"])
    op.create_index("idx_commercial_margins_material_id", "commercial_margins", ["material_id"])
    op.create_index("idx_commercial_margins_presentation_id", "commercial_margins", ["presentation_id"])
    op.create_index("idx_commercial_margins_product_key", "commercial_margins", ["product_key"])


def downgrade() -> None:
    op.drop_index("idx_commercial_margins_product_key", table_name="commercial_margins")
    op.drop_index("idx_commercial_margins_presentation_id", table_name="commercial_margins")
    op.drop_index("idx_commercial_margins_material_id", table_name="commercial_margins")
    op.drop_index("idx_commercial_margins_scope_activo", table_name="commercial_margins")
    op.drop_table("commercial_margins")
