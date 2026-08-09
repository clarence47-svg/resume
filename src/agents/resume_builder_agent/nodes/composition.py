from career.models import CareerSettings
from job_search.models import JobPosting
from matching.models import JDMatchResult
from resumes.composition import compose_resume as build_document
from resumes.models import ResumeTemplate


def compose_resume(state: dict) -> dict:
    document = build_document(
        JDMatchResult.model_validate(state["match_result"]),
        JobPosting.model_validate(state["job"]),
        CareerSettings.model_validate(state.get("career_settings", {})),
        ResumeTemplate(state.get("template", ResumeTemplate.ATS_STANDARD.value)),
    )
    return {"document": document.model_dump(mode="json")}
