from typing import Optional
from app.repositories.base_repository import BaseRepository
from app.models.knowledge_doc_model import KnowledgeDoc
from app.models.knowledge_doc_model import KnowledgeChunk
from sqlalchemy import delete
from app.di.container import container
from dependency_injector.wiring import inject, Provide
from structlog import get_logger
from typing import Any

logger = get_logger(__name__)


class KnowledgeRepository(BaseRepository[KnowledgeDoc]):
    @inject
    def __init__(self, database = Provide["database"], cache: Optional[Any] = Provide["cache"]):
        super().__init__(KnowledgeDoc, database, cache)

    async def create(
        self,
        filename: str,
        file_type: str,
        file_url: str,
    ) -> KnowledgeDoc:
        try:
            logger.info(f"KnowledgeRepository: Creating knowledge doc {filename}...")

            doc_data = {
                "filename": filename,
                "file_type": file_type,
                "file_url": file_url,
                "status": "pending",
                "chunk_count": 0,
            }
            doc = await super().create(doc_data)

            logger.info(f"KnowledgeRepository: Created knowledge doc {doc.id}")
            return doc

        except Exception as e:
            logger.error(f"KnowledgeRepository: Failed to create knowledge doc {filename}.", exc_info=True)
            raise e

    async def update_status(self, doc_id: str, status: str, chunk_count: int = 0) -> None:
        try:
            logger.info(f"KnowledgeRepository: Updating status for doc {doc_id}...")

            update_data = {"status": status}
            if chunk_count > 0:
                update_data["chunk_count"] = chunk_count

            await self.update(doc_id, update_data)

            logger.info(f"KnowledgeRepository: Updated status for doc {doc_id}")

        except Exception as e:
            logger.error(f"KnowledgeRepository: Failed to update status for doc {doc_id}.", exc_info=True)
            raise e

    async def list_all(self) -> list[KnowledgeDoc]:
        try:
            logger.info("KnowledgeRepository: Listing knowledge docs...")

            docs = await self.findAll()

            logger.info(f"KnowledgeRepository: Listed {len(docs)} knowledge docs")
            return docs

        except Exception as e:
            logger.error("KnowledgeRepository: Failed to list knowledge docs.", exc_info=True)
            raise e

    async def delete_qdrant_chunks(self, doc_id: str) -> None:
        try:
            logger.info(f"KnowledgeRepository: Deleting chunks for doc {doc_id}...")

            # Delete from PostgreSQL chunks table
            chunk_repo = BaseRepository(KnowledgeChunk, self.database, self.cache)
            await chunk_repo.deleteWhere(filters={"doc_id": doc_id})

            logger.info(f"KnowledgeRepository: Deleted chunks for doc {doc_id}")
            # Note: Qdrant deletion is handled in knowledge_indexer worker

        except Exception as e:
            logger.error(f"KnowledgeRepository: Failed to delete chunks for doc {doc_id}.", exc_info=True)
            raise e
