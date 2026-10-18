"""mobile session refresh tokens

Revision ID: f7895dca1761
Revises: 0bbb096cc6eb
Create Date: 2026-10-18 11:34:31.220102

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "f7895dca1761"
down_revision: Union[str, None] = "0bbb096cc6eb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "mobile_sessions",
        sa.Column("refresh_token_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "mobile_sessions",
        sa.Column(
            "prev_refresh_token_hash", sa.String(length=64), nullable=True
        ),
    )
    op.create_index(
        op.f("ix_mobile_sessions_prev_refresh_token_hash"),
        "mobile_sessions",
        ["prev_refresh_token_hash"],
        unique=False,
    )
    op.create_unique_constraint(
        op.f("uq_mobile_sessions_refresh_token_hash"),
        "mobile_sessions",
        ["refresh_token_hash"],
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("uq_mobile_sessions_refresh_token_hash"),
        "mobile_sessions",
        type_="unique",
    )
    op.drop_index(
        op.f("ix_mobile_sessions_prev_refresh_token_hash"),
        table_name="mobile_sessions",
    )
    op.drop_column("mobile_sessions", "prev_refresh_token_hash")
    op.drop_column("mobile_sessions", "refresh_token_hash")

