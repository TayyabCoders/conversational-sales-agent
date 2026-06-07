from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import json


class RAGService:
    """
    Retrieval-Augmented Generation using PostgreSQL + pgvector.
    Uses your existing Database class (read session → replica if available).
    """

    def __init__(self, db: AsyncSession, openai: AsyncOpenAI):
        self.db     = db
        self.openai = openai

    async def retrieve(self, query: str, top_k: int = 5) -> str:
        # 1. Embed the query using OpenAI
        embed_resp = await self.openai.embeddings.create(
            model = "text-embedding-3-small",
            input = query,
        )
        query_vector = embed_resp.data[0].embedding
        # Convert to pgvector literal string e.g. "[0.1, 0.2, ...]"
        vector_str = "[" + ",".join(str(v) for v in query_vector) + "]"

        # 2. Cosine similarity search
        # <=> operator = cosine distance (lower = more similar)
        sql = text("""
            SELECT content,
                   1 - (embedding <=> :query_vec::vector) AS similarity
            FROM   knowledge_chunks
            WHERE  1 - (embedding <=> :query_vec::vector) > 0.72
            ORDER  BY embedding <=> :query_vec::vector
            LIMIT  :top_k
        """)

        result = await self.db.execute(
            sql,
            {
                "query_vec": vector_str,
                "top_k":     top_k,
            },
        )
        rows = result.fetchall()

        if not rows:
            return "No relevant knowledge found for this query."

        # 3. Format as numbered context string
        chunks = [f"[{i+1}] {row.content}" for i, row in enumerate(rows)]
        return "\n\n".join(chunks)

    async def embed_text(self, text_input: str) -> list[float]:
        """Embed a single string — used by knowledge_consumer."""
        resp = await self.openai.embeddings.create(
            model = "text-embedding-3-small",
            input = text_input,
        )
        return resp.data[0].embedding
