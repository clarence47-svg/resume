from datetime import datetime

from pydantic import BaseModel, Field

from job_search.models import JobEvaluation, JobPlatform, JobPosting


class JobManualCreate(BaseModel):
    campaign_id: str
    company: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=255)
    jd_text: str = Field(min_length=1, max_length=100000)
    source_url: str = ""
    platform: JobPlatform = JobPlatform.MANUAL
    external_id: str = ""
    location: str = ""
    salary_text: str = ""
    salary_min_k: float | None = Field(default=None, ge=0)
    salary_max_k: float | None = Field(default=None, ge=0)
    employment_type: str = ""
    experience_level: str = ""
    published_at: datetime | None = None


class JobsImportRequest(BaseModel):
    jobs: list[JobManualCreate] = Field(min_length=1, max_length=100)


class JobWithEvaluation(BaseModel):
    job: JobPosting
    evaluation: JobEvaluation | None = None


class JobListResponse(BaseModel):
    items: list[JobWithEvaluation] = Field(default_factory=list)
