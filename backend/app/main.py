from contextlib import asynccontextmanager
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
from app.api.dashboard_page import router as dashboard_page_router

from app.core.logging_config import get_logger, log_event, setup_logging
from app.database.database import Base, engine

from app.models import Document, DocumentChunk, ParsingJob, User


setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    startup_start_time = time.perf_counter()

    try:
        log_event(
            logger=logger,
            event="app_startup_started",
            message="Application startup started",
        )

        Base.metadata.create_all(bind=engine)

        startup_duration_ms = (
            time.perf_counter() - startup_start_time
        ) * 1000

        log_event(
            logger=logger,
            event="app_startup_completed",
            message="Application startup completed",
            duration_ms=round(startup_duration_ms, 2),
        )

        yield

    except Exception:
        startup_duration_ms = (
            time.perf_counter() - startup_start_time
        ) * 1000

        logger.exception(
            "Application startup failed",
            extra={
                "event": "app_startup_failed",
                "extra_fields": {
                    "duration_ms": round(startup_duration_ms, 2),
                },
            },
        )

        raise

    finally:
        log_event(
            logger=logger,
            event="app_shutdown_completed",
            message="Application shutdown completed",
        )


app = FastAPI(
    title="DocuMind AI",
    description="Multilingual RAG-based Document Intelligence Platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
app.include_router(dashboard_page_router)


@app.get("/")
def root():
    return {
        "message": "DocuMind AI Backend is running",
    }


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "documind-ai-backend",
    }


@app.get("/db-health")
def database_health_check():
    start_time = time.perf_counter()

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        duration_ms = (time.perf_counter() - start_time) * 1000

        log_event(
            logger=logger,
            event="database_health_check_completed",
            message="Database health check completed",
            status="ok",
            duration_ms=round(duration_ms, 2),
        )

        return {
            "status": "ok",
            "database": "connected",
            "service": "postgresql",
        }

    except Exception as error:
        duration_ms = (time.perf_counter() - start_time) * 1000

        logger.exception(
            "Database health check failed",
            extra={
                "event": "database_health_check_failed",
                "extra_fields": {
                    "status": "error",
                    "duration_ms": round(duration_ms, 2),
                },
            },
        )

        return {
            "status": "error",
            "database": "disconnected",
            "detail": str(error),
        }