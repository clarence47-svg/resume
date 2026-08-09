from pydantic import BaseModel, Field

from campaigns.models import JobCampaign, TailoringBatch
from career.models import ApplicationStrategy
from job_search.models import JobPosting


class CampaignCreateRequest(BaseModel):
    profile_task_id: str
    title: str = Field(min_length=1, max_length=255)
    strategy: ApplicationStrategy = ApplicationStrategy.VOLUME
    search_keywords: list[str] = Field(default_factory=list, max_length=20)
    target_cities: list[str] = Field(default_factory=list, max_length=20)
    source_platforms: list[str] = Field(default_factory=lambda: ["manual"])


class CampaignResponse(BaseModel):
    campaign: JobCampaign


class CampaignDiscoverRequest(BaseModel):
    include_official_search: bool = True
    include_boss: bool = False
    manual_jobs: list[dict] = Field(default_factory=list, max_length=100)


class CampaignJobsResponse(BaseModel):
    jobs: list[dict] = Field(default_factory=list)


class TailoringBatchCreateRequest(BaseModel):
    campaign_id: str
    job_ids: list[str] = Field(min_length=1, max_length=20)
    title: str = Field(default="批量岗位定制", max_length=255)


class TailoringBatchResponse(BaseModel):
    batch: TailoringBatch


class TailoringBatchResumeRequest(BaseModel):
    answers: dict[str, str] = Field(default_factory=dict)


class JobImportEnvelope(BaseModel):
    campaign_id: str
    jobs: list[JobPosting] = Field(min_length=1, max_length=100)
