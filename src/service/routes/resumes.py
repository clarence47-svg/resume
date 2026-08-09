from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from schema.resume_api import ResumeResponse
from service.dependencies import get_career_repository
from storage.career_repositories import CareerRepository

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.get("", response_model=list[ResumeResponse])
def list_resumes(
    job_id: str | None = Query(default=None),
    repository: CareerRepository = Depends(get_career_repository),
) -> list[ResumeResponse]:
    return [ResumeResponse(resume=item) for item in repository.list_resumes(job_id)]


@router.get("/{resume_id}", response_model=ResumeResponse)
def get_resume(
    resume_id: str,
    repository: CareerRepository = Depends(get_career_repository),
) -> ResumeResponse:
    resume = repository.get_resume(resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail="简历版本不存在。")
    return ResumeResponse(resume=resume)


@router.get("/{resume_id}/export")
def export_resume(
    resume_id: str,
    format: str = Query(pattern="^(json|md|html|docx|pdf)$"),
    repository: CareerRepository = Depends(get_career_repository),
):
    resume = repository.get_resume(resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail="简历版本不存在。")
    if format == "json":
        return resume.model_dump(mode="json")
    path_value = {
        "md": resume.markdown_path,
        "html": resume.html_path,
        "docx": resume.docx_path,
        "pdf": resume.pdf_path,
    }[format]
    path = Path(path_value) if path_value else None
    if path is None or not path.exists():
        raise HTTPException(status_code=404, detail="导出文件不存在。")
    media = {
        "md": "text/markdown",
        "html": "text/html",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "pdf": "application/pdf",
    }[format]
    return FileResponse(path, media_type=media, filename=path.name)
