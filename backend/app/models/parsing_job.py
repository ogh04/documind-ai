from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database.database import Base


class ParsingJob(Base):
    __tablename__ = "parsing_jobs"

    id = Column(Integer, primary_key=True, index=True)

    document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    job_type = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False, default="pending")

    error_message = Column(Text, nullable=True)

    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    document = relationship(
        "Document",
        back_populates="parsing_jobs",
    )