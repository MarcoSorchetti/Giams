"""add_check_constraints_stati

Revision ID: j1a2b3c4d5e6
Revises: 1c12a60738b9
Create Date: 2026-03-07 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'j1a2b3c4d5e6'
down_revision: Union[str, None] = '1c12a60738b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_check_constraint(
        'ck_costi_stato_pagamento',
        'costi',
        "stato_pagamento IN ('da_pagare', 'pagato', 'parziale')"
    )
    op.create_check_constraint(
        'ck_costi_stato_riscontro',
        'costi',
        "stato_riscontro IN ('da_riscontrare', 'verificato', 'da_verificare')"
    )
    op.create_check_constraint(
        'ck_vendite_stato',
        'vendite',
        "stato IN ('bozza', 'confermata', 'spedita', 'pagata')"
    )


def downgrade() -> None:
    op.drop_constraint('ck_vendite_stato', 'vendite', type_='check')
    op.drop_constraint('ck_costi_stato_riscontro', 'costi', type_='check')
    op.drop_constraint('ck_costi_stato_pagamento', 'costi', type_='check')
