from pathlib import Path
from profile.models import ConflictRecord
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from ingestion.validation import FileValidationError, validate_file
from jobs.runner import JobAction, JobRunner
from schema.profile_api import (
    DeleteResponse,
    DocumentStatus,
    DocumentSummary,
    FactsResponse,
    FactsUpdateRequest,
    ResultResponse,
    ReviewMode,
    TaskCreated,
    TaskDetail,
    TaskStatus,
    TaskSummary,
)
from service.dependencies import (
    get_job_runner,
    get_match_repository,
    get_repository,
    get_storage,
)
from storage.files import FileStorage
from storage.repositories import MatchRepository, ProfileRepository

router = APIRouter(prefix="/profiles", tags=["profiles"])
ACTIVE_STATUSES = {
    TaskStatus.QUEUED.value,
    TaskStatus.PARSING.value,
    TaskStatus.EXTRACTING.value,
    TaskStatus.GENERATING.value,
    TaskStatus.AUDITING.value,
}


@router.post("", response_model=TaskCreated, status_code=status.HTTP_202_ACCEPTED)
async def create_profile(
    files: list[UploadFile] = File(...),
    review_mode: ReviewMode = Form(ReviewMode.AUTO),
    title: str = Form(""),
    repository: ProfileRepository = Depends(get_repository),
    storage: FileStorage = Depends(get_storage),
    runner: JobRunner = Depends(get_job_runner),
) -> TaskCreated:
    settings = storage.settings
    if not files:
        raise HTTPException(status_code=400, detail="至少上传一个文件。")
    if len(files) > settings.max_files:
        raise HTTPException(status_code=400, detail=f"一次最多上传 {settings.max_files} 个文件。")
    task_id = str(uuid4())
    task_title = title.strip() or f"画像任务 {task_id[:8]}"
    repository.create_task(task_id, task_title, review_mode)
    valid_count = 0
    total_size = 0
    errors: list[str] = []

    for upload in files:
        original_name = upload.filename or "document"
        extension = Path(original_name).suffix.lower()
        try:
            document_id, path, size_bytes, digest = await storage.save_upload(task_id, upload)
            total_size += size_bytes
            if total_size > settings.max_total_size_mb * 1024 * 1024:
                path.unlink(missing_ok=True)
                raise FileValidationError(f"上传总大小超过 {settings.max_total_size_mb} MB 限制。")
            media_type = validate_file(path, original_name, settings)
            repository.add_document(
                document_id=document_id,
                task_id=task_id,
                original_name=original_name,
                extension=extension,
                size_bytes=size_bytes,
                stored_path=str(path),
                media_type=media_type or upload.content_type,
                sha256=digest,
            )
            valid_count += 1
        except Exception as exc:
            errors.append(f"{original_name}: {exc}")
            repository.add_document(
                document_id=str(uuid4()),
                task_id=task_id,
                original_name=original_name,
                extension=extension,
                size_bytes=0,
                stored_path=None,
                media_type=upload.content_type,
                sha256=None,
                status=DocumentStatus.FAILED,
                error=str(exc),
            )

    if valid_count == 0:
        repository.update_task(
            task_id,
            status=TaskStatus.FAILED.value,
            stage="upload_failed",
            error="; ".join(errors),
        )
        raise HTTPException(status_code=400, detail={"task_id": task_id, "errors": errors})
    if errors:
        repository.update_task(task_id, error="; ".join(errors))
    await runner.enqueue(task_id, JobAction.FULL)
    return TaskCreated(task_id=task_id, status=TaskStatus.QUEUED)


@router.get("", response_model=list[TaskSummary])
def list_profiles(
    repository: ProfileRepository = Depends(get_repository),
) -> list[TaskSummary]:
    return [_task_summary(task) for task in repository.list_tasks()]


@router.get("/{task_id}", response_model=TaskDetail)
def get_profile_task(
    task_id: str, repository: ProfileRepository = Depends(get_repository)
) -> TaskDetail:
    task = _require_task(repository, task_id)
    return TaskDetail(
        **_task_summary(task).model_dump(),
        documents=[
            DocumentSummary(
                id=document.id,
                original_name=document.original_name,
                extension=document.extension,
                size_bytes=document.size_bytes,
                status=document.status,
                error=document.error,
            )
            for document in task.documents
        ],
        conflicts=[ConflictRecord.model_validate(item) for item in task.conflicts],
    )


@router.get("/{task_id}/facts", response_model=FactsResponse)
def get_facts(
    task_id: str, repository: ProfileRepository = Depends(get_repository)
) -> FactsResponse:
    _require_task(repository, task_id)
    return FactsResponse(
        task_id=task_id,
        facts=repository.get_facts(task_id),
        conflicts=repository.get_conflicts(task_id),
    )


