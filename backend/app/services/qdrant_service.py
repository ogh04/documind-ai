from functools import lru_cache
from uuid import NAMESPACE_DNS, uuid5

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    ScoredPoint,
    VectorParams,
)

from app.core.config import settings
from app.models.document import Document
from app.models.document_chunk import DocumentChunk


@lru_cache(maxsize=1)
def get_qdrant_client() -> QdrantClient:
    if settings.qdrant_api_key:
        return QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
        )

    return QdrantClient(
        url=settings.qdrant_url,
    )


def ensure_qdrant_collection_exists() -> None:
    client = get_qdrant_client()

    collection_exists = client.collection_exists(
        collection_name=settings.qdrant_collection_name,
    )

    if collection_exists:
        return

    client.create_collection(
        collection_name=settings.qdrant_collection_name,
        vectors_config=VectorParams(
            size=settings.embedding_vector_size,
            distance=Distance.COSINE,
        ),
    )


def create_qdrant_point_id(chunk_id: int) -> str:
    return str(
        uuid5(
            NAMESPACE_DNS,
            f"documind-chunk-{chunk_id}",
        )
    )


def upsert_document_chunks_to_qdrant(
    document: Document,
    chunks: list[DocumentChunk],
    embeddings: list[list[float]],
    user_id: int,
) -> int:
    if len(chunks) != len(embeddings):
        raise ValueError(
            "Chunks count and embeddings count must be equal."
        )

    ensure_qdrant_collection_exists()

    points: list[PointStruct] = []

    for chunk, embedding in zip(chunks, embeddings):
        points.append(
            PointStruct(
                id=create_qdrant_point_id(chunk.id),
                vector=embedding,
                payload={
                    "document_id": document.id,
                    "user_id": user_id,
                    "page_number": chunk.page_number,
                    "chunk_index": chunk.chunk_index,
                    "text": chunk.text,
                    "source_filename": document.original_filename,
                    "document_chunk_id": chunk.id,
                },
            )
        )

    if not points:
        return 0

    client = get_qdrant_client()

    client.upsert(
        collection_name=settings.qdrant_collection_name,
        points=points,
    )

    return len(points)


def search_similar_chunks(
    query_vector: list[float],
    user_id: int,
    top_k: int = 5,
    document_id: int | None = None,
) -> list[ScoredPoint]:
    ensure_qdrant_collection_exists()

    must_conditions = [
        FieldCondition(
            key="user_id",
            match=MatchValue(value=user_id),
        )
    ]

    if document_id is not None:
        must_conditions.append(
            FieldCondition(
                key="document_id",
                match=MatchValue(value=document_id),
            )
        )

    query_filter = Filter(
        must=must_conditions,
    )

    client = get_qdrant_client()

    search_results = client.query_points(
        collection_name=settings.qdrant_collection_name,
        query=query_vector,
        query_filter=query_filter,
        limit=top_k,
        with_payload=True,
    )

    return search_results.points