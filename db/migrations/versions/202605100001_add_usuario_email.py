"""add usuario email

Revision ID: 202605100001
Revises: 202605090001
Create Date: 2026-05-10 00:01:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202605100001"
down_revision: str | None = "202605090001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("usuarios", sa.Column("email", sa.String(length=160), nullable=True))
    op.create_unique_constraint("usuarios_email_key", "usuarios", ["email"])


def downgrade() -> None:
    op.drop_constraint("usuarios_email_key", "usuarios", type_="unique")
    op.drop_column("usuarios", "email")
