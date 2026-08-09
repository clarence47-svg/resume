import json
from datetime import UTC, datetime
from pathlib import Path
from profile.models import ProfileFact
from profile.section_documents import write_profile_section_documents
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, Response

from agents.jd_match_agent.nodes.audit import audit_result
from jobs.match_runner import MatchJobAction, MatchJobRunner
from matching.exporters import export_match_docx, export_match_markdown
from matching.materials import match_result_materials
from matching.models import JDMatchResult, MatchVersionSource
from matching.section_documents import render_result_section_documents
from matching.validation import apply_draft_updates, validate_jd_text
from schema.match_api import (
    DraftUpdateRequest,
    MatchCreateRequest,
    MatchDeleteResponse,
    MatchResultResponse,
    MatchTaskCreated,
    MatchTaskDetail,
    MatchTaskStatus,
    MatchTaskSummary,
    MatchVersionSummary,
)
from schema.profile_api import TaskStatus
from service.dependencies import (
    get_match_job_runner,
    get_match_repository,
    get_repository,
    get_storage,
)
from storage.files import FileStorage
from storage.repositories import MatchRepository, ProfileRepository

router = APIRouter(prefix="/matches", tags=["matches"])
ACTIVE_STATUSES = {
    MatchTaskStatus.QUEUED.value,
    MatchTaskStatus.ANALYZING_JD.value,
    MatchTaskStatus.MATCHING.value,
    MatchTaskStatus.GENERATING.value,
    MatchTaskStatus.AUDITING.value,
}


@router.post("", response_model=MatchTaskCreated, status_code=status.HTTP_202_ACCEPTED)
async def create_match(
    payload: MatchCreateRequest,
    profile_repository: ProfileRepository = Depends(get_repository),
    repository: MatchRepository = Depends(get_match_repository),
    storage: FileStorage = Depends(get_storage),
    runner: MatchJobRunner = Depends(get_match_job_runner),
) -> MatchTaskCreated:
    profile_task = profile_repository.get_task(payload.profile_task_id)
    if profile_task is None:
        raise HTTPException(status_code=404, detail="画像任务不存在。")
    if profile_task.status not in {
        TaskStatus.COMPLETED.value,
        TaskStatus.PARTIAL_SUCCESS.value,
    }:
        raise HTTPException(status_code=409, detail="画像任务尚未完成。")
    profile_result = profile_repository.get_result(payload.profile_task_id)
    if profile_result is None:
        raise HTTPException(status_code=409, detail="画像结果不存在。")
    try:
        jd_text = validate_jd_text(payload.jd_text)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    match_id = str(uuid4())
    facts = profile_repository.get_facts(payload.profile_task_id)
    for previous_task in repository.list_tasks(payload.profile_task_id):
        if previous_task.result and previous_task.result.result_json:
            previous_result = JDMatchResult.model_validate(previous_task.result.result_json)
            facts.extend(match_result_materials(previous_result, facts))
    section_paths = write_profile_section_documents(
        profile_result,
        facts,
        storage.profile_sections_dir(payload.profile_task_id),
    )
    repository.create_task(
        match_id=match_id,
        profile_task_id=payload.profile_task_id,
        title=payload.title.strip() or f"{profile_task.title} · JD 匹配",
        jd_text=jd_text,
        profile_result=profile_result,
        profile_sections={
            section_name: path.read_text(encoding="utf-8")
            for section_name, path in section_paths.items()
        },
        facts=facts,
        conflicts=profile_repository.get_conflicts(payload.profile_task_id),
    )
    await runner.enqueue(match_id, MatchJobAction.FULL)
    return MatchTaskCreated(match_id=match_id, status=MatchTaskStatus.QUEUED)


@router.get("", response_model=list[MatchTaskSummary])
def list_matches(
    profile_task_id: str | None = Query(default=None),
    repository: MatchRepository = Depends(get_match_repository),
) -> list[MatchTaskSummary]:
    return [_summary(task) for task in repository.list_tasks(profile_task_id)]


