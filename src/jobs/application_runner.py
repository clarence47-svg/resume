import asyncio
import logging
from dataclasses import dataclass
from enum import StrEnum

from applications.pipeline import ApplicationPipeline

logger = logging.getLogger(__name__)


class ApplicationAction(StrEnum):
    PREPARE = "prepare"
    CONFIRM = "confirm"


@dataclass(frozen=True)
class ApplicationJob:
    application_id: str
    action: ApplicationAction
    preview_hash: str = ""


class ApplicationRunner:
    def __init__(self, pipeline: ApplicationPipeline, workers: int = 1):
        self.pipeline = pipeline
        self.workers = workers
        self.queue: asyncio.Queue[ApplicationJob | None] = asyncio.Queue()
        self.tasks: list[asyncio.Task] = []
        self.running: dict[str, asyncio.Task] = {}

    async def start(self) -> None:
        self.tasks = [asyncio.create_task(self._worker()) for _ in range(self.workers)]

    async def stop(self) -> None:
        for _ in self.tasks:
            await self.queue.put(None)
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks.clear()

    async def enqueue(
        self, application_id: str, action: ApplicationAction, preview_hash: str = ""
    ) -> None:
        await self.queue.put(ApplicationJob(application_id, action, preview_hash))

    async def cancel(self, application_id: str) -> None:
        task = self.running.get(application_id)
        if task is not None:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        self.pipeline.cancel(application_id)

    async def _worker(self) -> None:
        while True:
            job = await self.queue.get()
            try:
                if job is None:
                    return
                task = asyncio.create_task(self._execute(job))
                self.running[job.application_id] = task
                await task
            except asyncio.CancelledError:
                pass
            except Exception:
                logger.exception("Unhandled application job error")
            finally:
                if job is not None:
                    self.running.pop(job.application_id, None)
                self.queue.task_done()

    async def _execute(self, job: ApplicationJob) -> None:
        if job.action == ApplicationAction.CONFIRM:
            await self.pipeline.confirm(job.application_id, job.preview_hash)
        else:
            await self.pipeline.prepare(job.application_id)
