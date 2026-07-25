"""add channels table and migrate conversations

Revision ID: channel_002
Revises: channel_001
Create Date: 2026-07-26 00:00:00.000000

"""
from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from alembic import op


revision: str = 'channel_002'
down_revision: Union[str, Sequence[str], None] = 'channel_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create channels table
    op.create_table(
        'channels',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('config', JSONB, nullable=False, server_default='{}'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )
    op.create_index('ix_channels_type', 'channels', ['type'])

    # 2. Seed a default WhatsApp channel so existing conversations can reference it.
    #    Update config via PATCH /channels/{id} after deployment to add real credentials.
    op.execute("""
        INSERT INTO channels (id, type, name, config, is_active)
        VALUES (
            gen_random_uuid(),
            'whatsapp',
            'Default WhatsApp',
            '{}',
            true
        )
    """)

    # 3. Add channel_id FK column to conversations (nullable initially)
    op.add_column('conversations', sa.Column(
        'channel_id',
        UUID(as_uuid=True),
        sa.ForeignKey('channels.id'),
        nullable=True,
    ))

    # 4. Point all existing conversations to the default WhatsApp channel
    op.execute("""
        UPDATE conversations
        SET channel_id = (SELECT id FROM channels WHERE type = 'whatsapp' LIMIT 1)
        WHERE channel_id IS NULL
    """)

    # 5. Make channel_id NOT NULL
    op.alter_column('conversations', 'channel_id', nullable=False)

    # 6. Drop the old channel string column (now represented by the FK + channels.type)
    op.drop_index('ix_conversations_channel', table_name='conversations', if_exists=True)
    op.drop_column('conversations', 'channel')

    op.create_index('ix_conversations_channel_id', 'conversations', ['channel_id'])


def downgrade() -> None:
    op.drop_index('ix_conversations_channel_id', table_name='conversations')
    op.add_column('conversations', sa.Column('channel', sa.String(50), nullable=True))

    # Restore channel string from the joined channel type
    op.execute("""
        UPDATE conversations c
        SET channel = ch.type
        FROM channels ch
        WHERE c.channel_id = ch.id
    """)

    op.alter_column('conversations', 'channel', nullable=False)
    op.create_index('ix_conversations_channel', 'conversations', ['channel'])
    op.drop_column('conversations', 'channel_id')
    op.drop_index('ix_channels_type', table_name='channels')
    op.drop_table('channels')
