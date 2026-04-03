"""Add signals column to product_analyses

Revision ID: a335b2dc6b17
Revises: 0006
Create Date: 2026-04-03 23:00:36.626622

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a335b2dc6b17'
down_revision: Union[str, None] = '0006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('product_analyses', sa.Column('signals', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('product_analyses', 'signals')
