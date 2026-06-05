"""add chat conversations

Revision ID: 202606050001
Revises: 202605130001
Create Date: 2026-06-05 00:01:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "202606050001"
down_revision: str | None = "202605130001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chat_conversations",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("usuario_id", sa.BigInteger(), nullable=False),
        sa.Column("titulo", sa.String(length=160), nullable=False),
        sa.Column("material_actual_id", sa.Integer(), nullable=True),
        sa.Column("horizonte_actual", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("trim(titulo) <> ''", name="chat_conversations_titulo_not_blank"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], name="chat_conversations_usuario_id_fkey", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["material_actual_id"], ["materiales.id"], name="chat_conversations_material_actual_id_fkey", ondelete="SET NULL"),
    )
    op.create_index("idx_chat_conversations_usuario_updated", "chat_conversations", ["usuario_id", "updated_at"])
    op.create_index("idx_chat_conversations_usuario_archived", "chat_conversations", ["usuario_id", "archived_at"])

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("conversation_id", sa.BigInteger(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tipo_intencion", sa.String(length=30), nullable=True),
        sa.Column("contexto_usado", sa.Boolean(), nullable=True),
        sa.Column("fuentes_recuperadas", sa.JSON(), nullable=True),
        sa.Column("fuentes_evidencia", sa.JSON(), nullable=True),
        sa.Column("material_resuelto_id", sa.Integer(), nullable=True),
        sa.Column("material_resuelto", sa.String(length=160), nullable=True),
        sa.Column("horizonte_resuelto", sa.Integer(), nullable=True),
        sa.Column("visualizacion_sugerida", sa.JSON(), nullable=True),
        sa.Column("proveedor_ia", sa.String(length=40), nullable=True),
        sa.Column("fallback_usado", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("role IN ('user', 'assistant')", name="chat_messages_role_allowed"),
        sa.CheckConstraint("trim(content) <> ''", name="chat_messages_content_not_blank"),
        sa.ForeignKeyConstraint(["conversation_id"], ["chat_conversations.id"], name="chat_messages_conversation_id_fkey", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["material_resuelto_id"], ["materiales.id"], name="chat_messages_material_resuelto_id_fkey", ondelete="SET NULL"),
    )
    op.create_index("idx_chat_messages_conversation_created", "chat_messages", ["conversation_id", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_chat_messages_conversation_created", table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_index("idx_chat_conversations_usuario_archived", table_name="chat_conversations")
    op.drop_index("idx_chat_conversations_usuario_updated", table_name="chat_conversations")
    op.drop_table("chat_conversations")
