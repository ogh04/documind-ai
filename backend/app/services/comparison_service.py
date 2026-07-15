import time
from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.user import User
from app.schemas.answer import AnswerSource
from app.schemas.comparison import (
    ComparisonMethodResult,
    ComparisonResponse,
    RagasScores,
)
from app.services.answer_service import NO_ANSWER_MESSAGE
from app.services.bm25_service import search_chunks_with_bm25
from app.services.embedding_service import embed_query
from app.services.fusion_service import FusionInputResult, fuse_search_results
from app.services.llm_service import generate_answer
from app.services.qdrant_service import search_similar_chunks
from app.services.ragas_service import (
    apply_ragas_evaluation,
    choose_winner_by_answer_quality,
)
from app.services.reranker_service import rerank_fused_results


def build_source_from_payload(
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


def get_user_chunks(
    db: Session,
    user_id: int,
    document_id: int | None,
) -> list[DocumentChunk]:
    chunks_query = (
        db.query(DocumentChunk)
        .join(Document, DocumentChunk.document_id == Document.id)
        .options(joinedload(DocumentChunk.document))
        .filter(Document.owner_id == user_id)
    )

    if document_id is not None:
        chunks_query = chunks_query.filter(
            DocumentChunk.document_id == document_id
        )

    return (
        chunks_query
        .order_by(DocumentChunk.chunk_index.asc())
        .all()
    )


def run_semantic_pipeline(
    question: str,
    document_id: int | None,
    top_k: int,
    current_user: User,
) -> ComparisonMethodResult:
    start_time = time.perf_counter()

    query_vector = embed_query(question)

    semantic_points = search_similar_chunks(
        query_vector=query_vector,
        user_id=current_user.id,
        top_k=top_k,
        document_id=document_id,
    )

    sources: list[AnswerSource] = []

    for point in semantic_points:
        payload = point.payload or {}

        required_fields = [
            "document_id",
            "chunk_index",
            "source_filename",
            "document_chunk_id",
            "text",
        ]

        if any(field not in payload for field in required_fields):
            continue

        sources.append(
            build_source_from_payload(
                payload=payload,
                score=float(point.score),
            )
        )

    answer = generate_answer(
        question=question,
        sources=sources,
    )

    latency_ms = (time.perf_counter() - start_time) * 1000

    return ComparisonMethodResult(
        method_name="Method A",
        retrieval_pipeline="normal semantic search",
        answer=answer,
        context_used=answer.strip() != NO_ANSWER_MESSAGE,
        answer_quality=None,
        retrieved_chunks=sources,
        retrieved_chunks_count=len(sources),
        ragas_scores=RagasScores(
            status="not_computed",
        ),
        latency_ms=round(latency_ms, 2),
    )


def run_hybrid_reranker_pipeline(
    question: str,
    document_id: int | None,
    top_k: int,
    db: Session,
    current_user: User,
) -> ComparisonMethodResult:
    start_time = time.perf_counter()

    candidate_limit = min(
        max(
            settings.reranker_candidate_limit,
            top_k * 10,
        ),
        50,
    )

    query_vector = embed_query(question)

    semantic_points = search_similar_chunks(
        query_vector=query_vector,
        user_id=current_user.id,
        top_k=candidate_limit,
        document_id=document_id,
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

    chunks = get_user_chunks(
        db=db,
        user_id=current_user.id,
        document_id=document_id,
    )

    keyword_matches = search_chunks_with_bm25(
        query=question,
        chunks=chunks,
        top_k=candidate_limit,
    )

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

    fused_results = fuse_search_results(
        semantic_results=semantic_results,
        keyword_results=keyword_results,
        top_k=candidate_limit,
    )

    reranked_results = rerank_fused_results(
        question=question,
        fused_results=fused_results,
        top_k=top_k,
    )

    sources: list[AnswerSource] = []

    for reranked_result in reranked_results:
        fused_result = reranked_result.fused_result
        payload = fused_result.payload

        sources.append(
            build_source_from_payload(
                payload=payload,
                score=float(reranked_result.reranker_score),
            )
        )

    answer = generate_answer(
        question=question,
        sources=sources,
    )

    latency_ms = (time.perf_counter() - start_time) * 1000

    return ComparisonMethodResult(
        method_name="Method B",
        retrieval_pipeline="hybrid search plus reranking",
        answer=answer,
        context_used=answer.strip() != NO_ANSWER_MESSAGE,
        answer_quality=None,
        retrieved_chunks=sources,
        retrieved_chunks_count=len(sources),
        ragas_scores=RagasScores(
            status="not_computed",
        ),
        latency_ms=round(latency_ms, 2),
    )


def compare_retrieval_pipelines(
    question: str,
    document_id: int | None,
    top_k: int,
    reference_answer: str | None,
    db: Session,
    current_user: User,
) -> ComparisonResponse:
    method_a = run_semantic_pipeline(
        question=question,
        document_id=document_id,
        top_k=top_k,
        current_user=current_user,
    )

    method_b = run_hybrid_reranker_pipeline(
        question=question,
        document_id=document_id,
        top_k=top_k,
        db=db,
        current_user=current_user,
    )

    notes: list[str] = [
        "Method A uses normal semantic search.",
        "Method B uses hybrid search plus reranking.",
    ]

    winner: str | None = None

    clean_reference_answer = (
        reference_answer.strip()
        if reference_answer is not None and reference_answer.strip()
        else None
    )

    if clean_reference_answer is None:
        notes.append(
            "RAGAS scores and answer quality are not computed because no reference_answer was provided."
        )

    else:
        method_a = apply_ragas_evaluation(
            question=question,
            method_result=method_a,
            reference_answer=clean_reference_answer,
        )

        method_b = apply_ragas_evaluation(
            question=question,
            method_result=method_b,
            reference_answer=clean_reference_answer,
        )

        winner = choose_winner_by_answer_quality(
            method_a=method_a,
            method_b=method_b,
        )

        if (
            method_a.ragas_scores.status == "computed_ragas"
            and method_b.ragas_scores.status == "computed_ragas"
        ):
            notes.append(
                "RAGAS scores were computed because reference_answer was provided."
            )

        else:
            notes.append(
                "RAGAS evaluation was attempted, but at least one method did not complete successfully."
            )
            notes.append(
                f"Method A RAGAS status: {method_a.ragas_scores.status}"
            )
            notes.append(
                f"Method B RAGAS status: {method_b.ragas_scores.status}"
            )

    return ComparisonResponse(
        question=question,
        document_id=document_id,
        top_k=top_k,
        has_reference_answer=clean_reference_answer is not None,
        method_a=method_a,
        method_b=method_b,
        winner=winner,
        notes=notes,
    )