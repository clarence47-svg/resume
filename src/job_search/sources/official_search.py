import re

import httpx

from campaigns.models import JobCampaign
from core.settings import Settings
from job_search.models import JobPosting
from job_search.normalization import detect_platform, normalize_job
from job_search.sources.base import JobSource
from matching.job_research import fetch_search_results

TAG_PATTERN = re.compile(r"<[^>]+>")


class OfficialSearchSource(JobSource):
    def __init__(self, settings: Settings):
        self.settings = settings

    async def collect(self, campaign: JobCampaign, **kwargs) -> list[JobPosting]:
        output: list[JobPosting] = []
        timeout = httpx.Timeout(self.settings.job_search_timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            for keyword in campaign.search_keywords:
                _, sources = await fetch_search_results(keyword, self.settings)
                for source in sources:
                    try:
                        response = await client.get(source.url)
                        response.raise_for_status()
                    except Exception:
                        continue
                    text = " ".join(TAG_PATTERN.sub(" ", response.text).split())
                    if len(text) < 80:
                        continue
                    output.append(
                        normalize_job(
                            JobPosting(
                                campaign_id=campaign.id,
                                profile_task_id=campaign.profile_task_id,
                                platform=detect_platform(str(response.url)),
                                source_url=str(response.url),
                                company=source.title.split("-")[0][:255] or "待确认公司",
                                title=keyword,
                                jd_text=text[:100000],
                                metadata={"discovery_query": source.query},
                            )
                        )
                    )
                    if len(output) >= self.settings.job_search_max_results:
                        return output
        return output
