import time

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.auth import get_current_user
from app.core.logging_config import get_logger, log_event
from app.core.rate_limiter import RAG_RATE_LIMIT, enforce_user_rate_limit
from app.models.user import User
from app.schemas.query import QueryRequest, QueryResponse, QueryResult
from app.services.embedding_service import embed_query
from app.services.qdrant_service import search_similar_chunks


router = APIRouter(
    tags=["Query"],
)

logger = get_logger(__name__)


def get_question_preview(question: str, max_length: int = 200) -> str:
    clean_question = " ".join(question.split())

    if len(clean_question) <= max_length:
        return clean_question

    return f"{clean_question[:max_length]}..."


@router.post("/query", response_model=QueryResponse)
def query_documents(
    query_request: QueryRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    total_start_time = time.perf_counter()

    enforce_user_rate_limit(
        request=request,
        current_user=current_user,
        rule=RAG_RATE_LIMIT,
    )

    try:
        log_event(
            logger=logger,
            event="semantic_query_started",
            message="Semantic query started",
            user_id=current_user.id,
            document_id=query_request.document_id,
            top_k=query_request.top_k,
            question_preview=get_question_preview(query_request.question),
        )

        embedding_start_time = time.perf_counter()

        query_vector = embed_query(query_request.question)

        embedding_duration_ms = (
            time.perf_counter() - embedding_start_time
        ) * 1000

        log_event(
            logger=logger,
            event="query_embedding_completed",
            message="Query embedding completed",
            user_id=current_user.id,
            document_id=query_request.document_id,
            vector_size=len(query_vector),
            duration_ms=round(embedding_duration_ms, 2),
        )

        qdrant_start_time = time.perf_counter()

        search_results = search_similar_chunks(
            query_vector=query_vector,
            user_id=current_user.id,
            top_k=query_request.top_k,
            document_id=query_request.document_id,
        )

        qdrant_search_duration_ms = (
            time.perf_counter() - qdrant_start_time
        ) * 1000

        log_event(
            logger=logger,
            event="qdrant_search_completed",
            message="Qdrant semantic search completed",
            user_id=current_user.id,
            document_id=query_request.document_id,
            top_k=query_request.top_k,
            results_count=len(search_results),
            duration_ms=round(qdrant_search_duration_ms, 2),
        )

        response_build_start_time = time.perf_counter()

        results: list[QueryResult] = []

        for point in search_results:
            payload = point.payload or {}

            results.append(
                QueryResult(
                    score=point.score,
                    document_id=payload["document_id"],
                    user_id=payload["user_id"],
                    page_number=payload.get("page_number"),
                    chunk_index=payload["chunk_index"],
                    text=payload["text"],
                    source_filename=payload["source_filename"],
                    document_chunk_id=payload["document_chunk_id"],
                )
            )

        response_build_duration_ms = (
            time.perf_counter() - response_build_start_time
        ) * 1000

        total_duration_ms = (
            time.perf_counter() - total_start_time
        ) * 1000

        log_event(
            logger=logger,
            event="semantic_query_completed",
            message="Semantic query completed",
            user_id=current_user.id,
            document_id=query_request.document_id,
            top_k=query_request.top_k,
            results_count=len(results),
            embedding_duration_ms=round(embedding_duration_ms, 2),
            qdrant_search_duration_ms=round(qdrant_search_duration_ms, 2),
            response_build_duration_ms=round(response_build_duration_ms, 2),
            total_duration_ms=round(total_duration_ms, 2),
        )

        return QueryResponse(
            question=query_request.question,
            top_k=query_request.top_k,
            results_count=len(results),
            results=results,
        )

    except Exception as error:
        total_duration_ms = (
            time.perf_counter() - total_start_time
        ) * 1000

        logger.exception(
            "Semantic query failed",
            extra={
                "event": "semantic_query_failed",
                "extra_fields": {
                    "user_id": current_user.id,
                    "document_id": query_request.document_id,
                    "top_k": query_request.top_k,
                    "question_preview": get_question_preview(
                        query_request.question
                    ),
                    "duration_ms": round(total_duration_ms, 2),
                    "error": str(error),
                },
            },
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Semantic search failed: {str(error)}",
        ) from error