from collections.abc import Iterable
from datetime import UTC, datetime
from profile.models import ConflictRecord, EvidenceRef, ProfileFact, ProfileResult

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session, selectinload, sessionmaker

from matching.models import JDMatchResult, MatchVersionSource
from schema.profile_api import DocumentStatus, ReviewMode, TaskStatus
from storage.orm import (
    DocumentORM,
    FactORM,
    MatchResultORM,
    MatchResultVersionORM,
    MatchTaskORM,
    ProfileResultORM,
    ProfileTaskORM,
)


class ProfileRepository:
    def __init__(self, session_factory: sessionmaker[Session]):
        self.session_factory = session_factory

    def create_task(self, task_id: str, title: str, review_mode: ReviewMode) -> ProfileTaskORM:
        with self.session_factory.begin() as session:
            task = ProfileTaskORM(
                id=task_id,
                title=title,
                status=TaskStatus.QUEUED.value,
                stage="queued",
                progress=0,
                review_mode=review_mode.value,
                graph_thread_id=f"{task_id}:1",
            )
            session.add(task)
        return task

    def get_task(self, task_id: str) -> ProfileTaskORM | None:
        with self.session_factory() as session:
            statement = (
                select(ProfileTaskORM)
                .where(ProfileTaskORM.id == task_id)
                .options(
                    selectinload(ProfileTaskORM.documents), selectinload(ProfileTaskORM.result)
                )
            )
            return session.scalar(statement)

    def list_tasks(self, limit: int = 100) -> list[ProfileTaskORM]:
        with self.session_factory() as session:
            statement = (
                select(ProfileTaskORM).order_by(ProfileTaskORM.created_at.desc()).limit(limit)
            )
            return list(session.scalars(statement))

    def update_task(self, task_id: str, **values: object) -> None:
        values["updated_at"] = datetime.now(UTC)
        with self.session_factory.begin() as session:
            session.execute(
                update(ProfileTaskORM).where(ProfileTaskORM.id == task_id).values(**values)
            )

    def mark_running_tasks_retryable(self) -> None:
        running = [
            TaskStatus.PARSING.value,
            TaskStatus.EXTRACTING.value,
            TaskStatus.GENERATING.value,
            TaskStatus.AUDITING.value,
        ]
        with self.session_factory.begin() as session:
            session.execute(
                update(ProfileTaskORM)
                .where(ProfileTaskORM.status.in_(running))
                .values(
                    status=TaskStatus.FAILED_RETRYABLE.value,
                    stage="service_restarted",
                    error="服务重启导致任务中断，可点击重试。",
                )
            )

    def increment_attempt(self, task_id: str) -> str:
        with self.session_factory.begin() as session:
            task = session.get(ProfileTaskORM, task_id)
            if task is None:
                raise KeyError(task_id)
            task.attempt += 1
            task.graph_thread_id = f"{task_id}:{task.attempt}"
            task.error = None
            return task.graph_thread_id

    def add_document(
        self,
        *,
        document_id: str,
        task_id: str,
        original_name: str,
        extension: str,
        size_bytes: int,
        stored_path: str | None,
        media_type: str | None,
        sha256: str | None,
        status: DocumentStatus = DocumentStatus.STORED,
        error: str | None = None,
    ) -> DocumentORM:
        with self.session_factory.begin() as session:
            document = DocumentORM(
                id=document_id,
                task_id=task_id,
                original_name=original_name,
                extension=extension,
                size_bytes=size_bytes,
                stored_path=stored_path,
                media_type=media_type,
                sha256=sha256,
                status=status.value,
                error=error,
            )
            session.add(document)
        return document

    def get_documents(self, task_id: str) -> list[DocumentORM]:
        with self.session_factory() as session:
            return list(session.scalars(select(DocumentORM).where(DocumentORM.task_id == task_id)))

    def update_document(self, document_id: str, **values: object) -> None:
        with self.session_factory.begin() as session:
            session.execute(
                update(DocumentORM).where(DocumentORM.id == document_id).values(**values)
            )

    def replace_facts(self, task_id: str, facts: Iterable[ProfileFact]) -> None:
        with self.session_factory.begin() as session:
            session.execute(delete(FactORM).where(FactORM.task_id == task_id))
            session.add_all(
                FactORM(
                    id=fact.id,
                    task_id=task_id,
                    category=fact.category.value,
                    statement=fact.statement,
                    basis_type=fact.basis_type.value,
                    confidence=fact.confidence,
                    evidence_refs=[item.model_dump(mode="json") for item in fact.evidence_refs],
                    rationale=fact.rationale,
                    status=fact.status.value,
                    extra_data=fact.metadata,
                )
                for fact in facts
            )

    def get_facts(self, task_id: str) -> list[ProfileFact]:
        with self.session_factory() as session:
            rows = session.scalars(select(FactORM).where(FactORM.task_id == task_id)).all()
        return [
            ProfileFact(
                id=row.id,
                category=row.category,
                statement=row.statement,
                basis_type=row.basis_type,
                confidence=row.confidence,
                evidence_refs=[EvidenceRef.model_validate(item) for item in row.evidence_refs],
                rationale=row.rationale,
                status=row.status,
                metadata=row.extra_data,
            )
            for row in rows
        ]

    def set_conflicts(self, task_id: str, conflicts: list[ConflictRecord]) -> None:
        self.update_task(
            task_id,
            conflicts=[conflict.model_dump(mode="json") for conflict in conflicts],
        )

    def get_conflicts(self, task_id: str) -> list[ConflictRecord]:
        task = self.get_task(task_id)
        if task is None:
            return []
        return [ConflictRecord.model_validate(item) for item in task.conflicts]

    def save_result(
        self, task_id: str, result: ProfileResult, markdown_path: str, docx_path: str
    ) -> None:
        with self.session_factory.begin() as session:
            row = session.get(ProfileResultORM, task_id)
            if row is None:
                row = ProfileResultORM(task_id=task_id, result_json={})
                session.add(row)
            row.result_json = result.model_dump(mode="json")
            row.markdown_path = markdown_path
            row.docx_path = docx_path

    def get_result(self, task_id: str) -> ProfileResult | None:
        with self.session_factory() as session:
            row = session.get(ProfileResultORM, task_id)
            return ProfileResult.model_validate(row.result_json) if row else None

    def get_result_paths(self, task_id: str) -> tuple[str | None, str | None]:
        with self.session_factory() as session:
            row = session.get(ProfileResultORM, task_id)
            return (row.markdown_path, row.docx_path) if row else (None, None)

    def delete_task(self, task_id: str) -> bool:
        with self.session_factory.begin() as session:
            task = session.get(ProfileTaskORM, task_id)
            if task is None:
                return False
            session.delete(task)
            return True


