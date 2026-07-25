from typing import Dict, Any
from fastapi import UploadFile, HTTPException, status
from structlog import get_logger
from dependency_injector.wiring import inject, Provide

logger = get_logger(__name__)


class KnowledgeService:
    @inject
    def __init__(
        self,
        knowledge_repository = Provide["knowledge_repository"],
        prometheus = Provide["prometheus"],
    ):
        self.knowledge_repository = knowledge_repository
        self.prometheus = prometheus

    async def create_document(
        self,
        filename: str,
        file_type: str,
        file_url: str,
    ) -> Dict[str, Any]:
        try:
            logger.info(f"KnowledgeService: Creating knowledge doc {filename}...")
            
            doc = await self.knowledge_repository.create(
                filename=filename,
                file_type=file_type,
                file_url=file_url,
            )
            
            logger.info(f"KnowledgeService: Created knowledge doc {doc.id}")
            
            # Record business event
            self.prometheus.record_business_event("knowledge_document_create", "success")
            
            return doc
        
        except Exception as e:
            logger.error(f"KnowledgeService: Failed to create knowledge doc {filename}.", exc_info=True)
            raise e

    async def list_documents(self) -> list:
        try:
            logger.info("KnowledgeService: Listing knowledge docs...")
            
            docs = await self.knowledge_repository.list_all()
            
            logger.info(f"KnowledgeService: Listed {len(docs)} knowledge docs")
            
            # Record business event
            self.prometheus.record_business_event("knowledge_document_list", "success")
            
            return docs
        
        except Exception as e:
            logger.error("KnowledgeService: Failed to list knowledge docs.", exc_info=True)
            raise e

    async def delete_document(self, doc_id: str) -> None:
        try:
            logger.info(f"KnowledgeService: Deleting document {doc_id}...")
            
            # Remove from Qdrant (by doc_id metadata filter)
            await self.knowledge_repository.delete_qdrant_chunks(doc_id)
            # Delete DB record
            await self.knowledge_repository.delete(doc_id)
            
            logger.info(f"KnowledgeService: Document {doc_id} deleted successfully.")
            
            # Record business event
            self.prometheus.record_business_event("knowledge_document_delete", "success")
        
        except Exception as e:
            logger.error(f"KnowledgeService: Failed to delete document {doc_id}.", exc_info=True)
            raise e

    async def update_document_status(
        self,
        doc_id: str,
        status: str,
        chunk_count: int = 0,
    ) -> None:
        try:
            logger.info(f"KnowledgeService: Updating status for doc {doc_id}...")
            
            await self.knowledge_repository.update_status(doc_id, status, chunk_count)
            
            logger.info(f"KnowledgeService: Updated status for doc {doc_id}")
        
        except Exception as e:
            logger.error(f"KnowledgeService: Failed to update status for doc {doc_id}.", exc_info=True)
            raise e

    async def get_document(self, doc_id: str):
        try:
            logger.info(f"KnowledgeService: Getting document {doc_id}...")
            
            doc = await self.knowledge_repository.findById(doc_id)
            
            if not doc:
                logger.warning(f"KnowledgeService: Document {doc_id} not found")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Document not found"
                )
            
            logger.info(f"KnowledgeService: Retrieved document {doc_id}")
            return doc
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"KnowledgeService: Failed to get document {doc_id}.", exc_info=True)
            raise e
