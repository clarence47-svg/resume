from career.models import CareerSettings
from job_search.filtering import apply_hard_filters
from job_search.models import JobPosting


def hard_filter(state: dict) -> dict:
    settings = CareerSettings.model_validate(state.get("career_settings", {}))
    output = []
    for payload in state.get("normalized_jobs", []):
        job = JobPosting.model_validate(payload)
        passed, reasons, needs_user = apply_hard_filters(job, settings)
        output.append(
            {
                "job": job.model_dump(mode="json"),
                "passed": passed,
                "reasons": reasons,
                "needs_user": needs_user,
            }
        )
    return {"filtered_jobs": output}
