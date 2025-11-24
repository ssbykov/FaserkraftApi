"""добавлена Device

Revision ID: 1138f71642a1
Revises: 6ed58a8bf1bb
Create Date: 2025-11-24 17:38:54.624709

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1138f71642a1"
down_revision: Union[str, None] = "6ed58a8bf1bb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "devices",
        sa.Column("deviceId", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("manufacturer", sa.String(), nullable=False),
        sa.Column("androidVersion", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_devices")),
        sa.UniqueConstraint("deviceId", name=op.f("uq_devices_deviceId")),
    )
    op.create_index(op.f("ix_devices_id"), "devices", ["id"], unique=True)
    op.add_column("employees", sa.Column("device_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        op.f("fk_employees_device_id_devices"),
        "employees",
        "devices",
        ["device_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_employees_device_id_devices"), "employees", type_="foreignkey"
    )
    op.drop_column("employees", "device_id")
    op.drop_index(op.f("ix_devices_id"), table_name="devices")
    op.drop_table("devices")
