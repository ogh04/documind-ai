import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session, joinedload

from app.api.auth import get_current_user
from app.core.config import settings
from app.core.logging_config import get_logger, log_event
from app.core.rate_limiter import RAG_RATE_LIMIT, enforce_user_rate_limit
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

logger = get_logger(__name__)


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


def build_answer_source_from_payload(
    payload: dict[str, Any],
    score: float,
) -> AnswerSource:
    return AnswerSource(
        document_id=payload["document_id"],
        page_number=payload.get("page_number"),
        chunk_index=payload["chunk_index"],
        source_filename=payload["source_filename"],
        document_chunk_id=payload["document_chunk_id"],
        score=score,
        text=payload["text"],
    )


def build_answer_sources_from_reranked_results(
    reranked_results: list[Any],
) -> list[AnswerSource]:
    sources: list[AnswerSource] = []

    for reranked_result in reranked_results:
        fused_result = reranked_result.fused_result
        payload = fused_result.payload

        sources.append(
            build_answer_source_from_payload(
                payload=payload,
                score=float(reranked_result.reranker_score),
            )
        )

    return sources


def build_answer_sources_from_keyword_matches(
    keyword_matches: list[Any],
    user_id: int,
    limit: int,
) -> list[AnswerSource]:
    sources: list[AnswerSource] = []
    seen_chunk_ids: set[int] = set()

    for keyword_match in keyword_matches:
        chunk = keyword_match.chunk

        if chunk.id in seen_chunk_ids:
            continue

        seen_chunk_ids.add(chunk.id)

        payload = build_keyword_payload(
            chunk=chunk,
            user_id=user_id,
        )

        sources.append(
            build_answer_source_from_payload(
                payload=payload,
                score=float(keyword_match.score),
            )
        )

        if len(sources) >= limit:
            break

    return sources


def merge_answer_sources(
    source_groups: list[list[AnswerSource]],
    max_sources: int,
) -> list[AnswerSource]:
    merged_sources: list[AnswerSource] = []
    seen_chunk_ids: set[int] = set()

    for source_group in source_groups:
        for source in source_group:
            if source.document_chunk_id in seen_chunk_ids:
                continue

            seen_chunk_ids.add(source.document_chunk_id)
            merged_sources.append(source)

            if len(merged_sources) >= max_sources:
                return merged_sources

    return merged_sources


def build_multilingual_keyword_query(question: str) -> str:
    normalized_question = question.lower()

    expansion_terms: list[str] = []

    medical_trigger_terms = [
        "clinical",
        "clinic",
        "diagnostic",
        "diagnosis",
        "medical use",
        "real medical",
        "ready for real",
        "practical use",
        "medical tool",
    ]

    if any(term in normalized_question for term in medical_trigger_terms):
        expansion_terms.extend(
            [
                "outil",
                "diagnostic",
                "médical",
                "prêt",
                "utilisé",
                "pratique",
                "clinique",
                "application",
                "clinique réelle",
                "expérimental",
                "expertise médicale",
                "validation médicale",
                "ne vise pas à proposer",
                "outil de diagnostic médical",
                "prêt à être utilisé en pratique clinique",
            ]
        )

    if not expansion_terms:
        return question

    return f"{question} {' '.join(expansion_terms)}"


def build_no_answer_response(question: str) -> AnswerResponse:
    return AnswerResponse(
        question=question,
        answer=NO_ANSWER_MESSAGE,
        context_used=False,
        sources_count=0,
        sources=[],
    )


def get_question_preview(question: str, max_length: int = 200) -> str:
    clean_question = " ".join(question.split())

    if len(clean_question) <= max_length:
        return clean_question

    return f"{clean_question[:max_length]}..."


def log_query_completed(
    *,
    user_id: int,
    document_id: int | None,
    top_k: int,
    question: str,
    answer_strategy: str,
    context_used: bool,
    sources_count: int,
    total_duration_ms: float,
) -> None:
    log_event(
        logger=logger,
        event="query_completed",
        message="Answer query completed",
        user_id=user_id,
        document_id=document_id,
        top_k=top_k,
        question_preview=get_question_preview(question),
        answer_strategy=answer_strategy,
        context_used=context_used,
        sources_count=sources_count,
        total_duration_ms=round(total_duration_ms, 2),
    )


