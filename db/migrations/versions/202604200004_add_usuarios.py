"""add usuarios

Revision ID: 202604200004
Revises: 202604200003
Create Date: 2026-04-20 00:00:04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202604200004"
down_revision: str | None = "202604200003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "usuarios",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("password_hash", sa.String(length=220), nullable=False),
        sa.Column("rol", sa.String(length=20), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("rol IN ('admin', 'cliente')", name="usuarios_rol_allowed"),
        sa.CheckConstraint("btrim(username::text) <> ''::text", name="usuarios_username_not_blank"),
        sa.UniqueConstraint("username", name="usuarios_username_key"),
    )


def downgrade() -> None:
    op.drop_table("usuarios")
