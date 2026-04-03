"""Add role column to users

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("role", sa.Text(), server_default="user", nullable=False),
    )
    # Seed admin — idempotent: 0 rows if email doesn't exist
    op.execute("UPDATE users SET role = 'admin' WHERE email = 'aleksandre@alpo.ai'")


def downgrade() -> None:
    op.drop_column("users", "role")
