from fastapi import FastAPI

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