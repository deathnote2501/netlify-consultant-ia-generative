"""create_chat_messages_table

Revision ID: 7b4b95d97ffc
Revises: f20b65bd5931
Create Date: 2025-05-31 13:55:00.000000 # Placeholder, actual date will vary

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql # For postgresql.UUID

# revision identifiers, used by Alembic.
revision: str = '7b4b95d97ffc'
down_revision: Union[str, None] = 'f20b65bd5931' # Linked to previous users table migration
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('chat_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False), # Model handles default=uuid.uuid4
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('slide_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_chat_messages_user_id_users'))
    )
    # Optional: Indexes for foreign keys or frequently queried columns
    op.create_index(op.f('ix_chat_messages_user_id'), 'chat_messages', ['user_id'], unique=False)
    op.create_index(op.f('ix_chat_messages_slide_id'), 'chat_messages', ['slide_id'], unique=False)
    # Index for timestamp might be useful if querying by time ranges often
    op.create_index(op.f('ix_chat_messages_timestamp'), 'chat_messages', ['timestamp'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_chat_messages_timestamp'), table_name='chat_messages')
    op.drop_index(op.f('ix_chat_messages_slide_id'), table_name='chat_messages')
    op.drop_index(op.f('ix_chat_messages_user_id'), table_name='chat_messages')
    op.drop_table('chat_messages')
