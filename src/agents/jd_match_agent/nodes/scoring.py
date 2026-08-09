from profile.models import FactCategory, ProfileFact, ProfileResult
from profile.section_documents import extract_document_fact_ids

from matching.models import JDAnalysis, KeywordCoverage, RequirementMatch, SupportLevel
from matching.scoring import calculate_match_scores, fact_relevance_scores
from matching.section_documents import render_selected_section_documents

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
    section_fact_ids = {
        section_name: extract_document_fact_ids(content)
        for section_name, content in state.get("profile_sections", {}).items()
    }
    selected_entries: dict[str, list[dict]] = {}
    for category, limit in EXPERIENCE_LIMITS.items():
        selected_entries[category] = _rank_entries(
            getattr(profile, category).entries,
            facts,
            relevance,
            limit,
            section_fact_ids.get(category, set()),
        )
    selected_entries[FactCategory.EDUCATION.value] = _rank_entries(
        profile.education_history.entries,
        facts,
        relevance,
        None,
        section_fact_ids.get(FactCategory.EDUCATION.value, set()),
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
            and fact.id in section_fact_ids.get(category.value, set())
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
        and fact.id in section_fact_ids.get(FactCategory.PERSONAL.value, set())
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
    tailored_profile_sections = render_selected_section_documents(
        facts,
        selected_entries,
        selected_fact_ids,
        analysis,
    )
    return {
        "overall_score": overall,
        "dimension_scores": {
            key.value: value.model_dump(mode="json") for key, value in dimensions.items()
        },
        "keyword_coverage": keyword_coverage.model_dump(mode="json"),
        "fact_relevance": relevance,
        "selected_entries": selected_entries,
        "selected_fact_ids": selected_fact_ids,
        "tailored_profile_sections": tailored_profile_sections,
        "strengths": strengths,
        "gaps": gaps,
    }


def _rank_entries(
    entries,
    facts,
    relevance: dict[str, float],
    limit: int | None,
    allowed_fact_ids: set[str],
) -> list[dict]:
    fact_map = {fact.id: fact for fact in facts}
    grouped: dict[str, dict] = {}
    for entry in entries:
        span_ids = {item.span_id for item in entry.evidence_refs}
        declared_fact_ids = set(getattr(entry, "source_fact_ids", []))
        direct_fact_ids = [
            fact.id
            for fact in facts
            if fact.id in allowed_fact_ids
            if fact.id in declared_fact_ids
            or span_ids.intersection(item.span_id for item in fact.evidence_refs)
        ]
        group_ids = {
            fact_map[fact_id].material_group_id
            for fact_id in direct_fact_ids
            if fact_id in fact_map and fact_map[fact_id].material_group_id
        }
        fact_ids = [
            fact.id
            for fact in facts
            if fact.id in allowed_fact_ids
            if fact.id in direct_fact_ids or fact.material_group_id in group_ids
        ]
        score = max((relevance.get(fact_id, 0) for fact_id in fact_ids), default=0)
        if not fact_ids:
            continue
        direct_score = max(
            (relevance.get(fact_id, 0) for fact_id in direct_fact_ids), default=score
        )
        key = sorted(group_ids)[0] if group_ids else _entry_identity(entry)
        candidate = {
            "entry": entry.model_dump(mode="json"),
            "fact_ids": fact_ids,
            "relevance_score": score,
            "identity_score": direct_score,
        }
        existing = grouped.get(key)
        if existing is None:
            grouped[key] = candidate
        else:
            grouped[key] = _merge_ranked_entry(existing, candidate)
    ranked = list(grouped.values())
    ranked.sort(key=lambda item: item["relevance_score"], reverse=True)
    for item in ranked:
        item.pop("identity_score", None)
    return ranked if limit is None else ranked[:limit]


def _entry_identity(entry) -> str:
    values = [
        getattr(entry, "name", None) or getattr(entry, "institution", None),
        getattr(entry, "organization", None),
        getattr(entry, "period", None),
    ]
    return "|".join(str(value or "").lower().replace(" ", "") for value in values)


def _merge_ranked_entry(left: dict, right: dict) -> dict:
    preferred, complement = (
        (right, left) if right["identity_score"] > left["identity_score"] else (left, right)
    )
    entry = dict(preferred["entry"])
    entry["technologies"] = list(
        dict.fromkeys(
            [
                *preferred["entry"].get("technologies", []),
                *complement["entry"].get("technologies", []),
            ]
        )
    )
    entry["source_fact_ids"] = list(
        dict.fromkeys(
            [
                *preferred["entry"].get("source_fact_ids", []),
                *complement["entry"].get("source_fact_ids", []),
            ]
        )
    )
    evidence = {
        item["span_id"]: item
        for item in [
            *preferred["entry"].get("evidence_refs", []),
            *complement["entry"].get("evidence_refs", []),
        ]
    }
    entry["evidence_refs"] = list(evidence.values())
    return {
        "entry": entry,
        "fact_ids": list(dict.fromkeys([*left["fact_ids"], *right["fact_ids"]])),
        "relevance_score": max(left["relevance_score"], right["relevance_score"]),
        "identity_score": max(left["identity_score"], right["identity_score"]),
    }


def _keyword_coverage(analysis: JDAnalysis, facts: list[ProfileFact]) -> KeywordCoverage:
    searchable = " ".join(fact.statement for fact in facts).casefold()
    matched = [item for item in analysis.keywords if item.casefold() in searchable]
    missing = [item for item in analysis.keywords if item.casefold() not in searchable]
    ratio = len(matched) / len(analysis.keywords) if analysis.keywords else 1
    return KeywordCoverage(matched=matched, missing=missing, ratio=ratio)
