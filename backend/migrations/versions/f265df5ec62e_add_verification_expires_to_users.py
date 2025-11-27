"""add_verification_expires_to_users

Revision ID: f265df5ec62e
Revises: a827304d60aa
Create Date: 2025-11-27 08:23:26.889097

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f265df5ec62e'
down_revision = 'a827304d60aa'
branch_labels = None
depends_on = None


def upgrade():
    # Add verification_expires column to users table
    op.add_column('users',
        sa.Column('verification_expires', sa.DateTime(), nullable=True)
    )


def downgrade():
    # Remove verification_expires column
    op.drop_column('users', 'verification_expires')
