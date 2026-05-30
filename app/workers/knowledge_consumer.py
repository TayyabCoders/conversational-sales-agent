"""
Long-lived RabbitMQ consumer for document indexing.
Started inside FastAPI lifespan via asyncio.create_task().
"""
import asyncio
import logging
import uuid
import httpx
import io
from app.configs.messaging_config import RabbitMQClient
from app.repositories.knowledge_repository import KnowledgeRepository
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import PointStruct
from openai import AsyncOpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from structlog import get_logger

logger = get_logger(__name__)


async def start_knowledge_consumer(rabbitmq: RabbitMQClient) -> None:
    """
    Bind to exchange="ai", routing_key="ai.knowledge".
    Called once in main.py lifespan startup.
    """
    await rabbitmq.consume(
        exchange     = "ai",
        queue_name   = "ai.knowledge.queue",
        routing_keys = ["ai.knowledge"],
        callback     = handle_index_request,
    )
    logger.info("Knowledge consumer started — listening on ai.knowledge.queue")


async def handle_index_request(payload: dict) -> None:
    """
    Called by RabbitMQClient for every message on ai.knowledge.queue.
    payload keys: doc_id, file_url, file_type
    """
    try:
        await _index(
            doc_id    = payload["doc_id"],
            file_url  = payload["file_url"],
            file_type = payload["file_type"],
        )
    except Exception as exc:
        logger.error(f"Knowledge indexing failed: {exc}", exc_info=True)
        raise


async def _index(doc_id: str, file_url: str, file_type: str) -> None:
    repo = KnowledgeRepository()

    try:
        await repo.update_status(doc_id, "processing")

        # 1. Download file
        async with httpx.AsyncClient() as client:
            resp    = await client.get(file_url)
            content = resp.content

        # 2. Extract text based on file type
        text = _extract_text(content, file_type)

        # 3. Chunk with overlap
        splitter = RecursiveCharacterTextSplitter(
            chunk_size    = 500,
            chunk_overlap = 50,
            separators    = ["\n\n", "\n", ". ", " "],
        )
        chunks = splitter.split_text(text)

        # 4. Embed all chunks in single API call
        openai     = AsyncOpenAI()
        embed_resp = await openai.embeddings.create(
            model = "text-embedding-3-small",
            input = chunks,
        )
        vectors = [e.embedding for e in embed_resp.data]

        # 5. Upsert into Qdrant (tenant logic excluded - no tenant_id filter)
        qdrant = AsyncQdrantClient()
        points = [
            PointStruct(
                id      = str(uuid.uuid4()),
                vector  = vec,
                payload = {
                    "doc_id":    doc_id,
                    "content":   chunk,
                },
            )
            for chunk, vec in zip(chunks, vectors)
        ]
        await qdrant.upsert(collection_name="knowledge_base", points=points)

        # 6. Mark as indexed in PostgreSQL
        await repo.update_status(doc_id, "indexed", chunk_count=len(chunks))
        logger.info(f"Indexed {len(chunks)} chunks for doc {doc_id}")

    except Exception as exc:
        await repo.update_status(doc_id, "failed")
        logger.error(f"Indexing failed for doc {doc_id}: {exc}")
        raise


def _extract_text(content: bytes, file_type: str) -> str:
    if file_type == "pdf":
        import pypdf2
        reader = pypdf2.PdfReader(io.BytesIO(content))
        return "\n".join(page.extract_text() for page in reader.pages)
    elif file_type == "docx":
        from docx import Document
        doc = Document(io.BytesIO(content))
        return "\n".join(para.text for para in doc.paragraphs)
    else:
        return content.decode("utf-8", errors="ignore")
