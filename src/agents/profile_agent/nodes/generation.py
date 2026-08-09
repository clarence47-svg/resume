import json
from collections import defaultdict
from profile.competition_verification import competition_fact_is_verified
from profile.models import (
    PROFILE_SECTION_CATEGORIES,
    EducationEntry,
    EducationHistory,
    ExperienceEntry,
    ExperienceSection,
    FactCategory,
    PersonalInformationItem,
    PersonalIntroduction,
    ProfileClaim,
    ProfileFact,
    SectionStatus,
)

from langchain_core.messages import HumanMessage, SystemMessage

from agents.profile_agent.nodes.extraction import _detect_personal_field
from agents.profile_agent.prompts.sections import SECTION_SYSTEM_PROMPT, section_user_prompt
from agents.profile_agent.schemas import ClaimDraft, EntryDraft, SectionDraft
from core.model import get_profile_model
from core.settings import get_settings

SECTION_NAMES = [category.value for category in PROFILE_SECTION_CATEGORIES]

PERSONAL_LABELS = {
    "name": "姓名",
    "birth_date": "出生年月",
    "hometown": "籍贯",
    "school": "当前学校",
    "phone": "电话",
    "email": "邮箱",
    "target_role": "求职方向",
    "portfolio": "作品集",
    "location": "所在城市",
}


async def generate_section(state: dict) -> dict:
    section_name = state["section_name"]
    all_facts = [ProfileFact.model_validate(item) for item in state.get("facts", [])]
    facts = _relevant_facts(section_name, all_facts)
    if section_name == FactCategory.PERSONAL.value:
        section = _personal_information(facts)
        return {
            "section_outputs": [{"section": section_name, "data": section.model_dump(mode="json")}],
            "warnings": [],
        }
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
    selected = [
        fact
        for fact in facts
        if fact.category.value == section_name and fact.status.value != "rejected"
    ]
    if section_name == FactCategory.COMPETITION.value:
        return [fact for fact in selected if competition_fact_is_verified(fact)]
    return selected


def _heuristic_section(section_name: str, facts: list[ProfileFact]) -> SectionDraft:
    if not facts:
        return SectionDraft(overview="资料未提供足够信息。")
    overview = "；".join(fact.statement for fact in facts[:4])[:1000]
    grouped: defaultdict[str, list[ProfileFact]] = defaultdict(list)
    for fact in facts:
        grouped[fact.material_group_id or fact.id].append(fact)
    entries = []
    for group_facts in list(grouped.values())[:20]:
        fact_ids = [fact.id for fact in group_facts]
        name = str(
            group_facts[0].metadata.get("canonical_name")
            or group_facts[0].metadata.get("experience_name")
            or group_facts[0].statement[:40]
        )
        entries.append(
            EntryDraft(
                name=name,
                organization=_first_metadata(group_facts, "organization"),
                period=_first_metadata(group_facts, "period"),
                role=_first_metadata(group_facts, "role"),
                summary="；".join(fact.statement for fact in group_facts)[:1000],
                details=[
                    ClaimDraft(
                        content=fact.statement,
                        basis_type=fact.basis_type,
                        confidence=fact.confidence,
                        fact_ids=[fact.id],
                        rationale=fact.rationale,
                    )
                    for fact in group_facts
                ],
                attributes={
                    key: value
                    for key, value in {
                        "material_group_id": group_facts[0].material_group_id or "",
                        "degree": _first_metadata(group_facts, "degree"),
                        "major": _first_metadata(group_facts, "major"),
                        "courses": _first_metadata(group_facts, "courses"),
                        "average_score": _first_metadata(group_facts, "average_score"),
                        "ranking": _first_metadata(group_facts, "ranking"),
                        "evaluation": _first_metadata(group_facts, "evaluation"),
                        "language_scores": _first_metadata(group_facts, "language_scores"),
                    }.items()
                    if value
                },
                fact_ids=fact_ids,
            )
        )
    return SectionDraft(overview=overview, entries=entries)


