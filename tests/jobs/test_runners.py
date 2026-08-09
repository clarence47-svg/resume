import asyncio

import pytest

from jobs.match_runner import MatchJobAction, MatchJobRunner
from jobs.runner import JobAction, JobRunner


class BlockingProfilePipeline:
    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.cancelled = asyncio.Event()
        self.completed: list[str] = []

    async def run_full(self, task_id: str) -> None:
        if task_id == "cancel-me":
            self.started.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                self.cancelled.set()
                raise
        self.completed.append(task_id)

    async def resume(self, task_id: str) -> None:
        self.completed.append(task_id)

    async def regenerate(self, task_id: str) -> None:
        self.completed.append(task_id)


class BlockingMatchPipeline:
    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.cancelled = asyncio.Event()
        self.completed: list[str] = []

    async def run_full(self, match_id: str, _source) -> None:
        if match_id == "cancel-me":
            self.started.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                self.cancelled.set()
                raise
        self.completed.append(match_id)

    async def regenerate(self, match_id: str) -> None:
        self.completed.append(match_id)


@pytest.mark.asyncio
async def test_profile_runner_cancels_running_job_and_keeps_worker_alive() -> None:
    pipeline = BlockingProfilePipeline()
    runner = JobRunner(pipeline, workers=1)
    await runner.start()
    try:
        await runner.enqueue("cancel-me", JobAction.FULL)
        await asyncio.wait_for(pipeline.started.wait(), timeout=1)

        await runner.cancel("cancel-me")

        assert pipeline.cancelled.is_set()
        await runner.enqueue("next-task", JobAction.FULL)
        await asyncio.wait_for(runner.queue.join(), timeout=1)
        assert pipeline.completed == ["next-task"]
    finally:
        await runner.stop()


@pytest.mark.asyncio
async def test_match_runner_cancels_running_job_and_keeps_worker_alive() -> None:
    pipeline = BlockingMatchPipeline()
    runner = MatchJobRunner(pipeline, workers=1)
    await runner.start()
    try:
        await runner.enqueue("cancel-me", MatchJobAction.FULL)
        await asyncio.wait_for(pipeline.started.wait(), timeout=1)

        await runner.cancel("cancel-me")

        assert pipeline.cancelled.is_set()
        await runner.enqueue("next-match", MatchJobAction.FULL)
        await asyncio.wait_for(runner.queue.join(), timeout=1)
        assert pipeline.completed == ["next-match"]
    finally:
        await runner.stop()
