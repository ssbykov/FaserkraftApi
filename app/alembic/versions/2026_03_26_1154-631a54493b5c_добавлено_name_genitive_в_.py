"""добавлено name_genitive в StepTemplateRead

Revision ID: 631a54493b5c
Revises: a16194e1c3c2
Create Date: 2026-03-26 11:54:34.284256

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "631a54493b5c"
down_revision: Union[str, None] = "a16194e1c3c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "step_templates",
        sa.Column("name_genitive", sa.String(), nullable=True),
    )
    op.execute("""
        UPDATE step_templates
        SET name_genitive = name
        WHERE name_genitive IS NULL
        """)
    op.alter_column("step_templates", "name_genitive", nullable=False)


def downgrade() -> None:
    op.drop_column("step_templates", "name_genitive")

