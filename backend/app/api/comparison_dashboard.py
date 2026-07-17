from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.rate_limiter import EVAL_RATE_LIMIT, enforce_user_rate_limit
from app.database.database import get_db
from app.models.user import User
from app.schemas.comparison import ComparisonRequest
from app.schemas.comparison_dashboard import ComparisonDashboardResponse
from app.services.comparison_dashboard_service import (
    build_comparison_dashboard_response,
)
from app.services.comparison_service import compare_retrieval_pipelines


router = APIRouter(
    tags=["Comparison Dashboard"],
)


@router.post(
    "/comparison/dashboard",
    response_model=ComparisonDashboardResponse,
)
def compare_methods_for_dashboard(
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
        comparison = compare_retrieval_pipelines(
            question=comparison_request.question,
            document_id=comparison_request.document_id,
            top_k=comparison_request.top_k,
            reference_answer=comparison_request.reference_answer,
            db=db,
            current_user=current_user,
        )

        return build_comparison_dashboard_response(
            comparison=comparison,
        )

    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Comparison dashboard failed: {str(error)}",
        ) from error