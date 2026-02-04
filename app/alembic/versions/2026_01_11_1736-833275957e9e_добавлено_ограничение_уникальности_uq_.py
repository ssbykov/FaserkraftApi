"""добавлено ограничение уникальности uq_daily_plans_employee_date

Revision ID: 833275957e9e
Revises: 90c2c7db9500
Create Date: 2026-01-11 17:36:01.401752

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "833275957e9e"
down_revision: Union[str, None] = "90c2c7db9500"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_daily_plans_employee_date", "daily_plans", ["employee_id", "date"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_daily_plans_employee_date", "daily_plans", type_="unique")
