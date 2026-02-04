"""добавлена модель DailyPlanStep

Revision ID: 90c2c7db9500
Revises: f1834d497584
Create Date: 2025-12-07 23:21:09.493598

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "90c2c7db9500"
down_revision: Union[str, None] = "f1834d497584"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "daily_plan_steps",
        sa.Column("daily_plan_id", sa.Integer(), nullable=False),
        sa.Column("step_definition_id", sa.Integer(), nullable=False),
        sa.Column("planned_quantity", sa.Integer(), nullable=False),
        sa.Column("actual_quantity", sa.Integer(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["daily_plan_id"],
            ["daily_plans.id"],
            name=op.f("fk_daily_plan_steps_daily_plan_id_daily_plans"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["step_definition_id"],
            ["step_definitions.id"],
            name=op.f("fk_daily_plan_steps_step_definition_id_step_definitions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_daily_plan_steps")),
    )
    op.create_index(
        op.f("ix_daily_plan_steps_id"), "daily_plan_steps", ["id"], unique=True
    )
    op.drop_column("daily_plans", "planned_steps")
    op.drop_column("daily_plans", "actual_steps")


def downgrade() -> None:
    op.add_column(
        "daily_plans",
        sa.Column("actual_steps", sa.INTEGER(), autoincrement=False, nullable=False),
    )
    op.add_column(
        "daily_plans",
        sa.Column("planned_steps", sa.INTEGER(), autoincrement=False, nullable=False),
    )
    op.drop_index(op.f("ix_daily_plan_steps_id"), table_name="daily_plan_steps")
    op.drop_table("daily_plan_steps")
