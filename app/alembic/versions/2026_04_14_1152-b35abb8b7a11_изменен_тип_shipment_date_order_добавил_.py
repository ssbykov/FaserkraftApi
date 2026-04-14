"""изменен тип shipment_date Order добавил зону

Revision ID: b35abb8b7a11
Revises: 9e6ed35f300c
Create Date: 2026-04-14 11:52:06.962086

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b35abb8b7a11"
down_revision: Union[str, None] = "9e6ed35f300c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "orders",
        "shipment_date",
        existing_type=postgresql.TIMESTAMP(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "orders",
        "shipment_date",
        existing_type=sa.DateTime(timezone=True),
        type_=postgresql.TIMESTAMP(),
        existing_nullable=True,
    )
