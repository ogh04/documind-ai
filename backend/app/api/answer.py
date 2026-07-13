from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.api.auth import get_current_user
from app.core.config import settings
from app.database.database import get_db
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.user import User
from app.schemas.answer import AnswerRequest, AnswerResponse, AnswerSource
from app.services.answer_service import NO_ANSWER_MESSAGE
from app.services.bm25_service import search_chunks_with_bm25
from app.services.embedding_service import embed_query
from app.services.fusion_service import FusionInputResult, fuse_search_results
from app.services.llm_service import generate_answer
from app.services.qdrant_service import search_similar_chunks
from app.services.reranker_service import rerank_fused_results


router = APIRouter(
    tags=["Answer"],
)


def build_keyword_payload(
    chunk: DocumentChunk,
    user_id: int,
) -> dict[str, Any]:
    source_filename = (
        chunk.document.original_filename
        if chunk.document is not None
        else "unknown"
    )

    return {
        "document_id": chunk.document_id,
        "user_id": user_id,
        "page_number": chunk.page_number,
        "chunk_index": chunk.chunk_index,
        "text": chunk.text,
        "source_filename": source_filename,
        "document_chunk_id": chunk.id,
    }


@router.post("/answer", response_model=AnswerResponse)
def answer_question(
    answer_request: AnswerRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        candidate_limit = min(
            max(settings.reranker_candidate_limit, answer_request.top_k),
            50,
        )

        query_vector = embed_query(answer_request.question)

        semantic_points = search_similar_chunks(
            query_vector=query_vector,
            user_id=current_user.id,
            top_k=candidate_limit,
            document_id=answer_request.document_id,
        )

        semantic_results: list[FusionInputResult] = []

        for point in semantic_points:
            payload = point.payload or {}
            document_chunk_id = payload.get("document_chunk_id")

            if document_chunk_id is None:
                continue

            semantic_results.append(
                FusionInputResult(
                    document_chunk_id=int(document_chunk_id),
                    score=float(point.score),
                    payload=payload,
                )
            )

        chunks_query = (
            db.query(DocumentChunk)
            .join(Document, DocumentChunk.document_id == Document.id)
            .options(joinedload(DocumentChunk.document))
            .filter(Document.owner_id == current_user.id)
        )

        if answer_request.document_id is not None:
            chunks_query = chunks_query.filter(
                DocumentChunk.document_id == answer_request.document_id
            )

        chunks = (
            chunks_query
            .order_by(DocumentChunk.chunk_index.asc())
            .all()
        )

        keyword_matches = search_chunks_with_bm25(
            query=answer_request.question,
            chunks=chunks,
            top_k=candidate_limit,
        )

        keyword_results: list[FusionInputResult] = []

        for keyword_match in keyword_matches:
            chunk = keyword_match.chunk

            keyword_results.append(
                FusionInputResult(
                    document_chunk_id=chunk.id,
                    score=keyword_match.score,
                    payload=build_keyword_payload(
                        chunk=chunk,
                        user_id=current_user.id,
                    ),
                )
            )

        fused_results = fuse_search_results(
            semantic_results=semantic_results,
            keyword_results=keyword_results,
            top_k=candidate_limit,
        )

        reranked_results = rerank_fused_results(
            question=answer_request.question,
            fused_results=fused_results,
            top_k=answer_request.top_k,
        )

        sources: list[AnswerSource] = []

        for reranked_result in reranked_results:
            fused_result = reranked_result.fused_result
            payload = fused_result.payload

            sources.append(
                AnswerSource(
                    document_id=payload["document_id"],
                    page_number=payload.get("page_number"),
                    chunk_index=payload["chunk_index"],
                    source_filename=payload["source_filename"],
                    document_chunk_id=payload["document_chunk_id"],
                    score=reranked_result.reranker_score,
                    text=payload["text"],
                )
            )

        if not sources:
            return AnswerResponse(
                question=answer_request.question,
                answer=NO_ANSWER_MESSAGE,
                context_used=False,
                sources_count=0,
                sources=[],
            )

        answer = generate_answer(
            question=answer_request.question,
            sources=sources,
        )

        if answer.strip() == NO_ANSWER_MESSAGE:
            return AnswerResponse(
                question=answer_request.question,
                answer=NO_ANSWER_MESSAGE,
                context_used=False,
                sources_count=0,
                sources=[],
            )

        return AnswerResponse(
            question=answer_request.question,
            answer=answer,
            context_used=True,
            sources_count=len(sources),
            sources=sources,
        )

    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Answer generation failed: {str(error)}",
        ) from error