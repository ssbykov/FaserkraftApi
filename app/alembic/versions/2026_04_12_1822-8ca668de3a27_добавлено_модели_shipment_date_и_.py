"""добавлено модели shipment_date и shipment_by_id в  Order

Revision ID: 8ca668de3a27
Revises: 6e29b75bd5d5
Create Date: 2026-04-12 18:22:48.189910

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "8ca668de3a27"
down_revision: Union[str, None] = "6e29b75bd5d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "orders", sa.Column("shipment_date", sa.Date(), nullable=True)
    )
    op.add_column(
        "orders", sa.Column("shipment_by_id", sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        op.f("fk_orders_shipment_by_id_employees"),
        "orders",
        "employees",
        ["shipment_by_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_orders_shipment_by_id_employees"),
        "orders",
        type_="foreignkey",
    )
    op.drop_column("orders", "shipment_by_id")
    op.drop_column("orders", "shipment_date")
