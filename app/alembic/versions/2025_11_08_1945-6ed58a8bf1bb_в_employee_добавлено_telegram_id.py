"""в Employee добавлено telegram_id

Revision ID: 6ed58a8bf1bb
Revises: f2318fd2b927
Create Date: 2025-11-08 19:45:06.836543

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6ed58a8bf1bb"
down_revision: Union[str, None] = "f2318fd2b927"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("employees", sa.Column("telegram_id", sa.String(), nullable=True))
    op.create_unique_constraint(
        op.f("uq_employees_telegram_id"), "employees", ["telegram_id"]
    )


def downgrade() -> None:
    op.drop_constraint(op.f("uq_employees_telegram_id"), "employees", type_="unique")
    op.drop_column("employees", "telegram_id")
