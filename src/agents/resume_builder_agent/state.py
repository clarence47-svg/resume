from typing import Any, TypedDict


class ResumeBuilderState(TypedDict, total=False):
    match_result: dict[str, Any]
    job: dict[str, Any]
    career_settings: dict[str, Any]
    template: str
    document: dict[str, Any]
    audit: dict[str, Any]
    export_paths: dict[str, str]
