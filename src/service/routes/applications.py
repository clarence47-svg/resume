from fastapi import APIRouter, Depends, HTTPException, status

from applications.browser.runtime import BrowserRuntime
from applications.models import ApplicationStatus
from applications.pipeline import ApplicationPipeline
from jobs.application_runner import ApplicationAction, ApplicationRunner
from schema.application_api import (
    ApplicationConfirmRequest,
    ApplicationCreateRequest,
    ApplicationDeleteResponse,
    ApplicationPreviewResponse,
    ApplicationResponse,
    BrowserStatusResponse,
)
from service.dependencies import (
    get_application_pipeline,
    get_application_runner,
    get_career_repository,
    get_storage,
)
from storage.career_repositories import CareerRepository
from storage.files import FileStorage

router = APIRouter(prefix="/applications", tags=["applications"])


@router.get("/browser/status", response_model=BrowserStatusResponse)
async def browser_status(
    pipeline: ApplicationPipeline = Depends(get_application_pipeline),
) -> BrowserStatusResponse:
    return BrowserStatusResponse(browser=await pipeline.runtime.inspect())


@router.post("/browser/open-boss", response_model=BrowserStatusResponse)
async def open_boss(
    pipeline: ApplicationPipeline = Depends(get_application_pipeline),
) -> BrowserStatusResponse:
    if not pipeline.settings.browser_automation_enabled:
        raise HTTPException(status_code=409, detail="浏览器自动化尚未启用。")
    runtime = BrowserRuntime(pipeline.settings)
    result = await runtime.inspect(open_boss=True)
    if not result.connected:
        raise HTTPException(status_code=409, detail=result.message)
    return BrowserStatusResponse(browser=result)


@router.post("", response_model=ApplicationResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_application(
    payload: ApplicationCreateRequest,
    pipeline: ApplicationPipeline = Depends(get_application_pipeline),
    runner: ApplicationRunner = Depends(get_application_runner),
) -> ApplicationResponse:
    try:
        application = pipeline.create(payload.job_id, payload.resume_version_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="岗位或简历版本不存在。") from exc
    await runner.enqueue(application.id, ApplicationAction.PREPARE)
    return ApplicationResponse(application=application)


@router.get("", response_model=list[ApplicationResponse])
def list_applications(
    repository: CareerRepository = Depends(get_career_repository),
    pipeline: ApplicationPipeline = Depends(get_application_pipeline),
) -> list[ApplicationResponse]:
    output = []
    for application in repository.list_applications():
        application.preview = pipeline.get_preview(application.id)
        output.append(ApplicationResponse(application=application))
    return output


@router.get("/{application_id}", response_model=ApplicationResponse)
def get_application(
    application_id: str,
    repository: CareerRepository = Depends(get_career_repository),
    pipeline: ApplicationPipeline = Depends(get_application_pipeline),
) -> ApplicationResponse:
    application = repository.get_application(application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="投递任务不存在。")
    application.preview = pipeline.get_preview(application_id)
    return ApplicationResponse(application=application)


@router.get("/{application_id}/preview", response_model=ApplicationPreviewResponse)
def get_application_preview(
    application_id: str,
    pipeline: ApplicationPipeline = Depends(get_application_pipeline),
) -> ApplicationPreviewResponse:
    preview = pipeline.get_preview(application_id)
    if preview is None:
        raise HTTPException(status_code=409, detail="投递预览尚未生成。")
    return ApplicationPreviewResponse(application_id=application_id, preview=preview)


@router.post("/{application_id}/confirm", status_code=status.HTTP_202_ACCEPTED)
async def confirm_application(
    application_id: str,
    payload: ApplicationConfirmRequest,
    repository: CareerRepository = Depends(get_career_repository),
    runner: ApplicationRunner = Depends(get_application_runner),
) -> dict[str, str]:
    row = repository.get_application_row(application_id)
    if row is None:
        raise HTTPException(status_code=404, detail="投递任务不存在。")
    if row.status != ApplicationStatus.AWAITING_CONFIRMATION.value:
        raise HTTPException(status_code=409, detail="投递任务当前不在等待确认状态。")
    if row.preview_hash != payload.preview_hash:
        raise HTTPException(status_code=409, detail="预览已变化，请重新确认。")
    await runner.enqueue(application_id, ApplicationAction.CONFIRM, payload.preview_hash)
    return {"status": "submitting"}


@router.post("/{application_id}/resume", status_code=status.HTTP_202_ACCEPTED)
async def resume_application(
    application_id: str,
    repository: CareerRepository = Depends(get_career_repository),
    runner: ApplicationRunner = Depends(get_application_runner),
) -> dict[str, str]:
    if repository.get_application_row(application_id) is None:
        raise HTTPException(status_code=404, detail="投递任务不存在。")
    await runner.enqueue(application_id, ApplicationAction.PREPARE)
    return {"status": "queued"}


@router.post("/{application_id}/cancel")
async def cancel_application(
    application_id: str,
    repository: CareerRepository = Depends(get_career_repository),
    runner: ApplicationRunner = Depends(get_application_runner),
) -> dict[str, str]:
    if repository.get_application_row(application_id) is None:
        raise HTTPException(status_code=404, detail="投递任务不存在。")
    await runner.cancel(application_id)
    return {"status": "cancelled"}


@router.delete("/{application_id}", response_model=ApplicationDeleteResponse)
async def delete_application(
    application_id: str,
    repository: CareerRepository = Depends(get_career_repository),
    runner: ApplicationRunner = Depends(get_application_runner),
    storage: FileStorage = Depends(get_storage),
) -> ApplicationDeleteResponse:
    if repository.get_application_row(application_id) is None:
        raise HTTPException(status_code=404, detail="投递任务不存在。")
    await runner.cancel(application_id)
    repository.delete_application(application_id)
    storage.delete_application_files(application_id)
    return ApplicationDeleteResponse()
