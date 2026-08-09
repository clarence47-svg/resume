from difflib import SequenceMatcher

from job_search.models import JobPosting


def semantic_duplicate(left: JobPosting, right: JobPosting, threshold: float = 0.92) -> bool:
    if left.canonical_url and left.canonical_url == right.canonical_url:
        return True
    if (
        left.external_id
        and left.platform == right.platform
        and left.external_id == right.external_id
    ):
        return True
    if left.content_hash and left.content_hash == right.content_hash:
        return True
    identity = (
        left.company.casefold() == right.company.casefold()
        and left.location.casefold() == right.location.casefold()
    )
    if not identity:
        return False
    title_ratio = SequenceMatcher(None, left.title.casefold(), right.title.casefold()).ratio()
    jd_ratio = SequenceMatcher(None, left.jd_text.casefold(), right.jd_text.casefold()).ratio()
    return title_ratio >= 0.8 and jd_ratio >= threshold


def deduplicate_jobs(jobs: list[JobPosting]) -> tuple[list[JobPosting], list[str]]:
    unique: list[JobPosting] = []
    duplicate_ids: list[str] = []
    for job in jobs:
        if any(semantic_duplicate(job, existing) for existing in unique):
            duplicate_ids.append(job.id)
        else:
            unique.append(job)
    return unique, duplicate_ids
