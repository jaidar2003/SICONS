"""add external indices and imputation metadata

Revision ID: 202605050001
Revises: 202604200004
Create Date: 2026-05-05 00:00:01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202605050001"
down_revision: str | None = "202604200004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "precios_historicos",
        sa.Column("origen_dato", sa.String(length=20), nullable=False, server_default="REAL"),
    )
    op.add_column(
        "precios_historicos",
        sa.Column("metodo_estimacion", sa.String(length=50), nullable=True),
    )
    op.create_check_constraint(
        "precios_historicos_origen_dato_allowed",
        "precios_historicos",
        "origen_dato IN ('REAL', 'ESTIMADO')",
    )

    op.create_table(
        "external_index_values",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("source_name", sa.String(length=50), nullable=False),
        sa.Column("series_id", sa.String(length=100), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("value", sa.Numeric(18, 6), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("value >= 0", name="external_index_values_value_nonnegative"),
        sa.UniqueConstraint("series_id", "date", name="external_index_values_series_date_unique"),
    )
    op.create_index("idx_external_index_values_source_name", "external_index_values", ["source_name"])
    op.create_index(
        "idx_external_index_values_series_date",
        "external_index_values",
        ["series_id", "date"],
    )


def downgrade() -> None:
    op.drop_index("idx_external_index_values_series_date", table_name="external_index_values")
    op.drop_index("idx_external_index_values_source_name", table_name="external_index_values")
    op.drop_table("external_index_values")
    op.drop_constraint("precios_historicos_origen_dato_allowed", "precios_historicos", type_="check")
    op.drop_column("precios_historicos", "metodo_estimacion")
    op.drop_column("precios_historicos", "origen_dato")
