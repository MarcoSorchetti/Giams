"""add indexes on date columns and movimenti.cliente_id

Revision ID: e1f2a3b4c5d6
Revises: d9e2f3a4b5c6
Create Date: 2026-03-04 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, None] = 'd9e2f3a4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(op.f('ix_raccolte_data_raccolta'), 'raccolte', ['data_raccolta'], unique=False)
    op.create_index(op.f('ix_vendite_data_vendita'), 'vendite', ['data_vendita'], unique=False)
    op.create_index(op.f('ix_movimenti_magazzino_data_movimento'), 'movimenti_magazzino', ['data_movimento'], unique=False)
    op.create_index(op.f('ix_movimenti_magazzino_cliente_id'), 'movimenti_magazzino', ['cliente_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_movimenti_magazzino_cliente_id'), table_name='movimenti_magazzino')
    op.drop_index(op.f('ix_movimenti_magazzino_data_movimento'), table_name='movimenti_magazzino')
    op.drop_index(op.f('ix_vendite_data_vendita'), table_name='vendite')
    op.drop_index(op.f('ix_raccolte_data_raccolta'), table_name='raccolte')
