"""能力②路由：参考文档导入与管理。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas import DocumentOut, DocumentParseOut
from ..services import document_service

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("", response_model=list[DocumentOut])
def list_documents(db: Session = Depends(get_db)):
    return document_service.list_documents(db)


@router.post("/upload", response_model=DocumentOut, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    data = await file.read()
    if not data:
        raise HTTPException(400, "empty file")
    doc = document_service.import_upload(db, file.filename or "unknown", data)
    return doc


@router.get("/{doc_id}", response_model=DocumentOut)
def get_document(doc_id: str, db: Session = Depends(get_db)):
    doc = document_service.get_document(db, doc_id)
    if not doc:
        raise HTTPException(404, "document not found")
    return doc


@router.get("/{doc_id}/preview", response_model=DocumentParseOut)
def document_preview(doc_id: str, db: Session = Depends(get_db)):
    doc = document_service.get_document(db, doc_id)
    if not doc:
        raise HTTPException(404, "document not found")
    preview = document_service.parse_preview(db, doc_id)
    return DocumentParseOut(
        id=doc.id, title=doc.title, status=doc.status,
        chunk_count=doc.chunk_count, preview=preview,
    )


@router.delete("/{doc_id}")
def delete_document(doc_id: str, db: Session = Depends(get_db)):
    if not document_service.delete_document(db, doc_id):
        raise HTTPException(404, "document not found")
    return {"ok": True}
