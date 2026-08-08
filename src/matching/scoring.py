from collections import defaultdict
from profile.models import FactCategory

from matching.models import (
    DimensionMatch,
    JDRequirement,
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
