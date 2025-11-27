"""add_can_process_after_to_withdrawals

Revision ID: a827304d60aa
Revises: 86a4c2890ea2
Create Date: 2025-11-27 08:21:56.994489

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a827304d60aa'
down_revision = '86a4c2890ea2'
branch_labels = None
depends_on = None


def upgrade():
    # Add can_process_after column to withdrawal_requests
    op.add_column('withdrawal_requests',
        sa.Column('can_process_after', sa.DateTime(), nullable=True)
    )


def downgrade():
    # Remove can_process_after column
    op.drop_column('withdrawal_requests', 'can_process_after')
