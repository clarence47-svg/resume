from job_search.deduplication import deduplicate_jobs
from job_search.models import JobPosting
from job_search.normalization import normalize_job


def normalize_and_dedupe(state: dict) -> dict:
    jobs = [
        normalize_job(JobPosting.model_validate(item)) for item in state.get("collected_jobs", [])
    ]
    unique, duplicates = deduplicate_jobs(jobs)
    return {
        "normalized_jobs": [item.model_dump(mode="json") for item in unique],
        "duplicate_ids": duplicates,
    }
