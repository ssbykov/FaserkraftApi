"""create production_calendar_days table

Revision ID: 16b1dca052a5
Revises: 95681b56d14e
Create Date: 2026-09-17 13:56:12.127345

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "16b1dca052a5"
down_revision: Union[str, None] = "95681b56d14e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "production_calendar_days",
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("is_working", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint(
            "id", name=op.f("pk_production_calendar_days")
        ),
        sa.UniqueConstraint("day", name="uq_production_calendar_days_day"),
    )
    op.create_index(
        op.f("ix_production_calendar_days_day"),
        "production_calendar_days",
        ["day"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_production_calendar_days_day"),
        table_name="production_calendar_days",
    )
    op.drop_table("production_calendar_days")
