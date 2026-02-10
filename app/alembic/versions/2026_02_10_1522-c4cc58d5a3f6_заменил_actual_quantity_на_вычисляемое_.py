"""заменил actual_quantity на вычисляемое значение

Revision ID: c4cc58d5a3f6
Revises: 9e48720055a4
Create Date: 2026-02-10 15:22:13.135588

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c4cc58d5a3f6"
down_revision: Union[str, None] = "9e48720055a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("daily_plan_steps", "actual_quantity")


def downgrade() -> None:
    op.add_column(
        "daily_plan_steps",
        sa.Column(
            "actual_quantity",
            sa.INTEGER(),
            autoincrement=False,
            nullable=False,
        ),
    )
