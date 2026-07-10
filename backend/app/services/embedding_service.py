from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.core.config import settings


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    return SentenceTransformer(settings.embedding_model_name)


def format_passage_text(text: str) -> str:
    return f"passage: {text}"


def format_query_text(text: str) -> str:
    return f"query: {text}"


def embed_passages(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    model = get_embedding_model()

    formatted_texts = [
        format_passage_text(text)
        for text in texts
    ]

    embeddings = model.encode(
        formatted_texts,
        normalize_embeddings=True,
    )

    return embeddings.tolist()


def embed_query(text: str) -> list[float]:
    model = get_embedding_model()

    formatted_text = format_query_text(text)

    embedding = model.encode(
        formatted_text,
        normalize_embeddings=True,
    )

    return embedding.tolist()