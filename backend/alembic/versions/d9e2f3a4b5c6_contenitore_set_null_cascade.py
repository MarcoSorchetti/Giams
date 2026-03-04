"""fix contenitore_id ondelete SET NULL

Revision ID: d9e2f3a4b5c6
Revises: c8f1a2b3d4e5
Create Date: 2026-03-04 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'd9e2f3a4b5c6'
down_revision: Union[str, None] = 'c8f1a2b3d4e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint('fk_confezionamenti_contenitore', 'confezionamenti', type_='foreignkey')
    op.create_foreign_key(
        'fk_confezionamenti_contenitore', 'confezionamenti',
        'contenitori', ['contenitore_id'], ['id'], ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('fk_confezionamenti_contenitore', 'confezionamenti', type_='foreignkey')
    op.create_foreign_key(
        'fk_confezionamenti_contenitore', 'confezionamenti',
        'contenitori', ['contenitore_id'], ['id'],
    )
