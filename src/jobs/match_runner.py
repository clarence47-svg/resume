import asyncio
import logging
from dataclasses import dataclass
from enum import StrEnum

from matching.models import MatchVersionSource
from matching.pipeline import MatchPipeline

logger = logging.getLogger(__name__)


class MatchJobAction(StrEnum):
    FULL = "full"
    REGENERATE = "regenerate"
    RETRY = "retry"


@dataclass(frozen=True)
class MatchJob:
    match_id: str
    action: MatchJobAction


class MatchJobRunner:
    def __init__(self, pipeline: MatchPipeline, workers: int = 1):
        self.pipeline = pipeline
        self.workers = workers
        self.queue: asyncio.Queue[MatchJob | None] = asyncio.Queue()
        self.tasks: list[asyncio.Task] = []

    async def start(self) -> None:
        self.tasks = [asyncio.create_task(self._worker()) for _ in range(self.workers)]

    async def stop(self) -> None:
        for _ in self.tasks:
            await self.queue.put(None)
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks.clear()

    async def enqueue(self, match_id: str, action: MatchJobAction) -> None:
        await self.queue.put(MatchJob(match_id=match_id, action=action))

    async def _worker(self) -> None:
        while True:
            job = await self.queue.get()
            try:
                if job is None:
                    return
                if job.action == MatchJobAction.REGENERATE:
                    await self.pipeline.regenerate(job.match_id)
                else:
                    source = (
                        MatchVersionSource.REGENERATED
                        if job.action == MatchJobAction.RETRY
                        else MatchVersionSource.GENERATED
                    )
                    await self.pipeline.run_full(job.match_id, source)
            except Exception:
                logger.exception("Unhandled JD match job error")
            finally:
                self.queue.task_done()
