from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from profile.pipeline import ProfilePipeline

from fastapi import FastAPI

from agents import get_agent
from applications.pipeline import ApplicationPipeline
from campaigns.batch_tailoring import BatchTailoringService
from career.encryption import LocalEncryptor
from career.service import CareerService
from core.logging import configure_logging
from core.settings import Settings, get_settings
from ingestion.service import IngestionService
from ingestion.validation import SUPPORTED_EXTENSIONS
from interview.pipeline import InterviewPipeline
from job_search.pipeline import JobDiscoveryPipeline
from jobs.application_runner import ApplicationRunner
from jobs.match_runner import MatchJobRunner
from jobs.runner import JobRunner
from matching.pipeline import MatchPipeline
from memory import CheckpointerManager
from resumes.pipeline import ResumePipeline
from schema.schema import HealthResponse, ServiceInfo
from service.routes.applications import router as applications_router
from service.routes.campaigns import router as campaigns_router
from service.routes.career import router as career_router
from service.routes.interviews import router as interviews_router
from service.routes.jobs import router as jobs_router
from service.routes.matches import router as matches_router
from service.routes.profiles import router as profiles_router
from service.routes.resumes import router as resumes_router
from service.routes.tracking import router as tracking_router
from storage.career_repositories import CareerRepository
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
        career_repository = CareerRepository(session_factory)
        repository.mark_running_tasks_retryable()
        match_repository.mark_running_tasks_retryable()
        career_repository.mark_running_applications_retryable()
        storage = FileStorage(resolved)
        ingestion = IngestionService(repository, storage, resolved)
        checkpointer_manager = CheckpointerManager(resolved)
        checkpointer = await checkpointer_manager.start()
        graph = get_agent("profile-agent", checkpointer=checkpointer)
        match_graph = get_agent("jd-match-agent", checkpointer=checkpointer)
        pipeline = ProfilePipeline(repository, ingestion, graph)
        match_pipeline = MatchPipeline(match_repository, match_graph, str(resolved.exports_dir))
        encryptor = LocalEncryptor(resolved)
        career_service = CareerService(career_repository, encryptor)
        job_discovery_pipeline = JobDiscoveryPipeline(career_repository, career_service)
        resume_pipeline = ResumePipeline(
            career_repository, match_repository, career_service, storage
        )
        application_pipeline = ApplicationPipeline(
            career_repository,
            career_service,
            encryptor,
            storage,
            resolved,
        )
        interview_pipeline = InterviewPipeline(career_repository, storage)
        runner = JobRunner(pipeline, workers=resolved.profile_workers)
        match_runner = MatchJobRunner(match_pipeline, workers=resolved.match_workers)
        application_runner = ApplicationRunner(
            application_pipeline, workers=resolved.career_workers
        )
        batch_tailoring_service = BatchTailoringService(
            career_repository,
            repository,
            match_repository,
            storage,
            match_runner,
        )
        await runner.start()
        await match_runner.start()
        await application_runner.start()
        app.state.settings = resolved
        app.state.repository = repository
        app.state.match_repository = match_repository
        app.state.career_repository = career_repository
        app.state.career_service = career_service
        app.state.storage = storage
        app.state.job_runner = runner
        app.state.match_job_runner = match_runner
        app.state.job_discovery_pipeline = job_discovery_pipeline
        app.state.batch_tailoring_service = batch_tailoring_service
        app.state.resume_pipeline = resume_pipeline
        app.state.application_pipeline = application_pipeline
        app.state.application_runner = application_runner
        app.state.interview_pipeline = interview_pipeline
        yield
        await application_runner.stop()
        await match_runner.stop()
        await runner.stop()
        await checkpointer_manager.stop()

    app = FastAPI(title=resolved.app_name, version=resolved.app_version, lifespan=lifespan)
    app.include_router(profiles_router)
    app.include_router(matches_router)
    app.include_router(career_router)
    app.include_router(campaigns_router)
    app.include_router(jobs_router)
    app.include_router(resumes_router)
    app.include_router(applications_router)
    app.include_router(tracking_router)
    app.include_router(interviews_router)

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse()

    @app.get("/info", response_model=ServiceInfo)
    def info() -> ServiceInfo:
        return ServiceInfo(
            name=resolved.app_name,
            version=resolved.app_version,
            agent=(
                "profile-agent,jd-match-agent,job-discovery-agent,"
                "resume-builder-agent,application-agent,interview-agent"
            ),
            model=resolved.profile_model if resolved.llm_configured else "heuristic-fallback",
            llm_configured=resolved.llm_configured,
            supported_extensions=sorted(SUPPORTED_EXTENSIONS),
        )

    return app


app = create_app()
