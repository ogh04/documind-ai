from fastapi import APIRouter, Depends, HTTPException, status

from app.api.auth import get_current_user
from app.core.config import settings
from app.models.user import User
from app.schemas.answer import AnswerRequest, AnswerResponse, AnswerSource
from app.services.answer_service import (
    NO_ANSWER_MESSAGE,
    filter_sources_by_min_score,
)
from app.services.embedding_service import embed_query
from app.services.llm_service import generate_answer
from app.services.qdrant_service import search_similar_chunks


router = APIRouter(
    tags=["Answer"],
)


@router.post("/answer", response_model=AnswerResponse)
def answer_question(
    answer_request: AnswerRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        query_vector = embed_query(answer_request.question)

        search_results = search_similar_chunks(
            query_vector=query_vector,
            user_id=current_user.id,
            top_k=answer_request.top_k,
            document_id=answer_request.document_id,
        )

        sources: list[AnswerSource] = []

        for point in search_results:
            payload = point.payload or {}

            sources.append(
                AnswerSource(
                    document_id=payload["document_id"],
                    page_number=payload.get("page_number"),
                    chunk_index=payload["chunk_index"],
                    source_filename=payload["source_filename"],
                    document_chunk_id=payload["document_chunk_id"],
                    score=point.score,
                    text=payload["text"],
                )
            )

        reliable_sources = filter_sources_by_min_score(
            sources=sources,
            min_score=settings.answer_min_score,
        )

        answer = generate_answer(
            question=answer_request.question,
            sources=reliable_sources,
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
            context_used=bool(reliable_sources),
            sources_count=len(reliable_sources),
            sources=reliable_sources,
        )

    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Answer generation failed: {str(error)}",
        ) from error