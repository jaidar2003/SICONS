"""relax precio historico uniqueness

Revision ID: 202604200003
Revises: 202604200002
Create Date: 2026-04-20 00:00:03
"""

from collections.abc import Sequence

from alembic import op


revision: str = "202604200003"
down_revision: str | None = "202604200002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "precios_historicos_material_presentacion_fecha_fuente_unique",
        "precios_historicos",
        type_="unique",
    )
    op.create_index(
        "idx_precios_historicos_material_presentacion_fecha_fuente",
        "precios_historicos",
        ["material_id", "presentacion_id", "fecha", "fuente_id"],
    )


def downgrade() -> None:
    op.drop_index("idx_precios_historicos_material_presentacion_fecha_fuente", table_name="precios_historicos")
    op.create_unique_constraint(
        "precios_historicos_material_presentacion_fecha_fuente_unique",
        "precios_historicos",
        ["material_id", "presentacion_id", "fecha", "fuente_id"],
    )
