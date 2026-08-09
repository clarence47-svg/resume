from career.models import CareerSettings
from career.rules import hard_filter_job
from job_search.models import JobPosting


def apply_hard_filters(
    job: JobPosting,
    settings: CareerSettings,
) -> tuple[bool, list[str], bool]:
    return hard_filter_job(job.model_dump(mode="python"), settings)