@router.put("/{task_id}/facts", response_model=FactsResponse)
def update_facts(
    task_id: str,
    payload: FactsUpdateRequest,
    repository: ProfileRepository = Depends(get_repository),
) -> FactsResponse:
    _require_task(repository, task_id)
    repository.replace_facts(task_id, payload.facts)
    return FactsResponse(
        task_id=task_id,
        facts=repository.get_facts(task_id),
        conflicts=repository.get_conflicts(task_id),
    )


@router.post("/{task_id}/resume", response_model=TaskCreated, status_code=202)
async def resume_profile(
    task_id: str,
    repository: ProfileRepository = Depends(get_repository),
    runner: JobRunner = Depends(get_job_runner),
) -> TaskCreated:
    task = _require_task(repository, task_id)
    if task.status != TaskStatus.AWAITING_REVIEW.value:
        raise HTTPException(status_code=409, detail="任务当前不在等待核对状态。")
    await runner.enqueue(task_id, JobAction.RESUME)
    return TaskCreated(task_id=task_id, status=TaskStatus.GENERATING)


@router.post("/{task_id}/regenerate", response_model=TaskCreated, status_code=202)
async def regenerate_profile(
    task_id: str,
    repository: ProfileRepository = Depends(get_repository),
    runner: JobRunner = Depends(get_job_runner),
) -> TaskCreated:
    task = _require_task(repository, task_id)
    if task.status in ACTIVE_STATUSES:
        raise HTTPException(status_code=409, detail="任务正在处理中。")
    if not repository.get_facts(task_id):
        raise HTTPException(status_code=409, detail="没有可用于重新生成的事实。")
    await runner.enqueue(task_id, JobAction.REGENERATE)
    return TaskCreated(task_id=task_id, status=TaskStatus.GENERATING)


@router.post("/{task_id}/retry", response_model=TaskCreated, status_code=202)
async def retry_profile(
    task_id: str,
    repository: ProfileRepository = Depends(get_repository),
    runner: JobRunner = Depends(get_job_runner),
) -> TaskCreated:
    task = _require_task(repository, task_id)
    if task.status not in {TaskStatus.FAILED.value, TaskStatus.FAILED_RETRYABLE.value}:
        raise HTTPException(status_code=409, detail="只有失败任务可以重试。")
    repository.increment_attempt(task_id)
    repository.update_task(
        task_id,
        status=TaskStatus.QUEUED.value,
        stage="queued",
        progress=0,
        error=None,
    )
    await runner.enqueue(task_id, JobAction.FULL)
    return TaskCreated(task_id=task_id, status=TaskStatus.QUEUED)


@router.get("/{task_id}/result", response_model=ResultResponse)
def get_result(
    task_id: str, repository: ProfileRepository = Depends(get_repository)
) -> ResultResponse:
    _require_task(repository, task_id)
    result = repository.get_result(task_id)
    if result is None:
        raise HTTPException(status_code=409, detail="画像尚未生成。")
    return ResultResponse(result=result)


@router.get("/{task_id}/export")
def export_result(
    task_id: str,
    format: str,
    repository: ProfileRepository = Depends(get_repository),
):
    _require_task(repository, task_id)
    markdown_path, docx_path = repository.get_result_paths(task_id)
    if format == "md" and markdown_path:
        return FileResponse(markdown_path, media_type="text/markdown", filename="profile.md")
    if format == "docx" and docx_path:
        return FileResponse(
            docx_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename="profile.docx",
        )
    raise HTTPException(status_code=404, detail="导出文件不存在或格式不支持。")


@router.delete("/{task_id}", response_model=DeleteResponse)
def delete_profile(
    task_id: str,
    repository: ProfileRepository = Depends(get_repository),
    match_repository: MatchRepository = Depends(get_match_repository),
    storage: FileStorage = Depends(get_storage),
) -> DeleteResponse:
    task = _require_task(repository, task_id)
    if task.status in ACTIVE_STATUSES:
        raise HTTPException(status_code=409, detail="任务处理中，暂不能删除。")
    for match_id in match_repository.list_ids_for_profile(task_id):
        storage.delete_match_files(match_id)
    storage.delete_task_files(task_id)
    repository.delete_task(task_id)
    return DeleteResponse()


def _require_task(repository: ProfileRepository, task_id: str):
    task = repository.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在。")
    return task


def _task_summary(task) -> TaskSummary:
    return TaskSummary(
        id=task.id,
        title=task.title,
        status=task.status,
        stage=task.stage,
        progress=task.progress,
        review_mode=task.review_mode,
        created_at=task.created_at,
        updated_at=task.updated_at,
        error=task.error,
    )
