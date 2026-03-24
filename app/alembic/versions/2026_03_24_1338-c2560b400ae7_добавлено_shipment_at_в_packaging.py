"""добавлено shipment_at в Packaging

Revision ID: c2560b400ae7
Revises: 1af2d5ca965f
Create Date: 2026-03-24 13:38:37.441866

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c2560b400ae7"
down_revision: Union[str, None] = "1af2d5ca965f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "packaging",
        sa.Column("shipment_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("packaging", "shipment_at")
