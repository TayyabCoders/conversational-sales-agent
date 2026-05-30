from fastapi import APIRouter, UploadFile, File, Depends
from dependency_injector.wiring import inject, Provide

from app.edge.http.controller.knowledge_controller import KnowledgeController
from app.schemas.knowledge_schema import KnowledgeDocResponse

router = APIRouter()


@router.post("/knowledge/upload")
@inject
async def upload_document(
    file: UploadFile = File(...),
    controller: KnowledgeController = Depends(Provide["knowledge_controller"]),
):
    return await controller.upload(file)


@router.get("/knowledge/docs", response_model=list[KnowledgeDocResponse])
@inject
async def list_docs(
    controller: KnowledgeController = Depends(Provide["knowledge_controller"]),
):
    return await controller.list_docs()


@router.delete("/knowledge/docs/{doc_id}")
@inject
async def delete_doc(
    doc_id: str,
    controller: KnowledgeController = Depends(Provide["knowledge_controller"]),
):
    return await controller.delete_doc(doc_id)


@router.post("/knowledge/docs/{doc_id}/reindex")
@inject
async def reindex_doc(
    doc_id: str,
    controller: KnowledgeController = Depends(Provide["knowledge_controller"]),
):
    return await controller.reindex_doc(doc_id)
