"""добавлена модель для Яндекс токенов

Revision ID: f1834d497584
Revises: 6c0c32a63930
Create Date: 2025-12-07 13:40:14.272022

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f1834d497584"
down_revision: Union[str, None] = "6c0c32a63930"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "yandex_tokens",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("access_token", sa.String(), nullable=False),
        sa.Column("refresh_token", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_yandex_tokens")),
    )


def downgrade() -> None:
    op.drop_table("yandex_tokens")
