"""Add emd_breakdown JSONB column to tenders

Revision ID: a1b2c3d4e5f6
Revises: 5760beb5b967
Create Date: 2026-08-18 11:00:00.000000

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: str | None = '5760beb5b967'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add emd_breakdown JSONB column: stores lot-wise EMD amounts as
    # {"StateName": amount_in_inr_crores, ...} matching real CESL tender structure.
    # emd_amount (existing scalar) is updated to hold the correct cumulative total.
    op.add_column(
        'tenders',
        sa.Column(
            'emd_breakdown',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment='Lot-wise EMD breakdown per CESL norms: {"StateOrLot": amount_INR_crores}'
        )
    )


def downgrade() -> None:
    op.drop_column('tenders', 'emd_breakdown')
