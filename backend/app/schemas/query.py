from typing import Optional

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1)
    document_id: Optional[int] = None
    top_k: int = Field(default=5, ge=1, le=20)


class QueryResult(BaseModel):
    score: float
    document_id: int
    user_id: int
    page_number: Optional[int] = None
    chunk_index: int
    text: str
    source_filename: str
    document_chunk_id: int


class QueryResponse(BaseModel):
    question: str
    top_k: int
    results_count: int
    results: list[QueryResult]