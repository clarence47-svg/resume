import json
from profile.models import EvidenceRef, FactCategory, ProfileFact, SectionStatus

from langchain_core.messages import HumanMessage, SystemMessage

from agents.jd_match_agent.prompts.sections import SECTION_SYSTEM_PROMPT, section_user_prompt
from agents.jd_match_agent.schemas import CopyUnitDraft, TailoredEntryDraft, TailoredSectionDraft
from core.model import get_match_model
from core.settings import get_settings
from matching.models import (
    JDAnalysis,
    RequirementMatch,
    TailoredCopyUnit,
    TailoredEducationEntry,
    TailoredEducationSection,
    TailoredExperienceEntry,
    TailoredExperienceSection,
    TailoredTextSection,
)

SECTION_NAMES = [category.value for category in FactCategory]


async def generate_section(state: dict) -> dict:
    section_name = state["section_name"]
    facts = [ProfileFact.model_validate(item) for item in state.get("facts", [])]
    analysis = JDAnalysis.model_validate(state["jd_analysis"])
    settings = get_settings()
    warnings: list[str] = []
    context = {
        "jd_analysis": analysis.model_dump(mode="json"),
        "facts": [fact.model_dump(mode="json") for fact in facts],
        "selected_fact_ids": state.get("selected_fact_ids", {}).get(section_name, []),
        "selected_entries": state.get("selected_entries", {}).get(section_name, []),
        "requirement_matches": state.get("requirement_matches", []),
    }
    draft = None
    if settings.llm_configured:
        try:
            model = get_match_model(settings).with_structured_output(TailoredSectionDraft)
            draft = await model.ainvoke(
                [
                    SystemMessage(content=SECTION_SYSTEM_PROMPT),
                    HumanMessage(
                        content=section_user_prompt(
                            section_name, json.dumps(context, ensure_ascii=False)
                        )
                    ),
                ]
            )
        except Exception as exc:
            if not settings.allow_heuristic_fallback:
                raise
            warnings.append(f"{section_name} 文案生成失败，已使用规则回退：{exc}")
    if draft is None:
        draft = _heuristic_draft(section_name, context, facts)
    section = _materialize(section_name, draft, state, facts)
    return {
        "section_outputs": [{"section": section_name, "data": section.model_dump(mode="json")}],
        "warnings": warnings,
    }


def _heuristic_draft(section_name: str, context: dict, facts: list[ProfileFact]):
    fact_map = {fact.id: fact for fact in facts}
    if section_name in {FactCategory.PERSONAL.value, FactCategory.PROFESSIONAL.value}:
        selected = [
            fact_map[fact_id] for fact_id in context["selected_fact_ids"] if fact_id in fact_map
        ]
        if not selected:
            return TailoredSectionDraft(
                overview=CopyUnitDraft(content="画像资料未提供足够的相关信息。")
            )
        overview_ids = [fact.id for fact in selected[:4]]
        return TailoredSectionDraft(
            overview=CopyUnitDraft(
                content="；".join(fact.statement for fact in selected[:4])[:800],
                source_fact_ids=overview_ids,
            ),
            bullets=[
                CopyUnitDraft(content=fact.statement, source_fact_ids=[fact.id])
                for fact in selected[:8]
            ],
            keywords=[
                item
                for item in context["jd_analysis"].get("keywords", [])
                if any(item.casefold() in fact.statement.casefold() for fact in selected)
            ][:12],
        )
    entries = []
    for selected in context["selected_entries"]:
        entry = selected["entry"]
        source_facts = [fact_map[item] for item in selected["fact_ids"] if item in fact_map]
        if not source_facts:
            continue
        summary_content = entry.get("summary") or entry.get("overview") or source_facts[0].statement
        entries.append(
            TailoredEntryDraft(
                source_name=entry.get("name") or entry.get("institution") or "经历",
                summary=CopyUnitDraft(
                    content=summary_content,
                    source_fact_ids=[fact.id for fact in source_facts[:4]],
                ),
                bullets=[
                    CopyUnitDraft(content=fact.statement, source_fact_ids=[fact.id])
                    for fact in source_facts[:4]
                ],
                selected_reason="与岗位要求存在事实支持的能力重合。",
            )
        )
    overview_ids = [fact_id for item in context["selected_entries"] for fact_id in item["fact_ids"]]
    return TailoredSectionDraft(
        overview=CopyUnitDraft(
            content="已优先选择与岗位要求相关度最高的经历。"
            if entries
            else "画像资料未提供足够的相关经历。",
            source_fact_ids=overview_ids[:8],
        ),
        entries=entries,
    )


