import json
from collections import defaultdict
from profile.models import (
    EducationEntry,
    EducationHistory,
    ExperienceEntry,
    ExperienceSection,
    FactCategory,
    PersonalIntroduction,
    ProfessionalIntroduction,
    ProfileClaim,
    ProfileFact,
    SectionStatus,
)

from langchain_core.messages import HumanMessage, SystemMessage

from agents.profile_agent.prompts.sections import SECTION_SYSTEM_PROMPT, section_user_prompt
from agents.profile_agent.schemas import ClaimDraft, EntryDraft, SectionDraft
from core.model import get_profile_model
from core.settings import get_settings

SECTION_NAMES = [category.value for category in FactCategory]


async def generate_section(state: dict) -> dict:
    section_name = state["section_name"]
    all_facts = [ProfileFact.model_validate(item) for item in state.get("facts", [])]
    facts = _relevant_facts(section_name, all_facts)
    settings = get_settings()
    warnings: list[str] = []
    if settings.llm_configured:
        try:
            model = get_profile_model(settings).with_structured_output(SectionDraft)
            response = await model.ainvoke(
                [
                    SystemMessage(content=SECTION_SYSTEM_PROMPT),
                    HumanMessage(
                        content=section_user_prompt(
                            section_name,
                            json.dumps(
                                [fact.model_dump(mode="json") for fact in facts],
                                ensure_ascii=False,
                            ),
                        )
                    ),
                ]
            )
        except Exception as exc:
            if not settings.allow_heuristic_fallback:
                raise
            warnings.append(f"{section_name} 模型生成失败，已使用规则回退：{exc}")
            response = _heuristic_section(section_name, facts)
    else:
        response = _heuristic_section(section_name, facts)
    section = _materialize_section(section_name, response, facts)
    return {
        "section_outputs": [{"section": section_name, "data": section.model_dump(mode="json")}],
        "warnings": warnings,
    }


def _relevant_facts(section_name: str, facts: list[ProfileFact]) -> list[ProfileFact]:
    if section_name == FactCategory.PERSONAL.value:
        return [fact for fact in facts if fact.status.value != "rejected"]
    return [
        fact
        for fact in facts
        if fact.category.value == section_name and fact.status.value != "rejected"
    ]


def _heuristic_section(section_name: str, facts: list[ProfileFact]) -> SectionDraft:
    if not facts:
        return SectionDraft(overview="资料未提供足够信息。")
    overview = "；".join(fact.statement for fact in facts[:4])[:1000]
    if section_name in {
        FactCategory.PERSONAL.value,
        FactCategory.PROFESSIONAL.value,
    }:
        default_group = "core_strength" if section_name == FactCategory.PERSONAL.value else "skill"
        claims = [
            ClaimDraft(
                group=default_group,
                content=fact.statement,
                basis_type=fact.basis_type,
                confidence=fact.confidence,
                fact_ids=[fact.id],
                rationale=fact.rationale,
            )
            for fact in facts[:12]
        ]
        return SectionDraft(overview=overview, claims=claims)
    entries = [
        EntryDraft(
            name=fact.statement[:40],
            summary=fact.statement,
            details=[
                ClaimDraft(
                    content=fact.statement,
                    basis_type=fact.basis_type,
                    confidence=fact.confidence,
                    fact_ids=[fact.id],
                    rationale=fact.rationale,
                )
            ],
            fact_ids=[fact.id],
        )
        for fact in facts[:20]
    ]
    return SectionDraft(overview=overview, entries=entries)


