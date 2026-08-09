from pydantic import BaseModel

from interview.models import InterviewKit
from tracking.models import FollowUpEvent, TrackingDashboard


class TrackingDashboardResponse(BaseModel):
    dashboard: TrackingDashboard


class FollowUpResponse(BaseModel):
    follow_up: FollowUpEvent


class InterviewCreateRequest(BaseModel):
    job_id: str
    resume_version_id: str


class InterviewKitResponse(BaseModel):
    kit: InterviewKit
