"""add employee_norm_calculations table

Revision ID: 95681b56d14e
Revises: 83124da12c46
Create Date: 2026-09-15 09:18:00.654748

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "95681b56d14e"
down_revision: Union[str, None] = "83124da12c46"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "employee_norm_calculations",
        sa.Column("step_definition_id", sa.Integer(), nullable=False),
        sa.Column(
            "date",
            sa.Date(),
            server_default=sa.text("CURRENT_DATE"),
            nullable=False,
        ),
        sa.Column(
            "salary_rate", sa.Numeric(precision=12, scale=2), nullable=False
        ),
        sa.Column(
            "difficulty_coefficient",
            sa.Numeric(precision=6, scale=3),
            nullable=False,
        ),
        sa.Column(
            "daily_norm", sa.Numeric(precision=10, scale=2), nullable=False
        ),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["step_definition_id"],
            ["step_definitions.id"],
            name=op.f(
                "fk_employee_norm_calculations_step_definition_id_step_definitions"
            ),
        ),
        sa.PrimaryKeyConstraint(
            "id", name=op.f("pk_employee_norm_calculations")
        ),
    )
    op.create_index(
        op.f("ix_employee_norm_calculations_id"),
        "employee_norm_calculations",
        ["id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_employee_norm_calculations_step_definition_id"),
        "employee_norm_calculations",
        ["step_definition_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_employee_norm_calculations_step_definition_id"),
        table_name="employee_norm_calculations",
    )
    op.drop_index(
        op.f("ix_employee_norm_calculations_id"),
        table_name="employee_norm_calculations",
    )
    op.drop_table("employee_norm_calculations")
