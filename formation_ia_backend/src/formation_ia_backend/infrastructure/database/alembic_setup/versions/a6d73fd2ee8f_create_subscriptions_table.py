"""create_subscriptions_table

Revision ID: a6d73fd2ee8f
Revises: 7b4b95d97ffc
Create Date: 2025-05-31 14:00:00.000000 # Placeholder, actual date will vary

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql # For postgresql.UUID

# revision identifiers, used by Alembic.
revision: str = 'a6d73fd2ee8f'
down_revision: Union[str, None] = '7b4b95d97ffc' # Linked to previous chat_messages table migration
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('subscriptions',
        sa.Column('id', sa.String(), nullable=False), # Stripe Subscription ID
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('stripe_customer_id', sa.String(), nullable=False),
        sa.Column('plan_id', sa.String(), nullable=False), # Stripe Price ID
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('current_period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('cancel_at_period_end', sa.Boolean(), nullable=False, server_default=sa.false_()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_subscriptions')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_subscriptions_user_id_users'))
    )
    op.create_index(op.f('ix_subscriptions_user_id'), 'subscriptions', ['user_id'], unique=False)
    op.create_index(op.f('ix_subscriptions_stripe_customer_id'), 'subscriptions', ['stripe_customer_id'], unique=False)
    # Optional: Index on status if queried often
    op.create_index(op.f('ix_subscriptions_status'), 'subscriptions', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_subscriptions_status'), table_name='subscriptions')
    op.drop_index(op.f('ix_subscriptions_stripe_customer_id'), table_name='subscriptions')
    op.drop_index(op.f('ix_subscriptions_user_id'), table_name='subscriptions')
    op.drop_table('subscriptions')
