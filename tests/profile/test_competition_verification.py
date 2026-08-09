from profile.competition_verification import _source_score

from matching.models import JobResearchSource


def test_competition_search_uses_fuzzy_name_matching() -> None:
    source = JobResearchSource(
        title="亚太杯大学生数学建模竞赛官方网站",
        url="https://example.com/apmcm",
        snippet="亚太杯数学建模竞赛报名、赛题与获奖名单。",
    )
    score = _source_score(source, "亚太杯数学建模竞赛 省级三等奖")
    assert score >= 0.58


def test_non_competition_award_source_is_not_verified() -> None:
    source = JobResearchSource(
        title="广州大学一等奖学金名单",
        url="https://example.com/scholarship",
        snippet="学校发布年度奖学金名单。",
    )
    assert _source_score(source, "广州大学一等奖学金") == 0
