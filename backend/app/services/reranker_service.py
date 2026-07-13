from dataclasses import dataclass
from functools import lru_cache

from sentence_transformers import CrossEncoder

from app.core.config import settings
from app.services.fusion_service import FusedSearchResult


@dataclass
class RerankedSearchResult:
    reranker_score: float
    fused_result: FusedSearchResult


@lru_cache(maxsize=1)
def get_reranker_model() -> CrossEncoder:
    return CrossEncoder(settings.reranker_model_name)


def truncate_text(
    text: str,
    max_characters: int = 4000,
) -> str:
    if len(text) <= max_characters:
        return text

    return text[:max_characters]


def rerank_fused_results(
    question: str,
    fused_results: list[FusedSearchResult],
    top_k: int = 5,
) -> list[RerankedSearchResult]:
    if not question.strip() or not fused_results:
        return []

    pairs: list[tuple[str, str]] = []

    valid_fused_results: list[FusedSearchResult] = []

    for fused_result in fused_results:
        text = fused_result.payload.get("text", "")

        if not text.strip():
            continue

        pairs.append(
            (
                question,
                truncate_text(text),
            )
        )

        valid_fused_results.append(fused_result)

    if not pairs:
        return []

    model = get_reranker_model()
    scores = model.predict(pairs)

    reranked_results: list[RerankedSearchResult] = []

    for score, fused_result in zip(scores, valid_fused_results):
        reranked_results.append(
            RerankedSearchResult(
                reranker_score=float(score),
                fused_result=fused_result,
            )
        )

    reranked_results.sort(
        key=lambda result: result.reranker_score,
        reverse=True,
    )

    return reranked_results[:top_k]