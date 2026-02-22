"""добавил status в Product

Revision ID: af89605984bc
Revises: c4cc58d5a3f6
Create Date: 2026-02-22 18:28:17.275771

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "af89605984bc"
down_revision: Union[str, None] = "c4cc58d5a3f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


product_status_enum = postgresql.ENUM(
    "normal", "scrap", "rework", name="product_status_enum"
)

def upgrade() -> None:
    product_status_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "products",
        sa.Column(
            "status",
            product_status_enum,
            nullable=False,
            server_default="normal",
        ),
    )


def downgrade() -> None:
    op.drop_column("products", "status")
