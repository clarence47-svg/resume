from resumes.ats import audit_resume
from resumes.models import ResumeDocument


def ats_audit(state: dict) -> dict:
    document = ResumeDocument.model_validate(state["document"])
    audit = audit_resume(document, state.get("job", {}).get("jd_text", ""))
    document.audit = audit
    return {"document": document.model_dump(mode="json"), "audit": audit.model_dump(mode="json")}


def repair(state: dict) -> dict:
    return {"document": state["document"]}
