from pydantic import BaseModel, Field

from app.schemas.answer import AnswerSource


class ComparisonRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        description="Question used to compare retrieval pipelines.",
    )
    document_id: int | None = Field(
        default=None,
        description="Optional document ID to restrict the comparison to one document.",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of retrieved chunks returned by each method.",
    )
    reference_answer: str | None = Field(
        default=None,
        description=(
            "Optional ground-truth answer used to compute answer quality "
            "and RAGAS scores when available."
        ),
    )


class RagasScores(BaseModel):
    faithfulness: float | None = Field(
        default=None,
        description="Measures whether the answer is supported by the retrieved context.",
    )
    context_precision: float | None = Field(
        default=None,
        description="Measures how relevant the retrieved chunks are.",
    )
    context_recall: float | None = Field(
        default=None,
        description="Measures whether the retrieved context covers the expected answer.",
    )
    answer_relevance: float | None = Field(
        default=None,
        description="Measures how relevant the generated answer is to the question.",
    )
    status: str = Field(
        default="not_computed",
        description=(
            "computed when reference_answer is provided; "
            "not_computed when reference_answer is missing."
        ),
    )


class ComparisonMethodResult(BaseModel):
    method_name: str = Field(
        ...,
        description="Readable name of the compared method.",
    )
    retrieval_pipeline: str = Field(
        ...,
        description="Technical description of the retrieval pipeline.",
    )
    answer: str = Field(
        ...,
        description="Generated answer for this method.",
    )
    context_used: bool = Field(
        ...,
        description="Whether retrieved context was used to generate the answer.",
    )
    answer_quality: float | None = Field(
        default=None,
        description=(
            "Answer quality score when reference_answer is provided; "
            "otherwise null."
        ),
    )
    retrieved_chunks: list[AnswerSource] = Field(
        default_factory=list,
        description="Chunks retrieved and used by this method.",
    )
    retrieved_chunks_count: int = Field(
        default=0,
        description="Number of retrieved chunks returned by this method.",
    )
    ragas_scores: RagasScores = Field(
        default_factory=RagasScores,
        description="RAGAS scores when computable.",
    )
    latency_ms: float = Field(
        ...,
        description="Pipeline latency in milliseconds.",
    )


class ComparisonResponse(BaseModel):
    question: str
    document_id: int | None
    top_k: int
    has_reference_answer: bool
    method_a: ComparisonMethodResult
    method_b: ComparisonMethodResult
    winner: str | None = Field(
        default=None,
        description="Best method based on answer quality when computable.",
    )
    notes: list[str] = Field(default_factory=list)