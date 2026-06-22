"""add chat provider settings and material resolution source

Revision ID: 202606190001
Revises: 202606050001
Create Date: 2026-06-19 00:01:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202606190001"
down_revision: str | None = "202606050001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("chat_messages", sa.Column("material_resolution_source", sa.String(length=30), nullable=True))
    op.create_table(
        "chat_provider_settings",
        sa.Column("key", sa.String(length=40), primary_key=True),
        sa.Column("proveedor_activo", sa.String(length=20), nullable=False),
        sa.Column("modelo_facultad", sa.String(length=200), nullable=True),
        sa.Column("modelo_claude", sa.String(length=200), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )


def downgrade() -> None:
    op.drop_table("chat_provider_settings")
    op.drop_column("chat_messages", "material_resolution_source")
