"""Drop costo_totale from confezionamenti

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-03-05 10:00:00.000000
"""
from alembic import op
from sqlalchemy import text

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.execute(text("ALTER TABLE confezionamenti DROP COLUMN IF EXISTS costo_totale"))


def downgrade():
    conn = op.get_bind()
    conn.execute(text(
        "ALTER TABLE confezionamenti ADD COLUMN costo_totale NUMERIC(8,2)"
    ))
