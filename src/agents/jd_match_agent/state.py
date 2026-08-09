import operator
from typing import Annotated, Any, TypedDict


class JDMatchAgentState(TypedDict, total=False):
    match_id: str
    profile_task_id: str
    jd_text: str
    profile_result: dict[str, Any]
    facts: list[dict[str, Any]]
    conflicts: list[dict[str, Any]]
    profile_sections: dict[str, str]
    tailored_profile_sections: dict[str, str]
    jd_analysis: dict[str, Any]
    job_research: dict[str, Any]
    requirement_matches: list[dict[str, Any]]
    overall_score: float
    dimension_scores: dict[str, Any]
    keyword_coverage: dict[str, Any]
    fact_relevance: dict[str, float]
    material_scores: dict[str, dict[str, Any]]
    experience_matrix: list[dict[str, Any]]
    selected_entries: dict[str, list[dict[str, Any]]]
    selected_fact_ids: dict[str, list[str]]
    strengths: list[str]
    gaps: list[str]
    section_name: str
    section_outputs: Annotated[list[dict[str, Any]], operator.add]
    result: dict[str, Any]
    audit_attempt: int
    audit_passed: bool
    warnings: Annotated[list[str], operator.add]
    export_dir: str
    target_version: int
    export_paths: dict[str, Any]
