import httpx

from app.core.config import settings
from app.schemas.answer import AnswerSource
from app.services.answer_service import (
    build_context_from_sources,
    build_grounded_draft_answer,
)


def build_rag_prompt(
    question: str,
    sources: list[AnswerSource],
) -> str:
    context = build_context_from_sources(sources)

    return f"""
You are DocuMind AI, a document question-answering assistant.

You must answer using only the provided context.
Do not use outside knowledge.

If the answer is not present in the context, say:
"I could not find enough information in the provided document context to answer this question."

Question:
{question}

Context:
{context}

Answer:
""".strip()


def is_mistral_configured() -> bool:
    return (
        settings.llm_provider.lower() == "mistral"
        and bool(settings.mistral_api_key.strip())
    )


def generate_answer(
    question: str,
    sources: list[AnswerSource],
) -> str:
    if not sources:
        return (
            "I could not find relevant information in the indexed documents "
            "to answer this question."
        )

    if not is_mistral_configured():
        return build_grounded_draft_answer(
            question=question,
            sources=sources,
        )

    return generate_answer_with_mistral(
        question=question,
        sources=sources,
    )


def generate_answer_with_mistral(
    question: str,
    sources: list[AnswerSource],
) -> str:
    prompt = build_rag_prompt(
        question=question,
        sources=sources,
    )

    headers = {
        "Authorization": f"Bearer {settings.mistral_api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": settings.mistral_model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a strict RAG assistant. "
                    "Answer only from the provided context."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "temperature": 0.2,
        "max_tokens": 500,
    }

    with httpx.Client(timeout=60) as client:
        response = client.post(
            settings.mistral_api_url,
            headers=headers,
            json=payload,
        )

    response.raise_for_status()

    response_data = response.json()

    return response_data["choices"][0]["message"]["content"].strip()