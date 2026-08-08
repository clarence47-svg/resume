from profile.models import ConflictRecord, FactStatus, ProfileFact, ProfileResult

from matching.models import JDAnalysis


def prepare(state: dict) -> dict:
    ProfileResult.model_validate(state["profile_result"])
    facts = [ProfileFact.model_validate(item) for item in state.get("facts", [])]
    conflicts = [ConflictRecord.model_validate(item) for item in state.get("conflicts", [])]
    unresolved_ids = {fact_id for conflict in conflicts for fact_id in conflict.fact_ids}
    usable = [
        fact
        for fact in facts
        if fact.status != FactStatus.REJECTED
        and not (fact.id in unresolved_ids and fact.status == FactStatus.EXTRACTED)
    ]
    warnings = []
    excluded = len(facts) - len(usable)
    if excluded:
        warnings.append(f"已排除 {excluded} 条被拒绝或存在未解决冲突的事实。")
    return {
        "facts": [fact.model_dump(mode="json") for fact in usable],
        "jd_analysis": JDAnalysis().model_dump(mode="json"),
        "audit_attempt": 0,
        "warnings": warnings,
    }