def _materialize_section(section_name: str, draft: SectionDraft, facts: list[ProfileFact]):
    fact_map = {fact.id: fact for fact in facts}
    if section_name == FactCategory.EDUCATION.value:
        entries = []
        seen_groups: set[str] = set()
        for entry in draft.entries:
            entry_fact_ids = _expanded_entry_fact_ids(entry, fact_map)
            group_key = _entry_group_key(entry_fact_ids, fact_map)
            if group_key in seen_groups:
                continue
            seen_groups.add(group_key)
            evidence = _fact_ids_evidence(entry_fact_ids, fact_map)
            complete_claims = _complete_entry_claims(
                entry.details + entry.outcomes, entry_fact_ids, fact_map
            )
            grouped = _group_claims(complete_claims, fact_map)
            entries.append(
                EducationEntry(
                    institution=entry.name,
                    degree=entry.attributes.get("degree"),
                    major=entry.attributes.get("major"),
                    period=entry.period,
                    overview=entry.summary,
                    average_score=entry.attributes.get("average_score"),
                    ranking=entry.attributes.get("ranking"),
                    evaluation=entry.attributes.get("evaluation"),
                    language_scores=_split_attribute(entry.attributes.get("language_scores")),
                    courses=_split_attribute(entry.attributes.get("courses")),
                    honors=grouped["honor"] + grouped["outcome"],
                    campus_experiences=grouped["detail"],
                    evidence_refs=evidence,
                    source_fact_ids=entry_fact_ids,
                    confidence=_entry_confidence(entry, fact_map),
                )
            )
        return EducationHistory(
            status=SectionStatus.COMPLETE if entries else SectionStatus.INSUFFICIENT_EVIDENCE,
            overview=draft.overview,
            entries=entries,
        )
    entries = []
    seen_groups: set[str] = set()
    for entry in draft.entries:
        entry_fact_ids = _expanded_entry_fact_ids(entry, fact_map)
        group_key = _entry_group_key(entry_fact_ids, fact_map)
        if group_key in seen_groups:
            continue
        seen_groups.add(group_key)
        complete_details = _complete_entry_claims(
            entry.details,
            entry_fact_ids,
            fact_map,
            represented_drafts=entry.details + entry.outcomes,
        )
        grouped = _group_claims(complete_details, fact_map)
        outcomes = [_claim(item, fact_map) for item in entry.outcomes]
        group_ids = {
            fact_map[fact_id].material_group_id
            for fact_id in entry_fact_ids
            if fact_id in fact_map and fact_map[fact_id].material_group_id
        }
        attributes = dict(entry.attributes)
        if len(group_ids) == 1:
            attributes["material_group_id"] = next(iter(group_ids))
        if section_name == FactCategory.COMPETITION.value:
            verification = next(
                (
                    fact_map[fact_id].metadata.get("competition_verification")
                    for fact_id in entry_fact_ids
                    if fact_id in fact_map
                    and fact_map[fact_id].metadata.get("competition_verification")
                ),
                None,
            )
            if isinstance(verification, dict):
                attributes["verification_status"] = str(verification.get("status") or "")
                attributes["verification_matched_name"] = str(
                    verification.get("matched_name") or ""
                )
                attributes["verification_score"] = str(verification.get("score") or "")
                attributes["verification_sources"] = json.dumps(
                    verification.get("sources") or [], ensure_ascii=False
                )
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
                evidence_refs=_fact_ids_evidence(entry_fact_ids, fact_map),
                source_fact_ids=entry_fact_ids,
                confidence=_entry_confidence(entry, fact_map),
                attributes=attributes,
            )
        )
    return ExperienceSection(
        status=SectionStatus.COMPLETE if entries else SectionStatus.INSUFFICIENT_EVIDENCE,
        overview=draft.overview,
        entries=entries,
    )


