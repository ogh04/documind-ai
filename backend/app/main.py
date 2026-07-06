from fastapi import FastAPI
from sqlalchemy import text

from app.database.database import engine

app = FastAPI(
    title="DocuMind AI",
    description="Multilingual RAG-based Document Intelligence Platform",
    version="0.1.0",
)


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