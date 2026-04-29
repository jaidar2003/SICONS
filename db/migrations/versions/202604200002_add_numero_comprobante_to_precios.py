"""add numero comprobante to precios

Revision ID: 202604200002
Revises: 202604200001
Create Date: 2026-04-20 00:00:02
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "202604200002"
down_revision: str | None = "202604200001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("precios_historicos", sa.Column("numero_comprobante", sa.String(length=50), nullable=True))
    op.create_index(
        "idx_precios_historicos_fuente_comprobante_unique",
        "precios_historicos",
        ["fuente_id", "numero_comprobante"],
        unique=True,
        postgresql_where=sa.text("numero_comprobante IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("idx_precios_historicos_fuente_comprobante_unique", table_name="precios_historicos")
    op.drop_column("precios_historicos", "numero_comprobante")
