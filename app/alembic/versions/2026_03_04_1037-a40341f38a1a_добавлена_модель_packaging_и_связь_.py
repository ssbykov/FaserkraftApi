"""добавлена модель packaging и связь  product packaging

Revision ID: a40341f38a1a
Revises: af89605984bc
Create Date: 2026-03-04 10:37:39.994825

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a40341f38a1a"
down_revision: Union[str, None] = "af89605984bc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "packaging",
        sa.Column("serial_number", sa.String(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_packaging")),
        sa.UniqueConstraint("serial_number", name=op.f("uq_packaging_serial_number")),
    )
    op.create_index(op.f("ix_packaging_id"), "packaging", ["id"], unique=True)
    op.add_column("products", sa.Column("packaging_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        op.f("fk_products_packaging_id_packaging"),
        "products",
        "packaging",
        ["packaging_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_products_packaging_id_packaging"),
        "products",
        type_="foreignkey",
    )
    op.drop_column("products", "packaging_id")
    op.drop_index(op.f("ix_packaging_id"), table_name="packaging")
    op.drop_table("packaging")
