from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.api.auth import get_current_user
from app.database.database import get_db
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.user import User
from app.schemas.query import QueryRequest, QueryResponse, QueryResult
from app.services.bm25_service import search_chunks_with_bm25


router = APIRouter(
    tags=["Keyword Search"],
)


@router.post("/keyword-search", response_model=QueryResponse)
def keyword_search_documents(
    query_request: QueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chunks_query = (
        db.query(DocumentChunk)
        .join(Document, DocumentChunk.document_id == Document.id)
        .options(joinedload(DocumentChunk.document))
        .filter(Document.owner_id == current_user.id)
    )

    if query_request.document_id is not None:
        chunks_query = chunks_query.filter(
            DocumentChunk.document_id == query_request.document_id
        )

    chunks = (
        chunks_query
        .order_by(DocumentChunk.chunk_index.asc())
        .all()
    )

    bm25_results = search_chunks_with_bm25(
        query=query_request.question,
        chunks=chunks,
        top_k=query_request.top_k,
    )

    results: list[QueryResult] = []

    for bm25_result in bm25_results:
        chunk = bm25_result.chunk

        source_filename = (
            chunk.document.original_filename
            if chunk.document is not None
            else "unknown"
        )

        results.append(
            QueryResult(
                score=bm25_result.score,
                document_id=chunk.document_id,
                user_id=current_user.id,
                page_number=chunk.page_number,
                chunk_index=chunk.chunk_index,
                text=chunk.text,
                source_filename=source_filename,
                document_chunk_id=chunk.id,
            )
        )

    return QueryResponse(
        question=query_request.question,
        top_k=query_request.top_k,
        results_count=len(results),
        results=results,
    )