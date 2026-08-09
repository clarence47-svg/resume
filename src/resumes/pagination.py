from resumes.ats import estimate_pages
from resumes.models import ResumeDocument


def plan_pages(document: ResumeDocument) -> ResumeDocument:
    estimated = estimate_pages(document)
    document.target_pages = 1 if estimated <= 1 else 2
    return document
