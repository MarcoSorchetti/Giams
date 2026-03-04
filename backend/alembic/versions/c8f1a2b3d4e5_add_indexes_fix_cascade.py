"""add missing indexes and fix CASCADE constraints

Revision ID: c8f1a2b3d4e5
Revises: 4aa7e85d7438
Create Date: 2026-03-03 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'c8f1a2b3d4e5'
down_revision: Union[str, None] = '4aa7e85d7438'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Indici mancanti ---
    op.create_index(op.f('ix_raccolte_anno_campagna'), 'raccolte', ['anno_campagna'], unique=False)
    op.create_index(op.f('ix_lotti_olio_anno_campagna'), 'lotti_olio', ['anno_campagna'], unique=False)
    op.create_index(op.f('ix_confezionamenti_anno_campagna'), 'confezionamenti', ['anno_campagna'], unique=False)
    op.create_index(op.f('ix_costi_categoria_id'), 'costi', ['categoria_id'], unique=False)
    op.create_index(op.f('ix_costi_fornitore_id'), 'costi', ['fornitore_id'], unique=False)
    op.create_index(op.f('ix_vendite_cliente_id'), 'vendite', ['cliente_id'], unique=False)
    op.create_index(op.f('ix_movimenti_magazzino_confezionamento_id'), 'movimenti_magazzino', ['confezionamento_id'], unique=False)

    # --- Fix CASCADE su raccolta_parcelle.parcella_id ---
    op.drop_constraint('raccolta_parcelle_parcella_id_fkey', 'raccolta_parcelle', type_='foreignkey')
    op.create_foreign_key(
        'raccolta_parcelle_parcella_id_fkey', 'raccolta_parcelle',
        'parcelle', ['parcella_id'], ['id'], ondelete='CASCADE',
    )

    # --- Fix CASCADE su vendita_righe.confezionamento_id ---
    op.drop_constraint('vendita_righe_confezionamento_id_fkey', 'vendita_righe', type_='foreignkey')
    op.create_foreign_key(
        'vendita_righe_confezionamento_id_fkey', 'vendita_righe',
        'confezionamenti', ['confezionamento_id'], ['id'], ondelete='CASCADE',
    )


def downgrade() -> None:
    # --- Rollback CASCADE ---
    op.drop_constraint('vendita_righe_confezionamento_id_fkey', 'vendita_righe', type_='foreignkey')
    op.create_foreign_key(
        'vendita_righe_confezionamento_id_fkey', 'vendita_righe',
        'confezionamenti', ['confezionamento_id'], ['id'],
    )

    op.drop_constraint('raccolta_parcelle_parcella_id_fkey', 'raccolta_parcelle', type_='foreignkey')
    op.create_foreign_key(
        'raccolta_parcelle_parcella_id_fkey', 'raccolta_parcelle',
        'parcelle', ['parcella_id'], ['id'],
    )

    # --- Rollback indici ---
    op.drop_index(op.f('ix_movimenti_magazzino_confezionamento_id'), table_name='movimenti_magazzino')
    op.drop_index(op.f('ix_vendite_cliente_id'), table_name='vendite')
    op.drop_index(op.f('ix_costi_fornitore_id'), table_name='costi')
    op.drop_index(op.f('ix_costi_categoria_id'), table_name='costi')
    op.drop_index(op.f('ix_confezionamenti_anno_campagna'), table_name='confezionamenti')
    op.drop_index(op.f('ix_lotti_olio_anno_campagna'), table_name='lotti_olio')
    op.drop_index(op.f('ix_raccolte_anno_campagna'), table_name='raccolte')
