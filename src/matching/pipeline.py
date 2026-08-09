import logging
from profile.section_documents import SECTION_SNAPSHOT_KEY

from matching.models import JDMatchResult, MatchVersionSource
from schema.match_api import MatchTaskStatus
from storage.repositories import MatchRepository

logger = logging.getLogger(__name__)


class MatchPipeline:
    def __init__(self, repository: MatchRepository, graph, export_dir: str):
        self.repository = repository
        self.graph = graph
        self.export_dir = export_dir

    async def run_full(
        self, match_id: str, source: MatchVersionSource = MatchVersionSource.GENERATED
    ) -> None:
        task = self._require_task(match_id)
        version = self.repository.next_version(match_id)
        self.repository.update_task(
            match_id,
            status=MatchTaskStatus.ANALYZING_JD.value,
            stage="analyzing_jd",
            progress=10,
            error=None,
        )
        try:
            profile_snapshot = dict(task.profile_result_snapshot)
            profile_sections = profile_snapshot.pop(SECTION_SNAPSHOT_KEY, {})
            output = await self.graph.ainvoke(
                {
                    "match_id": match_id,
                    "profile_task_id": task.profile_task_id,
                    "jd_text": task.jd_text,
                    "profile_result": profile_snapshot,
                    "profile_sections": profile_sections,
                    "facts": task.facts_snapshot,
                    "conflicts": task.conflicts_snapshot,
                    "section_outputs": [],
                    "warnings": [],
                    "audit_attempt": 0,
                    "audit_passed": False,
                    "target_version": version,
                    "export_dir": self.export_dir,
                },
                config={"configurable": {"thread_id": task.graph_thread_id}},
            )
            result = JDMatchResult.model_validate(output["result"])
            export_paths = output["export_paths"]
            self.repository.save_version(
                match_id,
                result,
                source,
                export_paths["markdown"],
                export_paths["docx"],
            )
            status = (
                MatchTaskStatus.COMPLETED
                if result.audit.passed
                else MatchTaskStatus.PARTIAL_SUCCESS
            )
            self.repository.update_task(
                match_id,
                status=status.value,
                stage="completed",
                progress=100,
                error="; ".join(result.audit.warnings) or None,
            )
        except Exception as exc:
            logger.exception("JD match task %s failed", match_id)
            self.repository.update_task(
                match_id,
                status=MatchTaskStatus.FAILED_RETRYABLE.value,
                stage="failed",
                error=str(exc),
            )

    async def regenerate(self, match_id: str) -> None:
        self.repository.increment_attempt(match_id)
        await self.run_full(match_id, MatchVersionSource.REGENERATED)

    def _require_task(self, match_id: str):
        task = self.repository.get_task(match_id)
        if task is None:
            raise KeyError(match_id)
        return task
