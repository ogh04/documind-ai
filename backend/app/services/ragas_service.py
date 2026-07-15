import math
from statistics import mean

from app.core.config import settings
from app.schemas.answer import AnswerSource
from app.schemas.comparison import ComparisonMethodResult, RagasScores


def build_contexts_from_sources(sources: list[AnswerSource]) -> list[str]:
    return [
        source.text
        for source in sources
        if source.text and source.text.strip()
    ]


def safe_metric_value(value) -> float | None:
    try:
        numeric_value = float(value)

        if math.isnan(numeric_value):
            return None

        return round(max(0.0, min(1.0, numeric_value)), 4)

    except (TypeError, ValueError):
        return None


def compute_answer_quality_from_ragas(scores: RagasScores) -> float | None:
    values = [
        scores.faithfulness,
        scores.context_precision,
        scores.context_recall,
        scores.answer_relevance,
    ]

    valid_values = [
        value
        for value in values
        if value is not None
    ]

    if not valid_values:
        return None

    return round(mean(valid_values), 4)


def compute_real_ragas_scores(
    question: str,
    answer: str,
    sources: list[AnswerSource],
    reference_answer: str,
) -> RagasScores:
    contexts = build_contexts_from_sources(sources)

    if not contexts:
        return RagasScores(
            status="failed_no_context",
        )

    if not settings.mistral_api_key:
        return RagasScores(
            status="failed_missing_mistral_api_key",
        )

    try:
        from datasets import Dataset
        from langchain_community.embeddings import HuggingFaceEmbeddings
        from langchain_mistralai import ChatMistralAI
        from ragas import evaluate
        from ragas.metrics import (
            answer_relevancy,
            context_precision,
            context_recall,
            faithfulness,
        )

        dataset = Dataset.from_dict(
            {
                "question": [question],
                "answer": [answer],
                "contexts": [contexts],
                "ground_truth": [reference_answer],
            }
        )

        evaluator_llm = ChatMistralAI(
            model=settings.mistral_model,
            mistral_api_key=settings.mistral_api_key,
            temperature=0,
        )

        evaluator_embeddings = HuggingFaceEmbeddings(
            model_name=settings.embedding_model_name,
            encode_kwargs={
                "normalize_embeddings": True,
            },
        )

        result = evaluate(
            dataset=dataset,
            metrics=[
                context_precision,
                faithfulness,
                answer_relevancy,
                context_recall,
            ],
            llm=evaluator_llm,
            embeddings=evaluator_embeddings,
            raise_exceptions=False,
        )

        result_df = result.to_pandas()
        result_row = result_df.iloc[0].to_dict()

        return RagasScores(
            faithfulness=safe_metric_value(
                result_row.get("faithfulness")
            ),
            context_precision=safe_metric_value(
                result_row.get("context_precision")
            ),
            context_recall=safe_metric_value(
                result_row.get("context_recall")
            ),
            answer_relevance=safe_metric_value(
                result_row.get("answer_relevancy")
            ),
            status="computed_ragas",
        )

    except Exception as error:
        return RagasScores(
            status=f"failed_ragas_error: {str(error)}",
        )


def apply_ragas_evaluation(
    question: str,
    method_result: ComparisonMethodResult,
    reference_answer: str,
) -> ComparisonMethodResult:
    ragas_scores = compute_real_ragas_scores(
        question=question,
        answer=method_result.answer,
        sources=method_result.retrieved_chunks,
        reference_answer=reference_answer,
    )

    method_result.ragas_scores = ragas_scores
    method_result.answer_quality = compute_answer_quality_from_ragas(
        scores=ragas_scores,
    )

    return method_result


def choose_winner_by_answer_quality(
    method_a: ComparisonMethodResult,
    method_b: ComparisonMethodResult,
) -> str | None:
    if method_a.answer_quality is None or method_b.answer_quality is None:
        return None

    if abs(method_a.answer_quality - method_b.answer_quality) < 0.001:
        return "tie"

    if method_a.answer_quality > method_b.answer_quality:
        return method_a.method_name

    return method_b.method_name