from app.schemas.comparison import ComparisonMethodResult, ComparisonResponse
from app.schemas.comparison_dashboard import (
    AnswerQualityChartItem,
    ComparisonDashboardResponse,
    DashboardMethodSummary,
    LatencyChartItem,
    RagasScoreChartItem,
)


def build_method_summary(
    method_result: ComparisonMethodResult,
) -> DashboardMethodSummary:
    return DashboardMethodSummary(
        method_name=method_result.method_name,
        retrieval_pipeline=method_result.retrieval_pipeline,
        answer=method_result.answer,
        context_used=method_result.context_used,
        answer_quality=method_result.answer_quality,
        latency_ms=method_result.latency_ms,
        retrieved_chunks_count=method_result.retrieved_chunks_count,
        faithfulness=method_result.ragas_scores.faithfulness,
        context_precision=method_result.ragas_scores.context_precision,
        context_recall=method_result.ragas_scores.context_recall,
        answer_relevance=method_result.ragas_scores.answer_relevance,
        ragas_status=method_result.ragas_scores.status,
    )


def build_answer_quality_chart(
    comparison: ComparisonResponse,
) -> list[AnswerQualityChartItem]:
    return [
        AnswerQualityChartItem(
            method="Method A",
            answer_quality=comparison.method_a.answer_quality,
        ),
        AnswerQualityChartItem(
            method="Method B",
            answer_quality=comparison.method_b.answer_quality,
        ),
    ]


def build_latency_chart(
    comparison: ComparisonResponse,
) -> list[LatencyChartItem]:
    return [
        LatencyChartItem(
            method="Method A",
            latency_ms=comparison.method_a.latency_ms,
        ),
        LatencyChartItem(
            method="Method B",
            latency_ms=comparison.method_b.latency_ms,
        ),
    ]


def build_ragas_score_chart(
    comparison: ComparisonResponse,
) -> list[RagasScoreChartItem]:
    return [
        RagasScoreChartItem(
            metric="Faithfulness",
            method_a=comparison.method_a.ragas_scores.faithfulness,
            method_b=comparison.method_b.ragas_scores.faithfulness,
        ),
        RagasScoreChartItem(
            metric="Context precision",
            method_a=comparison.method_a.ragas_scores.context_precision,
            method_b=comparison.method_b.ragas_scores.context_precision,
        ),
        RagasScoreChartItem(
            metric="Context recall",
            method_a=comparison.method_a.ragas_scores.context_recall,
            method_b=comparison.method_b.ragas_scores.context_recall,
        ),
        RagasScoreChartItem(
            metric="Answer relevance",
            method_a=comparison.method_a.ragas_scores.answer_relevance,
            method_b=comparison.method_b.ragas_scores.answer_relevance,
        ),
    ]


def build_comparison_dashboard_response(
    comparison: ComparisonResponse,
) -> ComparisonDashboardResponse:
    return ComparisonDashboardResponse(
        question=comparison.question,
        document_id=comparison.document_id,
        has_reference_answer=comparison.has_reference_answer,
        winner=comparison.winner,
        method_a=build_method_summary(comparison.method_a),
        method_b=build_method_summary(comparison.method_b),
        answer_quality_chart=build_answer_quality_chart(comparison),
        latency_chart=build_latency_chart(comparison),
        ragas_score_chart=build_ragas_score_chart(comparison),
        notes=comparison.notes,
    )