from openai import AsyncOpenAI
import google.generativeai as genai
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import json


class RAGService:
    """
    Retrieval-Augmented Generation using PostgreSQL + pgvector.
    Uses your existing Database class (read session → replica if available).
    Supports both OpenAI and Gemini embeddings based on configuration.
    """

    def __init__(self, db: AsyncSession, openai: AsyncOpenAI = None, gemini_client=None, use_gemini: bool = False):
        self.db = db
        self.openai = openai
        self.gemini_client = gemini_client
        self.use_gemini = use_gemini

    async def retrieve(self, query: str, top_k: int = 5) -> str:
        # 1. Embed the query using configured provider
        if self.use_gemini and self.gemini_client:
            embed_resp = genai.embed_content(
                model="text-embedding-004",
                content=query,
                task_type="retrieval_document"
            )
            query_vector = embed_resp['embedding']
        elif self.openai:
            embed_resp = await self.openai.embeddings.create(
                model="text-embedding-3-small",
                input=query,
            )
            query_vector = embed_resp.data[0].embedding
        else:
            raise ValueError("No AI client configured for embeddings")

        # Convert to pgvector literal string e.g. "[0.1, 0.2, ...]"
        vector_str = "[" + ",".join(str(v) for v in query_vector) + "]"

        # 2. Cosine similarity search
        # <=> operator = cosine distance (lower = more similar)
        # Use appropriate embedding column based on provider
        embedding_column = "embedding_gemini" if self.use_gemini else "embedding"
        sql = text(f"""
            SELECT content,
                   1 - ({embedding_column} <=> :query_vec::vector) AS similarity
            FROM   knowledge_chunks
            WHERE  1 - ({embedding_column} <=> :query_vec::vector) > 0.72
            ORDER  BY {embedding_column} <=> :query_vec::vector
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
        if self.use_gemini and self.gemini_client:
            resp = genai.embed_content(
                model="text-embedding-004",
                content=text_input,
                task_type="retrieval_document"
            )
            return resp['embedding']
        elif self.openai:
            resp = await self.openai.embeddings.create(
                model="text-embedding-3-small",
                input=text_input,
            )
            return resp.data[0].embedding
        else:
            raise ValueError("No AI client configured for embeddings")
