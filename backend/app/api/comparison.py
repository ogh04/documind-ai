from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.rate_limiter import EVAL_RATE_LIMIT, enforce_user_rate_limit
from app.database.database import get_db
from app.models.user import User
from app.schemas.comparison import ComparisonRequest, ComparisonResponse
from app.services.comparison_service import compare_retrieval_pipelines


router = APIRouter(
    tags=["Comparison"],
)


@router.post("/comparison", response_model=ComparisonResponse)
def compare_methods(
    comparison_request: ComparisonRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    enforce_user_rate_limit(
        request=request,
        current_user=current_user,
        rule=EVAL_RATE_LIMIT,
    )

    try:
        return compare_retrieval_pipelines(
            question=comparison_request.question,
            document_id=comparison_request.document_id,
            top_k=comparison_request.top_k,
            reference_answer=comparison_request.reference_answer,
            db=db,
            current_user=current_user,
        )

    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Comparison failed: {str(error)}",
        ) from error