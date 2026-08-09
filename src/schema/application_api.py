from pydantic import BaseModel

from applications.models import ApplicationAttempt, ApplicationPreview, BrowserConnectionStatus


class ApplicationCreateRequest(BaseModel):
    job_id: str
    resume_version_id: str


class ApplicationConfirmRequest(BaseModel):
    preview_hash: str


class ApplicationResponse(BaseModel):
    application: ApplicationAttempt


class ApplicationPreviewResponse(BaseModel):
    application_id: str
    preview: ApplicationPreview


class ApplicationDeleteResponse(BaseModel):
    status: str = "deleted"


class BrowserStatusResponse(BaseModel):
    browser: BrowserConnectionStatus
