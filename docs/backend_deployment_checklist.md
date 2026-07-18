# R33 Backend Deployment Checklist

Recommended MVP deployment path:
- Backend API: Railway
- PostgreSQL: Railway PostgreSQL
- Redis: Railway Redis or external Redis
- Vector database: Qdrant Cloud

Required production variables:
- DATABASE_URL
- REDIS_URL
- SECRET_KEY
- CORS_ALLOWED_ORIGINS
- QDRANT_URL
- QDRANT_API_KEY
- MISTRAL_API_KEY

Health checks after deployment:
- GET /health
- GET /db-health

Production logs to verify:
- app_startup_started
- app_startup_completed
- database_health_check_completed
- rate_limit_allowed
- upload_started
- document_processing_completed
- indexing_completed
- query_completed
