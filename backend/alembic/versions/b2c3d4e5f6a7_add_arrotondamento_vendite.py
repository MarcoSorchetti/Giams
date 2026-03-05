"""Add arrotondamento to vendite

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-04 20:00:00.000000
"""
from alembic import op
from sqlalchemy import text

revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.execute(text(
        "ALTER TABLE vendite ADD COLUMN IF NOT EXISTS arrotondamento NUMERIC(10,2) NOT NULL DEFAULT 0"
    ))


def downgrade():
    op.drop_column("vendite", "arrotondamento")
