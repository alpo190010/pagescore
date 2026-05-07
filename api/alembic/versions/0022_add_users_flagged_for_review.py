"""Add ``flagged_for_review`` column to users for chargeback fraud review.

Set to true by the Paddle webhook when an ``adjustment.created`` event with
``action="chargeback"`` is processed. The flag has no automatic side-effect
on access (the chargeback already revokes the relevant store_subscriptions
row); it exists so admins / future automation can identify users with prior
chargebacks for extra scrutiny on subsequent purchases.

Revision ID: 0022
Revises: 0021
Create Date: 2026-05-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0022"
down_revision: Union[str, None] = "0021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "flagged_for_review",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "flagged_for_review")
