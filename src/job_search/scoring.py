import re
from collections import defaultdict
from profile.models import FactCategory, ProfileFact, ProfileResult

from career.models import CareerSettings
from job_search.models import (
    JobDecision,
    JobEvaluation,
    JobPosting,
    JobScoreDimension,
)

DIMENSION_WEIGHTS = {
    "skills": 0.3,
    "experience": 0.25,
    "industry": 0.1,
    "seniority": 0.1,
    "education": 0.1,
    "location": 0.1,
    "rules": 0.05,
}


def evaluate_job(
    job: JobPosting,
    facts: list[ProfileFact],
    profile: ProfileResult,
    settings: CareerSettings,
    *,
    hard_filter_passed: bool = True,
    hard_filter_reasons: list[str] | None = None,
    needs_user: bool = False,
) -> JobEvaluation:
    keywords = extract_job_keywords(job.jd_text)
    fact_text = " ".join(
        fact.statement for fact in facts if fact.status.value != "rejected"
    ).casefold()
    matched = [keyword for keyword in keywords if keyword.casefold() in fact_text]
    missing = [keyword for keyword in keywords if keyword not in matched]
    skill_score = 100 * len(matched) / max(len(keywords), 1)
    category_scores = _category_coverage(job.jd_text, facts)
    location_score = _location_score(job, settings)
    rule_score = 100 if hard_filter_passed else 0
    dimensions = {
        "skills": JobScoreDimension(
            score=round(skill_score, 1), rationale="画像事实与 JD 技能关键词覆盖率。"
        ),
        "experience": JobScoreDimension(
            score=round(
                max(
                    category_scores[FactCategory.PROJECT],
                    category_scores[FactCategory.INTERNSHIP],
                ),
                1,
            ),
            rationale="项目和实习事实对岗位职责的覆盖。",
        ),
        "industry": JobScoreDimension(
            score=round(_industry_score(job, settings), 1),
            rationale="岗位行业与用户偏好的一致程度。",
        ),
        "seniority": JobScoreDimension(
            score=round(_seniority_score(job, profile), 1),
            rationale="岗位经验级别与画像经历丰富度的匹配。",
        ),
        "education": JobScoreDimension(
            score=round(category_scores[FactCategory.EDUCATION], 1),
            rationale="学历、专业和课程要求的事实覆盖。",
        ),
        "location": JobScoreDimension(
            score=round(location_score, 1), rationale="岗位城市与目标城市设置。"
        ),
        "rules": JobScoreDimension(score=rule_score, rationale="求职硬规则通过情况。"),
    }
    overall = sum(dimensions[key].score * weight for key, weight in DIMENSION_WEIGHTS.items())
    if not hard_filter_passed:
        decision = JobDecision.NOT_RECOMMENDED
        overall = min(overall, 39)
    elif needs_user:
        decision = JobDecision.NEEDS_USER
    elif overall >= settings.rules.precision_score_threshold:
        decision = JobDecision.RECOMMENDED
    elif overall >= settings.rules.minimum_match_score:
        decision = JobDecision.REVIEW
    else:
        decision = JobDecision.NOT_RECOMMENDED
    strengths = [f"已覆盖关键词：{item}" for item in matched[:6]]
    gaps = [f"画像未直接支持：{item}" for item in missing[:6]]
    return JobEvaluation(
        job_id=job.id,
        overall_score=round(overall, 1),
        decision=decision,
        hard_filter_passed=hard_filter_passed,
        hard_filter_reasons=hard_filter_reasons or [],
        dimensions=dimensions,
        matched_keywords=matched,
        missing_keywords=missing,
        strengths=strengths,
        gaps=gaps,
    )


def extract_job_keywords(text: str) -> list[str]:
    ascii_tokens = re.findall(r"\b[A-Za-z][A-Za-z0-9+#.\-]{1,30}\b", text)
    known_cn = [
        "数据分析",
        "机器学习",
        "深度学习",
        "大模型",
        "项目管理",
        "产品设计",
        "用户研究",
        "需求分析",
        "沟通协作",
        "团队管理",
    ]
    found = [item for item in known_cn if item in text]
    stop = {"the", "and", "with", "for", "job", "work", "years", "experience"}
    output = [item for item in [*found, *ascii_tokens] if item.casefold() not in stop]
    return list(dict.fromkeys(output))[:30]


def _category_coverage(text: str, facts: list[ProfileFact]) -> dict[FactCategory, float]:
    tokens = extract_job_keywords(text)
    grouped: dict[FactCategory, list[ProfileFact]] = defaultdict(list)
    for fact in facts:
        if fact.status.value != "rejected":
            grouped[fact.category].append(fact)
    scores = {}
    for category in FactCategory:
        category_text = " ".join(item.statement for item in grouped[category]).casefold()
        coverage = sum(token.casefold() in category_text for token in tokens)
        confidence = (
            sum(item.confidence for item in grouped[category]) / len(grouped[category])
            if grouped[category]
            else 0
        )
        scores[category] = min(100.0, 100 * coverage / max(len(tokens), 1) + confidence * 25)
    return scores


def _location_score(job: JobPosting, settings: CareerSettings) -> float:
    targets = settings.target_cities or ([settings.city] if settings.city else [])
    if not targets:
        return 70
    return 100 if any(item.casefold() in job.location.casefold() for item in targets) else 25


def _industry_score(job: JobPosting, settings: CareerSettings) -> float:
    preferred = settings.rules.preferred_industries
    if not preferred:
        return 70
    text = f"{job.company} {job.jd_text}".casefold()
    return 100 if any(item.casefold() in text for item in preferred) else 35


def _seniority_score(job: JobPosting, profile: ProfileResult) -> float:
    experiences = (
        len(profile.project_experiences.entries)
        + len(profile.internship_experiences.entries)
        + len(profile.competition_experiences.entries)
    )
    years = [int(value) for value in re.findall(r"(\d+)\s*年", job.jd_text)]
    required_years = max(years, default=0)
    if required_years == 0:
        return 80 if experiences else 45
    approximate_years = min(experiences / 2, 10)
    return min(100, approximate_years / required_years * 100)