def _materialize_section(section_name: str, draft: SectionDraft, facts: list[ProfileFact]):
    fact_map = {fact.id: fact for fact in facts}
    if section_name == FactCategory.PERSONAL.value:
        grouped = _group_claims(draft.claims, fact_map)
        return PersonalIntroduction(
            status=SectionStatus.COMPLETE if facts else SectionStatus.INSUFFICIENT_EVIDENCE,
            overview=draft.overview,
            core_strengths=grouped["core_strength"],
            work_characteristics=grouped["work_characteristic"],
            career_direction=grouped["career_direction"],
            keywords=draft.keywords,
        )
    if section_name == FactCategory.PROFESSIONAL.value:
        grouped = _group_claims(draft.claims, fact_map)
        return ProfessionalIntroduction(
            status=SectionStatus.COMPLETE if facts else SectionStatus.INSUFFICIENT_EVIDENCE,
            overview=draft.overview,
            knowledge_domains=grouped["knowledge_domain"],
            skills=grouped["skill"],
            tools_and_technologies=draft.keywords,
            research_interests=grouped["research_interest"],
            certifications=grouped["certification"],
        )
    if section_name == FactCategory.EDUCATION.value:
        entries = []
        for entry in draft.entries:
            evidence = _entry_evidence(entry, fact_map)
            grouped = _group_claims(entry.details + entry.outcomes, fact_map)
            entries.append(
                EducationEntry(
                    institution=entry.name,
                    degree=entry.attributes.get("degree"),
                    major=entry.attributes.get("major"),
                    period=entry.period,
                    overview=entry.summary,
                    courses=_split_attribute(entry.attributes.get("courses")),
                    honors=grouped["honor"] + grouped["outcome"],
                    campus_experiences=grouped["detail"],
                    evidence_refs=evidence,
                    confidence=_entry_confidence(entry, fact_map),
                )
            )
        return EducationHistory(
            status=SectionStatus.COMPLETE if entries else SectionStatus.INSUFFICIENT_EVIDENCE,
            overview=draft.overview,
            entries=entries,
        )
    entries = []
    for entry in draft.entries:
        grouped = _group_claims(entry.details, fact_map)
        outcomes = [_claim(item, fact_map) for item in entry.outcomes]
        entries.append(
            ExperienceEntry(
                name=entry.name,
                organization=entry.organization,
                period=entry.period,
                role=entry.role,
                summary=entry.summary,
                details=[claim for claims in grouped.values() for claim in claims],
                technologies=entry.technologies,
                outcomes=outcomes,
                evidence_refs=_entry_evidence(entry, fact_map),
                confidence=_entry_confidence(entry, fact_map),
                attributes=entry.attributes,
            )
        )
    return ExperienceSection(
        status=SectionStatus.COMPLETE if entries else SectionStatus.INSUFFICIENT_EVIDENCE,
        overview=draft.overview,
        entries=entries,
    )


def _group_claims(
    drafts: list[ClaimDraft], fact_map: dict[str, ProfileFact]
) -> defaultdict[str, list[ProfileClaim]]:
    grouped: defaultdict[str, list[ProfileClaim]] = defaultdict(list)
    for draft in drafts:
        grouped[draft.group].append(_claim(draft, fact_map))
    return grouped


def _claim(draft: ClaimDraft, fact_map: dict[str, ProfileFact]) -> ProfileClaim:
    selected = [fact_map[fact_id] for fact_id in draft.fact_ids if fact_id in fact_map]
    evidence = {item.span_id: item for fact in selected for item in fact.evidence_refs}
    if not evidence and fact_map:
        fallback = next(iter(fact_map.values()))
        evidence = {item.span_id: item for item in fallback.evidence_refs}
    return ProfileClaim(
        content=draft.content,
        basis_type=draft.basis_type,
        confidence=draft.confidence,
        evidence_refs=list(evidence.values()),
        rationale=draft.rationale,
    )


def _entry_evidence(entry: EntryDraft, fact_map: dict[str, ProfileFact]):
    fact_ids = set(entry.fact_ids)
    for claim in entry.details + entry.outcomes:
        fact_ids.update(claim.fact_ids)
    evidence = {
        item.span_id: item
        for fact_id in fact_ids
        if fact_id in fact_map
        for item in fact_map[fact_id].evidence_refs
    }
    return list(evidence.values())


def _entry_confidence(entry: EntryDraft, fact_map: dict[str, ProfileFact]) -> float:
    values = [fact_map[fact_id].confidence for fact_id in entry.fact_ids if fact_id in fact_map]
    return sum(values) / len(values) if values else 0.6


def _split_attribute(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.replace("，", ",").split(",") if item.strip()]
