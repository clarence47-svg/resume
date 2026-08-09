import logging
from profile.models import ConflictRecord, ProfileFact, ProfileResult
from profile.section_documents import write_profile_section_documents

from langgraph.types import Command

from ingestion.chunking import chunk_documents
from ingestion.service import IngestionService
from schema.profile_api import ReviewMode, TaskStatus
from storage.repositories import ProfileRepository

logger = logging.getLogger(__name__)


class ProfilePipeline:
    def __init__(
        self,
        repository: ProfileRepository,
        ingestion: IngestionService,
        graph,
    ):
        self.repository = repository
        self.ingestion = ingestion
        self.graph = graph

    async def run_full(self, task_id: str) -> None:
        task = self._require_task(task_id)
        self.repository.update_task(
            task_id,
            status=TaskStatus.PARSING.value,
            stage="parsing_documents",
            progress=10,
            error=None,
        )
        try:
            documents, parse_errors = self.ingestion.parse_task(task_id)
            if not documents:
                raise RuntimeError(
                    "所有文件均解析失败。" + (" " + "; ".join(parse_errors) if parse_errors else "")
                )
            chunks = chunk_documents(documents)
            self.repository.update_task(
                task_id,
                status=TaskStatus.EXTRACTING.value,
                stage="extracting_facts",
                progress=45,
                error="; ".join(parse_errors) if parse_errors else None,
            )
            output = await self.graph.ainvoke(
                {
                    "task_id": task_id,
                    "export_dir": str(self.ingestion.storage.settings.exports_dir),
                    "mode": "full",
                    "review_mode": task.review_mode,
                    "review_completed": False,
                    "chunks": [chunk.model_dump(mode="json") for chunk in chunks],
                    "facts": [],
                    "conflicts": [],
                    "extracted_fact_batches": [],
                    "section_outputs": [],
                    "warnings": [],
                },
                config=self._config(task.graph_thread_id),
            )
            output = await self._resolve_state(output, task.graph_thread_id)
            self._persist_facts(output)
            if output.get("__interrupt__"):
                self.repository.update_task(
                    task_id,
                    status=TaskStatus.AWAITING_REVIEW.value,
                    stage="awaiting_review",
                    progress=55,
                )
                return
            self._complete(task_id, output, parse_errors)
        except Exception as exc:
            logger.exception("Profile task %s failed", task_id)
            self.repository.update_task(
                task_id,
                status=TaskStatus.FAILED_RETRYABLE.value,
                stage="failed",
                error=str(exc),
            )

    async def resume(self, task_id: str) -> None:
        task = self._require_task(task_id)
        facts = self.repository.get_facts(task_id)
        self.repository.update_task(
            task_id,
            status=TaskStatus.GENERATING.value,
            stage="generating_profile",
            progress=60,
            error=None,
        )
        try:
            output = await self.graph.ainvoke(
                Command(resume={"facts": [fact.model_dump(mode="json") for fact in facts]}),
                config=self._config(task.graph_thread_id),
            )
            output = await self._resolve_state(output, task.graph_thread_id)
            self._persist_facts(output)
            self._complete(task_id, output, [])
        except Exception as exc:
            logger.exception("Profile task %s resume failed", task_id)
            self.repository.update_task(
                task_id,
                status=TaskStatus.FAILED_RETRYABLE.value,
                stage="resume_failed",
                error=str(exc),
            )

    async def regenerate(self, task_id: str) -> None:
        facts = self.repository.get_facts(task_id)
        if not facts:
            raise RuntimeError("没有可用于重新生成的事实。")
        thread_id = self.repository.increment_attempt(task_id)
        task = self._require_task(task_id)
        self.repository.update_task(
            task_id,
            status=TaskStatus.GENERATING.value,
            stage="regenerating_profile",
            progress=60,
            error=None,
        )
        try:
            output = await self.graph.ainvoke(
                {
                    "task_id": task_id,
                    "export_dir": str(self.ingestion.storage.settings.exports_dir),
                    "mode": "facts_only",
                    "review_mode": ReviewMode.AUTO.value,
                    "review_completed": True,
                    "chunks": [],
                    "facts": [fact.model_dump(mode="json") for fact in facts],
                    "conflicts": [
                        conflict.model_dump(mode="json")
                        for conflict in self.repository.get_conflicts(task_id)
                    ],
                    "extracted_fact_batches": [],
                    "section_outputs": [],
                    "warnings": [],
                },
                config=self._config(thread_id),
            )
            self._persist_facts(output)
            self._complete(task.id, output, [])
        except Exception as exc:
            logger.exception("Profile task %s regenerate failed", task_id)
            self.repository.update_task(
                task_id,
                status=TaskStatus.FAILED_RETRYABLE.value,
                stage="regenerate_failed",
                error=str(exc),
            )

    def _complete(self, task_id: str, output: dict, parse_errors: list[str]) -> None:
        result = ProfileResult.model_validate(output["result"])
        export_paths = output["export_paths"]
        self.repository.save_result(
            task_id,
            result,
            export_paths["markdown"],
            export_paths["docx"],
        )
        write_profile_section_documents(
            result,
            self.repository.get_facts(task_id),
            self.ingestion.storage.profile_sections_dir(task_id),
        )
        status = TaskStatus.PARTIAL_SUCCESS if parse_errors else TaskStatus.COMPLETED
        self.repository.update_task(
            task_id,
            status=status.value,
            stage="completed",
            progress=100,
            error="; ".join(parse_errors) if parse_errors else None,
        )

    def _persist_facts(self, output: dict) -> None:
        task_id = output.get("task_id")
        if not task_id:
            return
        facts = [ProfileFact.model_validate(item) for item in output.get("facts", [])]
        conflicts = [ConflictRecord.model_validate(item) for item in output.get("conflicts", [])]
        if facts:
            self.repository.replace_facts(task_id, facts)
        self.repository.set_conflicts(task_id, conflicts)

    async def _resolve_state(self, output: dict, thread_id: str) -> dict:
        if output.get("facts") or output.get("result"):
            return output
        snapshot = await self.graph.aget_state(self._config(thread_id))
        values = dict(snapshot.values)
        if getattr(snapshot, "interrupts", None):
            values["__interrupt__"] = list(snapshot.interrupts)
        return values

    def _require_task(self, task_id: str):
        task = self.repository.get_task(task_id)
        if task is None:
            raise KeyError(task_id)
        return task

    @staticmethod
    def _config(thread_id: str) -> dict:
        return {"configurable": {"thread_id": thread_id}}
