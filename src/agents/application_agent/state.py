from typing import Any, TypedDict


class ApplicationAgentState(TypedDict, total=False):
    application_id: str
    preview: dict[str, Any]
    preview_hash: str
    confirmed: bool
    blockers: list[str]
    submitted: bool
    evidence: dict[str, Any]
