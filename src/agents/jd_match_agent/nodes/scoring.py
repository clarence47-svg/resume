from profile.models import FactCategory, ProfileFact, ProfileResult

from matching.models import JDAnalysis, KeywordCoverage, RequirementMatch, SupportLevel
from matching.scoring import calculate_match_scores, fact_relevance_scores

EXPERIENCE_LIMITS = {
    FactCategory.PROJECT.value: 3,
    FactCategory.COMPETITION.value: 2,
    FactCategory.INTERNSHIP.value: 2,
}


def score_and_select(state: dict) -> dict:
    analysis = JDAnalysis.model_validate(state["jd_analysis"])
    matches = [RequirementMatch.model_validate(item) for item in state["requirement_matches"]]
    facts = [ProfileFact.model_validate(item) for item in state.get("facts", [])]
    profile = ProfileResult.model_validate(state["profile_result"])
    overall, dimensions = calculate_match_scores(analysis.requirements, matches)
    relevance = fact_relevance_scores(analysis.requirements, matches)
    selected_entries: dict[str, list[dict]] = {}
    for category, limit in EXPERIENCE_LIMITS.items():
        selected_entries[category] = _rank_entries(
            getattr(profile, category).entries, facts, relevance, limit
        )
    selected_entries[FactCategory.EDUCATION.value] = _rank_entries(
        profile.education_history.entries, facts, relevance, None
    )
    selected_fact_ids = {
        category.value: [
            fact.id
            for fact in sorted(
                (item for item in facts if item.category == category),
                key=lambda item: (relevance.get(item.id, 0), item.confidence),
                reverse=True,
            )
            if relevance.get(fact.id, 0) > 0
        ][:12]
        for category in FactCategory
    }
    selected_fact_ids[FactCategory.PERSONAL.value] = [
        fact.id
        for fact in sorted(
            facts,
            key=lambda item: (relevance.get(item.id, 0), item.confidence),
            reverse=True,
        )
        if relevance.get(fact.id, 0) > 0
    ][:12]
    keyword_coverage = _keyword_coverage(analysis, facts)
    requirement_map = {item.id: item for item in analysis.requirements}
    strengths = [
        requirement_map[item.requirement_id].text
        for item in matches
        if item.support_level == SupportLevel.EXACT and item.requirement_id in requirement_map
    ][:6]
    gaps = [
        requirement_map[item.requirement_id].text
        for item in matches
        if item.support_level == SupportLevel.NONE and item.requirement_id in requirement_map
    ][:8]
    return {
        "overall_score": overall,
        "dimension_scores": {
            key.value: value.model_dump(mode="json") for key, value in dimensions.items()
        },
        "keyword_coverage": keyword_coverage.model_dump(mode="json"),
        "fact_relevance": relevance,
        "selected_entries": selected_entries,
        "selected_fact_ids": selected_fact_ids,
        "strengths": strengths,
        "gaps": gaps,
    }


def _rank_entries(entries, facts, relevance: dict[str, float], limit: int | None) -> list[dict]:
    ranked = []
    for entry in entries:
        span_ids = {item.span_id for item in entry.evidence_refs}
        fact_ids = [
            fact.id
            for fact in facts
            if span_ids.intersection(item.span_id for item in fact.evidence_refs)
        ]
        score = max((relevance.get(fact_id, 0) for fact_id in fact_ids), default=0)
        if not fact_ids:
            continue
        ranked.append(
            {
                "entry": entry.model_dump(mode="json"),
                "fact_ids": fact_ids,
                "relevance_score": score,
            }
        )
    ranked.sort(key=lambda item: item["relevance_score"], reverse=True)
    return ranked if limit is None else ranked[:limit]


def _keyword_coverage(analysis: JDAnalysis, facts: list[ProfileFact]) -> KeywordCoverage:
    searchable = " ".join(fact.statement for fact in facts).casefold()
    matched = [item for item in analysis.keywords if item.casefold() in searchable]
    missing = [item for item in analysis.keywords if item.casefold() not in searchable]
    ratio = len(matched) / len(analysis.keywords) if analysis.keywords else 1
    return KeywordCoverage(matched=matched, missing=missing, ratio=ratio)
