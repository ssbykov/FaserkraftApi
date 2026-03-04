"""добавлена performed_by_id performed_at в модель

Revision ID: fc95e5f16577
Revises: a40341f38a1a
Create Date: 2026-03-04 14:42:10.549937

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "fc95e5f16577"
down_revision: Union[str, None] = "a40341f38a1a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "packaging", sa.Column("performed_by_id", sa.Integer(), nullable=True)
    )
    op.add_column(
        "packaging",
        sa.Column("performed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        op.f("fk_packaging_performed_by_id_employees"),
        "packaging",
        "employees",
        ["performed_by_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_packaging_performed_by_id_employees"),
        "packaging",
        type_="foreignkey",
    )
    op.drop_column("packaging", "performed_at")
    op.drop_column("packaging", "performed_by_id")
