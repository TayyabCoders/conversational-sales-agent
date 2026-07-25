"""rename customer_phone to customer_identifier

Revision ID: channel_001
Revises: gemini_002
Create Date: 2026-07-26 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op


revision: str = 'channel_001'
down_revision: Union[str, Sequence[str], None] = 'gemini_002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('conversations', 'customer_phone', new_column_name='customer_identifier')
    op.alter_column('leads', 'customer_phone', new_column_name='customer_identifier')


def downgrade() -> None:
    op.alter_column('conversations', 'customer_identifier', new_column_name='customer_phone')
    op.alter_column('leads', 'customer_identifier', new_column_name='customer_phone')
