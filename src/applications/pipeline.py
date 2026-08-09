import asyncio
import random
from datetime import UTC, datetime, timedelta

from applications.browser.runtime import BrowserRuntime
from applications.browser.session import acquire_page
from applications.evidence import verified_evidence
from applications.models import ApplicationAttempt, ApplicationPreview, ApplicationStatus
from applications.platforms import (
    AshbyAdapter,
    BossAdapter,
    GenericAdapter,
    GreenhouseAdapter,
    LeverAdapter,
)
from applications.preview import compute_preview_hash
from applications.validation import validate_preview
from career.encryption import LocalEncryptor
from career.service import CareerService
from core.settings import Settings
from storage.career_repositories import CareerRepository
from storage.files import FileStorage
from tracking.follow_up import default_follow_up
from tracking.models import BlockerRecord

ADAPTERS = {
    "boss": BossAdapter,
    "greenhouse": GreenhouseAdapter,
    "lever": LeverAdapter,
    "ashby": AshbyAdapter,
    "official": GenericAdapter,
    "generic": GenericAdapter,
    "manual": GenericAdapter,
}


class ApplicationPipeline:
    def __init__(
        self,
        repository: CareerRepository,
        career_service: CareerService,
        encryptor: LocalEncryptor,
        storage: FileStorage,
        settings: Settings,
        runtime: BrowserRuntime | None = None,
    ):
        self.repository = repository
        self.career_service = career_service
        self.encryptor = encryptor
        self.storage = storage
        self.settings = settings
        self.runtime = runtime or BrowserRuntime(settings)
        self.boss_action_times: list[datetime] = []

    def create(self, job_id: str, resume_version_id: str) -> ApplicationAttempt:
        job = self.repository.get_job(job_id)
        resume = self.repository.get_resume(resume_version_id)
        if job is None or resume is None or resume.job_id != job_id:
            raise KeyError("job_or_resume")
        application = ApplicationAttempt(
            job_id=job_id,
            resume_version_id=resume_version_id,
            platform=job.platform,
        )
        self.repository.create_application(application)
        return application

    async def prepare(self, application_id: str) -> None:
        application = self.repository.get_application(application_id)
        if application is None:
            raise KeyError(application_id)
        if not self.settings.browser_automation_enabled:
            self._block(
                application_id,
                "browser_disabled",
                "浏览器自动化未启用。",
                "设置 BROWSER_AUTOMATION_ENABLED=true 并启动 Chrome Remote Debugging。",
            )
            return
        job = self.repository.get_job(application.job_id)
        resume = self.repository.get_resume(application.resume_version_id)
        if job is None or resume is None:
            raise KeyError("job_or_resume")
        self.repository.update_application(
            application_id,
            status=ApplicationStatus.CONNECTING.value,
            stage="connect_browser",
            progress=10,
            error=None,
        )
        adapter = ADAPTERS.get(job.platform.value, GenericAdapter)()
        try:
            async with self.runtime.connect() as context:
                page = await acquire_page(context)
                preview = await adapter.prepare(
                    page,
                    job,
                    resume,
                    self.career_service.get_settings(),
                    self.career_service.list_answers(),
                )
                blockers = validate_preview(preview)
                if blockers:
                    self._block(application_id, "needs_user", blockers[0], "在浏览器中处理后继续。")
                    return
                preview.preview_hash = compute_preview_hash(preview)
                self.repository.update_application(
                    application_id,
                    status=ApplicationStatus.AWAITING_CONFIRMATION.value,
                    stage="preview_ready",
                    progress=70,
                    encrypted_preview=self.encryptor.encrypt(preview.model_dump_json()),
                    preview_hash=preview.preview_hash,
                )
                self.repository.add_application_event(
                    application_id, "preview_ready", {"preview_hash": preview.preview_hash}
                )
        except Exception as exc:
            self.repository.update_application(
                application_id,
                status=ApplicationStatus.FAILED_RETRYABLE.value,
                stage="prepare_failed",
                error=str(exc),
            )

    def get_preview(self, application_id: str) -> ApplicationPreview | None:
        row = self.repository.get_application_row(application_id)
        if row is None or not row.encrypted_preview:
            return None
        return ApplicationPreview.model_validate_json(self.encryptor.decrypt(row.encrypted_preview))

    async def confirm(self, application_id: str, preview_hash: str) -> None:
        row = self.repository.get_application_row(application_id)
        if row is None:
            raise KeyError(application_id)
        if row.status != ApplicationStatus.AWAITING_CONFIRMATION.value:
            raise RuntimeError("投递任务当前不在等待确认状态。")
        if not preview_hash or preview_hash != row.preview_hash:
            raise ValueError("预览已变化，请重新生成并确认。")
        preview = self.get_preview(application_id)
        job = self.repository.get_job(row.job_id)
        resume = self.repository.get_resume(row.resume_version_id)
        if preview is None or job is None or resume is None:
            raise RuntimeError("投递预览或关联数据不存在。")
        adapter = ADAPTERS.get(job.platform.value, GenericAdapter)()
        self.repository.update_application(
            application_id,
            status=ApplicationStatus.SUBMITTING.value,
            stage="revalidate",
            progress=80,
        )
        try:
            if job.platform.value == "boss" and not await self.respect_boss_rate_limit(
                application_id
            ):
                return
            async with self.runtime.connect() as context:
                page = await acquire_page(context)
                fresh = await adapter.prepare(
                    page,
                    job,
                    resume,
                    self.career_service.get_settings(),
                    self.career_service.list_answers(),
                )
                fresh.preview_hash = compute_preview_hash(fresh)
                if fresh.preview_hash != preview_hash:
                    self.repository.update_application(
                        application_id,
                        status=ApplicationStatus.AWAITING_CONFIRMATION.value,
                        stage="preview_changed",
                        progress=70,
                        encrypted_preview=self.encryptor.encrypt(fresh.model_dump_json()),
                        preview_hash=fresh.preview_hash,
                    )
                    return
                await adapter.submit(page)
                confirmation_text, confirmation_url, reference = await adapter.verify(page)
                screenshot_path = self.storage.application_confirmation_path(application_id)
                await page.screenshot(path=str(screenshot_path), full_page=True)
                evidence = verified_evidence(
                    confirmation_text,
                    confirmation_url,
                    reference,
                    str(screenshot_path),
                )
                if evidence is None:
                    self._block(
                        application_id,
                        "unverified_submission",
                        "未发现明确的投递成功证据。",
                        "请在浏览器中检查提交结果。",
                    )
                    return
                self.repository.update_application(
                    application_id,
                    status=ApplicationStatus.SUBMITTED.value,
                    stage="submitted",
                    progress=100,
                    evidence_json=evidence.model_dump(mode="json"),
                    error=None,
                )
                self.repository.add_application_event(
                    application_id, "submitted", evidence.model_dump(mode="json")
                )
                self.repository.update_job(job.id, status="submitted")
                self.repository.save_follow_up(
                    default_follow_up(application_id, job.company, job.title)
                )
        except Exception as exc:
            self.repository.update_application(
                application_id,
                status=ApplicationStatus.FAILED_RETRYABLE.value,
                stage="submit_failed",
                error=str(exc),
            )

    def cancel(self, application_id: str) -> None:
        self.repository.update_application(
            application_id,
            status=ApplicationStatus.CANCELLED.value,
            stage="cancelled",
        )

    def _block(self, application_id: str, code: str, message: str, next_action: str) -> None:
        self.repository.update_application(
            application_id,
            status=ApplicationStatus.NEEDS_USER.value,
            stage=code,
            blocker_code=code,
        )
        self.repository.add_blocker(
            BlockerRecord(
                application_id=application_id,
                code=code,
                message=message,
                next_action=next_action,
            )
        )

    async def respect_boss_rate_limit(self, application_id: str) -> bool:
        now = datetime.now(UTC)
        self.boss_action_times = [
            item for item in self.boss_action_times if item >= now - timedelta(days=1)
        ]
        settings = self.career_service.get_settings()
        limit = min(settings.rules.daily_action_limit, self.settings.boss_daily_action_limit)
        if len(self.boss_action_times) >= limit:
            self._block(
                application_id,
                "boss_daily_limit",
                "已达到 BOSS 当日安全操作上限。",
                "次日再继续，或调整求职规则中的每日上限。",
            )
            return False
        if self.boss_action_times:
            minimum = max(
                settings.rules.action_interval_min_seconds,
                self.settings.boss_action_interval_min_seconds,
            )
            maximum = max(
                minimum,
                min(
                    settings.rules.action_interval_max_seconds,
                    self.settings.boss_action_interval_max_seconds,
                ),
            )
            elapsed = (now - self.boss_action_times[-1]).total_seconds()
            wait_seconds = max(0, random.uniform(minimum, maximum) - elapsed)
            if wait_seconds:
                await asyncio.sleep(wait_seconds)
        self.boss_action_times.append(datetime.now(UTC))
        return True
