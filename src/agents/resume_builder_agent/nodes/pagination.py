from resumes.models import ResumeDocument
from resumes.pagination import plan_pages as plan


def plan_pages(state: dict) -> dict:
    document = plan(ResumeDocument.model_validate(state["document"]))
    return {"document": document.model_dump(mode="json")}
