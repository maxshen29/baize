"""能力③路由：知识库检索。"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas import SearchHit, SearchRequest, SearchResponse
from ..services import knowledge_service

router = APIRouter(prefix="/api/kb", tags=["knowledge"])


@router.post("/search", response_model=SearchResponse)
def search(req: SearchRequest, db: Session = Depends(get_db)):
    hits_raw = knowledge_service.search(db, req)
    hits = [
        SearchHit(
            chunk_id=h["chunk_id"],
            document_id=h["document_id"],
            document_title=h["document_title"],
            heading_path=h["heading_path"],
            content=h["content"],
            score=h["score"],
            keywords=h["keywords"],
        )
        for h in hits_raw
    ]
    return SearchResponse(query=req.query, hits=hits)
