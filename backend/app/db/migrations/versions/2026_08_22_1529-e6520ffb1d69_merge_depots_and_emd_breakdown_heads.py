"""merge_depots_and_emd_breakdown_heads

Revision ID: e6520ffb1d69
Revises: ('42330befd521', 'a1b2c3d4e5f6')
Create Date: 2026-08-22 15:29:46.181550

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e6520ffb1d69'
down_revision: Union[str, None] = ('42330befd521', 'a1b2c3d4e5f6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
