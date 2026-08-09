from pydantic import BaseModel

from resumes.models import ResumeTemplate, ResumeVersion


class ResumeCreateRequest(BaseModel):
    match_id: str
    match_version: int | None = None
    template: ResumeTemplate = ResumeTemplate.ATS_STANDARD


class ResumeResponse(BaseModel):
    resume: ResumeVersion
