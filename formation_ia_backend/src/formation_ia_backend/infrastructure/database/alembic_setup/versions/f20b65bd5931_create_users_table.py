"""create_users_table

Revision ID: f20b65bd5931
Revises: fe91e4902933
Create Date: 2025-05-31 13:50:00.000000 # Placeholder, actual date will vary

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
# sqlalchemy.dialects.postgresql.UUID is not strictly needed if sa.Uuid works,
# but good to be aware of for specific DB features. sa.Uuid is preferred for cross-dialect compatibility.

# revision identifiers, used by Alembic.
revision: str = 'f20b65bd5931'
down_revision: Union[str, None] = 'fe91e4902933' # Linked to previous migration
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('users',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('email', sa.String(length=320), nullable=False),
        sa.Column('hashed_password', sa.String(length=1024), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true_()),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default=sa.false_()),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.false_()),
        # Custom fields
        sa.Column('submitted_email', sa.String(), nullable=True),
        sa.Column('stripe_customer_id', sa.String(), nullable=True),
        sa.Column('active_subscription_id', sa.String(), nullable=True),
        sa.Column('subscription_tier', sa.String(), nullable=True),
        sa.Column('subscription_expires_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    # Index on ID is typically created by PrimaryKeyConstraint, but explicit can be added if needed.
    # op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)


def downgrade() -> None:
    # op.drop_index(op.f('ix_users_id'), table_name='users') # If ix_users_id was created
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
