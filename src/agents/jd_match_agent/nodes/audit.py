import re
from profile.models import ProfileFact

from agents.profile_agent.prompts.audit import SENSITIVE_TERMS
from matching.models import (
    JDAnalysis,
    JDMatchResult,
    MatchAudit,
    iter_copy_units,
)

NUMBER_PATTERN = re.compile(r"\d+(?:\.\d+)?%?")


def assemble_result(state: dict) -> dict:
    data = {item["section"]: item["data"] for item in state.get("section_outputs", [])}
    result = JDMatchResult(
        match_id=state["match_id"],
        profile_task_id=state["profile_task_id"],
        jd_analysis=state["jd_analysis"],
        requirement_matches=state.get("requirement_matches", []),
        overall_score=state.get("overall_score", 0),
        dimension_scores=state.get("dimension_scores", {}),
        keyword_coverage=state.get("keyword_coverage", {}),
        strengths=state.get("strengths", []),
        gaps=state.get("gaps", []),
        personal_introduction=data.get("personal_introduction", {}),
        professional_introduction=data.get("professional_introduction", {}),
        project_experiences=data.get("project_experiences", {}),
        competition_experiences=data.get("competition_experiences", {}),
        internship_experiences=data.get("internship_experiences", {}),
        education_history=data.get("education_history", {}),
        model=_model_name(),
        version=state.get("target_version", 1),
    )
    return {"result": result.model_dump(mode="json")}


def audit_result(state: dict) -> dict:
    result = JDMatchResult.model_validate(state["result"])
    facts = [ProfileFact.model_validate(item) for item in state.get("facts", [])]
    analysis = JDAnalysis.model_validate(state["jd_analysis"])
    fact_map = {fact.id: fact for fact in facts}
    unsupported: list[str] = []
    cited = 0
    eligible = 0
    for _, _, unit in iter_copy_units(result):
        if not unit.source_fact_ids:
            if "资料未提供" not in unit.content and "资料不足" not in unit.content:
                unsupported.append(f"{unit.id}: 文案缺少来源事实。")
            continue
        eligible += 1
        selected = [fact_map[fact_id] for fact_id in unit.source_fact_ids if fact_id in fact_map]
        if len(selected) != len(unit.source_fact_ids):
            unsupported.append(f"{unit.id}: 使用了不存在的事实 ID。")
        if unit.evidence_refs:
            cited += 1
        source_text = " ".join(fact.statement for fact in selected).casefold()
        unsupported_numbers = set(NUMBER_PATTERN.findall(unit.content)) - set(
            NUMBER_PATTERN.findall(source_text)
        )
        if unsupported_numbers:
            unsupported.append(f"{unit.id}: 包含无事实支持的数字 {sorted(unsupported_numbers)}。")
        for skill in [*analysis.required_skills, *analysis.preferred_skills]:
            if skill.casefold() in unit.content.casefold() and skill.casefold() not in source_text:
                unsupported.append(f"{unit.id}: 技能 {skill} 缺少事实支持。")
    searchable = result.model_dump_json()
    sensitive = any(term in searchable for term in SENSITIVE_TERMS)
    coverage = cited / eligible if eligible else 1
    warnings = list(state.get("warnings", []))
    if unsupported:
        warnings.append("部分文案未通过事实一致性审计。")
    if sensitive:
        warnings.append("检测到可能的敏感属性推断。")
    result.audit = MatchAudit(
        passed=not unsupported and not sensitive,
        evidence_coverage=coverage,
        unsupported_claims=unsupported,
        warnings=list(dict.fromkeys(warnings)),
        sensitive_inference_detected=sensitive,
    )
    return {
        "result": result.model_dump(mode="json"),
        "audit_passed": result.audit.passed,
    }


def repair_result(state: dict) -> dict:
    result = JDMatchResult.model_validate(state["result"])
    facts = [ProfileFact.model_validate(item) for item in state.get("facts", [])]
    fact_map = {fact.id: fact for fact in facts}
    violating_ids = {
        item.split(":", 1)[0] for item in result.audit.unsupported_claims if ":" in item
    }
    for _, _, unit in iter_copy_units(result):
        if unit.id not in violating_ids:
            continue
        selected = [fact_map[fact_id] for fact_id in unit.source_fact_ids if fact_id in fact_map]
        if selected:
            unit.content = "；".join(fact.statement for fact in selected[:3])[:1000]
        else:
            unit.content = "资料未提供足够证据。"
            unit.source_fact_ids = []
            unit.evidence_refs = []
    return {
        "result": result.model_dump(mode="json"),
        "audit_attempt": state.get("audit_attempt", 0) + 1,
    }


def _model_name() -> str:
    from core.settings import get_settings

    settings = get_settings()
    if not settings.llm_configured:
        return "heuristic-fallback"
    return settings.match_model or settings.profile_model
