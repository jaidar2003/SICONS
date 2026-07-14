"""reconcile alerts and identifier types

Revision ID: 202607140001
Revises: 202606190001
Create Date: 2026-07-14 15:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202607140001"
down_revision: str | None = "202606190001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("chat_conversations_material_actual_id_fkey", "chat_conversations", type_="foreignkey")
    op.alter_column("chat_conversations", "material_actual_id", existing_type=sa.Integer(), type_=sa.BigInteger())
    op.create_foreign_key(
        "chat_conversations_material_actual_id_fkey",
        "chat_conversations",
        "materiales",
        ["material_actual_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.drop_constraint("chat_messages_material_resuelto_id_fkey", "chat_messages", type_="foreignkey")
    op.alter_column("chat_messages", "material_resuelto_id", existing_type=sa.Integer(), type_=sa.BigInteger())
    op.create_foreign_key(
        "chat_messages_material_resuelto_id_fkey",
        "chat_messages",
        "materiales",
        ["material_resuelto_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "alertas",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("usuario_id", sa.BigInteger(), nullable=True),
        sa.Column("material_id", sa.BigInteger(), nullable=True),
        sa.Column("tipo", sa.String(length=50), nullable=False),
        sa.Column("prioridad", sa.String(length=20), nullable=False),
        sa.Column("titulo", sa.String(length=200), nullable=False),
        sa.Column("mensaje", sa.Text(), nullable=False),
        sa.Column("data_context", sa.Text(), nullable=True),
        sa.Column("leida", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint(
            "tipo IN ('OPORTUNIDAD_COMPRA', 'DESVIO_PRECIO', 'DETERIORO_CONFIANZA')",
            name="alertas_tipo_allowed",
        ),
        sa.CheckConstraint("prioridad IN ('ALTA', 'MEDIA', 'BAJA')", name="alertas_prioridad_allowed"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], name="alertas_usuario_id_fkey", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["material_id"], ["materiales.id"], name="alertas_material_id_fkey", ondelete="CASCADE"),
    )
    op.create_index("idx_alertas_usuario_leida", "alertas", ["usuario_id", "leida"])
    op.create_index("idx_alertas_material_id", "alertas", ["material_id"])
    op.execute("CREATE INDEX idx_alertas_created_at ON alertas(created_at DESC)")


def downgrade() -> None:
    op.drop_index("idx_alertas_created_at", table_name="alertas")
    op.drop_index("idx_alertas_material_id", table_name="alertas")
    op.drop_index("idx_alertas_usuario_leida", table_name="alertas")
    op.drop_table("alertas")

    op.drop_constraint("chat_messages_material_resuelto_id_fkey", "chat_messages", type_="foreignkey")
    op.alter_column("chat_messages", "material_resuelto_id", existing_type=sa.BigInteger(), type_=sa.Integer())
    op.create_foreign_key(
        "chat_messages_material_resuelto_id_fkey",
        "chat_messages",
        "materiales",
        ["material_resuelto_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.drop_constraint("chat_conversations_material_actual_id_fkey", "chat_conversations", type_="foreignkey")
    op.alter_column("chat_conversations", "material_actual_id", existing_type=sa.BigInteger(), type_=sa.Integer())
    op.create_foreign_key(
        "chat_conversations_material_actual_id_fkey",
        "chat_conversations",
        "materiales",
        ["material_actual_id"],
        ["id"],
        ondelete="SET NULL",
    )
