import re
from profile.models import BasisType, EvidenceRef, FactCategory, ProfileFact

from langchain_core.messages import HumanMessage, SystemMessage

from agents.profile_agent.prompts.extraction import (
    EXTRACTION_SYSTEM_PROMPT,
    extraction_user_prompt,
)
from agents.profile_agent.schemas import FactExtractionResponse
from core.model import get_profile_model
from core.settings import get_settings
from ingestion.models import DocumentChunk, SourceSpan

CATEGORY_KEYWORDS = {
    FactCategory.PROJECT: ("项目", "系统", "平台", "开发", "设计", "技术栈", "github"),
    FactCategory.COMPETITION: ("比赛", "竞赛", "大赛", "奖项", "获奖", "一等奖", "二等奖"),
    FactCategory.INTERNSHIP: ("实习", "公司", "岗位", "部门", "企业", "工作"),
    FactCategory.EDUCATION: ("大学", "学院", "学校", "本科", "硕士", "专业", "课程", "gpa"),
    FactCategory.PROFESSIONAL: ("技能", "熟悉", "掌握", "研究", "方向", "证书", "python", "java"),
}


async def prepare(state: dict) -> dict:
    if state.get("mode") == "facts_only" and not state.get("facts"):
        raise ValueError("重新生成需要已确认事实。")
    if state.get("mode", "full") == "full" and not state.get("chunks"):
        raise ValueError("没有可供分析的资料片段。")
    return {"warnings": []}


async def extract_fact_chunk(state: dict) -> dict:
    chunk = DocumentChunk.model_validate(state["chunk"])
    settings = get_settings()
    warnings: list[str] = []
    if settings.llm_configured:
        try:
            model = get_profile_model(settings).with_structured_output(FactExtractionResponse)
            response = await model.ainvoke(
                [
                    SystemMessage(content=EXTRACTION_SYSTEM_PROMPT),
                    HumanMessage(content=extraction_user_prompt(chunk.text)),
                ]
            )
            facts = _materialize_facts(response, chunk.spans)
            return {
                "extracted_fact_batches": [[fact.model_dump(mode="json") for fact in facts]],
                "warnings": warnings,
            }
        except Exception as exc:
            if not settings.allow_heuristic_fallback:
                raise
            warnings.append(f"模型事实抽取失败，已使用规则回退：{exc}")
    elif not settings.allow_heuristic_fallback:
        raise RuntimeError("LLM 未配置且未允许规则回退。")
    facts = _heuristic_facts(chunk)
    warnings.append("当前结果使用规则回退生成，请配置 LLM 以获得更完整画像。")
    return {
        "extracted_fact_batches": [[fact.model_dump(mode="json") for fact in facts]],
        "warnings": warnings,
    }


def _materialize_facts(
    response: FactExtractionResponse, spans: list[SourceSpan]
) -> list[ProfileFact]:
    span_map = {span.id: span for span in spans}
    facts: list[ProfileFact] = []
    for draft in response.facts:
        selected = [span_map[span_id] for span_id in draft.evidence_span_ids if span_id in span_map]
        if not selected:
            selected = spans[:1]
        evidence = [_evidence_ref(span) for span in selected]
        if not evidence:
            continue
        facts.append(
            ProfileFact(
                category=draft.category,
                statement=draft.statement.strip(),
                basis_type=draft.basis_type,
                confidence=draft.confidence,
                evidence_refs=evidence,
                rationale=draft.rationale,
                metadata=draft.metadata,
            )
        )
    return facts


def _heuristic_facts(chunk: DocumentChunk) -> list[ProfileFact]:
    facts: list[ProfileFact] = []
    for span in chunk.spans:
        pieces = [piece.strip(" -•\t") for piece in re.split(r"[\n。；]+", span.text)]
        for piece in pieces:
            if len(piece) < 6:
                continue
            facts.append(
                ProfileFact(
                    category=_guess_category(piece),
                    statement=piece[:800],
                    basis_type=BasisType.FACT,
                    confidence=0.68,
                    evidence_refs=[_evidence_ref(span)],
                    rationale="由资料原文直接抽取。",
                    metadata={"fallback": True},
                )
            )
    return facts[:100]


def _guess_category(text: str) -> FactCategory:
    lowered = text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return category
    return FactCategory.PERSONAL


def _evidence_ref(span: SourceSpan) -> EvidenceRef:
    return EvidenceRef(
        span_id=span.id,
        document_id=span.document_id,
        file_name=span.file_name,
        quote=span.text[:500],
        page=span.page,
        slide=span.slide,
        paragraph=span.paragraph,
        section=span.section,
    )
