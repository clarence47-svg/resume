from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from interview.pipeline import InterviewPipeline
from schema.tracking_api import InterviewCreateRequest, InterviewKitResponse
from service.dependencies import get_career_repository, get_interview_pipeline
from storage.career_repositories import CareerRepository

router = APIRouter(prefix="/interviews", tags=["interviews"])


@router.post("", response_model=InterviewKitResponse)
def create_interview_kit(
    payload: InterviewCreateRequest,
    pipeline: InterviewPipeline = Depends(get_interview_pipeline),
) -> InterviewKitResponse:
    try:
        return InterviewKitResponse(
            kit=pipeline.generate(payload.job_id, payload.resume_version_id)
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="岗位或简历版本不存在。") from exc


@router.get("/{kit_id}", response_model=InterviewKitResponse)
def get_interview_kit(
    kit_id: str,
    repository: CareerRepository = Depends(get_career_repository),
) -> InterviewKitResponse:
    result = repository.get_interview_kit(kit_id)
    if result is None:
        raise HTTPException(status_code=404, detail="面试准备包不存在。")
    return InterviewKitResponse(kit=result[0])


@router.get("/{kit_id}/export")
def export_interview_kit(
    kit_id: str,
    repository: CareerRepository = Depends(get_career_repository),
):
    result = repository.get_interview_kit(kit_id)
    if result is None:
        raise HTTPException(status_code=404, detail="面试准备包不存在。")
    return FileResponse(result[1], media_type="text/markdown", filename="interview-kit.md")
