from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from profile.pipeline import ProfilePipeline

from fastapi import FastAPI

from agents import get_agent
from core.logging import configure_logging
from core.settings import Settings, get_settings
from ingestion.service import IngestionService
from ingestion.validation import SUPPORTED_EXTENSIONS
from jobs.match_runner import MatchJobRunner
from jobs.runner import JobRunner
from matching.pipeline import MatchPipeline
from memory import CheckpointerManager
from schema.schema import HealthResponse, ServiceInfo
from service.routes.matches import router as matches_router
from service.routes.profiles import router as profiles_router
from storage.db import create_session_factory, init_db
from storage.files import FileStorage
from storage.repositories import MatchRepository, ProfileRepository


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or get_settings()
    configure_logging(resolved)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        resolved.ensure_directories()
        init_db(resolved)
        session_factory = create_session_factory(resolved)
        repository = ProfileRepository(session_factory)
        match_repository = MatchRepository(session_factory)
        repository.mark_running_tasks_retryable()
        match_repository.mark_running_tasks_retryable()
        storage = FileStorage(resolved)
        ingestion = IngestionService(repository, storage, resolved)
        checkpointer_manager = CheckpointerManager(resolved)
        checkpointer = await checkpointer_manager.start()
        graph = get_agent("profile-agent", checkpointer=checkpointer)
        match_graph = get_agent("jd-match-agent", checkpointer=checkpointer)
        pipeline = ProfilePipeline(repository, ingestion, graph)
        match_pipeline = MatchPipeline(match_repository, match_graph, str(resolved.exports_dir))
        runner = JobRunner(pipeline, workers=resolved.profile_workers)
        match_runner = MatchJobRunner(match_pipeline, workers=resolved.match_workers)
        await runner.start()
        await match_runner.start()
        app.state.settings = resolved
        app.state.repository = repository
        app.state.match_repository = match_repository
        app.state.storage = storage
        app.state.job_runner = runner
        app.state.match_job_runner = match_runner
        yield
        await match_runner.stop()
        await runner.stop()
        await checkpointer_manager.stop()

    app = FastAPI(title=resolved.app_name, version=resolved.app_version, lifespan=lifespan)
    app.include_router(profiles_router)
    app.include_router(matches_router)

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse()

    @app.get("/info", response_model=ServiceInfo)
    def info() -> ServiceInfo:
        return ServiceInfo(
            name=resolved.app_name,
            version=resolved.app_version,
            agent="profile-agent,jd-match-agent",
            model=resolved.profile_model if resolved.llm_configured else "heuristic-fallback",
            llm_configured=resolved.llm_configured,
            supported_extensions=sorted(SUPPORTED_EXTENSIONS),
        )

    return app


app = create_app()
