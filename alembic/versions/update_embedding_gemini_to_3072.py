"""update_embedding_gemini_to_3072

Revision ID: gemini_002
Revises: gemini_001
Create Date: 2026-07-08 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op


revision: str = 'gemini_002'
down_revision: Union[str, Sequence[str], None] = 'gemini_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the 768-dim ivfflat index before resizing column
    op.execute("DROP INDEX IF EXISTS knowledge_chunks_embedding_gemini_idx")
    op.execute("ALTER TABLE knowledge_chunks ALTER COLUMN embedding_gemini TYPE vector(3072) USING embedding_gemini::text::vector")
    # pgvector (both ivfflat and hnsw) has a hard 2000-dim limit; skip ANN index for now.
    # Queries fall back to exact sequential scan which is fine for small knowledge bases.


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS knowledge_chunks_embedding_gemini_idx")
    op.execute("ALTER TABLE knowledge_chunks ALTER COLUMN embedding_gemini TYPE vector(768) USING embedding_gemini::text::vector")
    op.execute(
        "CREATE INDEX knowledge_chunks_embedding_gemini_idx "
        "ON knowledge_chunks USING ivfflat (embedding_gemini vector_cosine_ops) "
        "WITH (lists = 100)"
    )
