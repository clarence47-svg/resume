from typing import Any, TypedDict


class InterviewAgentState(TypedDict, total=False):
    job: dict[str, Any]
    resume: dict[str, Any]
    result: dict[str, Any]
