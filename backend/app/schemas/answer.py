from typing import Optional

from pydantic import BaseModel, Field


class AnswerRequest(BaseModel):
    question: str = Field(..., min_length=1)
    document_id: Optional[int] = None
    top_k: int = Field(default=5, ge=1, le=20)


class AnswerSource(BaseModel):
    document_id: int
    page_number: Optional[int] = None
    chunk_index: int
    source_filename: str
    document_chunk_id: int
    score: float
    text: str


class AnswerResponse(BaseModel):
    question: str
    answer: str
    context_used: bool
    sources_count: int
    sources: list[AnswerSource]