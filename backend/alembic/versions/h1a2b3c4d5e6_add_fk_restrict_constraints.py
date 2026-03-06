"""Aggiunge ondelete RESTRICT sulle FK critiche per prevenire dati orfani

Revision ID: h1a2b3c4d5e6
Revises: g1a2b3c4d5e6
Create Date: 2026-03-06

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'h1a2b3c4d5e6'
down_revision: Union[str, None] = 'g1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# FK da modificare: (constraint_name, table, column, ref_table, ref_column, new_rule, old_rule)
_FK_CHANGES = [
    ('vendite_cliente_id_fkey', 'vendite', ['cliente_id'], 'clienti', ['id'], 'RESTRICT', None),
    ('costi_categoria_id_fkey', 'costi', ['categoria_id'], 'categorie_costo', ['id'], 'RESTRICT', None),
    ('costi_fornitore_id_fkey', 'costi', ['fornitore_id'], 'fornitori', ['id'], 'RESTRICT', None),
    ('movimenti_magazzino_confezionamento_id_fkey', 'movimenti_magazzino', ['confezionamento_id'], 'confezionamenti', ['id'], 'RESTRICT', None),
    ('movimenti_magazzino_cliente_id_fkey', 'movimenti_magazzino', ['cliente_id'], 'clienti', ['id'], 'RESTRICT', None),
    ('vendita_righe_confezionamento_id_fkey', 'vendita_righe', ['confezionamento_id'], 'confezionamenti', ['id'], 'RESTRICT', 'CASCADE'),
]


def upgrade() -> None:
    for name, table, cols, ref_table, ref_cols, new_rule, _old in _FK_CHANGES:
        op.drop_constraint(name, table, type_='foreignkey')
        op.create_foreign_key(name, table, ref_table, cols, ref_cols, ondelete=new_rule)


def downgrade() -> None:
    for name, table, cols, ref_table, ref_cols, _new, old_rule in _FK_CHANGES:
        op.drop_constraint(name, table, type_='foreignkey')
        op.create_foreign_key(name, table, ref_table, cols, ref_cols, ondelete=old_rule)
