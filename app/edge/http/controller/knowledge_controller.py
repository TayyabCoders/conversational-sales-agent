from fastapi import UploadFile, HTTPException
from app.di.container import container
from dependency_injector.wiring import inject, Provide
from structlog import get_logger

logger = get_logger(__name__)

ALLOWED_TYPES = {"pdf", "docx", "txt", "csv"}


class KnowledgeController:
    @inject
    def __init__(
        self,
        knowledge_mediator = Provide["knowledge_mediator"],
    ):
        self.knowledge_mediator = knowledge_mediator

    async def upload(self, file: UploadFile):
        try:
            logger.info(f"KnowledgeController: Uploading document {file.filename}...")

            ext = file.filename.split(".")[-1].lower()
            if ext not in ALLOWED_TYPES:
                raise HTTPException(400, f"File type .{ext} not supported. Allowed: {ALLOWED_TYPES}")

            doc = await self.knowledge_mediator.ingest_document(file=file, file_type=ext)

            logger.info(f"KnowledgeController: Document {file.filename} uploaded successfully.")
            return {"message": "Document uploaded and indexing started.", "doc_id": str(doc.id)}

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"KnowledgeController: Failed to upload document {file.filename}.", exc_info=True)
            raise e

    async def list_docs(self):
        try:
            logger.info("KnowledgeController: Listing documents...")

            docs = await self.knowledge_mediator.list_documents()

            logger.info("KnowledgeController: Documents listed successfully.")
            return docs

        except Exception as e:
            logger.error("KnowledgeController: Failed to list documents.", exc_info=True)
            raise e

    async def delete_doc(self, doc_id: str):
        try:
            logger.info(f"KnowledgeController: Deleting document {doc_id}...")

            await self.knowledge_mediator.delete_document(doc_id)

            logger.info(f"KnowledgeController: Document {doc_id} deleted successfully.")
            return {"message": "Document deleted and removed from knowledge base."}

        except Exception as e:
            logger.error(f"KnowledgeController: Failed to delete document {doc_id}.", exc_info=True)
            raise e

    async def reindex_doc(self, doc_id: str):
        try:
            logger.info(f"KnowledgeController: Reindexing document {doc_id}...")

            await self.knowledge_mediator.reindex_document(doc_id)

            logger.info(f"KnowledgeController: Document {doc_id} reindexing started.")
            return {"message": "Reindexing started."}

        except Exception as e:
            logger.error(f"KnowledgeController: Failed to reindex document {doc_id}.", exc_info=True)
            raise e
