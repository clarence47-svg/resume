import re
from collections import defaultdict
from profile.models import FactCategory, ProfileFact

from matching.models import (
    DimensionMatch,
    JDAnalysis,
    JDRequirement,
    MaterialRelevanceScore,
    RequirementMatch,
    SupportLevel,
)

SUPPORT_VALUES = {
    SupportLevel.EXACT: 1.0,
    SupportLevel.PARTIAL: 0.6,
    SupportLevel.NONE: 0.0,
}


def calculate_match_scores(
    requirements: list[JDRequirement], matches: list[RequirementMatch]
) -> tuple[float, dict[FactCategory, DimensionMatch]]:
    match_map = {item.requirement_id: item for item in matches}
    total_weight = sum(item.weight for item in requirements)
    total_value = 0.0
    grouped: dict[FactCategory, list[JDRequirement]] = defaultdict(list)
    for requirement in requirements:
        grouped[requirement.category].append(requirement)
        match = match_map.get(requirement.id)
        if match is not None:
            total_value += (
                requirement.weight
                * SUPPORT_VALUES[match.support_level]
                * max(match.confidence, 0.01)
            )

    dimensions: dict[FactCategory, DimensionMatch] = {}
    for category in FactCategory:
        items = grouped.get(category, [])
        denominator = sum(item.weight for item in items)
        numerator = 0.0
        matched_ids: list[str] = []
        missing_ids: list[str] = []
        for requirement in items:
            match = match_map.get(requirement.id)
            if match is None or match.support_level == SupportLevel.NONE:
                missing_ids.append(requirement.id)
                continue
            numerator += (
                requirement.weight
                * SUPPORT_VALUES[match.support_level]
                * max(match.confidence, 0.01)
            )
            matched_ids.append(requirement.id)
        dimensions[category] = DimensionMatch(
            score=round(numerator / denominator * 100, 1) if denominator else 0,
            matched_requirement_ids=matched_ids,
            missing_requirement_ids=missing_ids,
        )
    overall = round(total_value / total_weight * 100, 1) if total_weight else 0
    return overall, dimensions


def fact_relevance_scores(
    requirements: list[JDRequirement], matches: list[RequirementMatch]
) -> dict[str, float]:
    requirement_map = {item.id: item for item in requirements}
    raw_scores: dict[str, float] = defaultdict(float)
    max_score = 0.0
    for match in matches:
        requirement = requirement_map.get(match.requirement_id)
        if requirement is None:
            continue
        contribution = requirement.weight * SUPPORT_VALUES[match.support_level] * match.confidence
        for fact_id in match.source_fact_ids:
            raw_scores[fact_id] += contribution
            max_score = max(max_score, raw_scores[fact_id])
    if max_score == 0:
        return {}
    return {fact_id: round(value / max_score * 100, 1) for fact_id, value in raw_scores.items()}


def material_relevance_scores(
    analysis: JDAnalysis,
    matches: list[RequirementMatch],
    facts: list[ProfileFact],
) -> dict[str, MaterialRelevanceScore]:
    requirement_map = {item.id: item for item in analysis.requirements}
    direct_raw: dict[str, float] = defaultdict(float)
    transferable_raw: dict[str, float] = defaultdict(float)
    matched_requirements: dict[str, set[str]] = defaultdict(set)
    for match in matches:
        requirement = requirement_map.get(match.requirement_id)
        if requirement is None or match.support_level == SupportLevel.NONE:
            continue
        contribution = requirement.weight * max(match.confidence, 0.01)
        target = direct_raw if match.support_level == SupportLevel.EXACT else transferable_raw
        for fact_id in match.source_fact_ids:
            target[fact_id] += contribution
            matched_requirements[fact_id].add(requirement.id)

    direct_max = max(direct_raw.values(), default=0)
    transferable_max = max(transferable_raw.values(), default=0)
    output: dict[str, MaterialRelevanceScore] = {}
    for fact in facts:
        text = _fact_search_text(fact)
        direct = _normalized(direct_raw.get(fact.id, 0), direct_max)
        transferable = _normalized(transferable_raw.get(fact.id, 0), transferable_max)
        adjacent = _adjacent_score(text, analysis.requirements)
        impact = _impact_score(fact)
        capability_scores = {
            dimension.id: _capability_score(
                text,
                dimension.keywords,
                dimension.requirement_ids,
                matched_requirements.get(fact.id, set()),
                requirement_map,
            )
            for dimension in analysis.capability_dimensions
        }
        overall = round(
            direct * 0.4 + transferable * 0.3 + adjacent * 0.2 + impact * 0.1,
            1,
        )
        output[fact.id] = MaterialRelevanceScore(
            direct_match=direct,
            transferable=transferable,
            adjacent=adjacent,
            impact=impact,
            overall=overall,
            capability_scores=capability_scores,
        )
    return output


def _normalized(value: float, maximum: float) -> float:
    return round(value / maximum * 100, 1) if maximum else 0


def _fact_search_text(fact: ProfileFact) -> str:
    values = [fact.statement, *[str(value) for value in fact.metadata.values() if value]]
    return " ".join(values).casefold()


def _adjacent_score(text: str, requirements: list[JDRequirement]) -> float:
    best = 0.0
    for requirement in requirements:
        keywords = requirement.keywords or _tokens(requirement.text)
        if not keywords:
            continue
        overlap = sum(1 for keyword in keywords if keyword.casefold() in text)
        score = overlap / len(keywords) * 100
        best = max(best, score)
    return round(best, 1)


def _impact_score(fact: ProfileFact) -> float:
    text = fact.statement
    score = 20.0
    if re.search(r"\d+(?:\.\d+)?(?:%|％|万|亿|倍|人|次|项|个|元|K|W|\+)?", text):
        score += 45
    if any(
        token in text
        for token in (
            "提升",
            "降低",
            "增长",
            "优化",
            "完成",
            "落地",
            "获奖",
            "负责",
            "主导",
            "实现",
            "解决",
        )
    ):
        score += 25
    score += fact.confidence * 10
    return round(min(score, 100), 1)


def _capability_score(
    text: str,
    keywords: list[str],
    requirement_ids: list[str],
    matched_requirement_ids: set[str],
    requirement_map: dict[str, JDRequirement],
) -> float:
    dimension_requirements = [
        requirement_map[item] for item in requirement_ids if item in requirement_map
    ]
    denominator = sum(item.weight for item in dimension_requirements)
    supported = sum(
        item.weight for item in dimension_requirements if item.id in matched_requirement_ids
    )
    requirement_score = supported / denominator * 100 if denominator else 0
    keyword_score = (
        sum(1 for keyword in keywords if keyword.casefold() in text) / len(keywords) * 100
        if keywords
        else 0
    )
    return round(max(requirement_score, keyword_score), 1)


def _tokens(text: str) -> list[str]:
    ascii_tokens = re.findall(r"\b[A-Za-z][A-Za-z0-9+#.\-]{1,30}\b", text)
    chinese = re.findall(r"[\u4e00-\u9fff]{2,6}", text)
    return list(dict.fromkeys([*ascii_tokens, *chinese]))[:20]
