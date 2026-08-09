from collections import Counter
from profile.models import FactCategory, ProfileFact
from uuid import NAMESPACE_URL, uuid5

from matching.models import JDMatchResult, TailoredTextSection


def match_result_materials(
    result: JDMatchResult, source_facts: list[ProfileFact]
) -> list[ProfileFact]:
    fact_map = {fact.id: fact for fact in source_facts}
    output: list[ProfileFact] = []
    for category in FactCategory:
        section = getattr(result, category.value)
        if isinstance(section, TailoredTextSection):
            units = [section.overview, *section.bullets]
            for unit in units:
                fact = _material_fact(result, category, unit, fact_map, {})
                if fact:
                    output.append(fact)
            continue
        for entry in section.entries:
            metadata = {
                "experience_name": getattr(entry, "name", None)
                or getattr(entry, "institution", None),
                "organization": getattr(entry, "organization", None),
                "period": getattr(entry, "period", None),
                "role": getattr(entry, "role", None),
            }
            units = [entry.tailored_summary, *entry.bullets]
            for unit in units:
                fact = _material_fact(result, category, unit, fact_map, metadata)
                if fact:
                    output.append(fact)
    return output


def _material_fact(result, category, unit, fact_map, metadata) -> ProfileFact | None:
    content = unit.content.strip()
    if not content or "资料未提供" in content or "资料不足" in content:
        return None
    source = [fact_map[fact_id] for fact_id in unit.source_fact_ids if fact_id in fact_map]
    evidence = {
        item.span_id: item
        for item in unit.evidence_refs
        + [reference for fact in source for reference in fact.evidence_refs]
    }
    group_ids = [fact.material_group_id for fact in source if fact.material_group_id]
    group_id = Counter(group_ids).most_common(1)[0][0] if group_ids else None
    resolved_metadata = {key: value for key, value in metadata.items() if value}
    if group_id:
        resolved_metadata["material_group_id"] = group_id
    resolved_metadata["canonical_name"] = resolved_metadata.get("experience_name", "")
    return ProfileFact(
        id=str(uuid5(NAMESPACE_URL, f"match:{result.match_id}:{result.version}:{unit.id}")),
        category=category,
        statement=content,
        confidence=max(0.7, min(0.95, unit.relevance_score / 100 or 0.78)),
        evidence_refs=list(evidence.values()),
        rationale=f"来自历史岗位 {result.jd_analysis.role_title} 的已生成表达素材。",
        metadata=resolved_metadata,
    )
