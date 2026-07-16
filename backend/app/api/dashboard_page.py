from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse


router = APIRouter(
    tags=["Dashboard UI"],
)


@router.get("/dashboard", include_in_schema=False)
def get_comparison_dashboard_page():
    dashboard_path = (
        Path(__file__).resolve().parents[1]
        / "static"
        / "comparison_dashboard.html"
    )

    return FileResponse(dashboard_path)