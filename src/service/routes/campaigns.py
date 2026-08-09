from fastapi import APIRouter, Depends, HTTPException, Query, status

from applications.browser.runtime import BrowserRuntime
from campaigns.batch_tailoring import BatchTailoringService
from campaigns.models import JobCampaign
from job_search.models import JobPosting
from job_search.pipeline import JobDiscoveryPipeline
from job_search.sources.boss import BossJobSource
from job_search.sources.official_search import OfficialSearchSource
from schema.campaign_api import (
    CampaignCreateRequest,
    CampaignDiscoverRequest,
    CampaignJobsResponse,
    CampaignResponse,
    TailoringBatchCreateRequest,
    TailoringBatchResponse,
    TailoringBatchResumeRequest,
)
from schema.profile_api import TaskStatus
from service.dependencies import (
    get_batch_tailoring_service,
    get_career_repository,
    get_job_discovery_pipeline,
    get_repository,
    get_storage,
)
from storage.career_repositories import CareerRepository
from storage.files import FileStorage
from storage.repositories import ProfileRepository

router = APIRouter(tags=["campaigns"])


@router.post("/campaigns", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
def create_campaign(
    payload: CampaignCreateRequest,
    repository: CareerRepository = Depends(get_career_repository),
    profile_repository: ProfileRepository = Depends(get_repository),
) -> CampaignResponse:
    profile = profile_repository.get_task(payload.profile_task_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="画像任务不存在。")
    if profile.status not in {TaskStatus.COMPLETED.value, TaskStatus.PARTIAL_SUCCESS.value}:
        raise HTTPException(status_code=409, detail="画像任务尚未完成。")
    campaign = JobCampaign(**payload.model_dump())
    repository.save_campaign(campaign)
    return CampaignResponse(campaign=campaign)


@router.get("/campaigns", response_model=list[JobCampaign])
def list_campaigns(
    profile_task_id: str | None = Query(default=None),
    repository: CareerRepository = Depends(get_career_repository),
) -> list[JobCampaign]:
    return repository.list_campaigns(profile_task_id)


@router.get("/campaigns/{campaign_id}", response_model=CampaignResponse)
def get_campaign(
    campaign_id: str,
    repository: CareerRepository = Depends(get_career_repository),
) -> CampaignResponse:
    campaign = repository.get_campaign(campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="求职活动不存在。")
    return CampaignResponse(campaign=campaign)


@router.post("/campaigns/{campaign_id}/discover", response_model=CampaignJobsResponse)
async def discover_jobs(
    campaign_id: str,
    payload: CampaignDiscoverRequest,
    repository: CareerRepository = Depends(get_career_repository),
    profile_repository: ProfileRepository = Depends(get_repository),
    pipeline: JobDiscoveryPipeline = Depends(get_job_discovery_pipeline),
) -> CampaignJobsResponse:
    campaign = repository.get_campaign(campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="求职活动不存在。")
    profile = profile_repository.get_result(campaign.profile_task_id)
    if profile is None:
        raise HTTPException(status_code=409, detail="画像结果不存在。")
    jobs = [
        JobPosting.model_validate(
            {
                **item,
                "campaign_id": campaign.id,
                "profile_task_id": campaign.profile_task_id,
            }
        )
        for item in payload.manual_jobs
    ]
    if payload.include_official_search:
        source = OfficialSearchSource(pipeline.career_service.encryptor.settings)
        jobs.extend(await source.collect(campaign))
    if payload.include_boss:
        if not pipeline.career_service.encryptor.settings.browser_automation_enabled:
            raise HTTPException(
                status_code=409,
                detail="BOSS 岗位采集需要启用浏览器自动化并连接已登录 Chrome。",
            )
        runtime = BrowserRuntime(pipeline.career_service.encryptor.settings)
        try:
            jobs.extend(await BossJobSource(runtime).collect(campaign))
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    results = pipeline.import_jobs(
        jobs,
        profile,
        profile_repository.get_facts(campaign.profile_task_id),
    )
    return CampaignJobsResponse(
        jobs=[
            {
                "job": job.model_dump(mode="json"),
                "evaluation": evaluation.model_dump(mode="json") if evaluation else None,
            }
            for job, evaluation in results
        ]
    )


@router.get("/campaigns/{campaign_id}/jobs", response_model=CampaignJobsResponse)
def campaign_jobs(
    campaign_id: str,
    repository: CareerRepository = Depends(get_career_repository),
) -> CampaignJobsResponse:
    if repository.get_campaign(campaign_id) is None:
        raise HTTPException(status_code=404, detail="求职活动不存在。")
    return CampaignJobsResponse(
        jobs=[
            {
                "job": job.model_dump(mode="json"),
                "evaluation": (
                    repository.get_evaluation(job.id).model_dump(mode="json")
                    if repository.get_evaluation(job.id)
                    else None
                ),
            }
            for job in repository.list_jobs(campaign_id)
        ]
    )


@router.delete("/campaigns/{campaign_id}")
def delete_campaign(
    campaign_id: str,
    repository: CareerRepository = Depends(get_career_repository),
    storage: FileStorage = Depends(get_storage),
) -> dict[str, str]:
    if not repository.delete_campaign(campaign_id):
        raise HTTPException(status_code=404, detail="求职活动不存在。")
    storage.delete_campaign_files(campaign_id)
    return {"status": "deleted"}


@router.post(
    "/tailoring-batches",
    response_model=TailoringBatchResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_tailoring_batch(
    payload: TailoringBatchCreateRequest,
    service: BatchTailoringService = Depends(get_batch_tailoring_service),
) -> TailoringBatchResponse:
    try:
        batch = await service.create(payload.campaign_id, payload.job_ids, payload.title)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"关联数据不存在：{exc}") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return TailoringBatchResponse(batch=batch)


@router.get("/tailoring-batches/{batch_id}", response_model=TailoringBatchResponse)
def get_tailoring_batch(
    batch_id: str,
    service: BatchTailoringService = Depends(get_batch_tailoring_service),
) -> TailoringBatchResponse:
    try:
        return TailoringBatchResponse(batch=service.refresh(batch_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="批量定制任务不存在。") from exc


@router.post("/tailoring-batches/{batch_id}/resume", response_model=TailoringBatchResponse)
def resume_tailoring_batch(
    batch_id: str,
    payload: TailoringBatchResumeRequest,
    repository: CareerRepository = Depends(get_career_repository),
    service: BatchTailoringService = Depends(get_batch_tailoring_service),
) -> TailoringBatchResponse:
    batch = repository.get_batch(batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="批量定制任务不存在。")
    answered = set(payload.answers)
    gaps = [item for item in batch.aggregate_gaps if item.key not in answered]
    repository.update_batch(
        batch_id,
        aggregate_gaps=[item.model_dump(mode="json") for item in gaps],
        stage="matching",
    )
    return TailoringBatchResponse(batch=service.refresh(batch_id))