def _personal_information(facts: list[ProfileFact]) -> PersonalIntroduction:
    selected: dict[tuple[str, str], PersonalInformationItem] = {}
    for fact in facts:
        field = str(fact.metadata.get("personal_field") or "").strip()
        value = str(fact.metadata.get("personal_value") or "").strip()
        detected = _detect_personal_field(fact.statement)
        if not field and detected:
            field, value = detected
        elif field and not value:
            value = (
                detected[1]
                if detected and detected[0] == field
                else _personal_value(fact.statement)
            )
        if field not in PERSONAL_LABELS or not value:
            continue
        key = (field, value.casefold())
        item = PersonalInformationItem(
            key=field,
            label=PERSONAL_LABELS[field],
            value=value,
            confidence=fact.confidence,
            evidence_refs=fact.evidence_refs,
            source_fact_ids=[fact.id],
        )
        existing = selected.get(key)
        if existing is None or item.confidence > existing.confidence:
            selected[key] = item
    items = sorted(
        selected.values(),
        key=lambda item: list(PERSONAL_LABELS).index(item.key),
    )
    overview = (
        "；".join(f"{item.label}：{item.value}" for item in items)
        if items
        else "未从资料中识别到姓名、联系方式、求职方向等个人基本信息。"
    )
    return PersonalIntroduction(
        status=SectionStatus.COMPLETE if items else SectionStatus.INSUFFICIENT_EVIDENCE,
        overview=overview,
        items=items,
    )


def _personal_value(statement: str) -> str:
    for separator in ("：", ":"):
        if separator in statement:
            return statement.split(separator, 1)[1].strip()
    return statement.strip()


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


def _expanded_entry_fact_ids(entry: EntryDraft, fact_map: dict[str, ProfileFact]) -> list[str]:
    fact_ids = set(entry.fact_ids)
    for claim in entry.details + entry.outcomes:
        fact_ids.update(claim.fact_ids)
    group_ids = {
        fact_map[fact_id].material_group_id
        for fact_id in fact_ids
        if fact_id in fact_map and fact_map[fact_id].material_group_id
    }
    if group_ids:
        fact_ids.update(
            fact.id for fact in fact_map.values() if fact.material_group_id in group_ids
        )
    return [fact_id for fact_id in fact_map if fact_id in fact_ids]


def _fact_ids_evidence(fact_ids: list[str], fact_map: dict[str, ProfileFact]):
    evidence = {
        item.span_id: item
        for fact_id in fact_ids
        if fact_id in fact_map
        for item in fact_map[fact_id].evidence_refs
    }
    return list(evidence.values())


def _complete_entry_claims(
    drafts: list[ClaimDraft],
    fact_ids: list[str],
    fact_map: dict[str, ProfileFact],
    represented_drafts: list[ClaimDraft] | None = None,
) -> list[ClaimDraft]:
    represented = {fact_id for draft in represented_drafts or drafts for fact_id in draft.fact_ids}
    output = list(drafts)
    for fact_id in fact_ids:
        if fact_id in represented or fact_id not in fact_map:
            continue
        fact = fact_map[fact_id]
        output.append(
            ClaimDraft(
                group="detail",
                content=fact.statement,
                basis_type=fact.basis_type,
                confidence=fact.confidence,
                fact_ids=[fact.id],
                rationale=fact.rationale,
            )
        )
    return output


def _entry_group_key(fact_ids: list[str], fact_map: dict[str, ProfileFact]) -> str:
    groups = [
        fact_map[fact_id].material_group_id
        for fact_id in fact_ids
        if fact_id in fact_map and fact_map[fact_id].material_group_id
    ]
    return groups[0] if groups else ":".join(sorted(fact_ids))


def _entry_confidence(entry: EntryDraft, fact_map: dict[str, ProfileFact]) -> float:
    values = [fact_map[fact_id].confidence for fact_id in entry.fact_ids if fact_id in fact_map]
    return sum(values) / len(values) if values else 0.6


def _split_attribute(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.replace("，", ",").split(",") if item.strip()]


def _first_metadata(facts: list[ProfileFact], key: str) -> str | None:
    for fact in facts:
        value = fact.metadata.get(key)
        if value:
            return str(value)
    return None
