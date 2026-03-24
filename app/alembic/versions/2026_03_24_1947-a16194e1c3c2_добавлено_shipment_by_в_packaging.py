"""добавлено shipment_by в Packaging

Revision ID: a16194e1c3c2
Revises: c2560b400ae7
Create Date: 2026-03-24 19:47:01.494062

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a16194e1c3c2"
down_revision: Union[str, None] = "c2560b400ae7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "packaging", sa.Column("shipment_by_id", sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        op.f("fk_packaging_shipment_by_id_employees"),
        "packaging",
        "employees",
        ["shipment_by_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_packaging_shipment_by_id_employees"),
        "packaging",
        type_="foreignkey",
    )
    op.drop_column("packaging", "shipment_by_id")
