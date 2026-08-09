from applications.models import ApplicationStatus
from job_search.models import JobDecision, JobStatus
from storage.career_repositories import CareerRepository
from tracking.models import TrackingDashboard


def build_dashboard(repository: CareerRepository) -> TrackingDashboard:
    jobs = repository.list_jobs()
    applications = repository.list_applications()
    evaluations = {job.id: repository.get_evaluation(job.id) for job in jobs}
    return TrackingDashboard(
        total_jobs=len(jobs),
        recommended_jobs=sum(
            evaluation is not None and evaluation.decision == JobDecision.RECOMMENDED
            for evaluation in evaluations.values()
        ),
        awaiting_confirmation=sum(
            item.status == ApplicationStatus.AWAITING_CONFIRMATION for item in applications
        ),
        submitted=sum(item.status == ApplicationStatus.SUBMITTED for item in applications),
        interviews=sum(job.status == JobStatus.INTERVIEW for job in jobs),
        offers=sum(job.status == JobStatus.OFFER for job in jobs),
        rejected=sum(job.status == JobStatus.REJECTED for job in jobs),
        blocked=sum(
            item.status in {ApplicationStatus.BLOCKED, ApplicationStatus.NEEDS_USER}
            for item in applications
        ),
        recent_jobs=[
            {
                "id": job.id,
                "company": job.company,
                "title": job.title,
                "status": job.status.value,
                "score": evaluations[job.id].overall_score if evaluations[job.id] else None,
            }
            for job in jobs[:10]
        ],
        open_blockers=repository.list_blockers(open_only=True),
        upcoming_follow_ups=repository.list_follow_ups(upcoming_only=True),
    )
