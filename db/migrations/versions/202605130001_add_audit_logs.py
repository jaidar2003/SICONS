"""add audit logs

Revision ID: 202605130001
Revises: 202605100001
Create Date: 2026-05-13 00:01:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "202605130001"
down_revision: str | None = "202605100001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("usuario_id", sa.BigInteger(), nullable=True),
        sa.Column("accion", sa.String(length=50), nullable=False),
        sa.Column("recurso", sa.String(length=50), nullable=False),
        sa.Column("recurso_id", sa.String(length=100), nullable=True),
        sa.Column("cambios", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], name="audit_logs_usuario_id_fkey"),
    )
    op.create_index("idx_audit_logs_usuario_id", "audit_logs", ["usuario_id"])
    op.create_index("idx_audit_logs_created_at", "audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("idx_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("idx_audit_logs_usuario_id", table_name="audit_logs")
    op.drop_table("audit_logs")
