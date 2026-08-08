import asyncio
import logging
from dataclasses import dataclass
from enum import StrEnum
from profile.pipeline import ProfilePipeline

logger = logging.getLogger(__name__)


class JobAction(StrEnum):
    FULL = "full"
    RESUME = "resume"
    REGENERATE = "regenerate"


@dataclass(frozen=True)
class ProfileJob:
    task_id: str
    action: JobAction


class JobRunner:
    def __init__(self, pipeline: ProfilePipeline, workers: int = 1):
        self.pipeline = pipeline
        self.workers = workers
        self.queue: asyncio.Queue[ProfileJob | None] = asyncio.Queue()
        self.tasks: list[asyncio.Task] = []

    async def start(self) -> None:
        self.tasks = [asyncio.create_task(self._worker()) for _ in range(self.workers)]

    async def stop(self) -> None:
        for _ in self.tasks:
            await self.queue.put(None)
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks.clear()

    async def enqueue(self, task_id: str, action: JobAction) -> None:
        await self.queue.put(ProfileJob(task_id=task_id, action=action))

    async def _worker(self) -> None:
        while True:
            job = await self.queue.get()
            try:
                if job is None:
                    return
                if job.action == JobAction.FULL:
                    await self.pipeline.run_full(job.task_id)
                elif job.action == JobAction.RESUME:
                    await self.pipeline.resume(job.task_id)
                else:
                    await self.pipeline.regenerate(job.task_id)
            except Exception:
                logger.exception("Unhandled profile job error")
            finally:
                self.queue.task_done()
