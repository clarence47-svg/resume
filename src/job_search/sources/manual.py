from campaigns.models import JobCampaign
from job_search.models import JobPosting
from job_search.normalization import normalize_job
from job_search.sources.base import JobSource


class ManualJobSource(JobSource):
    async def collect(self, campaign: JobCampaign, **kwargs) -> list[JobPosting]:
        jobs = kwargs.get("jobs", [])
        output = []
        for item in jobs:
            payload = dict(item)
            payload.setdefault("campaign_id", campaign.id)
            payload.setdefault("profile_task_id", campaign.profile_task_id)
            output.append(normalize_job(JobPosting.model_validate(payload)))
        return output
