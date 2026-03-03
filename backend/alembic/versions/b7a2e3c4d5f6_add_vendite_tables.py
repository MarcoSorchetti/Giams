"""add_vendite_tables

Revision ID: b7a2e3c4d5f6
Revises: fca5529f4f56
Create Date: 2026-03-03 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7a2e3c4d5f6'
down_revision: Union[str, None] = 'fca5529f4f56'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tabella vendite
    op.create_table(
        'vendite',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('codice', sa.String(20), nullable=False, unique=True, index=True),
        sa.Column('cliente_id', sa.Integer(), sa.ForeignKey('clienti.id'), nullable=False),
        sa.Column('data_vendita', sa.Date(), nullable=False),
        sa.Column('anno_campagna', sa.Integer(), nullable=False, index=True),
        sa.Column('stato', sa.String(15), nullable=False, server_default='bozza'),
        sa.Column('imponibile', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('sconto_percentuale', sa.Numeric(5, 2), nullable=True),
        sa.Column('imponibile_scontato', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('iva_percentuale', sa.Numeric(5, 2), nullable=False, server_default='4'),
        sa.Column('importo_iva', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('importo_totale', sa.Numeric(12, 2), nullable=False, server_default='0'),
        sa.Column('numero_fattura', sa.String(20), nullable=True, unique=True),
        sa.Column('data_pagamento', sa.Date(), nullable=True),
        sa.Column('modalita_pagamento', sa.String(50), nullable=True),
        sa.Column('riferimento_pagamento', sa.String(100), nullable=True),
        sa.Column('data_spedizione', sa.Date(), nullable=True),
        sa.Column('numero_ddt', sa.String(20), nullable=True),
        sa.Column('note_spedizione', sa.Text(), nullable=True),
        sa.Column('spedizione_indirizzo', sa.String(150), nullable=True),
        sa.Column('spedizione_cap', sa.String(5), nullable=True),
        sa.Column('spedizione_citta', sa.String(100), nullable=True),
        sa.Column('spedizione_provincia', sa.String(2), nullable=True),
        sa.Column('data_conferma', sa.Date(), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    # Tabella righe vendita
    op.create_table(
        'vendita_righe',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('vendita_id', sa.Integer(), sa.ForeignKey('vendite.id', ondelete='CASCADE'), nullable=False),
        sa.Column('confezionamento_id', sa.Integer(), sa.ForeignKey('confezionamenti.id'), nullable=False),
        sa.Column('quantita', sa.Integer(), nullable=False),
        sa.Column('prezzo_unitario', sa.Numeric(10, 2), nullable=False),
        sa.Column('importo_riga', sa.Numeric(12, 2), nullable=False),
    )

    # Aggiunge prezzo_unitario (listino) alla tabella confezionamenti
    op.add_column('confezionamenti', sa.Column('prezzo_unitario', sa.Numeric(10, 2), nullable=True))


def downgrade() -> None:
    op.drop_column('confezionamenti', 'prezzo_unitario')
    op.drop_table('vendita_righe')
    op.drop_table('vendite')