def _materialize(section_name: str, draft: TailoredSectionDraft, state: dict, facts):
    fact_map = {fact.id: fact for fact in facts}
    match_map = {
        item.requirement_id: item
        for item in [
            RequirementMatch.model_validate(value) for value in state.get("requirement_matches", [])
        ]
    }
    relevance = state.get("fact_relevance", {})
    if section_name in {FactCategory.PERSONAL.value, FactCategory.PROFESSIONAL.value}:
        overview = _unit(draft.overview, fact_map, match_map, relevance)
        bullets = [_unit(item, fact_map, match_map, relevance) for item in draft.bullets]
        status = (
            SectionStatus.COMPLETE
            if overview.source_fact_ids
            else SectionStatus.INSUFFICIENT_EVIDENCE
        )
        return TailoredTextSection(
            status=status, overview=overview, bullets=bullets, keywords=draft.keywords[:12]
        )
    selected = state.get("selected_entries", {}).get(section_name, [])
    selected_map = {
        (item["entry"].get("name") or item["entry"].get("institution")): item for item in selected
    }
    if section_name == FactCategory.EDUCATION.value:
        entries = []
        for item in draft.entries:
            source = selected_map.get(item.source_name)
            if source is None:
                continue
            raw = source["entry"]
            entries.append(
                TailoredEducationEntry(
                    institution=raw["institution"],
                    degree=raw.get("degree"),
                    major=raw.get("major"),
                    period=raw.get("period"),
                    tailored_summary=_unit(item.summary, fact_map, match_map, relevance),
                    bullets=[
                        _unit(value, fact_map, match_map, relevance) for value in item.bullets
                    ],
                    relevance_score=source["relevance_score"],
                    evidence_refs=_fact_evidence(source["fact_ids"], fact_map),
                )
            )
        return TailoredEducationSection(
            status=SectionStatus.COMPLETE if entries else SectionStatus.INSUFFICIENT_EVIDENCE,
            overview=_unit(draft.overview, fact_map, match_map, relevance),
            entries=entries,
        )
    entries = []
    for item in draft.entries:
        source = selected_map.get(item.source_name)
        if source is None:
            continue
        raw = source["entry"]
        entries.append(
            TailoredExperienceEntry(
                name=raw["name"],
                organization=raw.get("organization"),
                period=raw.get("period"),
                role=raw.get("role"),
                tailored_summary=_unit(item.summary, fact_map, match_map, relevance),
                bullets=[_unit(value, fact_map, match_map, relevance) for value in item.bullets],
                selected_reason=item.selected_reason,
                relevance_score=source["relevance_score"],
                evidence_refs=_fact_evidence(source["fact_ids"], fact_map),
            )
        )
    return TailoredExperienceSection(
        status=SectionStatus.COMPLETE if entries else SectionStatus.INSUFFICIENT_EVIDENCE,
        overview=_unit(draft.overview, fact_map, match_map, relevance),
        entries=entries,
    )


def _unit(draft, fact_map, match_map, relevance) -> TailoredCopyUnit:
    fact_ids = [fact_id for fact_id in draft.source_fact_ids if fact_id in fact_map]
    matched_requirement_ids = list(
        dict.fromkeys(
            [
                requirement_id
                for requirement_id in draft.matched_requirement_ids
                if requirement_id in match_map
            ]
            + [
                requirement_id
                for requirement_id, match in match_map.items()
                if set(match.source_fact_ids).intersection(fact_ids)
            ]
        )
    )
    score = max((relevance.get(fact_id, 0) for fact_id in fact_ids), default=0)
    return TailoredCopyUnit(
        content=draft.content.strip(),
        source_fact_ids=fact_ids,
        evidence_refs=_fact_evidence(fact_ids, fact_map),
        matched_requirement_ids=matched_requirement_ids,
        relevance_score=score,
    )


def _fact_evidence(fact_ids: list[str], fact_map) -> list[EvidenceRef]:
    items = {
        evidence.span_id: evidence
        for fact_id in fact_ids
        if fact_id in fact_map
        for evidence in fact_map[fact_id].evidence_refs
    }
    return list(items.values())
