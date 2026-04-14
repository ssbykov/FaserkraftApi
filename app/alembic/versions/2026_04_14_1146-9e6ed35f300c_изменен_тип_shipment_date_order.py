"""изменен тип shipment_date Order

Revision ID: 9e6ed35f300c
Revises: 8ca668de3a27
Create Date: 2026-04-14 11:46:11.855914

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "9e6ed35f300c"
down_revision: Union[str, None] = "8ca668de3a27"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "orders",
        "planned_shipment_date",
        existing_type=sa.DATE(),
        nullable=False,
    )
    op.alter_column(
        "orders",
        "shipment_date",
        existing_type=sa.DATE(),
        type_=sa.DateTime(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "orders",
        "shipment_date",
        existing_type=sa.DateTime(),
        type_=sa.DATE(),
        existing_nullable=True,
    )
    op.alter_column(
        "orders",
        "planned_shipment_date",
        existing_type=sa.DATE(),
        nullable=True,
    )
