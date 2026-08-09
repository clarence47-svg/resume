from fastapi import APIRouter, Depends, HTTPException

from job_search.filtering import apply_hard_filters
from job_search.models import JobPosting
from job_search.normalization import normalize_job
from job_search.pipeline import JobDiscoveryPipeline
from job_search.scoring import evaluate_job
from resumes.pipeline import ResumePipeline
from schema.job_api import JobListResponse, JobsImportRequest, JobWithEvaluation
from schema.resume_api import ResumeCreateRequest, ResumeResponse
from service.dependencies import (
    get_career_repository,
    get_career_service,
    get_job_discovery_pipeline,
    get_repository,
    get_resume_pipeline,
    get_storage,
)
from storage.career_repositories import CareerRepository
from storage.files import FileStorage
from storage.repositories import ProfileRepository

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/import", response_model=JobListResponse)
def import_jobs(
    payload: JobsImportRequest,
    repository: CareerRepository = Depends(get_career_repository),
    profile_repository: ProfileRepository = Depends(get_repository),
    pipeline: JobDiscoveryPipeline = Depends(get_job_discovery_pipeline),
) -> JobListResponse:
    output = []
    grouped: dict[str, list] = {}
    for item in payload.jobs:
        grouped.setdefault(item.campaign_id, []).append(item)
    for campaign_id, items in grouped.items():
        campaign = repository.get_campaign(campaign_id)
        if campaign is None:
            raise HTTPException(status_code=404, detail=f"求职活动不存在：{campaign_id}")
        profile = profile_repository.get_result(campaign.profile_task_id)
        if profile is None:
            raise HTTPException(status_code=409, detail="画像结果不存在。")
        jobs = [
            JobPosting(
                **item.model_dump(exclude={"campaign_id"}),
                campaign_id=campaign.id,
                profile_task_id=campaign.profile_task_id,
            )
            for item in items
        ]
        output.extend(
            pipeline.import_jobs(
                jobs,
                profile,
                profile_repository.get_facts(campaign.profile_task_id),
            )
        )
    return JobListResponse(
        items=[JobWithEvaluation(job=job, evaluation=evaluation) for job, evaluation in output]
    )


@router.get("", response_model=JobListResponse)
def list_jobs(
    repository: CareerRepository = Depends(get_career_repository),
) -> JobListResponse:
    return JobListResponse(
        items=[
            JobWithEvaluation(job=job, evaluation=repository.get_evaluation(job.id))
            for job in repository.list_jobs()
        ]
    )


@router.post("/{job_id}/evaluate", response_model=JobWithEvaluation)
def reevaluate_job(
    job_id: str,
    repository: CareerRepository = Depends(get_career_repository),
    profile_repository: ProfileRepository = Depends(get_repository),
    career_service=Depends(get_career_service),
) -> JobWithEvaluation:
    job = repository.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="岗位不存在。")
    profile = profile_repository.get_result(job.profile_task_id)
    if profile is None:
        raise HTTPException(status_code=409, detail="画像结果不存在。")
    passed, reasons, needs_user = apply_hard_filters(job, career_service.get_settings())
    evaluation = evaluate_job(
        normalize_job(job),
        profile_repository.get_facts(job.profile_task_id),
        profile,
        career_service.get_settings(),
        hard_filter_passed=passed,
        hard_filter_reasons=reasons,
        needs_user=needs_user,
    )
    repository.save_evaluation(evaluation)
    return JobWithEvaluation(job=job, evaluation=evaluation)


@router.post("/{job_id}/resume", response_model=ResumeResponse)
def create_resume(
    job_id: str,
    payload: ResumeCreateRequest,
    pipeline: ResumePipeline = Depends(get_resume_pipeline),
) -> ResumeResponse:
    try:
        resume = pipeline.build(
            job_id,
            payload.match_id,
            payload.template,
            payload.match_version,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="岗位或匹配任务不存在。") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ResumeResponse(resume=resume)


@router.delete("/{job_id}")
def delete_job(
    job_id: str,
    repository: CareerRepository = Depends(get_career_repository),
    storage: FileStorage = Depends(get_storage),
) -> dict[str, str]:
    if not repository.delete_job(job_id):
        raise HTTPException(status_code=404, detail="岗位不存在。")
    storage.delete_job_files(job_id)
    return {"status": "deleted"}
