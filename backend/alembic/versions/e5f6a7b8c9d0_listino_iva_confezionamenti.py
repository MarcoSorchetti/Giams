"""Listino con IVA su confezionamenti

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-03-05 12:00:00.000000
"""
from alembic import op
from sqlalchemy import text

revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    # Rinomina prezzo_unitario -> prezzo_imponibile
    conn.execute(text(
        "ALTER TABLE confezionamenti RENAME COLUMN prezzo_unitario TO prezzo_imponibile"
    ))
    # Aggiungi colonne IVA
    conn.execute(text(
        "ALTER TABLE confezionamenti "
        "ADD COLUMN iva_percentuale NUMERIC(5,2) NOT NULL DEFAULT 4, "
        "ADD COLUMN importo_iva NUMERIC(10,2), "
        "ADD COLUMN prezzo_listino NUMERIC(10,2)"
    ))
    # Backfill: calcola IVA e listino per righe esistenti
    conn.execute(text(
        "UPDATE confezionamenti SET "
        "importo_iva = ROUND(prezzo_imponibile * iva_percentuale / 100, 2), "
        "prezzo_listino = ROUND(prezzo_imponibile + ROUND(prezzo_imponibile * iva_percentuale / 100, 2), 2) "
        "WHERE prezzo_imponibile IS NOT NULL"
    ))


def downgrade():
    conn = op.get_bind()
    conn.execute(text(
        "ALTER TABLE confezionamenti "
        "DROP COLUMN prezzo_listino, "
        "DROP COLUMN importo_iva, "
        "DROP COLUMN iva_percentuale"
    ))
    conn.execute(text(
        "ALTER TABLE confezionamenti RENAME COLUMN prezzo_imponibile TO prezzo_unitario"
    ))
