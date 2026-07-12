from dataclasses import dataclass
from typing import Any


RRF_K = 60


@dataclass
class FusionInputResult:
    document_chunk_id: int
    score: float
    payload: dict[str, Any]


@dataclass
class FusedSearchResult:
    document_chunk_id: int
    fused_score: float
    payload: dict[str, Any]
    semantic_rank: int | None = None
    keyword_rank: int | None = None


def reciprocal_rank(rank: int, k: int = RRF_K) -> float:
    return 1.0 / (k + rank)


def fuse_search_results(
    semantic_results: list[FusionInputResult],
    keyword_results: list[FusionInputResult],
    top_k: int = 5,
) -> list[FusedSearchResult]:
    fused_results: dict[int, FusedSearchResult] = {}

    for rank, result in enumerate(semantic_results, start=1):
        fused_score = reciprocal_rank(rank)

        fused_results[result.document_chunk_id] = FusedSearchResult(
            document_chunk_id=result.document_chunk_id,
            fused_score=fused_score,
            payload=result.payload,
            semantic_rank=rank,
            keyword_rank=None,
        )

    for rank, result in enumerate(keyword_results, start=1):
        fused_score = reciprocal_rank(rank)

        existing_result = fused_results.get(result.document_chunk_id)

        if existing_result is None:
            fused_results[result.document_chunk_id] = FusedSearchResult(
                document_chunk_id=result.document_chunk_id,
                fused_score=fused_score,
                payload=result.payload,
                semantic_rank=None,
                keyword_rank=rank,
            )
        else:
            existing_result.fused_score += fused_score
            existing_result.keyword_rank = rank

    ranked_results = sorted(
        fused_results.values(),
        key=lambda result: result.fused_score,
        reverse=True,
    )

    return ranked_results[:top_k]