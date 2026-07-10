from fastapi import APIRouter, Depends, HTTPException, status

from app.api.auth import get_current_user
from app.models.user import User
from app.schemas.query import QueryRequest, QueryResponse, QueryResult
from app.services.embedding_service import embed_query
from app.services.qdrant_service import search_similar_chunks


router = APIRouter(
    tags=["Query"],
)


@router.post("/query", response_model=QueryResponse)
def query_documents(
    query_request: QueryRequest,
    current_user: User = Depends(get_current_user),
):
    try:
        query_vector = embed_query(query_request.question)

        search_results = search_similar_chunks(
            query_vector=query_vector,
            user_id=current_user.id,
            top_k=query_request.top_k,
            document_id=query_request.document_id,
        )

        results: list[QueryResult] = []

        for point in search_results:
            payload = point.payload or {}

            results.append(
                QueryResult(
                    score=point.score,
                    document_id=payload["document_id"],
                    user_id=payload["user_id"],
                    page_number=payload.get("page_number"),
                    chunk_index=payload["chunk_index"],
                    text=payload["text"],
                    source_filename=payload["source_filename"],
                    document_chunk_id=payload["document_chunk_id"],
                )
            )

        return QueryResponse(
            question=query_request.question,
            top_k=query_request.top_k,
            results_count=len(results),
            results=results,
        )

    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Semantic search failed: {str(error)}",
        ) from error