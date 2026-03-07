"""add_frantoi_banche_azienda

Revision ID: k1a2b3c4d5e6
Revises: j1a2b3c4d5e6
Create Date: 2026-03-07 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'k1a2b3c4d5e6'
down_revision: Union[str, None] = 'j1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tabella frantoi
    op.create_table(
        'frantoi',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('codice', sa.String(10), nullable=False, unique=True),
        sa.Column('denominazione', sa.String(200), nullable=False),
        sa.Column('partita_iva', sa.String(16), nullable=True),
        sa.Column('indirizzo', sa.String(200), nullable=True),
        sa.Column('cap', sa.String(5), nullable=True),
        sa.Column('citta', sa.String(100), nullable=True),
        sa.Column('provincia', sa.String(2), nullable=True),
        sa.Column('telefono', sa.String(20), nullable=True),
        sa.Column('email', sa.String(100), nullable=True),
        sa.Column('referente', sa.String(100), nullable=True),
        sa.Column('servizi', sa.String(50), nullable=False, server_default='molitura'),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('attivo', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_frantoi_codice', 'frantoi', ['codice'])

    # Tabella banche
    op.create_table(
        'banche',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('codice', sa.String(10), nullable=False, unique=True),
        sa.Column('denominazione', sa.String(200), nullable=False),
        sa.Column('iban', sa.String(34), nullable=True),
        sa.Column('bic_swift', sa.String(11), nullable=True),
        sa.Column('abi', sa.String(5), nullable=True),
        sa.Column('cab', sa.String(5), nullable=True),
        sa.Column('numero_conto', sa.String(20), nullable=True),
        sa.Column('filiale', sa.String(200), nullable=True),
        sa.Column('intestatario', sa.String(200), nullable=True),
        sa.Column('tipo_conto', sa.String(30), nullable=False, server_default='corrente'),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('attivo', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_banche_codice', 'banche', ['codice'])

    # Tabella azienda (singolo record)
    op.create_table(
        'azienda',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('ragione_sociale', sa.String(200), nullable=False),
        sa.Column('forma_giuridica', sa.String(30), nullable=True),
        sa.Column('partita_iva', sa.String(16), nullable=True),
        sa.Column('codice_fiscale', sa.String(16), nullable=True),
        sa.Column('rea', sa.String(30), nullable=True),
        sa.Column('codice_ateco', sa.String(10), nullable=True),
        sa.Column('pec', sa.String(100), nullable=True),
        sa.Column('codice_sdi', sa.String(7), nullable=True),
        sa.Column('sede_legale_indirizzo', sa.String(200), nullable=True),
        sa.Column('sede_legale_cap', sa.String(5), nullable=True),
        sa.Column('sede_legale_citta', sa.String(100), nullable=True),
        sa.Column('sede_legale_provincia', sa.String(2), nullable=True),
        sa.Column('sede_operativa_indirizzo', sa.String(200), nullable=True),
        sa.Column('sede_operativa_cap', sa.String(5), nullable=True),
        sa.Column('sede_operativa_citta', sa.String(100), nullable=True),
        sa.Column('sede_operativa_provincia', sa.String(2), nullable=True),
        sa.Column('telefono', sa.String(20), nullable=True),
        sa.Column('cellulare', sa.String(20), nullable=True),
        sa.Column('email', sa.String(100), nullable=True),
        sa.Column('sito_web', sa.String(200), nullable=True),
        sa.Column('banca_id', sa.Integer(), nullable=True),
        sa.Column('logo_path', sa.String(200), nullable=True),
        sa.Column('rappresentante_legale', sa.String(200), nullable=True),
        sa.Column('capitale_sociale', sa.Numeric(12, 2), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    # FK frantoio_id su lotti_olio (nullable, dati vecchi restano senza)
    op.add_column('lotti_olio', sa.Column('frantoio_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_lotti_olio_frantoio', 'lotti_olio', 'frantoi', ['frantoio_id'], ['id'])

    # FK frantoio_id su confezionamenti (imbottigliatore)
    op.add_column('confezionamenti', sa.Column('frantoio_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_confezionamenti_frantoio', 'confezionamenti', 'frantoi', ['frantoio_id'], ['id'])

    # CHECK constraint su frantoi.servizi
    op.create_check_constraint('ck_frantoi_servizi', 'frantoi', "servizi IN ('molitura', 'confezionamento', 'entrambi')")

    # CHECK constraint su banche.tipo_conto
    op.create_check_constraint('ck_banche_tipo_conto', 'banche', "tipo_conto IN ('corrente', 'deposito', 'carta')")


def downgrade() -> None:
    op.drop_constraint('ck_banche_tipo_conto', 'banche', type_='check')
    op.drop_constraint('ck_frantoi_servizi', 'frantoi', type_='check')
    op.drop_constraint('fk_confezionamenti_frantoio', 'confezionamenti', type_='foreignkey')
    op.drop_column('confezionamenti', 'frantoio_id')
    op.drop_constraint('fk_lotti_olio_frantoio', 'lotti_olio', type_='foreignkey')
    op.drop_column('lotti_olio', 'frantoio_id')
    op.drop_table('azienda')
    op.drop_table('banche')
    op.drop_table('frantoi')
