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
from app.configs.database_config import Database
from app.repositories.knowledge_repository import KnowledgeRepository
from app.services.ai.rag_service import RAGService
from openai import AsyncOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import text, cast
from structlog import get_logger
import pypdf

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
        extracted_text = _extract_text(content, file_type)

        # 3. Chunk with overlap
        splitter = RecursiveCharacterTextSplitter(
            chunk_size    = 500,
            chunk_overlap = 50,
            separators    = ["\n\n", "\n", ". ", " "],
        )
        chunks = splitter.split_text(extracted_text)

        # 4. Embed all chunks using configured provider
        from app.di.container import container
        from app.configs.app_config import settings
        db = container.resolve('database')

        use_gemini = settings.USE_GEMINI
        openai_client = container.resolve('openai_client') if not use_gemini else None
        gemini_client = container.resolve('gemini_client') if use_gemini else None

        vectors = []
        if use_gemini and gemini_client:
            import google.generativeai as genai
            for chunk in chunks:
                embed_resp = genai.embed_content(
                    model=settings.GEMINI_EMBEDDING_MODEL,
                    content=chunk,
                    task_type="retrieval_document"
                )
                vectors.append(embed_resp['embedding'])
        elif openai_client:
            for chunk in chunks:
                embed_resp = await openai_client.embeddings.create(
                    model="text-embedding-3-small",
                    input=chunk,
                )
                vectors.append(embed_resp.data[0].embedding)
        else:
            raise ValueError("No AI client configured for embeddings")

        # 5. Insert chunks + vectors into PostgreSQL (pgvector)
        # Use appropriate embedding column based on provider
        embedding_column = "embedding_gemini" if use_gemini else "embedding"
        async with db.get_session("write") as session:
            for chunk, vec in zip(chunks, vectors):
                vector_str = "[" + ",".join(str(v) for v in vec) + "]"
                await session.execute(
                    text(f"""
                        INSERT INTO knowledge_chunks
                            (id, doc_id, content, {embedding_column}, embedding_provider, created_at)
                        VALUES
                            (:id, :doc_id, :content, cast(:vector as vector), :provider, NOW())
                    """),
                    {
                        "id": str(uuid.uuid4()),
                        "doc_id": doc_id,
                        "content": chunk,
                        "vector": vector_str,
                        "provider": "gemini" if use_gemini else "openai"
                    },
                )
            await session.commit()

        # 6. Mark as indexed in PostgreSQL
        await repo.update_status(doc_id, "indexed", chunk_count=len(chunks))
        logger.info(f"Indexed {len(chunks)} chunks for doc {doc_id}")

    except Exception as exc:
        await repo.update_status(doc_id, "failed")
        logger.error(f"Indexing failed for doc {doc_id}: {exc}")
        raise


def _extract_text(content: bytes, file_type: str) -> str:
    if file_type == "pdf":
       
        reader = pypdf.PdfReader(io.BytesIO(content))
        return "\n".join(page.extract_text() for page in reader.pages)
    elif file_type == "docx":
        from docx import Document
        doc = Document(io.BytesIO(content))
        return "\n".join(para.text for para in doc.paragraphs)
    else:
        return content.decode("utf-8", errors="ignore")
