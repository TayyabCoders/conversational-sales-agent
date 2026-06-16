"""add_gemini_embedding_support

Revision ID: gemini_001
Revises: 4fa97bb67d7c
Create Date: 2026-06-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'gemini_001'
down_revision: Union[str, Sequence[str], None] = '4fa97bb67d7c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to support Gemini embeddings (768 dimensions)."""
    # Add new column for Gemini embeddings (768 dimensions)
    op.add_column('knowledge_chunks', sa.Column('embedding_gemini', sa.Text(), nullable=True))

    # Change embedding_gemini column to vector type
    op.execute("ALTER TABLE knowledge_chunks ALTER COLUMN embedding_gemini TYPE vector(768) USING embedding_gemini::vector")

    # Create index for Gemini embeddings
    op.execute(
        "CREATE INDEX knowledge_chunks_embedding_gemini_idx "
        "ON knowledge_chunks USING ivfflat (embedding_gemini vector_cosine_ops) "
        "WITH (lists = 100)"
    )

    # Add column to track which embedding provider was used
    op.add_column('knowledge_chunks', sa.Column('embedding_provider', sa.String(length=20), nullable=True, server_default='openai'))


def downgrade() -> None:
    """Downgrade schema - remove Gemini embedding support."""
    # Drop Gemini embedding index
    op.execute("DROP INDEX IF EXISTS knowledge_chunks_embedding_gemini_idx")

    # Drop Gemini embedding column
    op.drop_column('knowledge_chunks', 'embedding_gemini')

    # Drop embedding provider column
    op.drop_column('knowledge_chunks', 'embedding_provider')