class MatchRepository:
    def __init__(self, session_factory: sessionmaker[Session]):
        self.session_factory = session_factory

    def create_task(
        self,
        *,
        match_id: str,
        profile_task_id: str,
        title: str,
        jd_text: str,
        profile_result: ProfileResult,
        facts: list[ProfileFact],
        conflicts: list[ConflictRecord],
    ) -> MatchTaskORM:
        with self.session_factory.begin() as session:
            task = MatchTaskORM(
                id=match_id,
                profile_task_id=profile_task_id,
                title=title,
                jd_text=jd_text,
                profile_result_snapshot=profile_result.model_dump(mode="json"),
                facts_snapshot=[fact.model_dump(mode="json") for fact in facts],
                conflicts_snapshot=[item.model_dump(mode="json") for item in conflicts],
                status="queued",
                stage="queued",
                progress=0,
                graph_thread_id=f"match:{match_id}:1",
            )
            session.add(task)
        return task

    def get_task(self, match_id: str) -> MatchTaskORM | None:
        with self.session_factory() as session:
            statement = (
                select(MatchTaskORM)
                .where(MatchTaskORM.id == match_id)
                .options(selectinload(MatchTaskORM.result))
            )
            return session.scalar(statement)

    def list_tasks(
        self, profile_task_id: str | None = None, limit: int = 100
    ) -> list[MatchTaskORM]:
        with self.session_factory() as session:
            statement = select(MatchTaskORM).options(selectinload(MatchTaskORM.result))
            if profile_task_id:
                statement = statement.where(MatchTaskORM.profile_task_id == profile_task_id)
            statement = statement.order_by(MatchTaskORM.created_at.desc()).limit(limit)
            return list(session.scalars(statement))

    def list_ids_for_profile(self, profile_task_id: str) -> list[str]:
        with self.session_factory() as session:
            return list(
                session.scalars(
                    select(MatchTaskORM.id).where(MatchTaskORM.profile_task_id == profile_task_id)
                )
            )

    def update_task(self, match_id: str, **values: object) -> None:
        values["updated_at"] = datetime.now(UTC)
        with self.session_factory.begin() as session:
            session.execute(
                update(MatchTaskORM).where(MatchTaskORM.id == match_id).values(**values)
            )

    def mark_running_tasks_retryable(self) -> None:
        with self.session_factory.begin() as session:
            session.execute(
                update(MatchTaskORM)
                .where(
                    MatchTaskORM.status.in_(["analyzing_jd", "matching", "generating", "auditing"])
                )
                .values(
                    status="failed_retryable",
                    stage="service_restarted",
                    error="服务重启导致任务中断，可点击重试。",
                )
            )

    def increment_attempt(self, match_id: str) -> str:
        with self.session_factory.begin() as session:
            task = session.get(MatchTaskORM, match_id)
            if task is None:
                raise KeyError(match_id)
            task.attempt += 1
            task.graph_thread_id = f"match:{match_id}:{task.attempt}"
            task.error = None
            return task.graph_thread_id

    def next_version(self, match_id: str) -> int:
        with self.session_factory() as session:
            current = session.scalar(
                select(func.max(MatchResultVersionORM.version)).where(
                    MatchResultVersionORM.match_id == match_id
                )
            )
            return (current or 0) + 1

    def save_version(
        self,
        match_id: str,
        result: JDMatchResult,
        source: MatchVersionSource,
        markdown_path: str,
        docx_path: str,
    ) -> None:
        with self.session_factory.begin() as session:
            version = MatchResultVersionORM(
                match_id=match_id,
                version=result.version,
                source=source.value,
                result_json=result.model_dump(mode="json"),
                markdown_path=markdown_path,
                docx_path=docx_path,
            )
            session.add(version)
            current = session.get(MatchResultORM, match_id)
            if current is None:
                current = MatchResultORM(
                    match_id=match_id,
                    result_json={},
                    current_version=result.version,
                )
                session.add(current)
            current.result_json = result.model_dump(mode="json")
            current.current_version = result.version
            current.markdown_path = markdown_path
            current.docx_path = docx_path
            task = session.get(MatchTaskORM, match_id)
            if task is not None:
                task.jd_analysis = result.jd_analysis.model_dump(mode="json")

    def get_result(self, match_id: str) -> JDMatchResult | None:
        with self.session_factory() as session:
            row = session.get(MatchResultORM, match_id)
            return JDMatchResult.model_validate(row.result_json) if row else None

    def get_version(self, match_id: str, version: int) -> JDMatchResult | None:
        with self.session_factory() as session:
            row = session.get(MatchResultVersionORM, (match_id, version))
            return JDMatchResult.model_validate(row.result_json) if row else None

    def list_versions(self, match_id: str) -> list[MatchResultVersionORM]:
        with self.session_factory() as session:
            statement = (
                select(MatchResultVersionORM)
                .where(MatchResultVersionORM.match_id == match_id)
                .order_by(MatchResultVersionORM.version.desc())
            )
            return list(session.scalars(statement))

    def get_result_paths(
        self, match_id: str, version: int | None = None
    ) -> tuple[str | None, str | None]:
        with self.session_factory() as session:
            if version is None:
                row = session.get(MatchResultORM, match_id)
            else:
                row = session.get(MatchResultVersionORM, (match_id, version))
            return (row.markdown_path, row.docx_path) if row else (None, None)

    def delete_task(self, match_id: str) -> bool:
        with self.session_factory.begin() as session:
            task = session.get(MatchTaskORM, match_id)
            if task is None:
                return False
            session.delete(task)
            return True