@router.get("/{match_id}", response_model=MatchTaskDetail)
def get_match(
    match_id: str, repository: MatchRepository = Depends(get_match_repository)
) -> MatchTaskDetail:
    task = _require_task(repository, match_id)
    role_title = task.jd_analysis.get("role_title") if task.jd_analysis else None
    return MatchTaskDetail(
        **_summary(task).model_dump(), jd_text=task.jd_text, role_title=role_title
    )


@router.get("/{match_id}/result", response_model=MatchResultResponse)
def get_match_result(
    match_id: str,
    version: int | None = Query(default=None, ge=1),
    repository: MatchRepository = Depends(get_match_repository),
) -> MatchResultResponse:
    task = _require_task(repository, match_id)
    result = _get_result_version(repository, match_id, version)
    if result is None:
        raise HTTPException(status_code=409, detail="匹配结果尚未生成。")
    return MatchResultResponse(result=_with_section_documents(result, task))


@router.get("/{match_id}/versions", response_model=list[MatchVersionSummary])
def list_match_versions(
    match_id: str, repository: MatchRepository = Depends(get_match_repository)
) -> list[MatchVersionSummary]:
    _require_task(repository, match_id)
    return [
        MatchVersionSummary(version=row.version, source=row.source, created_at=row.created_at)
        for row in repository.list_versions(match_id)
    ]


@router.put("/{match_id}/draft", response_model=MatchResultResponse)
def update_match_draft(
    match_id: str,
    payload: DraftUpdateRequest,
    repository: MatchRepository = Depends(get_match_repository),
    storage: FileStorage = Depends(get_storage),
) -> MatchResultResponse:
    task = _require_task(repository, match_id)
    current = repository.get_result(match_id)
    if current is None:
        raise HTTPException(status_code=409, detail="匹配结果尚未生成。")
    current = _with_section_documents(current, task)
    if current.version != payload.expected_version:
        raise HTTPException(status_code=409, detail="结果版本已变化，请刷新后再编辑。")
    updated, violations = apply_draft_updates(
        current,
        payload.updates,
        facts=[ProfileFact.model_validate(item) for item in task.facts_snapshot],
        analysis=current.jd_analysis,
    )
    if violations:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "编辑内容未通过真实性校验。",
                "violations": [item.model_dump() for item in violations],
            },
        )
    updated.version = repository.next_version(match_id)
    updated.generated_at = datetime.now(UTC)
    audited = audit_result(
        {
            "result": updated.model_dump(mode="json"),
            "facts": task.facts_snapshot,
            "jd_analysis": updated.jd_analysis.model_dump(mode="json"),
            "warnings": [],
        }
    )
    updated = JDMatchResult.model_validate(audited["result"])
    if not updated.audit.passed:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "编辑内容未通过真实性审计。",
                "violations": updated.audit.unsupported_claims,
            },
        )
    markdown_path, docx_path = storage.match_export_paths(match_id, updated.version)
    export_match_markdown(updated, markdown_path)
    export_match_docx(updated, docx_path)
    repository.save_version(
        match_id,
        updated,
        MatchVersionSource.USER_EDIT,
        str(markdown_path),
        str(docx_path),
    )
    return MatchResultResponse(result=updated)


@router.post(
    "/{match_id}/versions/{version}/restore",
    response_model=MatchResultResponse,
)
def restore_match_version(
    match_id: str,
    version: int,
    repository: MatchRepository = Depends(get_match_repository),
    storage: FileStorage = Depends(get_storage),
) -> MatchResultResponse:
    task = _require_task(repository, match_id)
    source = repository.get_version(match_id, version)
    if source is None:
        raise HTTPException(status_code=404, detail="匹配版本不存在。")
    source = _with_section_documents(source, task)
    restored = source.model_copy(deep=True)
    restored.version = repository.next_version(match_id)
    restored.generated_at = datetime.now(UTC)
    markdown_path, docx_path = storage.match_export_paths(match_id, restored.version)
    export_match_markdown(restored, markdown_path)
    export_match_docx(restored, docx_path)
    repository.save_version(
        match_id,
        restored,
        MatchVersionSource.RESTORED,
        str(markdown_path),
        str(docx_path),
    )
    return MatchResultResponse(result=restored)


