"""sync nullable constraints and product steps fk

Revision ID: c07762c3efe3
Revises: 16b1dca052a5
Create Date: 2026-09-17 17:49:57.647017

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c07762c3efe3"
down_revision: Union[str, None] = "16b1dca052a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "devices", "is_active", existing_type=sa.BOOLEAN(), nullable=False
    )
    op.alter_column(
        "devices",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.execute(
        "ALTER TABLE product_steps "
        "DROP CONSTRAINT IF EXISTS fk_product_steps_step_definition_id_step_definitions"
    )
    op.create_foreign_key(
        op.f("fk_product_steps_step_definition_id_step_definitions"),
        "product_steps",
        "step_definitions",
        ["step_definition_id"],
        ["id"],
    )
    op.create_index(
        op.f("ix_production_calendar_days_id"),
        "production_calendar_days",
        ["id"],
        unique=True,
    )
    op.alter_column(
        "products",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "yandex_tokens",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=False,
    )

def downgrade() -> None:
    op.alter_column(
        "yandex_tokens",
        "updated_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
    )
    op.alter_column(
        "products",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text("now()"),
    )
    op.drop_index(
        op.f("ix_production_calendar_days_id"),
        table_name="production_calendar_days",
    )
    op.drop_constraint(
        op.f("fk_product_steps_step_definition_id_step_definitions"),
        "product_steps",
        type_="foreignkey",
    )
    op.alter_column(
        "devices",
        "created_at",
        existing_type=postgresql.TIMESTAMP(timezone=True),
        nullable=True,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "devices", "is_active", existing_type=sa.BOOLEAN(), nullable=True
    )

