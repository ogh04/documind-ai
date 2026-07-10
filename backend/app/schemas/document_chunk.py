from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DocumentChunkBase(BaseModel):
    document_id: int
    page_number: Optional[int] = None
    chunk_index: int
    text: str


class DocumentChunkCreate(DocumentChunkBase):
    pass


class DocumentChunkRead(DocumentChunkBase):
    id: int
    created_at: datetime

    model_config = {
        "from_attributes": True
    }