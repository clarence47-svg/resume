from datetime import UTC, datetime, timedelta

from tracking.models import FollowUpEvent


def default_follow_up(application_id: str, company: str, title: str) -> FollowUpEvent:
    return FollowUpEvent(
        application_id=application_id,
        event_type="application_follow_up",
        title=f"跟进 {company} · {title}",
        scheduled_at=datetime.now(UTC) + timedelta(days=7),
        notes="确认招聘方是否已查看申请。",
    )
