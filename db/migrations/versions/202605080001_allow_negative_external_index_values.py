"""allow negative external index values

Revision ID: 202605080001
Revises: 202605050001
Create Date: 2026-05-08 00:01:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "202605080001"
down_revision: str | None = "202605050001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("external_index_values_value_nonnegative", "external_index_values", type_="check")


def downgrade() -> None:
    op.create_check_constraint(
        "external_index_values_value_nonnegative",
        "external_index_values",
        "value >= 0",
    )
