from pydantic import BaseModel, Field


class DashboardMethodSummary(BaseModel):
    method_name: str
    retrieval_pipeline: str
    answer: str
    context_used: bool
    answer_quality: float | None
    latency_ms: float
    retrieved_chunks_count: int

    faithfulness: float | None
    context_precision: float | None
    context_recall: float | None
    answer_relevance: float | None
    ragas_status: str


class AnswerQualityChartItem(BaseModel):
    method: str
    answer_quality: float | None


class LatencyChartItem(BaseModel):
    method: str
    latency_ms: float


class RagasScoreChartItem(BaseModel):
    metric: str
    method_a: float | None
    method_b: float | None


class ComparisonDashboardResponse(BaseModel):
    question: str
    document_id: int | None
    has_reference_answer: bool
    winner: str | None

    method_a: DashboardMethodSummary
    method_b: DashboardMethodSummary

    answer_quality_chart: list[AnswerQualityChartItem] = Field(
        default_factory=list
    )
    latency_chart: list[LatencyChartItem] = Field(
        default_factory=list
    )
    ragas_score_chart: list[RagasScoreChartItem] = Field(
        default_factory=list
    )

    notes: list[str] = Field(default_factory=list)