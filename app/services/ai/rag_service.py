from app.di.container import container
from dependency_injector.wiring import inject, Provide
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from openai import AsyncOpenAI
from structlog import get_logger

logger = get_logger(__name__)


class RAGService:
    @inject
    def __init__(
        self,
        qdrant = Provide["qdrant_client"],
        openai = Provide["openai_client"],
    ):
        self.qdrant = qdrant
        self.openai = openai
        self.collection = "knowledge_chunks"

    async def retrieve(self, query: str, top_k: int = 5) -> str:
        try:
            logger.info("RAGService: Retrieving knowledge...")

            # 1. Embed the query
            embed_resp = await self.openai.embeddings.create(
                model="text-embedding-3-small",
                input=query,
            )
            query_vector = embed_resp.data[0].embedding

            # 2. Search Qdrant — no tenant filter (tenant logic excluded)
            results = await self.qdrant.search(
                collection_name=self.collection,
                query_vector=query_vector,
                limit=top_k,
                score_threshold=0.72,
            )

            if not results:
                logger.info("RAGService: No relevant knowledge found.")
                return "No relevant knowledge found for this query."

            # 3. Format as numbered context
            chunks = [f"[{i+1}] {r.payload['content']}" for i, r in enumerate(results)]
            context = "\n\n".join(chunks)

            logger.info(f"RAGService: Retrieved {len(chunks)} knowledge chunks.")
            return context

        except Exception as e:
            logger.error("RAGService: Failed to retrieve knowledge.", exc_info=True)
            raise e