@router.post("/{match_id}/regenerate", response_model=MatchTaskCreated, status_code=202)
async def regenerate_match(
    match_id: str,
    repository: MatchRepository = Depends(get_match_repository),
    runner: MatchJobRunner = Depends(get_match_job_runner),
) -> MatchTaskCreated:
    task = _require_task(repository, match_id)
    if task.status in ACTIVE_STATUSES:
        raise HTTPException(status_code=409, detail="匹配任务正在处理中。")
    repository.update_task(
        match_id,
        status=MatchTaskStatus.QUEUED.value,
        stage="queued",
        progress=0,
        error=None,
    )
    await runner.enqueue(match_id, MatchJobAction.REGENERATE)
    return MatchTaskCreated(match_id=match_id, status=MatchTaskStatus.QUEUED)


@router.post("/{match_id}/retry", response_model=MatchTaskCreated, status_code=202)
async def retry_match(
    match_id: str,
    repository: MatchRepository = Depends(get_match_repository),
    runner: MatchJobRunner = Depends(get_match_job_runner),
) -> MatchTaskCreated:
    task = _require_task(repository, match_id)
    if task.status not in {
        MatchTaskStatus.FAILED.value,
        MatchTaskStatus.FAILED_RETRYABLE.value,
    }:
        raise HTTPException(status_code=409, detail="只有失败任务可以重试。")
    repository.increment_attempt(match_id)
    repository.update_task(
        match_id,
        status=MatchTaskStatus.QUEUED.value,
        stage="queued",
        progress=0,
        error=None,
    )
    await runner.enqueue(match_id, MatchJobAction.RETRY)
    return MatchTaskCreated(match_id=match_id, status=MatchTaskStatus.QUEUED)


@router.get("/{match_id}/export")
def export_match(
    match_id: str,
    format: str,
    version: int | None = Query(default=None, ge=1),
    repository: MatchRepository = Depends(get_match_repository),
):
    task = _require_task(repository, match_id)
    result = _get_result_version(repository, match_id, version)
    if result is None:
        raise HTTPException(status_code=404, detail="匹配结果不存在。")
    result = _with_section_documents(result, task)
    if format == "json":
        return Response(
            content=json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2),
            media_type="application/json",
        )
    markdown_path, docx_path = repository.get_result_paths(match_id, version)
    if format == "md" and markdown_path and Path(markdown_path).exists():
        return FileResponse(markdown_path, media_type="text/markdown", filename="jd-match.md")
    if format == "docx" and docx_path and Path(docx_path).exists():
        return FileResponse(
            docx_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename="jd-match.docx",
        )
    raise HTTPException(status_code=404, detail="导出文件不存在或格式不支持。")


@router.delete("/{match_id}", response_model=MatchDeleteResponse)
async def delete_match(
    match_id: str,
    repository: MatchRepository = Depends(get_match_repository),
    storage: FileStorage = Depends(get_storage),
    runner: MatchJobRunner = Depends(get_match_job_runner),
) -> MatchDeleteResponse:
    _require_task(repository, match_id)
    await runner.cancel(match_id)
    storage.delete_match_files(match_id)
    repository.delete_task(match_id)
    return MatchDeleteResponse()


def _require_task(repository: MatchRepository, match_id: str):
    task = repository.get_task(match_id)
    if task is None:
        raise HTTPException(status_code=404, detail="匹配任务不存在。")
    return task


def _get_result_version(
    repository: MatchRepository, match_id: str, version: int | None
) -> JDMatchResult | None:
    return repository.get_version(match_id, version) if version else repository.get_result(match_id)


def _with_section_documents(result: JDMatchResult, task) -> JDMatchResult:
    if result.section_documents:
        return result
    result.section_documents = render_result_section_documents(
        result,
        [ProfileFact.model_validate(item) for item in task.facts_snapshot],
    )
    return result


def _summary(task) -> MatchTaskSummary:
    return MatchTaskSummary(
        id=task.id,
        profile_task_id=task.profile_task_id,
        job_id=task.job_id,
        batch_id=task.batch_id,
        title=task.title,
        status=task.status,
        stage=task.stage,
        progress=task.progress,
        current_version=task.result.current_version if task.result else None,
        created_at=task.created_at,
        updated_at=task.updated_at,
        error=task.error,
    )
