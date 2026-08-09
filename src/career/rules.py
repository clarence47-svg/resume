from datetime import UTC, datetime

from career.models import CareerSettings


def hard_filter_job(job: dict, settings: CareerSettings) -> tuple[bool, list[str], bool]:
    text = " ".join(
        str(job.get(key) or "")
        for key in ("company", "title", "location", "salary_text", "jd_text")
    ).casefold()
    reasons: list[str] = []
    needs_user = False
    rules = settings.rules
    if any(value.casefold() in text for value in rules.excluded_keywords if value.strip()):
        reasons.append("命中岗位排除关键词")
    if any(value.casefold() in text for value in rules.excluded_companies if value.strip()):
        reasons.append("命中排除公司")
    if not rules.allow_outsource and any(
        value.casefold() in text for value in rules.excluded_work_patterns if value.strip()
    ):
        reasons.append("岗位工作模式不符合规则")
    if not rules.allow_internship and any(token in text for token in ("实习", "internship")):
        reasons.append("当前规则不接受实习岗位")
    salary_max = job.get("salary_max_k")
    if settings.salary_min_k is not None and salary_max is not None:
        if float(salary_max) < settings.salary_min_k:
            reasons.append("岗位薪资上限低于期望下限")
    published_at = job.get("published_at")
    if published_at:
        if isinstance(published_at, str):
            try:
                published_at = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            except ValueError:
                published_at = None
        if published_at and published_at.tzinfo is None:
            published_at = published_at.replace(tzinfo=UTC)
        if (
            published_at
            and (datetime.now(UTC) - published_at).days > rules.require_fresh_posting_days
        ):
            reasons.append("岗位发布时间超过新鲜度限制")
    if "需要工作许可" in text and not settings.work_authorization:
        needs_user = True
    return not reasons, reasons, needs_user
