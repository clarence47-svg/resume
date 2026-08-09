from abc import ABC, abstractmethod

from campaigns.models import JobCampaign
from job_search.models import JobPosting


class JobSource(ABC):
    @abstractmethod
    async def collect(self, campaign: JobCampaign, **kwargs) -> list[JobPosting]:
        raise NotImplementedError
