"""Add user_id to scans and product_analyses

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "scans",
        sa.Column("user_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_scans_user_id",
        "scans",
        "users",
        ["user_id"],
        ["id"],
    )

    op.add_column(
        "product_analyses",
        sa.Column("user_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_product_analyses_user_id",
        "product_analyses",
        "users",
        ["user_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_product_analyses_user_id", "product_analyses", type_="foreignkey")
    op.drop_column("product_analyses", "user_id")

    op.drop_constraint("fk_scans_user_id", "scans", type_="foreignkey")
    op.drop_column("scans", "user_id")
