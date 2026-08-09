from typing import Any, TypedDict


class JobDiscoveryAgentState(TypedDict, total=False):
    campaign: dict[str, Any]
    collected_jobs: list[dict[str, Any]]
    normalized_jobs: list[dict[str, Any]]
    filtered_jobs: list[dict[str, Any]]
    evaluations: list[dict[str, Any]]
    shortlist: list[dict[str, Any]]
    result: dict[str, Any]
