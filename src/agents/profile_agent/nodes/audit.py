from profile.models import ProfileAudit, ProfileResult, SectionStatus

from agents.profile_agent.prompts.audit import SENSITIVE_TERMS


def audit_profile(state: dict) -> dict:
    result = ProfileResult.model_validate(state["result"])
    claims = list(_iter_claims(result))
    cited = sum(bool(claim.evidence_refs) for claim in claims)
    coverage = cited / len(claims) if claims else 1.0
    searchable = result.model_dump_json()
    sensitive = any(term in searchable for term in SENSITIVE_TERMS)
    warnings = list(state.get("warnings", []))
    if coverage < 1:
        warnings.append("部分画像陈述缺少来源证据。")
    if sensitive:
        warnings.append("检测到可能的敏感属性推断。")
    result.audit = ProfileAudit(
        passed=coverage == 1 and not sensitive,
        citation_coverage=coverage,
        warnings=warnings,
        sensitive_inference_detected=sensitive,
    )
    return {"result": result.model_dump(mode="json")}


def _iter_claims(result: ProfileResult):
    yield from result.personal_introduction.items
    for section in (
        result.project_experiences,
        result.competition_experiences,
        result.internship_experiences,
    ):
        for entry in section.entries:
            yield from entry.details
            yield from entry.outcomes
    for entry in result.education_history.entries:
        yield from entry.honors
        yield from entry.campus_experiences


def assemble_profile(state: dict) -> dict:
    data = {item["section"]: item["data"] for item in state.get("section_outputs", [])}
    result = ProfileResult(
        task_id=state["task_id"],
        personal_introduction=data.get("personal_introduction", {}),
        project_experiences=data.get("project_experiences", {}),
        competition_experiences=data.get("competition_experiences", {}),
        internship_experiences=data.get("internship_experiences", {}),
        education_history=data.get("education_history", {}),
        conflicts=state.get("conflicts", []),
        missing_information=[
            name
            for name, section in data.items()
            if section.get("status") == SectionStatus.INSUFFICIENT_EVIDENCE.value
        ],
        model=_model_name(),
    )
    return {"result": result.model_dump(mode="json")}


def _model_name() -> str:
    from core.settings import get_settings

    settings = get_settings()
    return settings.profile_model if settings.llm_configured else "heuristic-fallback"
