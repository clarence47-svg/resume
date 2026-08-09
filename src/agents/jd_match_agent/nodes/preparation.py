from profile.models import FactStatus, ProfileFact, ProfileResult
from profile.section_documents import render_profile_section_documents

from agents.profile_agent.nodes.merge import group_material_facts
from matching.models import JDAnalysis


async def prepare(state: dict) -> dict:
    profile = ProfileResult.model_validate(state["profile_result"])
    facts = [ProfileFact.model_validate(item) for item in state.get("facts", [])]
    usable = _deduplicate([fact for fact in facts if fact.status != FactStatus.REJECTED])
    usable, grouping_warnings = await group_material_facts(usable)
    warnings = list(grouping_warnings)
    excluded = len(facts) - len(usable)
    if excluded:
        warnings.append(f"已排除 {excluded} 条被拒绝或重复的素材。")
    profile_sections = state.get("profile_sections") or render_profile_section_documents(
        profile, usable
    )
    return {
        "facts": [fact.model_dump(mode="json") for fact in usable],
        "profile_sections": profile_sections,
        "jd_analysis": JDAnalysis().model_dump(mode="json"),
        "audit_attempt": 0,
        "warnings": warnings,
    }


def _deduplicate(facts: list[ProfileFact]) -> list[ProfileFact]:
    output: dict[tuple[str, str], ProfileFact] = {}
    for fact in facts:
        key = (fact.category.value, "".join(fact.statement.lower().split()))
        existing = output.get(key)
        if existing is None:
            output[key] = fact
            continue
        evidence = {item.span_id: item for item in existing.evidence_refs}
        evidence.update({item.span_id: item for item in fact.evidence_refs})
        output[key] = existing.model_copy(update={"evidence_refs": list(evidence.values())})
    return list(output.values())
