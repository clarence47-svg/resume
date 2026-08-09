from fastapi import APIRouter, Depends

from schema.tracking_api import TrackingDashboardResponse
from service.dependencies import get_career_repository
from storage.career_repositories import CareerRepository
from tracking.dashboard import build_dashboard

router = APIRouter(prefix="/tracking", tags=["tracking"])


@router.get("/dashboard", response_model=TrackingDashboardResponse)
def dashboard(
    repository: CareerRepository = Depends(get_career_repository),
) -> TrackingDashboardResponse:
    return TrackingDashboardResponse(dashboard=build_dashboard(repository))
