from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DocumentBase(BaseModel):
    filename: str
    original_filename: str
    file_type: str
    file_size: int
    status: str
    language: Optional[str] = None


class DocumentCreate(BaseModel):
    filename: str
    original_filename: str
    file_type: str
    file_path: str
    file_size: int
    owner_id: int


class DocumentRead(DocumentBase):
    id: int
    owner_id: int
    file_path: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True
    }