"""добавлена уникальность поля device_id

Revision ID: 6c0c32a63930
Revises: 45e28112c2e4
Create Date: 2025-11-29 11:56:30.142467

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6c0c32a63930"
down_revision: Union[str, None] = "45e28112c2e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        op.f("uq_employees_device_id"), "employees", ["device_id"]
    )


def downgrade() -> None:
    op.drop_constraint(op.f("uq_employees_device_id"), "employees", type_="unique")
