from urllib.parse import urlencode, urljoin

from applications.browser.runtime import BrowserRuntime
from applications.browser.safety import detect_blockers
from campaigns.models import JobCampaign
from job_search.models import JobPlatform, JobPosting
from job_search.normalization import normalize_job
from job_search.sources.base import JobSource


class BossJobSource(JobSource):
    def __init__(self, runtime: BrowserRuntime | None = None):
        self.runtime = runtime

    async def collect(self, campaign: JobCampaign, **kwargs) -> list[JobPosting]:
        collector = kwargs.get("browser_collector")
        if collector is not None:
            return await collector.collect_boss_jobs(campaign)
        if self.runtime is None:
            return []
        connection = await self.runtime.inspect()
        if not connection.connected:
            raise RuntimeError(connection.message)
        if not connection.boss_logged_in:
            raise RuntimeError("请先在独立 Chrome 窗口中登录 BOSS 直聘。")
        output = []
        max_jobs = self.runtime.settings.boss_discovery_max_jobs
        async with self.runtime.connect() as context:
            page = context.pages[-1] if context.pages else await context.new_page()
            for keyword in campaign.search_keywords:
                if len(output) >= max_jobs:
                    break
                query = urlencode(
                    {
                        "query": keyword,
                        "city": campaign.target_cities[0] if campaign.target_cities else "",
                    }
                )
                await page.goto(
                    f"https://www.zhipin.com/web/geek/job?{query}",
                    wait_until="domcontentloaded",
                )
                if await detect_blockers(page):
                    return output
                cards = page.locator(".job-card-wrapper, .job-list-box li")
                remaining = max_jobs - len(output)
                for index in range(min(await cards.count(), remaining)):
                    card = cards.nth(index)
                    title = await _text(card, ".job-name, .job-title")
                    company = await _text(card, ".company-name, .boss-name")
                    location = await _text(card, ".job-area, .company-location")
                    salary = await _text(card, ".salary, .job-salary")
                    link = await _attribute(card, "a", "href")
                    detail = await _text(
                        card,
                        ".job-info, .job-card-footer, .job-card-body, .job-card-box",
                    )
                    if not title or not company or not detail:
                        continue
                    output.append(
                        normalize_job(
                            JobPosting(
                                campaign_id=campaign.id,
                                profile_task_id=campaign.profile_task_id,
                                platform=JobPlatform.BOSS,
                                source_url=urljoin("https://www.zhipin.com", link),
                                company=company,
                                title=title,
                                location=location,
                                salary_text=salary,
                                jd_text=detail,
                                metadata={"search_keyword": keyword, "source": "boss_cdp"},
                            )
                        )
                    )
        return output


async def _text(locator, selector: str) -> str:
    target = locator.locator(selector)
    if not await target.count():
        return ""
    try:
        return (await target.first.inner_text()).strip()
    except Exception:
        return ""


async def _attribute(locator, selector: str, name: str) -> str:
    target = locator.locator(selector)
    return (await target.first.get_attribute(name) or "") if await target.count() else ""
