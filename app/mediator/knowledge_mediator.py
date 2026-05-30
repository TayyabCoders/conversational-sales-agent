from app.di.container import container
from dependency_injector.wiring import inject, Provide
from fastapi import UploadFile
from app.repositories.knowledge_repository import KnowledgeRepository
from app.configs.messaging_config import RabbitMQClient
from app.utils.storage_util import upload_to_s3
from structlog import get_logger

logger = get_logger(__name__)


class KnowledgeMediator:
    @inject
    def __init__(
        self,
        knowledge_repo = Provide["knowledge_repository"],
        rabbitmq = Provide["rabbitmq"],
    ):
        self.repo = knowledge_repo
        self.rabbitmq = rabbitmq

    async def ingest_document(self, file: UploadFile, file_type: str):
        try:
            logger.info(f"KnowledgeMediator: Ingesting document {file.filename}...")

            # 1. Upload raw file to S3
            file_bytes = await file.read()
            file_url = await upload_to_s3(file_bytes, file.filename)

            # 2. Create DB record (status=pending)
            doc = await self.repo.create(
                filename=file.filename,
                file_type=file_type,
                file_url=file_url,
            )

            # 3. Publish to RabbitMQ indexing queue
            await self.rabbitmq.publish(
                exchange    = "ai",
                routing_key = "ai.knowledge",
                message     = dict(
                    doc_id    = str(doc.id),
                    file_url  = file_url,
                    file_type = file_type,
                ),
            )

            logger.info(f"KnowledgeMediator: Document {file.filename} ingested successfully.")
            return doc

        except Exception as e:
            logger.error(f"KnowledgeMediator: Failed to ingest document {file.filename}.", exc_info=True)
            raise e

    async def delete_document(self, doc_id: str):
        try:
            logger.info(f"KnowledgeMediator: Deleting document {doc_id}...")

            doc = await self.repo.get_by_id(doc_id)
            # Remove from Qdrant (by doc_id metadata filter)
            await self.repo.delete_qdrant_chunks(doc_id)
            # Delete DB record
            await self.repo.delete(doc_id)

            logger.info(f"KnowledgeMediator: Document {doc_id} deleted successfully.")

        except Exception as e:
            logger.error(f"KnowledgeMediator: Failed to delete document {doc_id}.", exc_info=True)
            raise e

    async def reindex_document(self, doc_id: str):
        try:
            logger.info(f"KnowledgeMediator: Reindexing document {doc_id}...")

            doc = await self.repo.get_by_id(doc_id)
            await self.repo.update_status(doc_id, "pending")
            await self.rabbitmq.publish(
                exchange    = "ai",
                routing_key = "ai.knowledge",
                message     = dict(
                    doc_id    = doc_id,
                    file_url  = doc.file_url,
                    file_type = doc.file_type,
                ),
            )

            logger.info(f"KnowledgeMediator: Document {doc_id} reindexing started.")

        except Exception as e:
            logger.error(f"KnowledgeMediator: Failed to reindex document {doc_id}.", exc_info=True)
            raise e
