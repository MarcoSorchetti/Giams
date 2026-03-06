"""add_stato_riscontro_to_costi

Revision ID: 1c12a60738b9
Revises: h1a2b3c4d5e6
Create Date: 2026-03-06 23:39:29.789549

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '1c12a60738b9'
down_revision: Union[str, None] = 'h1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('costi', sa.Column('stato_riscontro', sa.String(length=20), server_default='da_riscontrare', nullable=False))


def downgrade() -> None:
    op.drop_column('costi', 'stato_riscontro')
