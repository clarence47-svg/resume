from profile.models import FactCategory, ProfileFact, ProfileResult

from career.models import CareerSettings
from job_search.filtering import apply_hard_filters
from job_search.models import JobPosting
from job_search.normalization import canonicalize_url, normalize_job
from job_search.scoring import evaluate_job


def test_normalization_removes_tracking_and_hard_filters_outsource():
    assert canonicalize_url("https://example.com/job/1?utm_source=x&id=2") == (
        "https://example.com/job/1?id=2"
    )
    job = normalize_job(
        JobPosting(
            campaign_id="c1",
            profile_task_id="p1",
            company="示例公司",
            title="Python 外包开发",
            jd_text="负责 FastAPI 服务开发",
        )
    )
    passed, reasons, _ = apply_hard_filters(job, CareerSettings())
    assert not passed
    assert "岗位工作模式不符合规则" in reasons


def test_high_priority_keyword_coverage_improves_job_score():
    job = normalize_job(
        JobPosting(
            campaign_id="c1",
            profile_task_id="p1",
            company="示例公司",
            title="Python 开发",
            location="上海",
            jd_text="必须掌握 Python FastAPI SQL，熟悉 Docker 优先",
        )
    )
    facts = [
        ProfileFact(
            category=FactCategory.CAPABILITY,
            statement="熟练使用 Python、FastAPI、SQL 和 Docker。",
            confidence=0.95,
        )
    ]
    settings = CareerSettings(target_cities=["上海"])
    result = evaluate_job(job, facts, ProfileResult(task_id="p1"), settings)
    empty_result = evaluate_job(job, [], ProfileResult(task_id="p1"), settings)
    assert result.overall_score >= 50
    assert result.overall_score > empty_result.overall_score
    assert {"Python", "FastAPI", "SQL", "Docker"}.issubset(set(result.matched_keywords))
