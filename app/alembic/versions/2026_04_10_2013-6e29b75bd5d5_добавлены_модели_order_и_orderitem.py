"""добавлены модели Order и OrderItem

Revision ID: 6e29b75bd5d5
Revises: 631a54493b5c
Create Date: 2026-04-10 20:13:54.829600

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "6e29b75bd5d5"
down_revision: Union[str, None] = "631a54493b5c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "orders",
        sa.Column("contract_number", sa.String(), nullable=False),
        sa.Column("contract_date", sa.Date(), nullable=False),
        sa.Column("planned_shipment_date", sa.Date(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_orders")),
    )
    op.create_index(op.f("ix_orders_id"), "orders", ["id"], unique=True)
    op.create_table(
        "order_items",
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("process_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "quantity > 0", name=op.f("ck_order_items_quantity_positive")
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            name=op.f("fk_order_items_order_id_orders"),
        ),
        sa.ForeignKeyConstraint(
            ["process_id"],
            ["processes.id"],
            name=op.f("fk_order_items_process_id_processes"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_order_items")),
    )
    op.create_index(
        op.f("ix_order_items_id"), "order_items", ["id"], unique=True
    )
    op.add_column(
        "packaging", sa.Column("order_id", sa.Integer(), nullable=True)
    )
    op.create_foreign_key(
        op.f("fk_packaging_order_id_orders"),
        "packaging",
        "orders",
        ["order_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_packaging_order_id_orders"), "packaging", type_="foreignkey"
    )
    op.drop_column("packaging", "order_id")
    op.drop_index(op.f("ix_order_items_id"), table_name="order_items")
    op.drop_table("order_items")
    op.drop_index(op.f("ix_orders_id"), table_name="orders")
    op.drop_table("orders")
