from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ParsingJobBase(BaseModel):
    document_id: int
    job_type: str
    status: str
    error_message: Optional[str] = None


class ParsingJobCreate(BaseModel):
    document_id: int
    job_type: str
    status: str = "pending"


class ParsingJobRead(ParsingJobBase):
    id: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    model_config = {
        "from_attributes": True
    }