@router.post("/answer", response_model=AnswerResponse)
def answer_question(
    answer_request: AnswerRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    start_time = time.perf_counter()

    enforce_user_rate_limit(
        request=request,
        current_user=current_user,
        rule=RAG_RATE_LIMIT,
    )

    try:
        log_event(
            logger=logger,
            event="query_started",
            message="Answer query started",
            user_id=current_user.id,
            document_id=answer_request.document_id,
            top_k=answer_request.top_k,
            question_preview=get_question_preview(answer_request.question),
        )

        candidate_limit = min(
            max(
                settings.reranker_candidate_limit,
                answer_request.top_k * 10,
            ),
            50,
        )

        semantic_start_time = time.perf_counter()

        query_vector = embed_query(answer_request.question)

        semantic_points = search_similar_chunks(
            query_vector=query_vector,
            user_id=current_user.id,
            top_k=candidate_limit,
            document_id=answer_request.document_id,
        )

        semantic_duration_ms = (
            time.perf_counter() - semantic_start_time
        ) * 1000

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

        log_event(
            logger=logger,
            event="semantic_search_completed",
            message="Semantic search completed for answer query",
            user_id=current_user.id,
            document_id=answer_request.document_id,
            candidate_limit=candidate_limit,
            semantic_points_count=len(semantic_points),
            semantic_results_count=len(semantic_results),
            duration_ms=round(semantic_duration_ms, 2),
        )

        keyword_start_time = time.perf_counter()

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

        expanded_keyword_query = build_multilingual_keyword_query(
            answer_request.question
        )

        keyword_matches = search_chunks_with_bm25(
            query=expanded_keyword_query,
            chunks=chunks,
            top_k=candidate_limit,
        )

        keyword_duration_ms = (
            time.perf_counter() - keyword_start_time
        ) * 1000

        keyword_results: list[FusionInputResult] = []
        seen_keyword_chunk_ids: set[int] = set()

        for keyword_match in keyword_matches:
            chunk = keyword_match.chunk

            if chunk.id in seen_keyword_chunk_ids:
                continue

            seen_keyword_chunk_ids.add(chunk.id)

            keyword_results.append(
                FusionInputResult(
                    document_chunk_id=chunk.id,
                    score=float(keyword_match.score),
                    payload=build_keyword_payload(
                        chunk=chunk,
                        user_id=current_user.id,
                    ),
                )
            )

        log_event(
            logger=logger,
            event="keyword_search_completed",
            message="Keyword search completed for answer query",
            user_id=current_user.id,
            document_id=answer_request.document_id,
            available_chunks_count=len(chunks),
            keyword_matches_count=len(keyword_matches),
            keyword_results_count=len(keyword_results),
            duration_ms=round(keyword_duration_ms, 2),
        )

        fusion_start_time = time.perf_counter()

        fused_results = fuse_search_results(
            semantic_results=semantic_results,
            keyword_results=keyword_results,
            top_k=candidate_limit,
        )

        fusion_duration_ms = (
            time.perf_counter() - fusion_start_time
        ) * 1000

        log_event(
            logger=logger,
            event="fusion_completed",
            message="Semantic and keyword results fused",
            user_id=current_user.id,
            document_id=answer_request.document_id,
            semantic_results_count=len(semantic_results),
            keyword_results_count=len(keyword_results),
            fused_results_count=len(fused_results),
            duration_ms=round(fusion_duration_ms, 2),
        )

        fallback_top_k = min(
            max(answer_request.top_k * 2, 10),
            candidate_limit,
        )

        rerank_start_time = time.perf_counter()

        reranked_results = rerank_fused_results(
            question=answer_request.question,
            fused_results=fused_results,
            top_k=fallback_top_k,
        )

        rerank_duration_ms = (
            time.perf_counter() - rerank_start_time
        ) * 1000

        log_event(
            logger=logger,
            event="reranking_completed",
            message="Reranking completed for answer query",
            user_id=current_user.id,
            document_id=answer_request.document_id,
            fallback_top_k=fallback_top_k,
            reranked_results_count=len(reranked_results),
            duration_ms=round(rerank_duration_ms, 2),
        )

        primary_sources = build_answer_sources_from_reranked_results(
            reranked_results[:answer_request.top_k]
        )

        keyword_fallback_sources = build_answer_sources_from_keyword_matches(
            keyword_matches=keyword_matches,
            user_id=current_user.id,
            limit=max(answer_request.top_k, 5),
        )

        if not primary_sources and not keyword_fallback_sources:
            total_duration_ms = (time.perf_counter() - start_time) * 1000

            log_query_completed(
                user_id=current_user.id,
                document_id=answer_request.document_id,
                top_k=answer_request.top_k,
                question=answer_request.question,
                answer_strategy="no_context",
                context_used=False,
                sources_count=0,
                total_duration_ms=total_duration_ms,
            )

            return build_no_answer_response(answer_request.question)

        primary_llm_start_time = time.perf_counter()

        answer = generate_answer(
            question=answer_request.question,
            sources=primary_sources,
        )

        primary_llm_duration_ms = (
            time.perf_counter() - primary_llm_start_time
        ) * 1000

        log_event(
            logger=logger,
            event="answer_generation_completed",
            message="Primary answer generation completed",
            user_id=current_user.id,
            document_id=answer_request.document_id,
            answer_strategy="primary_reranked_sources",
            context_used=answer.strip() != NO_ANSWER_MESSAGE,
            sources_count=len(primary_sources),
            duration_ms=round(primary_llm_duration_ms, 2),
        )

        if answer.strip() != NO_ANSWER_MESSAGE:
            total_duration_ms = (time.perf_counter() - start_time) * 1000

            log_query_completed(
                user_id=current_user.id,
                document_id=answer_request.document_id,
                top_k=answer_request.top_k,
                question=answer_request.question,
                answer_strategy="primary_reranked_sources",
                context_used=True,
                sources_count=len(primary_sources),
                total_duration_ms=total_duration_ms,
            )

            return AnswerResponse(
                question=answer_request.question,
                answer=answer,
                context_used=True,
                sources_count=len(primary_sources),
                sources=primary_sources,
            )

        reranked_fallback_sources = build_answer_sources_from_reranked_results(
            reranked_results
        )

        merged_fallback_sources = merge_answer_sources(
            source_groups=[
                primary_sources,
                keyword_fallback_sources,
                reranked_fallback_sources,
            ],
            max_sources=max(answer_request.top_k * 2, 10),
        )

        fallback_llm_start_time = time.perf_counter()

        fallback_answer = generate_answer(
            question=answer_request.question,
            sources=merged_fallback_sources,
        )

        fallback_llm_duration_ms = (
            time.perf_counter() - fallback_llm_start_time
        ) * 1000

        log_event(
            logger=logger,
            event="answer_generation_completed",
            message="Fallback answer generation completed",
            user_id=current_user.id,
            document_id=answer_request.document_id,
            answer_strategy="merged_fallback_sources",
            context_used=fallback_answer.strip() != NO_ANSWER_MESSAGE,
            sources_count=len(merged_fallback_sources),
            duration_ms=round(fallback_llm_duration_ms, 2),
        )

        if fallback_answer.strip() != NO_ANSWER_MESSAGE:
            total_duration_ms = (time.perf_counter() - start_time) * 1000

            log_query_completed(
                user_id=current_user.id,
                document_id=answer_request.document_id,
                top_k=answer_request.top_k,
                question=answer_request.question,
                answer_strategy="merged_fallback_sources",
                context_used=True,
                sources_count=len(merged_fallback_sources),
                total_duration_ms=total_duration_ms,
            )

            return AnswerResponse(
                question=answer_request.question,
                answer=fallback_answer,
                context_used=True,
                sources_count=len(merged_fallback_sources),
                sources=merged_fallback_sources,
            )

        keyword_llm_start_time = time.perf_counter()

        keyword_only_answer = generate_answer(
            question=answer_request.question,
            sources=keyword_fallback_sources,
        )

        keyword_llm_duration_ms = (
            time.perf_counter() - keyword_llm_start_time
        ) * 1000

        log_event(
            logger=logger,
            event="answer_generation_completed",
            message="Keyword-only answer generation completed",
            user_id=current_user.id,
            document_id=answer_request.document_id,
            answer_strategy="keyword_only_sources",
            context_used=keyword_only_answer.strip() != NO_ANSWER_MESSAGE,
            sources_count=len(keyword_fallback_sources),
            duration_ms=round(keyword_llm_duration_ms, 2),
        )

        if keyword_only_answer.strip() != NO_ANSWER_MESSAGE:
            total_duration_ms = (time.perf_counter() - start_time) * 1000

            log_query_completed(
                user_id=current_user.id,
                document_id=answer_request.document_id,
                top_k=answer_request.top_k,
                question=answer_request.question,
                answer_strategy="keyword_only_sources",
                context_used=True,
                sources_count=len(keyword_fallback_sources),
                total_duration_ms=total_duration_ms,
            )

            return AnswerResponse(
                question=answer_request.question,
                answer=keyword_only_answer,
                context_used=True,
                sources_count=len(keyword_fallback_sources),
                sources=keyword_fallback_sources,
            )

        total_duration_ms = (time.perf_counter() - start_time) * 1000

        log_query_completed(
            user_id=current_user.id,
            document_id=answer_request.document_id,
            top_k=answer_request.top_k,
            question=answer_request.question,
            answer_strategy="no_answer_after_fallbacks",
            context_used=False,
            sources_count=0,
            total_duration_ms=total_duration_ms,
        )

        return build_no_answer_response(answer_request.question)

    except Exception:
        total_duration_ms = (time.perf_counter() - start_time) * 1000

        logger.exception(
            "Answer query failed",
            extra={
                "event": "query_failed",
                "extra_fields": {
                    "user_id": current_user.id,
                    "document_id": answer_request.document_id,
                    "top_k": answer_request.top_k,
                    "question_preview": get_question_preview(
                        answer_request.question
                    ),
                    "duration_ms": round(total_duration_ms, 2),
                },
            },
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Answer generation failed.",
        )