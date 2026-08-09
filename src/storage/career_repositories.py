from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.orm import Session, selectinload, sessionmaker

from applications.models import ApplicationAttempt, ApplicationEvidence, ApplicationStatus
from campaigns.models import JobCampaign, TailoringBatch
from interview.models import InterviewKit
from job_search.models import JobEvaluation, JobPosting
from resumes.models import ResumeVersion
from storage.orm import (
    AnswerBankORM,
    ApplicationAttemptORM,
    ApplicationEventORM,
    BlockerORM,
    CareerSettingsORM,
    FollowUpORM,
    InterviewKitORM,
    JobCampaignORM,
    JobEvaluationORM,
    JobPostingORM,
    ResumeVersionORM,
    TailoringBatchORM,
)
from tracking.models import BlockerRecord, FollowUpEvent


class CareerRepository:
    def __init__(self, session_factory: sessionmaker[Session]):
        self.session_factory = session_factory

    def get_settings_payload(self) -> str | None:
        with self.session_factory() as session:
            row = session.get(CareerSettingsORM, 1)
            return row.encrypted_payload if row else None

    def save_settings_payload(self, encrypted_payload: str) -> None:
        with self.session_factory.begin() as session:
            row = session.get(CareerSettingsORM, 1)
            if row is None:
                row = CareerSettingsORM(id=1, encrypted_payload=encrypted_payload)
                session.add(row)
            else:
                row.encrypted_payload = encrypted_payload

    def list_answer_rows(self) -> list[AnswerBankORM]:
        with self.session_factory() as session:
            return list(session.scalars(select(AnswerBankORM).order_by(AnswerBankORM.question_key)))

    def replace_answers(self, rows: list[tuple[str, str, str, str]]) -> None:
        with self.session_factory.begin() as session:
            session.execute(delete(AnswerBankORM))
            session.add_all(
                AnswerBankORM(
                    id=item_id,
                    question_key=question_key,
                    status=status,
                    encrypted_payload=encrypted_payload,
                )
                for item_id, question_key, status, encrypted_payload in rows
            )

    def save_campaign(self, campaign: JobCampaign) -> None:
        with self.session_factory.begin() as session:
            session.add(
                JobCampaignORM(
                    id=campaign.id,
                    profile_task_id=campaign.profile_task_id,
                    title=campaign.title,
                    strategy=campaign.strategy.value,
                    search_keywords=campaign.search_keywords,
                    target_cities=campaign.target_cities,
                    source_platforms=campaign.source_platforms,
                    status=campaign.status.value,
                    created_at=campaign.created_at,
                    updated_at=campaign.updated_at,
                )
            )

    def get_campaign(self, campaign_id: str) -> JobCampaign | None:
        with self.session_factory() as session:
            row = session.get(JobCampaignORM, campaign_id)
            return self._campaign(row) if row else None

    def list_campaigns(self, profile_task_id: str | None = None) -> list[JobCampaign]:
        with self.session_factory() as session:
            statement = select(JobCampaignORM)
            if profile_task_id:
                statement = statement.where(JobCampaignORM.profile_task_id == profile_task_id)
            statement = statement.order_by(JobCampaignORM.created_at.desc())
            return [self._campaign(row) for row in session.scalars(statement)]

    def delete_campaign(self, campaign_id: str) -> bool:
        with self.session_factory.begin() as session:
            row = session.get(JobCampaignORM, campaign_id)
            if row is None:
                return False
            session.delete(row)
            return True

    def find_duplicate_job(
        self, campaign_id: str, content_hash: str, canonical_url: str
    ) -> JobPosting | None:
        with self.session_factory() as session:
            duplicate_condition = JobPostingORM.content_hash == content_hash
            if canonical_url:
                duplicate_condition = or_(
                    duplicate_condition,
                    JobPostingORM.canonical_url == canonical_url,
                )
            statement = select(JobPostingORM).where(
                JobPostingORM.campaign_id == campaign_id,
                duplicate_condition,
            )
            row = session.scalar(statement)
            return self._job(row) if row else None

    def save_job(self, job: JobPosting) -> None:
        with self.session_factory.begin() as session:
            session.add(
                JobPostingORM(
                    id=job.id,
                    campaign_id=job.campaign_id,
                    profile_task_id=job.profile_task_id,
                    platform=job.platform.value,
                    external_id=job.external_id,
                    source_url=job.source_url,
                    canonical_url=job.canonical_url,
                    company=job.company,
                    title=job.title,
                    location=job.location,
                    salary_text=job.salary_text,
                    salary_min_k=job.salary_min_k,
                    salary_max_k=job.salary_max_k,
                    employment_type=job.employment_type,
                    experience_level=job.experience_level,
                    jd_text=job.jd_text,
                    published_at=job.published_at,
                    fetched_at=job.fetched_at,
                    content_hash=job.content_hash,
                    status=job.status.value,
                    extra_data=job.metadata,
                )
            )

    def get_job(self, job_id: str) -> JobPosting | None:
        with self.session_factory() as session:
            row = session.get(JobPostingORM, job_id)
            return self._job(row) if row else None

    def get_job_row(self, job_id: str) -> JobPostingORM | None:
        with self.session_factory() as session:
            statement = (
                select(JobPostingORM)
                .where(JobPostingORM.id == job_id)
                .options(selectinload(JobPostingORM.evaluation))
            )
            return session.scalar(statement)

    def list_jobs(
        self,
        campaign_id: str | None = None,
        profile_task_id: str | None = None,
    ) -> list[JobPosting]:
        with self.session_factory() as session:
            statement = select(JobPostingORM)
            if campaign_id:
                statement = statement.where(JobPostingORM.campaign_id == campaign_id)
            if profile_task_id:
                statement = statement.where(JobPostingORM.profile_task_id == profile_task_id)
            statement = statement.order_by(JobPostingORM.created_at.desc())
            return [self._job(row) for row in session.scalars(statement)]

    def update_job(self, job_id: str, **values: object) -> None:
        values["updated_at"] = datetime.now(UTC)
        with self.session_factory.begin() as session:
            session.execute(
                update(JobPostingORM).where(JobPostingORM.id == job_id).values(**values)
            )

    def save_evaluation(self, evaluation: JobEvaluation) -> None:
        with self.session_factory.begin() as session:
            row = session.get(JobEvaluationORM, evaluation.job_id)
            if row is None:
                row = JobEvaluationORM(
                    job_id=evaluation.job_id,
                    evaluation_json={},
                    overall_score=evaluation.overall_score,
                    decision=evaluation.decision.value,
                )
                session.add(row)
            row.evaluation_json = evaluation.model_dump(mode="json")
            row.overall_score = evaluation.overall_score
            row.decision = evaluation.decision.value
            row.evaluated_at = evaluation.evaluated_at

    def get_evaluation(self, job_id: str) -> JobEvaluation | None:
        with self.session_factory() as session:
            row = session.get(JobEvaluationORM, job_id)
            return JobEvaluation.model_validate(row.evaluation_json) if row else None

    def save_batch(self, batch: TailoringBatch) -> None:
        with self.session_factory.begin() as session:
            session.add(
                TailoringBatchORM(
                    id=batch.id,
                    campaign_id=batch.campaign_id,
                    profile_task_id=batch.profile_task_id,
                    title=batch.title,
                    job_ids=batch.job_ids,
                    match_ids=batch.match_ids,
                    aggregate_gaps=[item.model_dump(mode="json") for item in batch.aggregate_gaps],
                    status=batch.status.value,
                    stage=batch.stage,
                    progress=batch.progress,
                    error=batch.error,
                    created_at=batch.created_at,
                    updated_at=batch.updated_at,
                )
            )

    def get_batch(self, batch_id: str) -> TailoringBatch | None:
        with self.session_factory() as session:
            row = session.get(TailoringBatchORM, batch_id)
            return self._batch(row) if row else None

    def list_batches(self, campaign_id: str | None = None) -> list[TailoringBatch]:
        with self.session_factory() as session:
            statement = select(TailoringBatchORM)
            if campaign_id:
                statement = statement.where(TailoringBatchORM.campaign_id == campaign_id)
            statement = statement.order_by(TailoringBatchORM.created_at.desc())
            return [self._batch(row) for row in session.scalars(statement)]

    def update_batch(self, batch_id: str, **values: object) -> None:
        values["updated_at"] = datetime.now(UTC)
        with self.session_factory.begin() as session:
            session.execute(
                update(TailoringBatchORM).where(TailoringBatchORM.id == batch_id).values(**values)
            )

    def next_resume_version(self, job_id: str) -> int:
        with self.session_factory() as session:
            value = session.scalar(
                select(func.max(ResumeVersionORM.version)).where(ResumeVersionORM.job_id == job_id)
            )
            return (value or 0) + 1

    def save_resume(self, resume: ResumeVersion) -> None:
        with self.session_factory.begin() as session:
            session.add(
                ResumeVersionORM(
                    id=resume.id,
                    job_id=resume.job_id,
                    profile_task_id=resume.profile_task_id,
                    match_id=resume.match_id,
                    match_version=resume.match_version,
                    version=resume.version,
                    template=resume.template.value,
                    document_json=resume.document.model_dump(mode="json"),
                    markdown_path=resume.markdown_path,
                    html_path=resume.html_path,
                    docx_path=resume.docx_path,
                    pdf_path=resume.pdf_path,
                    created_at=resume.created_at,
                )
            )

    def get_resume(self, resume_id: str) -> ResumeVersion | None:
        with self.session_factory() as session:
            row = session.get(ResumeVersionORM, resume_id)
            return self._resume(row) if row else None

    def list_resumes(self, job_id: str | None = None) -> list[ResumeVersion]:
        with self.session_factory() as session:
            statement = select(ResumeVersionORM)
            if job_id:
                statement = statement.where(ResumeVersionORM.job_id == job_id)
            statement = statement.order_by(ResumeVersionORM.created_at.desc())
            return [self._resume(row) for row in session.scalars(statement)]

    def create_application(self, application: ApplicationAttempt) -> None:
        with self.session_factory.begin() as session:
            session.add(
                ApplicationAttemptORM(
                    id=application.id,
                    job_id=application.job_id,
                    resume_version_id=application.resume_version_id,
                    status=application.status.value,
                    stage=application.stage,
                    progress=application.progress,
                    platform=application.platform.value,
                    encrypted_preview="",
                    preview_hash="",
                    evidence_json={},
                    blocker_code=application.blocker_code,
                    error=application.error,
                    graph_thread_id=application.graph_thread_id
                    or f"application:{application.id}:1",
                    attempt=application.attempt,
                )
            )

    def get_application_row(self, application_id: str) -> ApplicationAttemptORM | None:
        with self.session_factory() as session:
            statement = (
                select(ApplicationAttemptORM)
                .where(ApplicationAttemptORM.id == application_id)
                .options(
                    selectinload(ApplicationAttemptORM.events),
                    selectinload(ApplicationAttemptORM.blockers),
                    selectinload(ApplicationAttemptORM.follow_ups),
                )
            )
            return session.scalar(statement)

    def list_application_rows(self) -> list[ApplicationAttemptORM]:
        with self.session_factory() as session:
            statement = select(ApplicationAttemptORM).order_by(
                ApplicationAttemptORM.created_at.desc()
            )
            return list(session.scalars(statement))

    def get_application(self, application_id: str) -> ApplicationAttempt | None:
        row = self.get_application_row(application_id)
        return self._application(row) if row else None

    def list_applications(self) -> list[ApplicationAttempt]:
        return [self._application(row) for row in self.list_application_rows()]

    def update_application(self, application_id: str, **values: object) -> None:
        values["updated_at"] = datetime.now(UTC)
        with self.session_factory.begin() as session:
            session.execute(
                update(ApplicationAttemptORM)
                .where(ApplicationAttemptORM.id == application_id)
                .values(**values)
            )

    def delete_application(self, application_id: str) -> bool:
        with self.session_factory.begin() as session:
            row = session.get(ApplicationAttemptORM, application_id)
            if row is None:
                return False
            session.delete(row)
            return True

    def delete_job(self, job_id: str) -> bool:
        with self.session_factory.begin() as session:
            row = session.get(JobPostingORM, job_id)
            if row is None:
                return False
            session.delete(row)
            return True

    def mark_running_applications_retryable(self) -> None:
        running = [
            ApplicationStatus.CONNECTING.value,
            ApplicationStatus.OPENING.value,
            ApplicationStatus.FILLING.value,
            ApplicationStatus.SUBMITTING.value,
        ]
        with self.session_factory.begin() as session:
            session.execute(
                update(ApplicationAttemptORM)
                .where(ApplicationAttemptORM.status.in_(running))
                .values(
                    status=ApplicationStatus.FAILED_RETRYABLE.value,
                    stage="service_restarted",
                    error="服务重启导致投递中断，可在确认浏览器状态后重试。",
                )
            )

    def add_application_event(
        self, application_id: str, event_type: str, payload: dict | None = None
    ) -> None:
        with self.session_factory.begin() as session:
            session.add(
                ApplicationEventORM(
                    id=str(uuid4()),
                    application_id=application_id,
                    event_type=event_type,
                    payload=payload or {},
                )
            )

    def add_blocker(self, blocker: BlockerRecord) -> None:
        with self.session_factory.begin() as session:
            session.add(
                BlockerORM(
                    id=blocker.id,
                    application_id=blocker.application_id,
                    code=blocker.code,
                    message=blocker.message,
                    next_action=blocker.next_action,
                    status=blocker.status.value,
                    created_at=blocker.created_at,
                )
            )

    def list_blockers(self, open_only: bool = False) -> list[BlockerRecord]:
        with self.session_factory() as session:
            statement = select(BlockerORM)
            if open_only:
                statement = statement.where(BlockerORM.status == "open")
            statement = statement.order_by(BlockerORM.created_at.desc())
            return [
                BlockerRecord(
                    id=row.id,
                    application_id=row.application_id,
                    code=row.code,
                    message=row.message,
                    next_action=row.next_action,
                    status=row.status,
                    created_at=row.created_at,
                )
                for row in session.scalars(statement)
            ]

    def save_follow_up(self, event: FollowUpEvent) -> None:
        with self.session_factory.begin() as session:
            session.add(
                FollowUpORM(
                    id=event.id,
                    application_id=event.application_id,
                    event_type=event.event_type,
                    title=event.title,
                    scheduled_at=event.scheduled_at,
                    notes=event.notes,
                    completed=event.completed,
                    created_at=event.created_at,
                )
            )

    def list_follow_ups(self, upcoming_only: bool = False) -> list[FollowUpEvent]:
        with self.session_factory() as session:
            statement = select(FollowUpORM)
            if upcoming_only:
                statement = statement.where(
                    FollowUpORM.completed.is_(False), FollowUpORM.scheduled_at >= datetime.now(UTC)
                )
            statement = statement.order_by(FollowUpORM.scheduled_at)
            return [
                FollowUpEvent(
                    id=row.id,
                    application_id=row.application_id,
                    event_type=row.event_type,
                    title=row.title,
                    scheduled_at=row.scheduled_at,
                    notes=row.notes,
                    completed=row.completed,
                    created_at=row.created_at,
                )
                for row in session.scalars(statement)
            ]

    def save_interview_kit(self, kit: InterviewKit, markdown_path: str) -> None:
        with self.session_factory.begin() as session:
            session.add(
                InterviewKitORM(
                    id=kit.id,
                    job_id=kit.job_id,
                    resume_version_id=kit.resume_version_id,
                    kit_json=kit.model_dump(mode="json"),
                    markdown_path=markdown_path,
                    created_at=kit.created_at,
                )
            )

    def get_interview_kit(self, kit_id: str) -> tuple[InterviewKit, str] | None:
        with self.session_factory() as session:
            row = session.get(InterviewKitORM, kit_id)
            return (InterviewKit.model_validate(row.kit_json), row.markdown_path) if row else None

    def list_interview_kits(self, job_id: str | None = None) -> list[InterviewKit]:
        with self.session_factory() as session:
            statement = select(InterviewKitORM)
            if job_id:
                statement = statement.where(InterviewKitORM.job_id == job_id)
            statement = statement.order_by(InterviewKitORM.created_at.desc())
            return [InterviewKit.model_validate(row.kit_json) for row in session.scalars(statement)]

    @staticmethod
    def _campaign(row: JobCampaignORM) -> JobCampaign:
        return JobCampaign(
            id=row.id,
            profile_task_id=row.profile_task_id,
            title=row.title,
            strategy=row.strategy,
            search_keywords=row.search_keywords,
            target_cities=row.target_cities,
            source_platforms=row.source_platforms,
            status=row.status,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _job(row: JobPostingORM) -> JobPosting:
        return JobPosting(
            id=row.id,
            campaign_id=row.campaign_id,
            profile_task_id=row.profile_task_id,
            platform=row.platform,
            external_id=row.external_id,
            source_url=row.source_url,
            canonical_url=row.canonical_url,
            company=row.company,
            title=row.title,
            location=row.location,
            salary_text=row.salary_text,
            salary_min_k=row.salary_min_k,
            salary_max_k=row.salary_max_k,
            employment_type=row.employment_type,
            experience_level=row.experience_level,
            jd_text=row.jd_text,
            published_at=row.published_at,
            fetched_at=row.fetched_at,
            content_hash=row.content_hash,
            status=row.status,
            metadata=row.extra_data,
        )

    @staticmethod
    def _batch(row: TailoringBatchORM) -> TailoringBatch:
        return TailoringBatch(
            id=row.id,
            campaign_id=row.campaign_id,
            profile_task_id=row.profile_task_id,
            title=row.title,
            job_ids=row.job_ids,
            match_ids=row.match_ids,
            aggregate_gaps=row.aggregate_gaps,
            status=row.status,
            stage=row.stage,
            progress=row.progress,
            error=row.error,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _resume(row: ResumeVersionORM) -> ResumeVersion:
        return ResumeVersion(
            id=row.id,
            job_id=row.job_id,
            profile_task_id=row.profile_task_id,
            match_id=row.match_id,
            match_version=row.match_version,
            version=row.version,
            template=row.template,
            document=row.document_json,
            markdown_path=row.markdown_path,
            html_path=row.html_path,
            docx_path=row.docx_path,
            pdf_path=row.pdf_path,
            created_at=row.created_at,
        )

    @staticmethod
    def _application(row: ApplicationAttemptORM) -> ApplicationAttempt:
        preview = None
        if row.encrypted_preview:
            preview = None
        return ApplicationAttempt(
            id=row.id,
            job_id=row.job_id,
            resume_version_id=row.resume_version_id,
            status=row.status,
            stage=row.stage,
            progress=row.progress,
            platform=row.platform,
            preview=preview,
            evidence=application_evidence(row),
            blocker_code=row.blocker_code,
            error=row.error,
            graph_thread_id=row.graph_thread_id,
            attempt=row.attempt,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


def application_evidence(row: ApplicationAttemptORM) -> ApplicationEvidence | None:
    return ApplicationEvidence.model_validate(row.evidence_json) if row.evidence_json else None
