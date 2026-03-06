"""Aggiunge indici mancanti su colonne di JOIN frequenti

Revision ID: g1a2b3c4d5e6
Revises: f3a4b5c6d7e8
Create Date: 2026-03-06

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'g1a2b3c4d5e6'
down_revision: Union[str, None] = 'f3a4b5c6d7e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index('ix_vendita_righe_vendita_id', 'vendita_righe', ['vendita_id'], if_not_exists=True)
    op.create_index('ix_confezionamento_lotti_confezionamento_id', 'confezionamento_lotti', ['confezionamento_id'], if_not_exists=True)
    op.create_index('ix_raccolta_parcelle_raccolta_id', 'raccolta_parcelle', ['raccolta_id'], if_not_exists=True)
    op.create_index('ix_costi_anno_campagna', 'costi', ['anno_campagna'], if_not_exists=True)


def downgrade() -> None:
    op.drop_index('ix_costi_anno_campagna', table_name='costi')
    op.drop_index('ix_raccolta_parcelle_raccolta_id', table_name='raccolta_parcelle')
    op.drop_index('ix_confezionamento_lotti_confezionamento_id', table_name='confezionamento_lotti')
    op.drop_index('ix_vendita_righe_vendita_id', table_name='vendita_righe')
