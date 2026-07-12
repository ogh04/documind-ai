import re
from dataclasses import dataclass

from rank_bm25 import BM25Okapi

from app.models.document_chunk import DocumentChunk


@dataclass
class BM25Result:
    chunk: DocumentChunk
    score: float


def tokenize_text(text: str) -> list[str]:
    return re.findall(
        r"\b\w+\b",
        text.lower(),
        flags=re.UNICODE,
    )


def calculate_keyword_overlap_score(
    query_tokens: list[str],
    chunk_tokens: list[str],
) -> float:
    if not query_tokens or not chunk_tokens:
        return 0.0

    query_token_set = set(query_tokens)
    chunk_token_set = set(chunk_tokens)

    matched_terms = query_token_set.intersection(chunk_token_set)

    if not matched_terms:
        return 0.0

    return float(len(matched_terms)) / float(len(query_token_set))


def search_chunks_with_bm25(
    query: str,
    chunks: list[DocumentChunk],
    top_k: int = 5,
) -> list[BM25Result]:
    if not query.strip() or not chunks:
        return []

    tokenized_query = tokenize_text(query)

    if not tokenized_query:
        return []

    tokenized_chunks = [
        tokenize_text(chunk.text)
        for chunk in chunks
    ]

    valid_items = [
        (chunk, tokens)
        for chunk, tokens in zip(chunks, tokenized_chunks)
        if tokens
    ]

    if not valid_items:
        return []

    valid_chunks = [
        item[0]
        for item in valid_items
    ]

    valid_tokenized_chunks = [
        item[1]
        for item in valid_items
    ]

    bm25 = BM25Okapi(valid_tokenized_chunks)
    bm25_scores = bm25.get_scores(tokenized_query)

    results: list[BM25Result] = []

    for chunk, chunk_tokens, bm25_score in zip(
        valid_chunks,
        valid_tokenized_chunks,
        bm25_scores,
    ):
        overlap_score = calculate_keyword_overlap_score(
            query_tokens=tokenized_query,
            chunk_tokens=chunk_tokens,
        )

        if overlap_score == 0:
            continue

        final_score = max(
            float(bm25_score),
            overlap_score,
        )

        results.append(
            BM25Result(
                chunk=chunk,
                score=final_score,
            )
        )

    results.sort(
        key=lambda result: result.score,
        reverse=True,
    )

    return results[:top_k]