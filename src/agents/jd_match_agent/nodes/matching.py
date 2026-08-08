import json
import re
from profile.models import EvidenceRef, FactCategory, ProfileFact

from langchain_core.messages import HumanMessage, SystemMessage

from agents.jd_match_agent.prompts.matching import MATCHING_SYSTEM_PROMPT, matching_user_prompt
from agents.jd_match_agent.schemas import RequirementMatchResponse
from core.model import get_match_model
from core.settings import get_settings
from matching.models import JDAnalysis, RequirementMatch, SupportLevel


async def match_requirements(state: dict) -> dict:
    analysis = JDAnalysis.model_validate(state["jd_analysis"])
    facts = [ProfileFact.model_validate(item) for item in state.get("facts", [])]
    settings = get_settings()
    warnings: list[str] = []
    drafts = None
    if settings.llm_configured and analysis.requirements:
        try:
            model = get_match_model(settings).with_structured_output(RequirementMatchResponse)
            response = await model.ainvoke(
                [
                    SystemMessage(content=MATCHING_SYSTEM_PROMPT),
                    HumanMessage(
                        content=matching_user_prompt(
                            json.dumps(
                                [item.model_dump(mode="json") for item in analysis.requirements],
                                ensure_ascii=False,
                            ),
                            json.dumps(
                                [fact.model_dump(mode="json") for fact in facts],
                                ensure_ascii=False,
                            ),
                        )
                    ),
                ]
            )
            drafts = response.matches
        except Exception as exc:
            if not settings.allow_heuristic_fallback:
                raise
            warnings.append(f"岗位匹配模型失败，已使用规则回退：{exc}")
    matches = _materialize(analysis, facts, drafts)
    return {
        "requirement_matches": [item.model_dump(mode="json") for item in matches],
        "warnings": warnings,
    }


def _materialize(analysis: JDAnalysis, facts: list[ProfileFact], drafts) -> list[RequirementMatch]:
    fact_map = {fact.id: fact for fact in facts}
    draft_map = {item.requirement_id: item for item in drafts or []}
    output: list[RequirementMatch] = []
    for requirement in analysis.requirements:
        draft = draft_map.get(requirement.id)
        if draft is None:
            output.append(_heuristic_match(requirement, facts))
            continue
        valid_ids = [fact_id for fact_id in draft.source_fact_ids if fact_id in fact_map]
        support = draft.support_level if valid_ids else SupportLevel.NONE
        selected = [fact_map[fact_id] for fact_id in valid_ids]
        output.append(
            RequirementMatch(
                requirement_id=requirement.id,
                support_level=support,
                source_fact_ids=valid_ids,
                evidence_refs=_evidence(selected),
                confidence=draft.confidence if selected else 0,
                rationale=draft.rationale,
            )
        )
    return output


def _heuristic_match(requirement, facts: list[ProfileFact]) -> RequirementMatch:
    candidates = (
        facts
        if requirement.category == FactCategory.PERSONAL
        else [fact for fact in facts if fact.category == requirement.category]
    )
    keywords = requirement.keywords or _tokens(requirement.text)
    ranked: list[tuple[float, ProfileFact]] = []
    for fact in candidates:
        text = fact.statement.casefold()
        matched = [keyword for keyword in keywords if keyword.casefold() in text]
        score = len(matched) / max(len(keywords), 1)
        if score:
            ranked.append((score, fact))
    ranked.sort(key=lambda item: (item[0], item[1].confidence), reverse=True)
    selected = [fact for _, fact in ranked[:4]]
    best = ranked[0][0] if ranked else 0
    if best >= 0.6:
        support = SupportLevel.EXACT
    elif best > 0:
        support = SupportLevel.PARTIAL
    else:
        support = SupportLevel.NONE
    confidence = sum(fact.confidence for fact in selected) / len(selected) if selected else 0
    return RequirementMatch(
        requirement_id=requirement.id,
        support_level=support,
        source_fact_ids=[fact.id for fact in selected],
        evidence_refs=_evidence(selected),
        confidence=confidence,
        rationale="事实关键词与岗位要求直接重合。" if selected else "画像中未找到直接支持事实。",
    )


def _tokens(text: str) -> list[str]:
    ascii_tokens = re.findall(r"\b[A-Za-z][A-Za-z0-9+#.\-]{1,30}\b", text)
    chinese = re.findall(r"[\u4e00-\u9fff]{2,6}", text)
    return list(dict.fromkeys([*ascii_tokens, *chinese]))[:20]


def _evidence(facts: list[ProfileFact]) -> list[EvidenceRef]:
    items = {item.span_id: item for fact in facts for item in fact.evidence_refs}
    return list(items.values())
