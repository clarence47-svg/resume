from tracking.models import TrackingDashboard


def funnel_rates(dashboard: TrackingDashboard) -> dict[str, float]:
    denominator = max(dashboard.total_jobs, 1)
    return {
        "recommended_rate": round(dashboard.recommended_jobs / denominator, 3),
        "submitted_rate": round(dashboard.submitted / denominator, 3),
        "interview_rate": round(dashboard.interviews / denominator, 3),
        "offer_rate": round(dashboard.offers / denominator, 3),
    }
