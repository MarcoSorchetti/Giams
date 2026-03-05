"""Fix vendite anno_campagna da confezionamento

Revision ID: f3a4b5c6d7e8
Revises: e5f6a7b8c9d0
Create Date: 2026-03-05 16:00:00.000000
"""
from alembic import op
from sqlalchemy import text

revision = "f3a4b5c6d7e8"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    # Aggiorna anno_campagna di ogni vendita con l'anno_campagna
    # del primo confezionamento nelle sue righe
    conn.execute(text("""
        UPDATE vendite v
        SET anno_campagna = sub.conf_anno
        FROM (
            SELECT DISTINCT ON (vr.vendita_id)
                vr.vendita_id,
                c.anno_campagna AS conf_anno
            FROM vendita_righe vr
            JOIN confezionamenti c ON vr.confezionamento_id = c.id
            ORDER BY vr.vendita_id, vr.id
        ) sub
        WHERE v.id = sub.vendita_id
          AND v.anno_campagna != sub.conf_anno
    """))


def downgrade():
    # Non reversibile: i dati originali non sono recuperabili
    pass
