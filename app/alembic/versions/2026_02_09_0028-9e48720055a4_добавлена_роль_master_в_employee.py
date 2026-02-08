"""добавлена роль master в Employee

Revision ID: 9e48720055a4
Revises: 833275957e9e
Create Date: 2026-02-09 00:28:45.977928

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9e48720055a4"
down_revision: Union[str, None] = "833275957e9e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE role_enum ADD VALUE 'master'")


def downgrade() -> None:
    pass
