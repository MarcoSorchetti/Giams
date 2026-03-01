"""Add contenitori table and contenitore_id to confezionamenti

Revision ID: ddd920255e1c
Revises: f905f29db217
Create Date: 2026-03-01 22:54:11.782747

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ddd920255e1c'
down_revision: Union[str, None] = 'f905f29db217'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Contenitori di default da inserire
SEED_CONTENITORI = [
    ("bottiglia_025", "Bottiglia 0.25L", 0.25),
    ("bottiglia_050", "Bottiglia 0.50L", 0.50),
    ("bottiglia_075", "Bottiglia 0.75L", 0.75),
    ("lattina_5", "Lattina 5L", 5.00),
    ("bag_5", "Bag-in-Box 5L", 5.00),
]


def upgrade() -> None:
    # Seed contenitori di default
    contenitori_table = sa.table(
        "contenitori",
        sa.column("codice", sa.String),
        sa.column("descrizione", sa.String),
        sa.column("capacita_litri", sa.Numeric),
        sa.column("attivo", sa.Boolean),
    )
    for codice, descrizione, capacita in SEED_CONTENITORI:
        op.execute(
            contenitori_table.insert().values(
                codice=codice,
                descrizione=descrizione,
                capacita_litri=capacita,
                attivo=True,
            )
        )

    # Aggiungere contenitore_id (nullable) a confezionamenti
    op.add_column('confezionamenti', sa.Column('contenitore_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_confezionamenti_contenitore', 'confezionamenti', 'contenitori', ['contenitore_id'], ['id'])

    # Backfill: collegare confezionamenti esistenti al contenitore tramite formato
    op.execute("""
        UPDATE confezionamenti c
        SET contenitore_id = ct.id
        FROM contenitori ct
        WHERE c.formato = ct.codice AND c.contenitore_id IS NULL
    """)


def downgrade() -> None:
    op.drop_constraint('fk_confezionamenti_contenitore', 'confezionamenti', type_='foreignkey')
    op.drop_column('confezionamenti', 'contenitore_id')

    # Rimuovere seed contenitori
    for codice, _, _ in SEED_CONTENITORI:
        op.execute(f"DELETE FROM contenitori WHERE codice = '{codice}'")
