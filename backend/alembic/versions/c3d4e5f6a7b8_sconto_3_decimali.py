"""Sconto a 3 decimali + default 0

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-03-04 22:00:00.000000
"""
from alembic import op
from sqlalchemy import text

revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    # clienti.sconto_default: nullable float(5,2) -> NOT NULL NUMERIC(6,3) DEFAULT 0
    conn.execute(text(
        "UPDATE clienti SET sconto_default = 0 WHERE sconto_default IS NULL"
    ))
    conn.execute(text(
        "ALTER TABLE clienti "
        "ALTER COLUMN sconto_default TYPE NUMERIC(6,3), "
        "ALTER COLUMN sconto_default SET NOT NULL, "
        "ALTER COLUMN sconto_default SET DEFAULT 0"
    ))
    # vendita_righe.sconto_percentuale: NUMERIC(5,2) -> NUMERIC(6,3)
    conn.execute(text(
        "ALTER TABLE vendita_righe "
        "ALTER COLUMN sconto_percentuale TYPE NUMERIC(6,3)"
    ))


def downgrade():
    conn = op.get_bind()
    conn.execute(text(
        "ALTER TABLE vendita_righe "
        "ALTER COLUMN sconto_percentuale TYPE NUMERIC(5,2)"
    ))
    conn.execute(text(
        "ALTER TABLE clienti "
        "ALTER COLUMN sconto_default TYPE NUMERIC(5,2), "
        "ALTER COLUMN sconto_default DROP NOT NULL, "
        "ALTER COLUMN sconto_default DROP DEFAULT"
    ))
