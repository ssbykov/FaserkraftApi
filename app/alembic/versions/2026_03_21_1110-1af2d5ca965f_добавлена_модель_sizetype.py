"""добавлена модель SizeType

Revision ID: 1af2d5ca965f
Revises: fc95e5f16577
Create Date: 2026-03-21 11:10:05.200558

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1af2d5ca965f"
down_revision: Union[str, None] = "fc95e5f16577"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "size_type",
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("packaging_count", sa.Integer(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_size_type")),
        sa.UniqueConstraint("name", name=op.f("uq_size_type_name")),
    )
    op.create_index(op.f("ix_size_type_id"), "size_type", ["id"], unique=True)
    op.add_column("processes", sa.Column("size_type_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        op.f("fk_processes_size_type_id_size_type"),
        "processes",
        "size_type",
        ["size_type_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_processes_size_type_id_size_type"),
        "processes",
        type_="foreignkey",
    )
    op.drop_column("processes", "size_type_id")
    op.drop_index(op.f("ix_size_type_id"), table_name="size_type")
    op.drop_table("size_type")
