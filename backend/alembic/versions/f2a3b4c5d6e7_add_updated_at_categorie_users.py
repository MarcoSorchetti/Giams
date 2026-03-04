"""Add updated_at to categorie_costo and users

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-03-04 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = "f2a3b4c5d6e7"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    conn.execute(text("ALTER TABLE categorie_costo ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ"))
    conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ"))


def downgrade():
    op.drop_column("users", "updated_at")
    op.drop_column("categorie_costo", "updated_at")
