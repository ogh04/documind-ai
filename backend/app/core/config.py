from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "DocuMind AI"
    environment: str = "development"
    database_url: str
    qdrant_url: str

    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    upload_dir: str = "uploads"
    max_upload_size_mb: int = 20

    embedding_provider: str = "local"
    embedding_model_name: str = "intfloat/multilingual-e5-small"
    embedding_vector_size: int = 384

    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    qdrant_collection_name: str = "documind_chunks"

    llm_provider: str = "mistral"
    mistral_api_key: str = ""
    mistral_model: str = "mistral-small-latest"
    mistral_api_url: str = "https://api.mistral.ai/v1/chat/completions"

    answer_min_score: float = 0.55

    reranker_provider: str = "local"
    reranker_model_name: str = "BAAI/bge-reranker-base"
    reranker_candidate_limit: int = 50
    reranker_top_k: int = 5

    redis_url: str = "redis://redis:6379/0"

    rate_limit_enabled: bool = True
    rate_limit_fail_open: bool = True

    rate_limit_auth_login_per_minute: int = 5
    rate_limit_auth_register_per_minute: int = 3

    rate_limit_rag_per_minute: int = 30
    rate_limit_keyword_search_per_minute: int = 60
    rate_limit_rerank_per_minute: int = 20
    rate_limit_eval_per_minute: int = 10

    rate_limit_upload_per_minute: int = 5
    rate_limit_document_processing_per_minute: int = 10

    rate_limit_read_per_minute: int = 120
    rate_limit_chunks_read_per_minute: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()