"""Add prezzo_listino and sconto_percentuale to vendita_righe

Revision ID: a1b2c3d4e5f6
Revises: f2a3b4c5d6e7
Create Date: 2026-03-04 18:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = "a1b2c3d4e5f6"
down_revision = "f2a3b4c5d6e7"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.execute(text(
        "ALTER TABLE vendita_righe ADD COLUMN IF NOT EXISTS prezzo_listino NUMERIC(10,2)"
    ))
    conn.execute(text(
        "ALTER TABLE vendita_righe ADD COLUMN IF NOT EXISTS sconto_percentuale NUMERIC(5,2) NOT NULL DEFAULT 0"
    ))


def downgrade():
    op.drop_column("vendita_righe", "sconto_percentuale")
    op.drop_column("vendita_righe", "prezzo_listino")
