from profile.models import ProfileFact, ProfileResult

from career.service import CareerService
from job_search.deduplication import deduplicate_jobs
from job_search.filtering import apply_hard_filters
from job_search.models import JobPosting, JobStatus
from job_search.normalization import normalize_job
from job_search.scoring import evaluate_job
from storage.career_repositories import CareerRepository


class JobDiscoveryPipeline:
    def __init__(self, repository: CareerRepository, career_service: CareerService):
        self.repository = repository
        self.career_service = career_service

    def import_jobs(
        self,
        jobs: list[JobPosting],
        profile: ProfileResult,
        facts: list[ProfileFact],
    ) -> list[tuple[JobPosting, object]]:
        settings = self.career_service.get_settings()
        normalized = [normalize_job(job) for job in jobs]
        unique, _ = deduplicate_jobs(normalized)
        output = []
        for job in unique:
            duplicate = self.repository.find_duplicate_job(
                job.campaign_id, job.content_hash, job.canonical_url
            )
            if duplicate:
                output.append((duplicate, self.repository.get_evaluation(duplicate.id)))
                continue
            passed, reasons, needs_user = apply_hard_filters(job, settings)
            job.status = JobStatus.DISCOVERED if passed else JobStatus.FILTERED
            self.repository.save_job(job)
            evaluation = evaluate_job(
                job,
                facts,
                profile,
                settings,
                hard_filter_passed=passed,
                hard_filter_reasons=reasons,
                needs_user=needs_user,
            )
            self.repository.save_evaluation(evaluation)
            if passed:
                status = (
                    JobStatus.SHORTLISTED
                    if evaluation.decision.value == "recommended"
                    else JobStatus.EVALUATED
                )
                self.repository.update_job(job.id, status=status.value)
                job.status = status
            output.append((job, evaluation))
        return output
