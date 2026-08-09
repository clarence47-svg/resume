import re
from profile.section_documents import write_profile_section_documents
from uuid import uuid4

from campaigns.models import AggregateGap, BatchStatus, TailoringBatch
from jobs.match_runner import MatchJobAction, MatchJobRunner
from schema.profile_api import TaskStatus
from storage.career_repositories import CareerRepository
from storage.files import FileStorage
from storage.repositories import MatchRepository, ProfileRepository


class BatchTailoringService:
    def __init__(
        self,
        career_repository: CareerRepository,
        profile_repository: ProfileRepository,
        match_repository: MatchRepository,
        storage: FileStorage,
        match_runner: MatchJobRunner,
    ):
        self.career_repository = career_repository
        self.profile_repository = profile_repository
        self.match_repository = match_repository
        self.storage = storage
        self.match_runner = match_runner

    async def create(
        self,
        campaign_id: str,
        job_ids: list[str],
        title: str,
    ) -> TailoringBatch:
        campaign = self.career_repository.get_campaign(campaign_id)
        if campaign is None:
            raise KeyError("campaign")
        profile_task = self.profile_repository.get_task(campaign.profile_task_id)
        if profile_task is None:
            raise KeyError("profile")
        if profile_task.status not in {
            TaskStatus.COMPLETED.value,
            TaskStatus.PARTIAL_SUCCESS.value,
        }:
            raise RuntimeError("画像任务尚未完成。")
        profile_result = self.profile_repository.get_result(campaign.profile_task_id)
        if profile_result is None:
            raise RuntimeError("画像结果不存在。")
        jobs = []
        for job_id in list(dict.fromkeys(job_ids)):
            job = self.career_repository.get_job(job_id)
            if job is None or job.campaign_id != campaign_id:
                raise KeyError(f"job:{job_id}")
            jobs.append(job)
        facts = self.profile_repository.get_facts(campaign.profile_task_id)
        section_paths = write_profile_section_documents(
            profile_result,
            facts,
            self.storage.profile_sections_dir(campaign.profile_task_id),
        )
        batch = TailoringBatch(
            campaign_id=campaign_id,
            profile_task_id=campaign.profile_task_id,
            title=title,
            job_ids=[job.id for job in jobs],
            aggregate_gaps=_aggregate_gaps(jobs, facts),
            status=BatchStatus.GENERATING,
            stage="creating_matches",
            progress=10,
        )
        self.career_repository.save_batch(batch)
        match_ids: dict[str, str] = {}
        for job in jobs:
            match_id = str(uuid4())
            self.match_repository.create_task(
                match_id=match_id,
                profile_task_id=campaign.profile_task_id,
                job_id=job.id,
                batch_id=batch.id,
                title=f"{job.company} · {job.title}",
                jd_text=job.jd_text,
                profile_result=profile_result,
                profile_sections={
                    name: path.read_text(encoding="utf-8") for name, path in section_paths.items()
                },
                facts=facts,
                conflicts=[],
            )
            match_ids[job.id] = match_id
            await self.match_runner.enqueue(match_id, MatchJobAction.FULL)
        batch.match_ids = match_ids
        batch.stage = "matching"
        batch.progress = 20
        self.career_repository.update_batch(
            batch.id,
            match_ids=match_ids,
            aggregate_gaps=[item.model_dump(mode="json") for item in batch.aggregate_gaps],
            status=batch.status.value,
            stage=batch.stage,
            progress=batch.progress,
        )
        return batch

    def refresh(self, batch_id: str) -> TailoringBatch:
        batch = self.career_repository.get_batch(batch_id)
        if batch is None:
            raise KeyError(batch_id)
        tasks = [self.match_repository.get_task(match_id) for match_id in batch.match_ids.values()]
        tasks = [task for task in tasks if task is not None]
        if not tasks:
            return batch
        terminal = {"completed", "partial_success", "failed_retryable", "cancelled"}
        completed = [task for task in tasks if task.status in terminal]
        failures = [task for task in tasks if task.status == "failed_retryable"]
        if len(completed) == len(tasks):
            if len(failures) == len(tasks):
                status = BatchStatus.FAILED_RETRYABLE
            elif failures:
                status = BatchStatus.PARTIAL_SUCCESS
            else:
                status = BatchStatus.COMPLETED
            stage = "completed"
            progress = 100
        else:
            status = BatchStatus.GENERATING
            stage = "matching"
            progress = 20 + round(80 * len(completed) / len(tasks))
        self.career_repository.update_batch(
            batch.id, status=status.value, stage=stage, progress=progress
        )
        return self.career_repository.get_batch(batch.id) or batch


def _aggregate_gaps(jobs, facts) -> list[AggregateGap]:
    fact_text = " ".join(fact.statement for fact in facts).casefold()
    groups: dict[str, AggregateGap] = {}
    for job in jobs:
        tokens = re.findall(r"\b[A-Za-z][A-Za-z0-9+#.\-]{1,30}\b", job.jd_text)
        tokens.extend(
            item
            for item in ("机器学习", "深度学习", "大模型", "数据分析", "项目管理", "用户研究")
            if item in job.jd_text
        )
        for token in dict.fromkeys(tokens):
            key = token.casefold()
            if key in fact_text or len(token) < 2:
                continue
            gap = groups.setdefault(
                key,
                AggregateGap(
                    key=key,
                    text=f"是否有能够证明 {token} 的经历或成果？",
                    keywords=[token],
                    priority=2,
                ),
            )
            if job.id not in gap.job_ids:
                gap.job_ids.append(job.id)
    return sorted(groups.values(), key=lambda item: len(item.job_ids), reverse=True)[:20]
