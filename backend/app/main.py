from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.api.answer import router as answer_router
from app.api.auth import router as auth_router
from app.api.documents import router as documents_router
from app.api.hybrid_search import router as hybrid_search_router
from app.api.keyword_search import router as keyword_search_router
from app.api.query import router as query_router
from app.api.rerank_search import router as rerank_search_router
from app.api.comparison import router as comparison_router
from app.api.comparison_dashboard import router as comparison_dashboard_router

from app.database.database import Base, engine

from app.models import Document, DocumentChunk, ParsingJob, User


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="DocuMind AI",
    description="Multilingual RAG-based Document Intelligence Platform",
    version="0.1.0",
    lifespan=lifespan,
)


app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(query_router)
app.include_router(answer_router)
app.include_router(keyword_search_router)
app.include_router(hybrid_search_router)
app.include_router(rerank_search_router)
app.include_router(comparison_router)
app.include_router(comparison_dashboard_router)


@app.get("/")
def root():
    return {
        "message": "DocuMind AI Backend is running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "documind-ai-backend"
    }


@app.get("/db-health")
def database_health_check():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "ok",
            "database": "connected",
            "service": "postgresql"
        }

    except Exception as error:
        return {
            "status": "error",
            "database": "disconnected",
            "detail": str(error)
        }